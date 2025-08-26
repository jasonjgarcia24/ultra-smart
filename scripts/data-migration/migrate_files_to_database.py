#!/usr/bin/env python3

import json
import pandas as pd
import glob
import os
from database import UltraSmartDatabase

def parse_time_to_seconds(time_str):
    """Parse time string to seconds."""
    if pd.isna(time_str) or not time_str:
        return None
    try:
        parts = str(time_str).split(':')
        if len(parts) == 2:  # MM:SS
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:  # HH:MM:SS
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except (ValueError, TypeError):
        return None
    return None

def migrate_existing_data():
    """Migrate all existing JSON profiles and CSV splits to database."""
    db = UltraSmartDatabase()
    
    print("🔄 Starting migration of existing data files to database...")
    print("=" * 60)
    
    # Find all profile files
    profile_files = glob.glob('./data/*_profile.json')
    
    migrated_count = 0
    splits_count = 0
    
    for profile_file in profile_files:
        try:
            print(f"\n📁 Processing: {profile_file}")
            
            # Load JSON profile
            with open(profile_file, 'r') as f:
                profile_data = json.load(f)
            
            first_name = profile_data['first_name']
            last_name = profile_data['last_name']
            
            print(f"👤 Found athlete: {first_name} {last_name}")
            
            # Find corresponding CSV file
            name_part = os.path.basename(profile_file).replace('_profile.json', '')
            csv_files = glob.glob(f'./data/{name_part}_*_strava_splits_complete.csv')
            
            if not csv_files:
                print(f"⚠️  No CSV file found for {first_name} {last_name}")
                continue
            
            csv_file = csv_files[0]
            print(f"📊 Found splits file: {csv_file}")
            
            # Parse race info from filename
            filename = os.path.basename(csv_file)
            parts = filename.replace('_strava_splits_complete.csv', '').split('_')
            
            # Extract race name and year
            race_parts = []
            year = None
            for part in parts[2:]:  # Skip first_name and last_name
                if part.isdigit() and len(part) == 4:
                    year = int(part)
                    break
                race_parts.append(part)
            
            race_name = ' '.join(race_parts).title()
            if not year:
                year = 2025  # Default
            
            print(f"🏁 Race: {race_name} {year}")
            
            # Get or create race
            race_id = db.get_race_id(race_name, year)
            if not race_id:
                # Create the race if it doesn't exist
                race_id = db.add_race(
                    name=race_name,
                    year=year,
                    location="Black Canyon City to Flagstaff, AZ",  # Default for Cocodona
                    distance_miles=256,
                    elevation_gain_feet=40000,
                    elevation_loss_feet=35000,
                    time_limit_hours=125
                )
                print(f"✅ Created race: {race_name} {year}")
            
            # Check if runner already exists in database
            existing_runner_id = db.find_runner(
                first_name=first_name, 
                last_name=last_name,
                age=profile_data.get('age')
            )
            
            if existing_runner_id:
                runner_id = existing_runner_id
                print(f"✅ Found existing runner in database (ID: {runner_id})")
            else:
                # Create new runner
                runner_id = db.add_runner(
                    first_name=first_name,
                    last_name=last_name,
                    age=profile_data.get('age'),
                    gender=profile_data.get('gender'),
                    city=profile_data.get('city'),
                    state=profile_data.get('state'),
                    country=profile_data.get('country', 'USA')
                )
                print(f"✅ Created new runner (ID: {runner_id})")
            
            # Add runner profile data
            profile_id = db.add_runner_profile(
                runner_id=runner_id,
                bio=f"Ultra runner from {profile_data.get('city', '')}, {profile_data.get('state', '')}"
            )
            print(f"✅ Added runner profile (ID: {profile_id})")
            
            # Load and process CSV data
            print("📈 Processing splits data...")
            df = pd.read_csv(csv_file)
            print(f"   Found {len(df)} mile splits")
            
            # Check if race result exists
            race_result_id = db.get_race_result_id(race_id, runner_id)
            if not race_result_id:
                # Calculate finish time from last cumulative time
                last_split = df.iloc[-1]
                finish_time_seconds = parse_time_to_seconds(last_split.get('cumulative_time', '0:00'))
                finish_time_hours = finish_time_seconds / 3600 if finish_time_seconds else None
                
                # Add race result
                race_result_id = db.add_race_result(
                    race_id=race_id,
                    runner_id=runner_id,
                    finish_time_hours=finish_time_hours,
                    splits_available=True
                )
                print(f"✅ Created race result (ID: {race_result_id})")
            else:
                # Update existing race result to mark splits as available
                db.update_splits_availability(race_result_id, True)
                print(f"✅ Updated existing race result (ID: {race_result_id})")
            
            # Process each split
            splits_data = []
            for index, row in df.iterrows():
                mile_number = int(row.get('distance_miles', index + 1))
                
                split_data = {
                    'mile_number': mile_number,
                    'distance_miles': float(row.get('distance_miles', mile_number)),
                    'split_time_seconds': parse_time_to_seconds(row.get('split_time', '')),
                    'pace_seconds': parse_time_to_seconds(row.get('pace', '')),
                    'cumulative_time_seconds': parse_time_to_seconds(row.get('cumulative_time', '')),
                    'elevation_feet': float(row.get('elevation', 0)) if pd.notna(row.get('elevation')) else None,
                    'temperature_f': float(row.get('temperature', 0)) if pd.notna(row.get('temperature')) else None,
                    'notes': str(row.get('notes', '')) if pd.notna(row.get('notes')) else None
                }
                splits_data.append(split_data)
            
            # Add all splits to database
            added_splits = db.add_splits_data(race_result_id, splits_data)
            splits_count += added_splits
            print(f"✅ Added {added_splits} splits to database")
            
            migrated_count += 1
            print(f"🎉 Successfully migrated {first_name} {last_name}!")
            
        except Exception as e:
            print(f"❌ Error processing {profile_file}: {e}")
            continue
    
    print("\n" + "=" * 60)
    print(f"🏆 Migration Complete!")
    print(f"   Athletes migrated: {migrated_count}")
    print(f"   Total splits imported: {splits_count}")
    print(f"   Average splits per athlete: {splits_count / migrated_count if migrated_count > 0 else 0:.1f}")
    
    # Print summary of what's now in the database
    print("\n📊 Database Summary:")
    races = db.get_races()
    for race in races:
        runners = db.get_race_runners(race['id'])
        splits_count_race = sum([1 for r in runners if r['splits_available']])
        print(f"   {race['name']} {race['year']}: {len(runners)} runners, {splits_count_race} with detailed splits")
    
    # Test a few database queries to verify migration
    print("\n🧪 Testing database queries...")
    test_runner = db.search_runners(1, "Dan Green")  # Assuming Cocodona is race_id 1
    if test_runner:
        print(f"   ✅ Search test: Found {len(test_runner)} results for 'Dan Green'")
        runner = test_runner[0]
        
        # Test splits data
        race_result_id = db.get_race_result_id(1, runner['runner_id'])
        if race_result_id:
            splits_df = db.get_splits_as_dataframe(race_result_id)
            if splits_df is not None:
                print(f"   ✅ Splits test: Retrieved {len(splits_df)} splits for {runner['first_name']} {runner['last_name']}")
            else:
                print(f"   ❌ Splits test: No splits data found")
    
    print("\n🚀 Ready to use database-only approach!")
    return migrated_count, splits_count

if __name__ == "__main__":
    migrate_existing_data()