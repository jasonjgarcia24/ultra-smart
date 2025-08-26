#!/usr/bin/env python3
"""
Strava API Setup Helper

This script helps you set up Strava API access for the ultra-smart project.
"""

import os
import webbrowser
from urllib.parse import parse_qs, urlparse

def setup_strava_access():
    print("=== Strava API Setup ===")
    print()
    
    print("Step 1: Create a Strava Application")
    print("1. Go to https://www.strava.com/settings/api")
    print("2. Click 'Create App'")
    print("3. Fill in your application details:")
    print("   - Application Name: ultra-smart")
    print("   - Category: Data Importer")
    print("   - Club: (leave blank)")
    print("   - Website: http://localhost")
    print("   - Authorization Callback Domain: localhost")
    print("4. Click 'Create'")
    print()
    
    input("Press Enter after creating your Strava application...")
    
    print("Step 2: Get your Client ID and Client Secret")
    client_id = input("Enter your Client ID: ").strip()
    client_secret = input("Enter your Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("Error: Client ID and Client Secret are required!")
        return
    
    print()
    print("Step 3: Authorize the application")
    
    # Generate authorization URL
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri=http://localhost"
        f"&response_type=code"
        f"&scope=read,activity:read_all"
    )
    
    print(f"Opening authorization URL: {auth_url}")
    webbrowser.open(auth_url)
    
    print()
    print("After authorizing:")
    print("1. You'll be redirected to a localhost URL")
    print("2. Copy the entire URL from your browser")
    print("3. Paste it below")
    print()
    
    callback_url = input("Paste the callback URL here: ").strip()
    
    # Extract authorization code from callback URL
    try:
        parsed_url = urlparse(callback_url)
        query_params = parse_qs(parsed_url.query)
        auth_code = query_params.get('code', [None])[0]
        
        if not auth_code:
            print("Error: No authorization code found in URL!")
            return
            
    except Exception as e:
        print(f"Error parsing callback URL: {e}")
        return
    
    print()
    print("Step 4: Exchange code for access token")
    print("Run the following curl command to get your access token:")
    print()
    print(f"curl -X POST https://www.strava.com/oauth/token \\")
    print(f"  -d client_id={client_id} \\")
    print(f"  -d client_secret={client_secret} \\")
    print(f"  -d code={auth_code} \\")
    print(f"  -d grant_type=authorization_code")
    print()
    print("Copy the 'access_token' from the response and set it as an environment variable:")
    print("export STRAVA_ACCESS_TOKEN='your_access_token_here'")
    print()
    print("Then you can run the example with Strava integration!")

if __name__ == "__main__":
    setup_strava_access()