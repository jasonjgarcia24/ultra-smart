#!/usr/bin/env python3

import os
import sys

print("=== Strava Debug ===")
print(f"Python path: {sys.path}")

# Check environment variable
token = os.getenv('STRAVA_ACCESS_TOKEN')
print(f"Token exists: {bool(token)}")
if token:
    print(f"Token length: {len(token)}")
    print(f"Token preview: {token[:10]}...")

# Check stravalib import
try:
    from stravalib.client import Client
    print("stravalib: Available")
    STRAVA_AVAILABLE = True
except ImportError as e:
    print(f"stravalib: NOT AVAILABLE ({e})")
    STRAVA_AVAILABLE = False

# Test SplitReader initialization
try:
    from ultra_smart import SplitReader
    print("ultra_smart import: Success")
    
    reader = SplitReader(strava_access_token=token)
    print(f"SplitReader created: {reader}")
    print(f"Strava client: {reader.strava_client}")
    
    if reader.strava_client:
        print("Strava client initialized successfully!")
    else:
        print("ERROR: Strava client is None")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()