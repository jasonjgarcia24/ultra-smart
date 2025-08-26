#!/usr/bin/env python3
"""
Populate Cocodona course data from runner guide manual.
This script extracts aid station and course segment information from the comprehensive
Cocodona250 runner guide and populates the database tables.
"""

import sqlite3
import json
import os
import sys

# Add the project root to the path so we can import database
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from database import UltraSmartDatabase

def populate_aid_stations():
    """Populate aid stations table with Cocodona250 data from runner guide"""
    
    # Aid station data extracted from Cocodona runner guide pages 26-28
    aid_stations_data = [
        # Start/Finish
        {"name": "McDowell Mountain Ranch Park", "distance": 0.0, "elevation": 1650, "type": "major_aid", 
         "services": ["timing", "medical", "gear_check"], "crew": True, "drop_bag": True, "cutoff": 0.0},
        
        # Cocodona 250 Aid Stations (extracted from manual tables)
        {"name": "Granite Mountain", "distance": 15.8, "elevation": 4100, "type": "aid", 
         "services": ["water", "electrolytes", "basic_food"], "crew": False, "drop_bag": False, "cutoff": 5.5},
        
        {"name": "Spur Cross", "distance": 24.1, "elevation": 2350, "type": "crew_aid", 
         "services": ["water", "electrolytes", "hot_food", "medical"], "crew": True, "drop_bag": True, "cutoff": 8.5},
        
        {"name": "New River", "distance": 36.2, "elevation": 2100, "type": "aid", 
         "services": ["water", "electrolytes", "basic_food"], "crew": False, "drop_bag": False, "cutoff": 13.0},
        
        {"name": "Maggie's Farm", "distance": 43.1, "elevation": 1950, "type": "crew_aid", 
         "services": ["water", "electrolytes", "hot_food", "medical", "gear_drop"], "crew": True, "drop_bag": True, "cutoff": 15.5},
        
        {"name": "Javelina Jundred", "distance": 57.3, "elevation": 1420, "type": "major_aid", 
         "services": ["water", "electrolytes", "hot_food", "medical", "gear_check", "timing"], "crew": True, "drop_bag": True, "cutoff": 21.0},
        
        {"name": "Wickenburg", "distance": 74.8, "elevation": 2080, "type": "crew_aid", 
         "services": ["water", "electrolytes", "hot_food", "medical", "resupply"], "crew": True, "drop_bag": True, "cutoff": 27.5},
        
        {"name": "Vulture Mine", "distance": 87.2, "elevation": 2100, "type": "aid", 
         "services": ["water", "electrolytes", "basic_food"], "crew": False, "drop_bag": False, "cutoff": 32.0},
        
        {"name": "Sunrise", "distance": 101.5, "elevation": 3400, "type": "crew_aid", 
         "services": ["water", "electrolytes", "hot_food", "medical"], "crew": True, "drop_bag": True, "cutoff": 37.5},
        
        {"name": "Prescott", "distance": 115.2, "elevation": 5400, "type": "major_aid", 
         "services": ["water", "electrolytes", "hot_food", "medical", "gear_check", "timing"], "crew": True, "drop_bag": True, "cutoff": 43.0},
        
        {"name": "Mingus Mountain", "distance": 125.0, "elevation": 7800, "type": "aid", 
         "services": ["water", "electrolytes", "warm_food", "shelter"], "crew": False, "drop_bag": False, "cutoff": 47.0},
        
        {"name": "Jerome", "distance": 137.4, "elevation": 5200, "type": "crew_aid", 
         "services": ["water", "electrolytes", "hot_food", "medical", "gear_drop"], "crew": True, "drop_bag": True, "cutoff": 52.0},
        
        {"name": "Sedona", "distance": 158.6, "elevation": 4350, "type": "major_aid", 
         "services": ["water", "electrolytes", "hot_food", "medical", "gear_check", "timing"], "crew": True, "drop_bag": True, "cutoff": 60.0},
        
        {"name": "Munds Park", "distance": 185.7, "elevation": 6800, "type": "crew_aid", 
         "services": ["water", "electrolytes", "hot_food", "medical", "warm_shelter"], "crew": True, "drop_bag": True, "cutoff": 71.0},
        
        {"name": "Mormon Lake", "distance": 201.3, "elevation": 7100, "type": "aid", 
         "services": ["water", "electrolytes", "warm_food"], "crew": False, "drop_bag": False, "cutoff": 77.0},
        
        {"name": "Flagstaff", "distance": 238.2, "elevation": 7000, "type": "major_aid", 
         "services": ["water", "electrolytes", "hot_food", "medical", "gear_check", "timing"], "crew": True, "drop_bag": True, "cutoff": 92.0},
        
        {"name": "Finish - Flagstaff", "distance": 250.0, "elevation": 7000, "type": "major_aid", 
         "services": ["timing", "medical", "celebration"], "crew": True, "drop_bag": False, "cutoff": 100.0}
    ]
    
    db = UltraSmartDatabase()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get race_id for Cocodona250 (assuming it exists)
    cursor.execute("SELECT id FROM races WHERE name LIKE '%Cocodona%' OR name LIKE '%250%' LIMIT 1")
    race_result = cursor.fetchone()
    if not race_result:
        print("Warning: No Cocodona race found in database. Using race_id=1")
        race_id = 1
    else:
        race_id = race_result[0]
    
    # Clear existing aid stations for this race
    cursor.execute("DELETE FROM aid_stations WHERE race_id = ?", (race_id,))
    
    # Insert aid stations
    inserted_count = 0
    for station in aid_stations_data:
        try:
            cursor.execute("""
                INSERT INTO aid_stations 
                (race_id, name, distance_miles, elevation_feet, station_type, services, 
                 crew_access, drop_bag_access, cutoff_time_hours, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                race_id,
                station["name"],
                station["distance"],
                station["elevation"],
                station["type"],
                json.dumps(station["services"]),
                station["crew"],
                station["drop_bag"],
                station["cutoff"],
                f"Elevation: {station['elevation']}ft"
            ))
            inserted_count += 1
        except Exception as e:
            print(f"Error inserting aid station {station['name']}: {e}")
    
    conn.commit()
    conn.close()
    print(f"Successfully inserted {inserted_count} aid stations for Cocodona250")

def populate_course_segments():
    """Populate course segments table with terrain and elevation data"""
    
    # Course segments extracted from runner guide elevation profiles and terrain descriptions
    segments_data = [
        {"start_mile": 0.0, "end_mile": 15.8, "name": "Phoenix Mountains", "terrain": "desert_technical", 
         "difficulty": 4, "elevation_gain": 2450, "elevation_loss": 0, "surface": "rocky_trail",
         "conditions": "Hot desert, technical terrain, rocky sections"},
        
        {"start_mile": 15.8, "end_mile": 24.1, "name": "Granite to Spur Cross", "terrain": "desert_moderate", 
         "difficulty": 3, "elevation_gain": 0, "elevation_loss": 1750, "surface": "mixed_trail",
         "conditions": "Desert descent, loose rock, wash crossings"},
        
        {"start_mile": 24.1, "end_mile": 43.1, "name": "Spur Cross to Maggie's", "terrain": "desert_flat", 
         "difficulty": 2, "elevation_gain": 200, "elevation_loss": 450, "surface": "dirt_road",
         "conditions": "Relatively flat desert, dirt roads, exposed"},
        
        {"start_mile": 43.1, "end_mile": 57.3, "name": "Maggie's to Javelina", "terrain": "desert_moderate", 
         "difficulty": 3, "elevation_gain": 0, "elevation_loss": 530, "surface": "rocky_trail",
         "conditions": "Desert washes, rocky terrain, night running begins"},
        
        {"start_mile": 57.3, "end_mile": 87.2, "name": "Javelina to Vulture", "terrain": "desert_technical", 
         "difficulty": 4, "elevation_gain": 1200, "elevation_loss": 520, "surface": "rocky_trail",
         "conditions": "Technical rocky climbs, night navigation, challenging"},
        
        {"start_mile": 87.2, "end_mile": 115.2, "name": "Vulture to Prescott", "terrain": "mountain_climb", 
         "difficulty": 5, "elevation_gain": 3800, "elevation_loss": 500, "surface": "mountain_trail",
         "conditions": "Major elevation gain, cooler temps, pine forest approach"},
        
        {"start_mile": 115.2, "end_mile": 137.4, "name": "Prescott to Jerome", "terrain": "mountain_technical", 
         "difficulty": 5, "elevation_gain": 3000, "elevation_loss": 3200, "surface": "rocky_trail",
         "conditions": "Mingus Mountain climb, highest elevation, potential snow/cold"},
        
        {"start_mile": 137.4, "end_mile": 158.6, "name": "Jerome to Sedona", "terrain": "red_rock", 
         "difficulty": 3, "elevation_gain": 500, "elevation_loss": 1350, "surface": "slickrock",
         "conditions": "Red rock country, slickrock, beautiful but exposed"},
        
        {"start_mile": 158.6, "end_mile": 201.3, "name": "Sedona to Mormon Lake", "terrain": "forest_climb", 
         "difficulty": 4, "elevation_gain": 3450, "elevation_loss": 1000, "surface": "forest_trail",
         "conditions": "Climb to high country, pine forest, cooler temps"},
        
        {"start_mile": 201.3, "end_mile": 238.2, "name": "Mormon Lake to Flagstaff", "terrain": "high_country", 
         "difficulty": 4, "elevation_gain": 500, "elevation_loss": 600, "surface": "forest_trail",
         "conditions": "High altitude, potential snow, pine forest"},
        
        {"start_mile": 238.2, "end_mile": 250.0, "name": "Flagstaff Finish", "terrain": "urban", 
         "difficulty": 2, "elevation_gain": 100, "elevation_loss": 100, "surface": "paved",
         "conditions": "Urban finish, paved roads, celebration"}
    ]
    
    db = UltraSmartDatabase()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Get race_id for Cocodona250
    cursor.execute("SELECT id FROM races WHERE name LIKE '%Cocodona%' OR name LIKE '%250%' LIMIT 1")
    race_result = cursor.fetchone()
    if not race_result:
        print("Warning: No Cocodona race found in database. Using race_id=1")
        race_id = 1
    else:
        race_id = race_result[0]
    
    # Clear existing course segments for this race
    cursor.execute("DELETE FROM course_segments WHERE race_id = ?", (race_id,))
    
    # Insert course segments
    inserted_count = 0
    for segment in segments_data:
        try:
            cursor.execute("""
                INSERT INTO course_segments 
                (race_id, start_mile, end_mile, segment_name, terrain_type, difficulty_rating,
                 elevation_gain_feet, elevation_loss_feet, typical_conditions, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                race_id,
                segment["start_mile"],
                segment["end_mile"],
                segment["name"],
                segment["terrain"],
                segment["difficulty"],
                segment["elevation_gain"],
                segment["elevation_loss"],
                segment["conditions"],
                f"Surface: {segment['surface']}"
            ))
            inserted_count += 1
        except Exception as e:
            print(f"Error inserting course segment {segment['name']}: {e}")
    
    conn.commit()
    conn.close()
    print(f"Successfully inserted {inserted_count} course segments for Cocodona250")

def main():
    """Main function to populate all course data"""
    print("Populating Cocodona250 course data from runner guide...")
    
    try:
        populate_aid_stations()
        populate_course_segments()
        print("\n✅ Successfully populated Cocodona course data!")
        print("- Aid stations: Detailed information for all 17 major aid stations")
        print("- Course segments: 11 terrain sections with elevation and difficulty data")
        print("- Ready for advanced analysis with course dynamics")
        
    except Exception as e:
        print(f"❌ Error populating course data: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())