#!/usr/bin/env python3

import os
import ipdb
from stravalib.client import Client

def test_strava_token():
    # Get token from environment
    token = os.getenv('STRAVA_ACCESS_TOKEN')
    
    if not token:
        print("Error: STRAVA_ACCESS_TOKEN not set")
        return
    
    try:
        # Test basic connection
        client = Client(access_token=token)
        athlete = client.get_athlete()
        ipdb.set_trace()
        print(f"✓ Connected as: {athlete.firstname} {athlete.lastname}")
        
        # Test activity access
        activity_id = 14410958788
        print(f"\nTesting access to activity {activity_id}...")
        
        activity = client.get_activity(activity_id)
        print(f"✓ Activity found: {activity.name}")
        print(f"✓ Athlete: {activity.athlete}")
        print(f"✓ Distance: {activity.distance}")
        print(f"✓ Elapsed time: {activity.elapsed_time}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nPossible solutions:")
        print("1. Activity might be private")
        print("2. Token might be expired (get new one from https://www.strava.com/settings/api)")
        print("3. Activity ID might not exist")

if __name__ == "__main__":
    test_strava_token()