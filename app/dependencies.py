import os
import json
import logging
from dotenv import load_dotenv
from typing import Optional, Dict, Any

from fastapi import Header, HTTPException, Depends
from firebase_admin import credentials, initialize_app, get_app, _apps, auth, firestore as admin_firestore
from google.cloud import secretmanager
from google.api_core import exceptions as gapi_exceptions
load_dotenv()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


SERVICE_ACCOUNT_SECRET = os.getenv("SERVICE_ACCOUNT_SECRET")  # e.g. projects/PROJECT_ID/secrets/SA_KEY/versions/latest
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")  # local path (dev)
PROJECT_ID = os.getenv("PROJECT_ID")  # optional, used if you want to build secret name
DATABASE = os.getenv("DATABASE", "default")  # optional, used if you want to build secret name

def _access_secret_from_sm(resource_name: str) -> Optional[str]:
    """
    Given a full Secret Manager resource name (projects/.../secrets/.../versions/...),
    retrieve the secret payload (string).
    """
    try:
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": resource_name})
        payload = response.payload.data.decode("UTF-8")
        return payload
    except gapi_exceptions.GoogleAPIError as e:
        logger.exception("Unable to access secret %s: %s", resource_name, e)
        raise


def _init_firebase_from_service_account_dict(sa_dict: Dict[str, Any]):
    """
    Initialize firebase_admin using a service account dict.
    Idempotent: if already initialized, returns existing app.
    """
    if _apps:
        # already initialized
        try:
            return get_app()
        except Exception:
            pass

    cred = credentials.Certificate(sa_dict)
    app = initialize_app(cred)
    logger.info("Initialized firebase_admin with service account credential")
    return app


def _init_firebase_from_path(path: str):
    """
    Initialize firebase_admin from a local service account JSON file path.
    """
    if _apps:
        try:
            return get_app()
        except Exception:
            pass

    cred = credentials.Certificate(path)
    app = initialize_app(cred)
    logger.info("Initialized firebase_admin with service account path: %s", path)
    return app


def _init_firebase_adc():
    """
    Initialize firebase_admin with Application Default Credentials (ADC).
    Works on Cloud Run when the service account is attached.
    """
    if _apps:
        try:
            return get_app()
        except Exception:
            pass

    # No explicit credentials -> uses ADC
    app = initialize_app()
    logger.info("Initialized firebase_admin with Application Default Credentials (ADC)")
    return app


def init_firebase_admin():
    """
    Initialize firebase_admin and return Firestore client.
    Order of preference:
      1) SERVICE_ACCOUNT_SECRET env var -> fetch JSON from Secret Manager
      2) GOOGLE_APPLICATION_CREDENTIALS env var -> local file path (dev)
      3) ADC (Cloud Run) -> initialize_app() without args

    Returns:
        firestore.Client instance
    """
    # If already initialized, return the Firestore client
    if _apps:
        try:
            # firebase_admin.firestore.client returns the same underlying client
            return admin_firestore.client()
        except Exception:
            pass

    # 1) Secret Manager
    if SERVICE_ACCOUNT_SECRET:
        secret_res_name = SERVICE_ACCOUNT_SECRET
        # support shorthand secret ID (e.g., "SA_KEY") by turning it into a resource name if project id provided
        if not secret_res_name.startswith("projects/") and PROJECT_ID:
            secret_res_name = f"projects/{PROJECT_ID}/secrets/{SERVICE_ACCOUNT_SECRET}/versions/latest"
        logger.info("Loading service account from Secret Manager: %s", secret_res_name)
        secret_payload = _access_secret_from_sm(secret_res_name)
        sa_dict = json.loads(secret_payload)
        _init_firebase_from_service_account_dict(sa_dict)
        return admin_firestore.client(database_id=DATABASE)

    # 2) GOOGLE_APPLICATION_CREDENTIALS (local dev)
    if GOOGLE_APPLICATION_CREDENTIALS and os.path.exists(GOOGLE_APPLICATION_CREDENTIALS):
        logger.info("Loading service account from path: %s", GOOGLE_APPLICATION_CREDENTIALS)
        _init_firebase_from_path(GOOGLE_APPLICATION_CREDENTIALS)
        return admin_firestore.client(database_id=DATABASE)

    # 3) ADC (Cloud Run)
    logger.info("No explicit service account provided, attempting Application Default Credentials (ADC)")
    _init_firebase_adc()
    return admin_firestore.client()


# Lazily initialize a single global Firestore client to reuse across requests
_db_client = None


def get_firestore_client():
    global _db_client
    if _db_client is None:
        _db_client = init_firebase_admin()
    return _db_client


# ---------------------------
# FastAPI dependencies
# ---------------------------
def _extract_bearer_token(authorization_header: Optional[str]) -> str:
    if not authorization_header:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    parts = authorization_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    return parts[1]


def verify_id_token(token: str):
    """
    Verify Firebase ID token and return decoded token dict (contains uid, claims).
    Raises HTTPException(401) on failure.
    """
    try:
        decoded = auth.verify_id_token(token)
        return decoded
    except Exception as e:
        logger.exception("Invalid Firebase ID token: %s", e)
        raise HTTPException(status_code=401, detail="Invalid or expired ID token")


async def verify_id_token_dependency(authorization: Optional[str] = Header(None)):
    """
    FastAPI dependency that checks Authorization header and verifies the ID token.
    Returns decoded token (a dict). Use it as:
        @router.post(..., dependencies=[Depends(verify_id_token_dependency)])
    or as a parameter:
        def endpoint(decoded_token = Depends(verify_id_token_dependency)):
            uid = decoded_token["uid"]
    """
    token = _extract_bearer_token(authorization)
    decoded = verify_id_token(token)
    return decoded


def get_current_uid(decoded_token: Dict[str, Any]):
    """
    Helper to extract uid from decoded token.
    """
    return decoded_token.get("uid")
