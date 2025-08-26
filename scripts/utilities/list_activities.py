#!/usr/bin/env python3

import os
from stravalib.client import Client

def list_my_activities():
    token = os.getenv('STRAVA_ACCESS_TOKEN')
    
    if not token:
        print("Error: STRAVA_ACCESS_TOKEN not set")
        return
    
    try:
        client = Client(access_token=token)
        athlete = client.get_athlete()
        print(f"Connected as: {athlete.firstname} {athlete.lastname}")
        
        print("\nYour recent activities:")
        print("-" * 60)
        
        activities = client.get_activities(limit=10)
        
        for i, activity in enumerate(activities, 1):
            distance_miles = float(activity.distance) * 0.000621371 if activity.distance else 0
            print(f"{i}. ID: {activity.id}")
            print(f"   Name: {activity.name}")
            print(f"   Type: {activity.type}")
            print(f"   Distance: {distance_miles:.1f} miles")
            print(f"   Date: {activity.start_date}")
            print()
            
        print("Copy an activity ID to use in example.py")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_my_activities()