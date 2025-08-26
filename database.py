#!/usr/bin/env python3

import sqlite3
import os
import pdb
from datetime import datetime
from typing import List, Dict, Optional

class UltraSmartDatabase:
    def __init__(self, db_path: str = './data/ultra_smart.db'):
        self.db_path = db_path
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def get_connection(self):
        """Get database connection with foreign key support."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row  # This allows dict-like access to rows
        return conn
    
    def init_database(self):
        """Initialize database with all required tables."""
        conn = self.get_connection()
        try:
            # Create races table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS races (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    date TEXT,
                    location TEXT,
                    distance_miles REAL,
                    elevation_gain_feet REAL,
                    elevation_loss_feet REAL,
                    time_limit_hours REAL,
                    course_description TEXT,
                    ultrasignup_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(name, year)
                )
            ''')
            
            # Create runners table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS runners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bib_number TEXT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    age INTEGER,
                    gender TEXT CHECK(gender IN ('M', 'F', 'X')),
                    city TEXT,
                    state TEXT,
                    country TEXT DEFAULT 'USA',
                    ultrasignup_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create race_results table (links runners to specific race performances)
            conn.execute('''
                CREATE TABLE IF NOT EXISTS race_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    race_id INTEGER NOT NULL,
                    runner_id INTEGER NOT NULL,
                    bib_number TEXT,
                    finish_time_hours REAL,
                    finish_position INTEGER,
                    gender_position INTEGER,
                    age_group_position INTEGER,
                    status TEXT DEFAULT 'Finished' CHECK(status IN ('Finished', 'DNF', 'DNS', 'DQ')),
                    splits_available BOOLEAN DEFAULT FALSE,
                    splits_file_path TEXT,
                    strava_activity_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (race_id) REFERENCES races (id),
                    FOREIGN KEY (runner_id) REFERENCES runners (id),
                    UNIQUE(race_id, runner_id)
                )
            ''')
            
            # Create splits table for storing detailed mile-by-mile data
            conn.execute('''
                CREATE TABLE IF NOT EXISTS splits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    race_result_id INTEGER NOT NULL,
                    mile_number INTEGER NOT NULL,
                    distance_miles REAL,
                    split_time_seconds INTEGER,
                    pace_seconds INTEGER,
                    cumulative_time_seconds INTEGER,
                    elevation_feet REAL,
                    temperature_f REAL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (race_result_id) REFERENCES race_results (id),
                    UNIQUE(race_result_id, mile_number)
                )
            ''')
            
            # Create aid stations table for course dynamics analysis
            conn.execute('''
                CREATE TABLE IF NOT EXISTS aid_stations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    race_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    distance_miles REAL NOT NULL,
                    elevation_feet REAL,
                    station_type TEXT CHECK(station_type IN ('aid', 'crew', 'drop_bag', 'crew_aid', 'major_aid')),
                    services TEXT, -- JSON array of services: water, food, medical, etc.
                    crew_access BOOLEAN DEFAULT 0,
                    drop_bag_access BOOLEAN DEFAULT 0,
                    cutoff_time_hours REAL,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (race_id) REFERENCES races (id)
                )
            ''')
            
            # Create course segments table for terrain analysis
            conn.execute('''
                CREATE TABLE IF NOT EXISTS course_segments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    race_id INTEGER NOT NULL,
                    segment_name TEXT NOT NULL,
                    start_mile REAL NOT NULL,
                    end_mile REAL NOT NULL,
                    terrain_type TEXT, -- desert, mountain, forest, etc.
                    difficulty_rating INTEGER CHECK(difficulty_rating BETWEEN 1 AND 5),
                    elevation_gain_feet REAL,
                    elevation_loss_feet REAL,
                    typical_conditions TEXT, -- hot, cold, exposed, shaded, etc.
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (race_id) REFERENCES races (id)
                )
            ''')
            
            # Create runner_profiles table for storing additional athlete metadata
            conn.execute('''
                CREATE TABLE IF NOT EXISTS runner_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    runner_id INTEGER NOT NULL,
                    height_inches REAL,
                    weight_lbs REAL,
                    occupation TEXT,
                    running_experience_years INTEGER,
                    previous_ultras INTEGER,
                    training_miles_per_week REAL,
                    favorite_distance TEXT,
                    sponsors TEXT,
                    social_media_handles TEXT,
                    bio TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (runner_id) REFERENCES runners (id),
                    UNIQUE(runner_id)
                )
            ''')
            
            # Create indexes for better performance
            conn.execute('CREATE INDEX IF NOT EXISTS idx_runners_name ON runners(last_name, first_name)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_race_results_race ON race_results(race_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_race_results_runner ON race_results(runner_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_races_name_year ON races(name, year)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_splits_result ON splits(race_result_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_splits_mile ON splits(race_result_id, mile_number)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_runner_profiles_runner ON runner_profiles(runner_id)')
            
            conn.commit()
        finally:
            conn.close()
    
    # Race management methods
    def add_race(self, name: str, year: int, **kwargs) -> int:
        """Add a new race to the database."""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                INSERT OR IGNORE INTO races (
                    name, year, date, location, distance_miles, elevation_gain_feet, 
                    elevation_loss_feet, time_limit_hours, course_description, ultrasignup_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, year, kwargs.get('date'), kwargs.get('location'),
                kwargs.get('distance_miles'), kwargs.get('elevation_gain_feet'),
                kwargs.get('elevation_loss_feet'), kwargs.get('time_limit_hours'),
                kwargs.get('course_description'), kwargs.get('ultrasignup_id')
            ))
            race_id = cursor.lastrowid
            conn.commit()
            return race_id if race_id > 0 else self.get_race_id(name, year)
        finally:
            conn.close()
    
    def get_race_id(self, name: str, year: int) -> Optional[int]:
        """Get race ID by name and year."""
        conn = self.get_connection()
        try:
            cursor = conn.execute('SELECT id FROM races WHERE name = ? AND year = ?', (name, year))
            row = cursor.fetchone()
            return row['id'] if row else None
        finally:
            conn.close()
    
    def get_races(self) -> List[Dict]:
        """Get all races."""
        conn = self.get_connection()
        try:
            cursor = conn.execute('SELECT * FROM races ORDER BY year DESC, name')
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    # Runner management methods
    def add_runner(self, first_name: str, last_name: str, **kwargs) -> int:
        """Add a new runner to the database."""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                INSERT INTO runners (
                    first_name, last_name, age, gender, city, state, country, ultrasignup_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                first_name, last_name, kwargs.get('age'), kwargs.get('gender'),
                kwargs.get('city'), kwargs.get('state'), 
                kwargs.get('country', 'USA'), kwargs.get('ultrasignup_id')
            ))
            runner_id = cursor.lastrowid
            conn.commit()
            return runner_id
        finally:
            conn.close()
    
    def find_runner(self, first_name: str, last_name: str, **kwargs) -> Optional[int]:
        """Find a runner by name and optional additional criteria."""
        conn = self.get_connection()
        try:
            query = 'SELECT id FROM runners WHERE first_name = ? AND last_name = ?'
            params = [first_name, last_name]
            
            # Add optional criteria
            if kwargs.get('age'):
                query += ' AND age = ?'
                params.append(kwargs['age'])
            if kwargs.get('city'):
                query += ' AND city = ?'
                params.append(kwargs['city'])
                
            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return row['id'] if row else None
        finally:
            conn.close()
    
    def get_or_create_runner(self, first_name: str, last_name: str, **kwargs) -> int:
        """Get existing runner or create new one."""
        runner_id = self.find_runner(first_name, last_name, **kwargs)
        if runner_id:
            return runner_id
        return self.add_runner(first_name, last_name, **kwargs)
    
    # Race results management
    def add_race_result(self, race_id: int, runner_id: int, **kwargs) -> int:
        """Add a race result."""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                INSERT OR REPLACE INTO race_results (
                    race_id, runner_id, bib_number, finish_time_hours, finish_position,
                    gender_position, age_group_position, status, splits_available,
                    splits_file_path, strava_activity_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                race_id, runner_id, kwargs.get('bib_number'), kwargs.get('finish_time_hours'),
                kwargs.get('finish_position'), kwargs.get('gender_position'),
                kwargs.get('age_group_position'), kwargs.get('status', 'Finished'),
                kwargs.get('splits_available', False), kwargs.get('splits_file_path'),
                kwargs.get('strava_activity_id')
            ))
            result_id = cursor.lastrowid
            conn.commit()
            return result_id
        finally:
            conn.close()
    
    # Query methods
    def get_race_runners(self, race_id: int) -> List[Dict]:
        """Get all runners for a specific race."""

        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT 
                    r.id as runner_id,
                    r.first_name,
                    r.last_name,
                    r.age,
                    r.gender,
                    r.city,
                    r.state,
                    r.country,
                    rr.bib_number,
                    rr.finish_time_hours,
                    rr.finish_position,
                    rr.gender_position,
                    rr.status,
                    rr.splits_available,
                    rr.splits_file_path
                FROM runners r
                JOIN race_results rr ON r.id = rr.runner_id
                WHERE rr.race_id = ?
                ORDER BY rr.finish_position
            ''', (race_id,))

            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def search_runners(self, race_id: int, search_term: str = "") -> List[Dict]:
        """Search runners in a specific race."""
        conn = self.get_connection()
        try:
            query = '''
                SELECT 
                    r.id as runner_id,
                    r.first_name,
                    r.last_name,
                    r.age,
                    r.gender,
                    r.city,
                    r.state,
                    rr.bib_number,
                    rr.finish_time_hours,
                    rr.finish_position,
                    rr.splits_available,
                    rr.splits_file_path
                FROM runners r
                JOIN race_results rr ON r.id = rr.runner_id
                WHERE rr.race_id = ?
            '''
            params = [race_id]
            
            if search_term:
                query += ''' AND (
                    LOWER(r.first_name) LIKE LOWER(?) OR 
                    LOWER(r.last_name) LIKE LOWER(?) OR
                    LOWER(r.city) LIKE LOWER(?) OR
                    rr.bib_number LIKE ?
                )'''
                search_pattern = f'%{search_term}%'
                params.extend([search_pattern, search_pattern, search_pattern, search_pattern])
            
            query += ' ORDER BY rr.finish_position'
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_runner_races(self, runner_id: int) -> List[Dict]:
        """Get all races for a specific runner."""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT 
                    ra.id as race_id,
                    ra.name,
                    ra.year,
                    ra.date,
                    ra.location,
                    rr.finish_time_hours,
                    rr.finish_position,
                    rr.status,
                    rr.splits_available,
                    rr.splits_file_path
                FROM races ra
                JOIN race_results rr ON ra.id = rr.race_id
                WHERE rr.runner_id = ?
                ORDER BY ra.year DESC
            ''', (runner_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    # Splits data management
    def add_splits_data(self, race_result_id: int, splits_data: List[Dict]) -> int:
        """Add splits data for a race result."""
        conn = self.get_connection()
        try:
            added_count = 0
            for split in splits_data:
                cursor = conn.execute('''
                    INSERT OR REPLACE INTO splits (
                        race_result_id, mile_number, distance_miles, split_time_seconds,
                        pace_seconds, cumulative_time_seconds, elevation_feet, temperature_f, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    race_result_id, split.get('mile_number'), split.get('distance_miles'),
                    split.get('split_time_seconds'), split.get('pace_seconds'),
                    split.get('cumulative_time_seconds'), split.get('elevation_feet'),
                    split.get('temperature_f'), split.get('notes')
                ))
                added_count += 1
            conn.commit()
            return added_count
        finally:
            conn.close()
    
    def get_splits_data(self, race_result_id: int) -> List[Dict]:
        """Get splits data for a race result."""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT * FROM splits 
                WHERE race_result_id = ? 
                ORDER BY mile_number
            ''', (race_result_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_splits_as_dataframe(self, race_result_id: int):
        """Get splits data as pandas DataFrame for analysis."""
        import pandas as pd
        splits = self.get_splits_data(race_result_id)
        if not splits:
            return None
        return pd.DataFrame(splits)
    
    # Runner profiles management
    def add_runner_profile(self, runner_id: int, **profile_data) -> int:
        """Add or update runner profile data."""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                INSERT OR REPLACE INTO runner_profiles (
                    runner_id, height_inches, weight_lbs, occupation, running_experience_years,
                    previous_ultras, training_miles_per_week, favorite_distance, sponsors,
                    social_media_handles, bio, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                runner_id, profile_data.get('height_inches'), profile_data.get('weight_lbs'),
                profile_data.get('occupation'), profile_data.get('running_experience_years'),
                profile_data.get('previous_ultras'), profile_data.get('training_miles_per_week'),
                profile_data.get('favorite_distance'), profile_data.get('sponsors'),
                profile_data.get('social_media_handles'), profile_data.get('bio')
            ))
            profile_id = cursor.lastrowid
            conn.commit()
            return profile_id
        finally:
            conn.close()
    
    def get_runner_profile(self, runner_id: int) -> Optional[Dict]:
        """Get runner profile data."""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT * FROM runner_profiles WHERE runner_id = ?
            ''', (runner_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    # Utility methods for file migration
    def get_race_result_id(self, race_id: int, runner_id: int) -> Optional[int]:
        """Get race result ID for a specific race and runner."""
        conn = self.get_connection()
        try:
            cursor = conn.execute('''
                SELECT id FROM race_results WHERE race_id = ? AND runner_id = ?
            ''', (race_id, runner_id))
            row = cursor.fetchone()
            return row['id'] if row else None
        finally:
            conn.close()
    
    def update_splits_availability(self, race_result_id: int, available: bool = True):
        """Update splits availability flag for a race result."""
        conn = self.get_connection()
        try:
            conn.execute('''
                UPDATE race_results 
                SET splits_available = ?, splits_file_path = NULL
                WHERE id = ?
            ''', (available, race_result_id))
            conn.commit()
        finally:
            conn.close()


def populate_sample_data():
    """Populate the database with sample Cocodona 250 data."""
    db = UltraSmartDatabase()
    
    # Add Cocodona 250 race for 2025
    race_id = db.add_race(
        name="Cocodona 250",
        year=2025,
        date="2025-05-05",
        location="Black Canyon City to Flagstaff, AZ",
        distance_miles=256,
        elevation_gain_feet=40000,
        elevation_loss_feet=35000,
        time_limit_hours=125,
        course_description="Point-to-point course through the Sonoran Desert and high country of Arizona",
        ultrasignup_id="115785"
    )
    
    # Add sample runners based on our existing data
    runners_data = [
        {
            'first_name': 'Dan', 'last_name': 'Green', 'age': 28, 'gender': 'M',
            'city': 'Huntington', 'state': 'WV',
            'bib_number': '1', 'finish_time_hours': 58.79, 'finish_position': 1, 'gender_position': 1,
            'splits_available': True, 'splits_file_path': './data/dan_green_cocodona_250_2025_strava_splits_complete.csv'
        },
        {
            'first_name': 'Finn', 'last_name': 'Melanson', 'age': 33, 'gender': 'M',
            'city': 'Salt Lake City', 'state': 'UT',
            'bib_number': '2', 'finish_time_hours': 68.45, 'finish_position': 5, 'gender_position': 5,
            'splits_available': True, 'splits_file_path': './data/finn_melanson_cocodona_250_2025_strava_splits_complete.csv'
        },
        {
            'first_name': 'Jeff', 'last_name': 'Garmire', 'age': 34, 'gender': 'M',
            'city': 'Bozeman', 'state': 'MT',
            'bib_number': '3', 'finish_time_hours': 72.33, 'finish_position': 8, 'gender_position': 8,
            'splits_available': True, 'splits_file_path': './data/jeff_garmire_cocodona_250_2025_strava_splits_complete.csv'
        },
        # Add some additional sample runners without splits data
        {
            'first_name': 'Rachel', 'last_name': 'Entrekin', 'age': 29, 'gender': 'F',
            'city': 'Boulder', 'state': 'CO',
            'bib_number': '10', 'finish_time_hours': 63.85, 'finish_position': 2, 'gender_position': 1,
            'splits_available': False
        },
        {
            'first_name': 'John', 'last_name': 'Smith', 'age': 42, 'gender': 'M',
            'city': 'Phoenix', 'state': 'AZ',
            'bib_number': '15', 'finish_time_hours': 75.25, 'finish_position': 12, 'gender_position': 12,
            'splits_available': False
        },
        {
            'first_name': 'Sarah', 'last_name': 'Johnson', 'age': 38, 'gender': 'F',
            'city': 'Denver', 'state': 'CO',
            'bib_number': '22', 'finish_time_hours': 78.92, 'finish_position': 15, 'gender_position': 3,
            'splits_available': False
        },
        {
            'first_name': 'Mike', 'last_name': 'Williams', 'age': 45, 'gender': 'M',
            'city': 'Sedona', 'state': 'AZ',
            'bib_number': '33', 'finish_time_hours': 82.15, 'finish_position': 18, 'gender_position': 18,
            'splits_available': False
        },
        {
            'first_name': 'Lisa', 'last_name': 'Davis', 'age': 31, 'gender': 'F',
            'city': 'Flagstaff', 'state': 'AZ',
            'bib_number': '44', 'finish_time_hours': 85.67, 'finish_position': 22, 'gender_position': 5,
            'splits_available': False
        }
    ]
    
    # Add runners and their race results
    for runner_data in runners_data:
        # Extract runner info
        runner_info = {k: v for k, v in runner_data.items() if k in [
            'first_name', 'last_name', 'age', 'gender', 'city', 'state'
        ]}
        
        # Extract race result info
        result_info = {k: v for k, v in runner_data.items() if k in [
            'bib_number', 'finish_time_hours', 'finish_position', 'gender_position',
            'splits_available', 'splits_file_path'
        ]}
        
        # Create runner and add race result
        runner_id = db.get_or_create_runner(**runner_info)
        db.add_race_result(race_id, runner_id, **result_info)
    
    print(f"Sample data populated successfully! Race ID: {race_id}")
    print(f"Added {len(runners_data)} runners to the database.")
    
    # Print summary
    runners = db.get_race_runners(race_id)
    print(f"\nCocodona 250 2025 Results:")
    print("-" * 80)
    for runner in runners[:10]:  # Show top 10
        splits_status = "✓" if runner['splits_available'] else "✗"
        print(f"{runner['finish_position']:2d}. {runner['first_name']} {runner['last_name']:15s} "
              f"({runner['age']:2d}{runner['gender']}) - {runner['finish_time_hours']:5.1f}h - "
              f"{runner['city']}, {runner['state']} [Splits: {splits_status}]")


if __name__ == "__main__":
    populate_sample_data()