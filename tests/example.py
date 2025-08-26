#!/usr/bin/env python3

import os
from ultra_smart import SplitReader

def main():
    # Example 1: Read from Strava activity (Dan Green's Cocodona 250)
    print("Example 1: Reading from Strava activity")
    print("-" * 40)
    
    # Get Strava access token from environment variable
    strava_token = os.getenv('STRAVA_ACCESS_TOKEN')
    
    if strava_token:
        # Initialize reader with Strava access token
        reader = SplitReader(strava_access_token=strava_token)
        
        # Dan Green's Cocodona 250 activity ID: 14410958788
        athlete = reader.read_from_strava_activity(14410958788)
        
        if athlete:
            print(f"Loaded athlete: {athlete.name}")
            print(f"Finish time: {athlete.finish_time}")
            print(f"Status: {athlete.status}")
            print(f"Number of splits: {len(athlete.splits)}")
            
            # Show first few splits
            for split in athlete.splits[:5]:
                print(f"  {split.checkpoint_name}: {split.elapsed_time} ({split.distance_miles} miles)")
            
            # Export to CSV
            reader.export_to_csv([athlete], "dan_green_cocodona.csv")
            print("\nExported to dan_green_cocodona.csv")
        else:
            print("Failed to load athlete data from Strava")
    else:
        print("No Strava access token found.")
        print("Set STRAVA_ACCESS_TOKEN environment variable or follow these steps:")
        print("1. Go to https://www.strava.com/settings/api")
        print("2. Create an application")
        print("3. Get your access token")
        print("4. Run: export STRAVA_ACCESS_TOKEN='your_token_here'")
    
    # Example 2: Read from CSV file
    print("\nExample 2: Reading from CSV file")
    print("-" * 40)
    
    # Initialize regular reader
    reader = SplitReader()
    
    # Uncomment and modify the path to your actual CSV file
    # athletes = reader.read_from_csv("path/to/cocodona_results.csv")
    # 
    # if athletes:
    #     print(f"Loaded {len(athletes)} athletes")
    #     for athlete in athletes[:3]:  # Show first 3 athletes
    #         print(f"Bib #{athlete.bib_number}: {athlete.name}")
    #         if athlete.splits:
    #             print(f"  Has {len(athlete.splits)} checkpoint splits")
    #         print()
    
    # Example 3: Read from URL
    print("Example 3: Reading from URL")
    print("-" * 40)
    
    # Uncomment and modify URL to actual Cocodona results page
    # athletes = reader.read_from_url("https://example.com/cocodona-results")
    # 
    # if athletes:
    #     print(f"Loaded {len(athletes)} athletes from URL")
    
    # Example 4: Create sample data and export
    print("Example 4: Creating sample data")
    print("-" * 40)
    
    from ultra_smart.models import Athlete, Split
    
    # Create a sample athlete
    sample_athlete = Athlete(
        bib_number=123,
        name="John Runner",
        age=35,
        gender="M",
        city="Phoenix",
        state="AZ",
        overall_rank=42,
        status="Finished"
    )
    
    # Add some sample splits
    sample_athlete.add_split(Split(
        checkpoint_name="McDowell Mountain",
        distance_miles=15.4,
        elapsed_time="02:30:15"
    ))
    
    sample_athlete.add_split(Split(
        checkpoint_name="Tortilla Flat",
        distance_miles=42.8,
        elapsed_time="07:45:30"
    ))
    
    print(f"Created sample athlete: {sample_athlete.name}")
    print(f"Number of splits: {len(sample_athlete.splits)}")
    
    # Export to CSV
    reader.export_to_csv([sample_athlete], "sample_results.csv")
    print("Exported sample data to sample_results.csv")

if __name__ == "__main__":
    main()