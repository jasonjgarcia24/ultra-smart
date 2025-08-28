#!/usr/bin/env python3
"""
Update aid_stations table with complete Cocodona 250 data from CSV
"""
import sqlite3
import csv
import pandas as pd
from datetime import datetime

def update_aid_stations_table():
    # Connect to database
    conn = sqlite3.connect('/home/jasongarcia24/Documents/ultra-smart/data/ultra_smart.db')
    cursor = conn.cursor()
    
    # First, let's add the missing columns to the existing table
    try:
        # Add pacer_access column
        cursor.execute('ALTER TABLE aid_stations ADD COLUMN pacer_access BOOLEAN DEFAULT 0')
        print("Added pacer_access column")
    except sqlite3.OperationalError:
        print("pacer_access column already exists or other error")
    
    try:
        # Add gear_check column
        cursor.execute('ALTER TABLE aid_stations ADD COLUMN gear_check TEXT')
        print("Added gear_check column")
    except sqlite3.OperationalError:
        print("gear_check column already exists or other error")
    
    try:
        # Add has_medic column
        cursor.execute('ALTER TABLE aid_stations ADD COLUMN has_medic BOOLEAN DEFAULT 0')
        print("Added has_medic column")
    except sqlite3.OperationalError:
        print("has_medic column already exists or other error")
    
    try:
        # Add cutoff_datetime column
        cursor.execute('ALTER TABLE aid_stations ADD COLUMN cutoff_datetime TEXT')
        print("Added cutoff_datetime column")
    except sqlite3.OperationalError:
        print("cutoff_datetime column already exists or other error")
    
    # Clear existing Cocodona data (assuming race_id = 1 is Cocodona)
    cursor.execute('DELETE FROM aid_stations WHERE race_id = 1')
    print("Cleared existing Cocodona aid station data")
    
    # Read the CSV file
    csv_path = '/home/jasongarcia24/Documents/ultra-smart/data/cocodona_250_aid_stations_complete.csv'
    
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            # Parse the data
            name = row['name']
            distance_miles = float(row['distance_miles'])
            cutoff_time = row['cutoff_time']
            crew_access = 1 if row['crew_access'].lower() == 'yes' else 0
            pacer_access = 1 if row['pacer_access'].lower() == 'yes' else 0
            drop_bags = 1 if row['drop_bags'].lower() == 'yes' else 0
            gear_check = row['gear_check']
            sleep_station = 1 if row['sleep_station'].lower() == 'yes' else 0
            has_medic = 1 if row['has_medic'].lower() == 'yes' else 0
            cutoff_datetime = row['cutoff_datetime'] if row['cutoff_datetime'] != 'N/A' else None
            
            # Determine station type based on features
            # Valid types: 'aid', 'crew', 'drop_bag', 'crew_aid', 'major_aid'
            if crew_access and sleep_station:
                station_type = 'major_aid'
            elif crew_access:
                station_type = 'crew_aid'
            elif drop_bags and not crew_access:
                station_type = 'drop_bag'
            else:
                station_type = 'aid'
            
            # Build services array based on features
            services = []
            if crew_access:
                services.append('crew_support')
            if pacer_access:
                services.append('pacer_support')
            if drop_bags:
                services.append('drop_bags')
            if gear_check and gear_check != 'No':
                services.append('gear_check')
            if sleep_station:
                services.append('sleep_station')
            if has_medic:
                services.append('medical')
            if 'Water Station' not in name:
                services.extend(['water', 'electrolytes', 'food'])
            else:
                services.append('water')
            
            services_json = str(services).replace("'", '"')
            
            # Convert cutoff time to hours from start (rough estimate)
            cutoff_hours = 0.0
            if cutoff_datetime and cutoff_datetime != 'N/A':
                try:
                    # Parse the datetime and calculate hours from race start (5/5/25 5:00 AM)
                    race_start = datetime(2025, 5, 5, 5, 0, 0)
                    cutoff_dt = datetime.strptime(cutoff_datetime, '%Y-%m-%d %H:%M:%S')
                    cutoff_hours = (cutoff_dt - race_start).total_seconds() / 3600
                except:
                    cutoff_hours = distance_miles * 2.5  # rough estimate
            
            # Insert into database
            cursor.execute('''
                INSERT INTO aid_stations (
                    race_id, name, distance_miles, elevation_feet, station_type, services,
                    crew_access, drop_bag_access, cutoff_time_hours, notes, sleep_station,
                    pacer_access, gear_check, has_medic, cutoff_datetime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                1,  # race_id (Cocodona)
                name,
                distance_miles,
                None,  # elevation_feet - we don't have this data
                station_type,
                services_json,
                crew_access,
                drop_bags,
                cutoff_hours,
                f"Cutoff: {cutoff_time}" if cutoff_time != 'N/A' else '',
                sleep_station,
                pacer_access,
                gear_check,
                has_medic,
                cutoff_datetime
            ))
            
            print(f"Inserted: {name} at mile {distance_miles}")
    
    # Commit changes
    conn.commit()
    
    # Verify the update
    print("\nVerification - First 5 aid stations:")
    cursor.execute('SELECT name, distance_miles, crew_access, pacer_access, sleep_station, has_medic FROM aid_stations WHERE race_id = 1 ORDER BY distance_miles LIMIT 5')
    for row in cursor.fetchall():
        print(row)
    
    print(f"\nTotal aid stations inserted: {cursor.rowcount}")
    
    conn.close()
    print("Aid stations table updated successfully!")

if __name__ == "__main__":
    update_aid_stations_table()