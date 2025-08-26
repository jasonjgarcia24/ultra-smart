import requests
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Optional, Dict, Any
from datetime import datetime
import re
import os
try:
    from stravalib.client import Client
    STRAVA_AVAILABLE = True
except ImportError:
    STRAVA_AVAILABLE = False

from .models import Athlete, Split


class SplitReader:
    def __init__(self, strava_access_token: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        # Initialize Strava client if available and token provided
        self.strava_client = None
        if STRAVA_AVAILABLE and strava_access_token:
            self.strava_client = Client(access_token=strava_access_token)
        elif strava_access_token and not STRAVA_AVAILABLE:
            print("Warning: stravalib not installed. Run: pip install stravalib")
    
    def read_from_csv(self, file_path: str) -> List[Athlete]:
        """Read athlete splits from a CSV file."""
        try:
            df = pd.read_csv(file_path)
            return self._parse_dataframe_to_athletes(df)
        except Exception as e:
            print(f"Error reading CSV file: {e}")
            return []
    
    def read_from_url(self, url: str) -> List[Athlete]:
        """Read athlete splits from a web URL."""
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            # Try to parse as HTML first, then fall back to CSV
            if 'text/html' in response.headers.get('content-type', ''):
                return self._parse_html_results(response.text)
            else:
                # Assume CSV format
                df = pd.read_csv(response.text)
                return self._parse_dataframe_to_athletes(df)
                
        except Exception as e:
            print(f"Error reading from URL: {e}")
            return []
    
    def read_from_strava_activity(self, activity_id: int) -> Optional[Athlete]:
        """Read athlete data from a Strava activity."""
        if not self.strava_client:
            print("Error: Strava client not initialized. Provide access_token when creating SplitReader.")
            return None
        
        try:
            # Get activity details
            activity = self.strava_client.get_activity(activity_id)
            
            # Get activity streams for detailed split data
            streams = self.strava_client.get_activity_streams(
                activity_id, 
                types=['time', 'distance', 'latlng', 'altitude'],
                resolution='high'
            )
            
            # Create athlete from activity data
            athlete = self._create_athlete_from_strava_activity(activity, streams)
            return athlete
            
        except Exception as e:
            print(f"Error reading from Strava activity {activity_id}: {e}")
            return None
    
    def _parse_html_results(self, html_content: str) -> List[Athlete]:
        """Parse HTML content to extract athlete splits."""
        soup = BeautifulSoup(html_content, 'html.parser')
        athletes = []
        
        # This is a generic parser - would need to be customized 
        # based on the actual HTML structure of Cocodona 250 results
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            if not rows:
                continue
                
            # Extract headers
            header_row = rows[0]
            headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
            
            # Process data rows
            for row in rows[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                if len(cells) >= len(headers):
                    athlete_data = dict(zip(headers, cells))
                    athlete = self._create_athlete_from_dict(athlete_data)
                    if athlete:
                        athletes.append(athlete)
        
        return athletes
    
    def _parse_dataframe_to_athletes(self, df: pd.DataFrame) -> List[Athlete]:
        """Convert pandas DataFrame to list of Athletes."""
        athletes = []
        
        # Group by athlete (assuming bib_number or name column exists)
        if 'bib_number' in df.columns:
            grouped = df.groupby('bib_number')
        elif 'name' in df.columns:
            grouped = df.groupby('name')
        else:
            # If no grouping column, treat each row as a separate athlete
            grouped = df.groupby(df.index)
        
        for group_key, group_df in grouped:
            athlete = self._create_athlete_from_dataframe_group(group_df)
            if athlete:
                athletes.append(athlete)
        
        return athletes
    
    def _create_athlete_from_dict(self, data: Dict[str, str]) -> Optional[Athlete]:
        """Create an Athlete object from a dictionary of data."""
        try:
            # Map common column names
            bib_number = self._extract_int(data.get('bib', data.get('bib_number', data.get('number', '0'))))
            name = data.get('name', data.get('athlete', ''))
            
            if not name or bib_number == 0:
                return None
            
            athlete = Athlete(
                bib_number=bib_number,
                name=name,
                age=self._extract_int(data.get('age')),
                gender=data.get('gender', data.get('sex')),
                city=data.get('city'),
                state=data.get('state'),
                country=data.get('country'),
                overall_rank=self._extract_int(data.get('rank', data.get('overall_rank'))),
                finish_time=data.get('finish_time', data.get('time')),
                status=data.get('status')
            )
            
            # Add checkpoint splits if present
            for key, value in data.items():
                if self._is_checkpoint_column(key) and value:
                    split = self._create_split_from_checkpoint_data(key, value)
                    if split:
                        athlete.add_split(split)
            
            return athlete
            
        except Exception as e:
            print(f"Error creating athlete from data: {e}")
            return None
    
    def _create_athlete_from_dataframe_group(self, group_df: pd.DataFrame) -> Optional[Athlete]:
        """Create an Athlete object from a grouped DataFrame."""
        if group_df.empty:
            return None
        
        # Use the first row for basic athlete info
        first_row = group_df.iloc[0]
        
        athlete_data = first_row.to_dict()
        return self._create_athlete_from_dict(athlete_data)
    
    def _create_athlete_from_strava_activity(self, activity, streams) -> Optional[Athlete]:
        """Create an Athlete object from Strava activity data."""
        try:
            # Extract athlete basic info - MetaAthlete might not have detailed info
            # So we'll use the activity name and basic info available
            athlete_name = activity.name or f"Athlete {activity.athlete.id}"
            
            # Create athlete object
            athlete = Athlete(
                bib_number=0,  # Strava doesn't have bib numbers
                name=athlete_name,
                age=None,  # Not available from activity data
                gender=None,  # Not available from MetaAthlete
                city=None,   # Not available from MetaAthlete
                state=None,  # Not available from MetaAthlete
                country=None, # Not available from MetaAthlete
                overall_rank=None,
                finish_time=str(activity.elapsed_time) if activity.elapsed_time else None,
                status="Finished" if activity.elapsed_time else "Unknown"
            )
            
            # Generate splits from streams data if available
            if streams and 'distance' in streams and 'time' in streams:
                splits = self._generate_splits_from_streams(streams)
                for split in splits:
                    athlete.add_split(split)
            
            return athlete
            
        except Exception as e:
            print(f"Error creating athlete from Strava activity: {e}")
            return None
    
    def _generate_splits_from_streams(self, streams) -> List[Split]:
        """Generate splits from Strava activity streams."""
        splits = []
        
        try:
            distance_data = streams['distance'].data
            time_data = streams['time'].data
            
            # Create splits every 5 miles (or at significant distance markers)
            split_distances = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]  # miles
            
            total_distance_meters = max(distance_data) if distance_data else 0
            total_distance_miles = total_distance_meters * 0.000621371  # Convert to miles
            
            for split_distance in split_distances:
                if split_distance > total_distance_miles:
                    break
                
                # Find the closest data point to this split distance
                target_meters = split_distance / 0.000621371  # Convert to meters
                closest_idx = min(range(len(distance_data)), 
                                key=lambda i: abs(distance_data[i] - target_meters))
                
                if closest_idx < len(time_data):
                    elapsed_seconds = time_data[closest_idx]
                    elapsed_time = str(datetime.utcfromtimestamp(elapsed_seconds).strftime('%H:%M:%S'))
                    
                    split = Split(
                        checkpoint_name=f"Mile {split_distance}",
                        distance_miles=split_distance,
                        elapsed_time=elapsed_time,
                        split_time=None,  # Would need previous split to calculate
                        rank_at_checkpoint=None,
                        timestamp=None
                    )
                    splits.append(split)
            
        except Exception as e:
            print(f"Error generating splits from streams: {e}")
        
        return splits
    
    def _create_split_from_checkpoint_data(self, checkpoint_name: str, time_data: str) -> Optional[Split]:
        """Create a Split object from checkpoint data."""
        try:
            # Clean up checkpoint name
            clean_name = re.sub(r'[_\-\.]', ' ', checkpoint_name).strip()
            
            # Parse time data (could be elapsed time, split time, or both)
            elapsed_time = None
            split_time = None
            
            if time_data and time_data != '-':
                # Simple parsing - would need to be enhanced based on actual format
                elapsed_time = time_data.strip()
            
            return Split(
                checkpoint_name=clean_name,
                distance_miles=0.0,  # Would need to be mapped based on known checkpoints
                elapsed_time=elapsed_time,
                split_time=split_time
            )
            
        except Exception as e:
            print(f"Error creating split: {e}")
            return None
    
    def _is_checkpoint_column(self, column_name: str) -> bool:
        """Determine if a column represents a checkpoint."""
        checkpoint_indicators = ['checkpoint', 'aid', 'station', 'mile', 'km']
        column_lower = column_name.lower()
        return any(indicator in column_lower for indicator in checkpoint_indicators)
    
    def _extract_int(self, value: Any) -> Optional[int]:
        """Safely extract integer from various input types."""
        if value is None:
            return None
        try:
            if isinstance(value, str):
                # Remove non-numeric characters except digits
                cleaned = re.sub(r'[^\d]', '', value)
                return int(cleaned) if cleaned else None
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def export_to_csv(self, athletes: List[Athlete], filename: str):
        """Export athletes data to CSV."""
        if not athletes:
            print("No athletes to export")
            return
        
        # Flatten athlete and split data
        rows = []
        for athlete in athletes:
            base_row = {
                'bib_number': athlete.bib_number,
                'name': athlete.name,
                'age': athlete.age,
                'gender': athlete.gender,
                'city': athlete.city,
                'state': athlete.state,
                'country': athlete.country,
                'overall_rank': athlete.overall_rank,
                'finish_time': athlete.finish_time,
                'status': athlete.status
            }
            
            if athlete.splits:
                for split in athlete.splits:
                    row = base_row.copy()
                    row.update({
                        'checkpoint_name': split.checkpoint_name,
                        'distance_miles': split.distance_miles,
                        'elapsed_time': split.elapsed_time,
                        'split_time': split.split_time,
                        'rank_at_checkpoint': split.rank_at_checkpoint
                    })
                    rows.append(row)
            else:
                rows.append(base_row)
        
        df = pd.DataFrame(rows)
        df.to_csv(filename, index=False)
        print(f"Exported {len(athletes)} athletes to {filename}")