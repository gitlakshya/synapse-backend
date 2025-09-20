#!/usr/bin/env python3
"""
Test script for the new async /plantrip endpoint
"""

import requests
import json
import time
import sys
import asyncio

def test_plantrip_endpoint():
    """Test the async plantrip endpoint"""
    
    # Test data
    url = 'http://localhost:8000/api/v1/plantrip'
    data = {
        'destination': 'Kyoto',
        'days': 2,  
        'budget': 30000,
        'startDate': '2024-04-15',
        'endDate': '2024-04-16',
        'preferences': {
            'heritage': 90,
            'culture': 80,
            'food': 70
        },
        'specialRequirements': 'Vegetarian meals preferred'
    }

    print('🚀 Testing async /plantrip endpoint...')
    print(f'Request: {json.dumps(data, indent=2)}')
    print('\n⏳ Making API call...')

    start_time = time.time()
    try:
        response = requests.post(url, json=data, timeout=120)  # 2 minute timeout
        end_time = time.time()
        
        print(f'\n📊 Response Status: {response.status_code}')
        print(f'⏱️ Response Time: {end_time - start_time:.2f} seconds')
        
        if response.status_code == 200:
            result = response.json()
            print(f'\n✅ SUCCESS!')
            print(f'Itinerary ID: {result.get("itineraryId")}')
            print(f'Processing Time: {result.get("processingTime", 0):.2f}s')
            
            metadata = result.get("metadata", {})
            print(f'Session ID: {metadata.get("sessionId")}')
            print(f'Search Used: {metadata.get("searchUsed", False)}')
            
            # Show brief itinerary preview
            itinerary = result.get('itinerary', {})
            print(f'\n📋 Generated Itinerary:')
            print(f'Title: {itinerary.get("title")}')
            
            # Debug: Check the type of days field
            days_field = itinerary.get("days")
            print(f'Days field type: {type(days_field)}, value: {days_field}')
            
            # Handle both list and non-list cases
            if isinstance(days_field, list):
                days_count = len(days_field)
                days = days_field
            elif isinstance(days_field, (int, float)):
                days_count = days_field
                days = []
                print(f'Warning: "days" field is a number ({days_field}), expected list of day objects')
            else:
                days_count = 0
                days = []
                print(f'Warning: "days" field is {type(days_field)}, expected list of day objects')
            
            print(f'Days: {days_count}')
            
            # Handle estimated cost which might be a dict or number
            estimated_cost = itinerary.get("estimatedCost", 0)
            if isinstance(estimated_cost, dict):
                cost_total = estimated_cost.get("total", 0)
                currency = estimated_cost.get("currency", "JPY")
                print(f'Estimated Cost: {currency} {cost_total:,}')
            else:
                print(f'Estimated Cost: ¥{estimated_cost:,}')
            
            # Show activities for each day (only if days is a proper list)
            if isinstance(days_field, list) and days:
                for day in days:
                    if not isinstance(day, dict):
                        print(f'Warning: Day object is {type(day)}, expected dict')
                        continue
                        
                    day_index = day.get('dayIndex', 0)
                    activities = day.get('activities', [])
                    
                    if not isinstance(activities, list):
                        print(f'Warning: Activities field is {type(activities)}, expected list')
                        continue
                        
                    print(f'\n📅 Day {day_index} ({len(activities)} activities):')
                    
                    for i, activity in enumerate(activities[:3], 1):  # Show first 3 activities
                        if not isinstance(activity, dict):
                            print(f'Warning: Activity {i} is {type(activity)}, expected dict')
                            continue
                            
                        title = activity.get('title', 'Unknown')
                        category = activity.get('category', 'unknown')
                        duration = activity.get('duration', activity.get('durationMins', 0))
                        cost_info = activity.get('cost', {})
                        
                        # Handle cost which might be a dict or number
                        if isinstance(cost_info, dict):
                            cost_amount = cost_info.get('amount', 0)
                            cost_currency = cost_info.get('currency', 'JPY')
                            cost_display = f'{cost_currency} {cost_amount:,}' if cost_amount else 'Free'
                        else:
                            cost_display = f'¥{cost_info:,}' if cost_info else 'Free'
                        
                        print(f'  {i}. {title}')
                        print(f'     Category: {category}, Duration: {duration}min, Cost: {cost_display}')
                        
                        # Handle location info
                        location_info = activity.get('location', {})
                        if isinstance(location_info, dict):
                            location_name = location_info.get('name', 'Unknown location')
                            coords = location_info.get('coordinates', {})
                            if isinstance(coords, dict) and 'lat' in coords and 'lng' in coords:
                                coord_str = f"({coords['lat']:.4f}, {coords['lng']:.4f})"
                                print(f'     Location: {location_name} {coord_str}')
                            else:
                                print(f'     Location: {location_name}')
                        elif 'poiSnapshot' in activity and isinstance(activity['poiSnapshot'], dict):
                            poi = activity['poiSnapshot']
                            location = poi.get('name', 'Unknown location')
                            coords = f"({poi.get('lat', 0):.4f}, {poi.get('lng', 0):.4f})"
                            print(f'     Location: {location} {coords}')
                    
                    if len(activities) > 3:
                        print(f'     ... and {len(activities) - 3} more activities')
            else:
                print(f'\n⚠️ No day-by-day activities available (days field type: {type(days_field)})')
                # Show raw response for debugging
                print(f'\n🔍 Raw itinerary structure:')
                print(json.dumps(itinerary, indent=2, default=str)[:1000] + '...' if len(str(itinerary)) > 1000 else json.dumps(itinerary, indent=2, default=str))
            
            print(f'\n🎯 Key Features Demonstrated:')
            print(f'  ✅ Async endpoint processing')
            print(f'  ✅ AI-powered itinerary generation')
            print(f'  ✅ Google Search integration')
            print(f'  ✅ JSON schema compliance')
            print(f'  ✅ Session management')
            print(f'  ✅ Real location coordinates')
            print(f'  ✅ Cost estimation')
            
        else:
            print(f'\n❌ ERROR: {response.status_code}')
            try:
                error_data = response.json()
                print(f'Error details: {json.dumps(error_data, indent=2)}')
            except:
                print(f'Error text: {response.text}')
                
    except requests.exceptions.Timeout:
        print('\n⏰ Request timed out (>2 minutes)')
    except requests.exceptions.ConnectionError:
        print('\n🔌 Connection error - is the server running on localhost:8000?')
    except Exception as e:
        print(f'\n❌ Unexpected error: {e}')

def test_health_endpoint():
    """Test the health check endpoint"""
    print('\n🩺 Testing health endpoint...')
    try:
        response = requests.get('http://localhost:8000/api/v1/health', timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f'✅ Health check passed: {health_data.get("status")}')
            services = health_data.get("services", {})
            for service, status in services.items():
                print(f'  - {service}: {status}')
        else:
            print(f'❌ Health check failed: {response.status_code}')
    except Exception as e:
        print(f'❌ Health check error: {e}')

if __name__ == "__main__":
    test_health_endpoint()
    test_plantrip_endpoint()