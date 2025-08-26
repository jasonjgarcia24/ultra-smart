#!/usr/bin/env python3

import webbrowser

def get_strava_token():
    print("=== Get Strava Token with Proper Permissions ===")
    print()
    
    # You'll need your Client ID from https://www.strava.com/settings/api
    client_id = input("Enter your Client ID from Strava API settings: ").strip()
    
    if not client_id:
        print("Error: Client ID required!")
        return
    
    # Generate authorization URL with proper scopes
    auth_url = (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={client_id}"
        f"&redirect_uri=http://localhost"
        f"&response_type=code"
        f"&scope=read,activity:read_all"
        f"&approval_prompt=force"
    )
    
    print(f"Opening: {auth_url}")
    webbrowser.open(auth_url)
    
    print()
    print("Steps:")
    print("1. Authorize the app in your browser")
    print("2. Copy the ENTIRE URL you're redirected to")
    print("3. Paste it below")
    print()
    
    callback_url = input("Paste the callback URL: ").strip()
    
    # Extract code
    if "code=" in callback_url:
        code = callback_url.split("code=")[1].split("&")[0]
        print(f"\nAuthorization code: {code}")
        print()
        print("Now run this curl command to get your access token:")
        print()
        client_secret = input("Enter your Client Secret: ").strip()
        print()
        print(f"curl -X POST https://www.strava.com/oauth/token \\")
        print(f"  -d client_id={client_id} \\")
        print(f"  -d client_secret={client_secret} \\")
        print(f"  -d code={code} \\")
        print(f"  -d grant_type=authorization_code")
        print()
        print("Copy the 'access_token' from the response and run:")
        print("export STRAVA_ACCESS_TOKEN='new_token_here'")
    else:
        print("Error: No code found in URL")

if __name__ == "__main__":
    get_strava_token()