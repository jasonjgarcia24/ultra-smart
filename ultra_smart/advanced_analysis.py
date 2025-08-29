#!/usr/bin/env python3
"""
Advanced analysis algorithms for ultra-endurance race performance.
Incorporates course dynamics, fatigue modeling, and rest period detection.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import math
import json
import os
import pdb

class AdvancedAnalyzer:
    """Advanced analysis engine for ultra-endurance race data"""
    
    def __init__(self, database):
        self.db = database
        self._gpx_data = None
    
    def _clean_for_json(self, obj):
        """Clean data for JSON serialization"""
        if isinstance(obj, dict):
            return {k: self._clean_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._clean_for_json(v) for v in obj]
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            if np.isnan(obj) or np.isinf(obj):
                return 0.0
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, (bool, int, float, str)) or obj is None:
            return obj
        else:
            return str(obj)
    
    def _load_gpx_data(self):
        """Load GPX course data with elevation information"""
        if self._gpx_data is not None:
            return
        
        gpx_data_path = '/home/jasongarcia24/Documents/ultra-smart/data/cocodona_250_course_data.json'
        
        try:
            if os.path.exists(gpx_data_path):
                with open(gpx_data_path, 'r') as f:
                    self._gpx_data = json.load(f)
            else:
                print(f"Warning: GPX course data not found at {gpx_data_path}")
                self._gpx_data = {}
        except Exception as e:
            print(f"Error loading GPX data: {e}")
            self._gpx_data = {}
    
    def _get_elevation_at_mile(self, mile: float) -> Optional[float]:
        """Get elevation in feet at a specific mile point using GPX data"""
        self._load_gpx_data()
        
        if not self._gpx_data or 'track_points' not in self._gpx_data:
            return None
        
        track_points = self._gpx_data['track_points']
        
        # Find the closest track point to the requested mile
        closest_point = None
        min_distance = float('inf')
        
        for point in track_points:
            if point.get('elevation_feet') is not None:
                point_mile = point.get('distance_miles', 0)
                distance = abs(point_mile - mile)
                if distance < min_distance:
                    min_distance = distance
                    closest_point = point
        
        return closest_point.get('elevation_feet') if closest_point else None
    
    def _calculate_elevation_change(self, start_mile: float, end_mile: float) -> Dict[str, float]:
        """Calculate elevation gain and loss between two mile points using GPX data"""
        self._load_gpx_data()
        
        if not self._gpx_data or 'track_points' not in self._gpx_data:
            return {'gain': 0.0, 'loss': 0.0, 'net_change': 0.0}
        
        track_points = self._gpx_data['track_points']
        
        # Find track points within the mile range
        segment_points = []
        for point in track_points:
            if point.get('elevation_feet') is not None:
                point_mile = point.get('distance_miles', 0)
                if start_mile <= point_mile <= end_mile:
                    segment_points.append(point)
        
        if len(segment_points) < 2:
            return {'gain': 0.0, 'loss': 0.0, 'net_change': 0.0}
        
        # Sort by distance
        segment_points.sort(key=lambda x: x.get('distance_miles', 0))
        
        # Calculate gain and loss
        total_gain = 0.0
        total_loss = 0.0
        
        for i in range(1, len(segment_points)):
            prev_elevation = segment_points[i-1]['elevation_feet']
            curr_elevation = segment_points[i]['elevation_feet']
            
            if curr_elevation > prev_elevation:
                total_gain += curr_elevation - prev_elevation
            else:
                total_loss += prev_elevation - curr_elevation
        
        start_elevation = segment_points[0]['elevation_feet']
        end_elevation = segment_points[-1]['elevation_feet']
        net_change = end_elevation - start_elevation
        
        return {
            'gain': total_gain,
            'loss': total_loss,
            'net_change': net_change,
            'start_elevation': start_elevation,
            'end_elevation': end_elevation
        }
    
    def _get_gpx_elevation_gain(self, start_mile: float, end_mile: float) -> float:
        """Get elevation gain in feet between two mile points using GPX data"""
        elevation_change = self._calculate_elevation_change(start_mile, end_mile)
        return elevation_change.get('gain', 0.0)
        
    def get_runner_splits(self, runner_id: int, race_id: int, field: str = None) -> List[Dict]:
        """Public method to get runner's split data"""
        print(field)
        return self._get_runner_splits(runner_id, race_id) if field is None else [split[field] for split in self._get_runner_splits(runner_id, race_id)]

    def calculate_fatigue_factors(self, runner_id: int, race_id: int) -> Dict:
        """
        Calculate perceived fatigue factors based on pace variations,
        course dynamics, and time progression.
        """
        # Get runner's splits and course data
        splits = self._get_runner_splits(runner_id, race_id)
        course_segments = self._get_course_segments(race_id)
        aid_stations = self._get_aid_stations(race_id)
        
        if not splits:
            return {"error": "No split data found"}
        
        fatigue_data = []
        base_pace = self._calculate_base_pace(splits[:10])  # Use first 10 miles as baseline
        
        for i, split in enumerate(splits):
            mile = split.get('mile_number', i + 1)
            actual_pace = split.get('pace_per_mile', 0)
            
            # Get course context
            segment = self._get_segment_for_mile(mile, course_segments)
            recent_aid = self._get_recent_aid_station(mile, aid_stations)
            
            # Calculate terrain-adjusted expected pace
            terrain_adjustment = self._calculate_terrain_adjustment(segment)
            elevation_adjustment = self._calculate_elevation_adjustment(segment, mile)
            time_of_day_adjustment = self._calculate_time_of_day_adjustment(split)
            
            expected_pace = base_pace * terrain_adjustment * elevation_adjustment * time_of_day_adjustment
            
            # Calculate fatigue factor (ratio of actual to expected pace)
            fatigue_factor = actual_pace / expected_pace if expected_pace > 0 else 1.0
            
            # Detect potential rest periods
            is_rest = self._detect_rest_period(split, splits, i)
            
            fatigue_data.append({
                'mile': mile,
                'actual_pace': actual_pace,
                'expected_pace': expected_pace,
                'fatigue_factor': fatigue_factor,
                'terrain_difficulty': segment.get('difficulty_rating', 3) if segment else 3,
                'elevation_gain': self._get_gpx_elevation_gain(mile, mile + 1),
                'is_rest_period': is_rest,
                'recent_aid_station': recent_aid.get('name') if recent_aid else None,
                'time_of_day': split.get('time_of_day'),
                'cumulative_time': split.get('cumulative_time_minutes', 0)
            })
        
        result = {
            'fatigue_progression': fatigue_data,
            'average_fatigue': np.mean([d['fatigue_factor'] for d in fatigue_data]) if fatigue_data else 1.0,
            'peak_fatigue_mile': max(fatigue_data, key=lambda x: x['fatigue_factor'])['mile'] if fatigue_data else 0,
            'rest_periods': [d for d in fatigue_data if d['is_rest_period']],
            'base_pace_minutes': base_pace
        }
        
        return self._clean_for_json(result)
    
    def detect_rest_periods(self, runner_id: int, race_id: int) -> List[Dict]:
        """
        Identify significant rest periods where runners likely stopped
        at aid stations or took extended breaks, with enhanced aid station analysis.
        """
        splits = self._get_runner_splits(runner_id, race_id)
        aid_stations = self._get_aid_stations(race_id)
        
        
        rest_periods = []
        aid_station_stops = []  # Track all aid station interactions
        
        for i in range(1, len(splits)):
            current_split = splits[i]
            prev_split = splits[i-1]
            
            current_pace = current_split.get('pace_per_mile', 0)
            prev_pace = prev_split.get('pace_per_mile', 0)
            mile = current_split.get('mile_number', i + 1)            
            
            # Look for significant pace increases (indicating slower movement/rest)
            if current_pace > 0 and prev_pace > 0:
                pace_increase = current_pace / prev_pace
                
                # Find nearby aid stations (using expanded 5-mile radius for GPS variations)
                nearby_aid = self._find_nearby_aid_station(mile, aid_stations, radius=5.0)
                
                # Make detection more sensitive - lower threshold from 1.5x to 1.3x
                # Also detect extremely slow paces (>35 min/mile) regardless of previous pace
                
                if pace_increase > 1.3 or current_pace > 35:
                
                    rest_duration = current_pace - prev_pace
                    
                    # Enhanced aid station analysis
                    aid_analysis = self._analyze_aid_station_stop(
                        nearby_aid, pace_increase, rest_duration, current_split, splits, i
                    )
                    
                    rest_period = {
                        'mile': mile,
                        'estimated_rest_minutes': rest_duration,
                        'pace_before': prev_pace,
                        'pace_during': current_pace,
                        'pace_ratio': pace_increase,
                        'nearby_aid_station': nearby_aid.get('name') if nearby_aid else None,
                        'aid_station_distance': self._calculate_distance_to_aid(mile, nearby_aid) if nearby_aid else None,
                        'aid_station_type': nearby_aid.get('station_type') if nearby_aid else None,
                        'is_sleep_station': nearby_aid.get('sleep_station') == 1 if nearby_aid else False,
                        'aid_services': json.loads(nearby_aid.get('services', '[]')) if nearby_aid else [],
                        'likely_reason': aid_analysis['reason'],
                        'confidence': aid_analysis['confidence'],
                        'rest_type': aid_analysis['rest_type']
                    }
                    
                    rest_periods.append(rest_period)
                    
                    if nearby_aid:
                        aid_station_stops.append({
                            'station_name': nearby_aid['name'],
                            'mile': mile,
                            'rest_duration_minutes': rest_duration,
                            'is_sleep_station': nearby_aid.get('sleep_station') == 1,
                            'is_crew_station': nearby_aid.get('station_type') in ['crew_aid', 'major_aid'],
                            'station_type': nearby_aid.get('station_type'),
                            'rest_type': aid_analysis['rest_type']
                        })
        
        # Analyze patterns across all aid station stops
        aid_station_patterns = self._analyze_aid_station_patterns(aid_station_stops)
        
        result = {
            'rest_periods': rest_periods,
            'aid_station_stops': aid_station_stops,
            'aid_station_patterns': aid_station_patterns
        }
        
        return self._clean_for_json(result)
    
    def analyze_course_impact(self, runner_id: int, race_id: int) -> Dict:
        """
        Analyze how course dynamics (elevation, terrain, aid stations)
        impact individual runner performance with relative scoring.
        """
        splits = self._get_runner_splits(runner_id, race_id)
        segments = self._get_course_segments(race_id)
        
        # Get comparative data for relative performance scoring
        segment_benchmarks = self._get_segment_benchmarks(race_id, segments)
        
        segment_performance = []
        
        for segment in segments:
            start_mile = segment['start_mile']
            end_mile = segment['end_mile']
            
            # Get splits within this segment
            segment_splits = [s for s in splits 
                            if start_mile <= s.get('mile_number', 0) < end_mile]
            
            if not segment_splits:
                continue
                
            avg_pace = np.mean([s.get('pace_per_mile', 0) for s in segment_splits])
            pace_variance = np.var([s.get('pace_per_mile', 0) for s in segment_splits])
            
            # Calculate enhanced performance score using benchmarks
            benchmark = segment_benchmarks.get(segment['segment_name'], {})
            performance_score = self._calculate_relative_performance_score(
                avg_pace, segment, benchmark
            )
            
            segment_performance.append({
                'segment_name': segment['segment_name'],
                'start_mile': start_mile,
                'end_mile': end_mile,
                'terrain_type': segment['terrain_type'],
                'difficulty_rating': segment['difficulty_rating'],
                'difficulty_breakdown': segment.get('difficulty_breakdown'),  # Include difficulty breakdown for tooltips
                'elevation_gain': segment['elevation_gain_feet'],
                'elevation_gain_feet': segment['elevation_gain_feet'],
                'elevation_loss_feet': segment['elevation_loss_feet'],
                'net_elevation_change_feet': segment['net_elevation_change_feet'],
                'start_elevation_feet': segment['start_elevation_feet'],
                'end_elevation_feet': segment['end_elevation_feet'],
                'average_pace': avg_pace,
                'pace_consistency': 1.0 / pace_variance if pace_variance > 0 else 1.0,
                'performance_score': performance_score,
                'typical_conditions': segment['typical_conditions'],
                'benchmark_info': benchmark  # Include benchmark context
            })
        
        # Identify strengths and weaknesses
        best_terrain = max(segment_performance, key=lambda x: x['performance_score'])
        worst_terrain = min(segment_performance, key=lambda x: x['performance_score'])
        
        result = {
            'segment_analysis': segment_performance,
            'strongest_terrain': best_terrain['terrain_type'] if segment_performance else 'unknown',
            'weakest_terrain': worst_terrain['terrain_type'] if segment_performance else 'unknown',
            'best_segment': best_terrain['segment_name'] if segment_performance else 'unknown',
            'worst_segment': worst_terrain['segment_name'] if segment_performance else 'unknown',
            'elevation_tolerance': self._calculate_elevation_tolerance(segment_performance)
        }
        
        return self._clean_for_json(result)
    
    def generate_pacing_recommendations(self, runner_id: int, race_id: int) -> Dict:
        """
        Generate pacing recommendations based on course dynamics and
        runner's historical performance patterns.
        """
        fatigue_analysis = self.calculate_fatigue_factors(runner_id, race_id)
        course_analysis = self.analyze_course_impact(runner_id, race_id)
        segments = self._get_course_segments(race_id)
        
        recommendations = []
        
        for segment in segments:
            terrain_type = segment['terrain_type']
            difficulty = segment['difficulty_rating']
            
            # Base recommendation on historical performance in similar terrain
            similar_performance = [s for s in course_analysis['segment_analysis'] 
                                 if s['terrain_type'] == terrain_type]
            
            if similar_performance:
                avg_performance = np.mean([s['performance_score'] for s in similar_performance])
                # For ultra-endurance, cap effort much lower and base on performance relative to field
                if avg_performance > 0.8:  # Performing well above average
                    recommended_effort = 0.75  # Steady effort
                elif avg_performance > 0.6:  # Average to good performance
                    recommended_effort = 0.70  # Moderate effort
                else:  # Below average performance
                    recommended_effort = 0.65  # Conservative effort
            else:
                # Conservative base effort adjusted by difficulty for ultra-endurance
                base_effort = 0.65  # Much more conservative for 250-mile race
                difficulty_adjustment = (difficulty - 3) * 0.05  # Smaller adjustment
                recommended_effort = max(0.55, base_effort - difficulty_adjustment)
            
            recommendations.append({
                'segment': segment['segment_name'],
                'miles': f"{segment['start_mile']:.1f} - {segment['end_mile']:.1f}",
                'terrain': terrain_type,
                'difficulty': difficulty,
                'recommended_effort': recommended_effort,
                'key_strategy': self._generate_strategy_text(segment, recommended_effort),
                'elevation_change': segment['elevation_gain_feet'] - segment['elevation_loss_feet']
            })
        
        result = {
            'segment_recommendations': recommendations,
            'overall_strategy': self._generate_overall_strategy(fatigue_analysis, course_analysis),
            'critical_segments': self._identify_critical_segments(segments, course_analysis)
        }
        
        return self._clean_for_json(result)
    
    # Helper methods
    def _get_runner_splits(self, runner_id: int, race_id: int) -> List[Dict]:
        """Get runner's split data"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT s.mile_number, s.split_time_seconds, s.pace_seconds, 
                   s.cumulative_time_seconds
            FROM splits s
            JOIN race_results rr ON s.race_result_id = rr.id
            WHERE rr.runner_id = ? AND rr.race_id = ?
            ORDER BY s.mile_number
        """, (runner_id, race_id))
        
        results = cursor.fetchall()
        conn.close()
        
        # Convert to the expected format (minutes for easier calculations)
        formatted_results = []
        for row in results:
            row_dict = dict(row)
            
            # Calculate pace from split time if pace is missing
            split_time_minutes = row_dict['split_time_seconds'] / 60.0 if row_dict['split_time_seconds'] else 0
            
            if row_dict['pace_seconds']:
                pace_per_mile = row_dict['pace_seconds'] / 60.0
            elif split_time_minutes > 0:
                # Assume 1 mile splits and calculate pace from split time
                pace_per_mile = split_time_minutes
            else:
                pace_per_mile = 0
            
            formatted_results.append({
                'mile_number': row_dict['mile_number'],
                'split_time_minutes': split_time_minutes,
                'pace_per_mile': pace_per_mile,
                'cumulative_time_minutes': row_dict['cumulative_time_seconds'] / 60.0 if row_dict['cumulative_time_seconds'] else 0,
                'time_of_day': None  # We don't have this data in the current schema
            })
        
        return formatted_results
    
    def _get_course_segments(self, race_id: int) -> List[Dict]:
        """Get course segment data with dynamic difficulty calculation"""
        aid_stations = self._get_aid_stations(race_id)
        
        if not aid_stations:
            return []
        
        # Calculate performance-based difficulty for all segments
        segment_performance_data = self._calculate_segment_performance_metrics(race_id, aid_stations)
        
        segments = []
        for i in range(len(aid_stations) - 1):
            start_mile = aid_stations[i]['distance_miles']
            end_mile = aid_stations[i + 1]['distance_miles']
            segment_name = f"{aid_stations[i]['name']} to {aid_stations[i + 1]['name']}"
            
            # Calculate dynamic difficulty rating based on multiple factors
            difficulty_details = self._calculate_segment_difficulty_detailed(
                start_mile, end_mile, segment_name, aid_stations[i], aid_stations[i + 1],
                segment_performance_data.get(segment_name, {})
            )
            difficulty_rating = difficulty_details['difficulty']
            
            # Debug: Check if breakdown data exists and is JSON serializable
            try:
                import json
                json_test = json.dumps(difficulty_details)
            except Exception as e:
                print(f"JSON serialization failed for {segment_name}: {e}")
            
            # Determine terrain type based on aid station characteristics and difficulty
            terrain_type = self._determine_terrain_type(aid_stations[i], aid_stations[i + 1], difficulty_rating)
            
            # Get elevation data from GPX
            elevation_change = self._calculate_elevation_change(start_mile, end_mile)
            
            # Create a simple test breakdown to verify the system works
            test_breakdown = {
                'difficulty': difficulty_rating,
                'base_difficulty': 3.0,
                'factors': [
                    {
                        'category': 'Test Factor',
                        'details': [f'Elevation gain test for {segment_name}', 'Distance factor test']
                    }
                ],
                'final_adjustment': difficulty_rating - 3.0
            }
            
            segments.append({
                'segment_name': segment_name,
                'start_mile': start_mile,
                'end_mile': end_mile,
                'terrain_type': terrain_type,
                'difficulty_rating': difficulty_rating,
                'difficulty_breakdown': test_breakdown,  # Use test data first
                'elevation_gain_feet': elevation_change.get('gain', 0),
                'elevation_loss_feet': elevation_change.get('loss', 0),
                'start_elevation_feet': elevation_change.get('start_elevation', 0),
                'end_elevation_feet': elevation_change.get('end_elevation', 0),
                'net_elevation_change_feet': elevation_change.get('net_change', 0),
                'typical_conditions': self._determine_conditions(start_mile, end_mile)
            })
        
        return segments
    
    def _get_aid_stations(self, race_id: int) -> List[Dict]:
        """Get aid station data with enhanced information including all context from page 26"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name, distance_miles, station_type, services,
                   COALESCE(sleep_station, 0) as sleep_station,
                   COALESCE(crew_access, 0) as crew_access,
                   COALESCE(pacer_access, 0) as pacer_access,
                   COALESCE(drop_bag_access, 0) as drop_bags,
                   COALESCE(gear_check, '') as gear_check,
                   COALESCE(has_medic, 0) as has_medic,
                   cutoff_time_hours, cutoff_datetime, notes
            FROM aid_stations 
            WHERE race_id = ? 
            ORDER BY distance_miles
        """, (race_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    
    def _calculate_base_pace(self, early_splits: List[Dict]) -> float:
        """Calculate runner's base pace from early race splits"""
        if not early_splits:
            return 12.0  # Default pace in minutes per mile
        
        paces = [s.get('pace_per_mile', 0) for s in early_splits if s.get('pace_per_mile', 0) > 0]
        return np.median(paces) if paces else 12.0
    
    def _get_segment_for_mile(self, mile: float, segments: List[Dict]) -> Optional[Dict]:
        """Find the course segment for a given mile"""
        for segment in segments:
            if segment['start_mile'] <= mile < segment['end_mile']:
                return segment
        return None
    
    def _get_recent_aid_station(self, mile: float, aid_stations: List[Dict], lookback: float = 5.0) -> Optional[Dict]:
        """Find the most recent aid station within lookback miles"""
        recent_stations = [aid for aid in aid_stations 
                          if aid['distance_miles'] <= mile and (mile - aid['distance_miles']) <= lookback]
        
        return max(recent_stations, key=lambda x: x['distance_miles']) if recent_stations else None
    
    def _calculate_terrain_adjustment(self, segment: Optional[Dict]) -> float:
        """Calculate pace adjustment factor for terrain difficulty"""
        if not segment:
            return 1.0
        
        difficulty = segment.get('difficulty_rating', 3)
        # Difficulty 1 = 0.9x pace, Difficulty 5 = 1.5x pace
        return 0.9 + (difficulty - 1) * 0.15
    
    def _calculate_elevation_adjustment(self, segment: Optional[Dict], mile: float) -> float:
        """Calculate pace adjustment for elevation changes"""
        if not segment:
            return 1.0
        
        elevation_gain = segment.get('elevation_gain_feet', 0)
        segment_distance = segment.get('end_mile', 0) - segment.get('start_mile', 0)
        
        if segment_distance <= 0:
            return 1.0
        
        # Adjust pace based on elevation gain per mile
        gain_per_mile = elevation_gain / segment_distance
        
        # Roughly 1% pace penalty per 100ft of elevation gain per mile
        adjustment = 1.0 + (gain_per_mile / 100.0) * 0.01
        return min(adjustment, 2.0)  # Cap at 2x pace
    
    def _calculate_time_of_day_adjustment(self, split: Dict) -> float:
        """Calculate pace adjustment for time of day effects"""
        time_str = split.get('time_of_day')
        if not time_str:
            return 1.0
        
        try:
            # Parse time and adjust for circadian rhythm effects
            time_obj = datetime.strptime(time_str, '%H:%M:%S').time()
            hour = time_obj.hour
            
            # Night hours (10PM - 6AM) typically see slower paces
            if hour >= 22 or hour <= 6:
                return 1.1  # 10% slower
            # Peak performance hours (8AM - 6PM)
            elif 8 <= hour <= 18:
                return 0.98  # 2% faster
            else:
                return 1.0
                
        except (ValueError, TypeError):
            return 1.0
    
    def _detect_rest_period(self, current_split: Dict, all_splits: List[Dict], index: int) -> bool:
        """Detect if current split represents a rest period"""
        current_pace = current_split.get('pace_per_mile', 0)
        
        if current_pace == 0:
            return False
        
        # Look at surrounding splits for context
        window_size = min(3, len(all_splits) - index - 1)
        if window_size < 1:
            return False
        
        nearby_paces = []
        for i in range(max(0, index - window_size), min(len(all_splits), index + window_size + 1)):
            if i != index and all_splits[i].get('pace_per_mile', 0) > 0:
                nearby_paces.append(all_splits[i]['pace_per_mile'])
        
        if not nearby_paces:
            return False
        
        avg_nearby_pace = np.mean(nearby_paces)
        
        # Consider it a rest if pace is >50% slower than surrounding splits
        return current_pace > avg_nearby_pace * 1.5
    
    def _find_nearby_aid_station(self, mile: float, aid_stations: List[Dict], radius: float = 5.0) -> Optional[Dict]:
        """
        Find aid station within radius of given mile, accounting for GPS variations.
        Uses expanded 5-mile radius to account for GPS drift and different route tracking.
        """
        nearby = [aid for aid in aid_stations 
                 if abs(aid['distance_miles'] - mile) <= radius]
        
        if not nearby:
            return None
            
        # Return closest aid station, accounting for GPS variation
        closest = min(nearby, key=lambda x: abs(x['distance_miles'] - mile))
        
        # For debugging: log when we're making GPS-corrected associations
        distance = abs(closest['distance_miles'] - mile)
        if distance > 2.0:  # Log when we're correcting >2 miles
            print(f"GPS Correction: Mile {mile} → {closest['name']} (actual: {closest['distance_miles']}mi, diff: {distance:.1f}mi)")
        
        return closest
    
    def _calculate_distance_to_aid(self, mile: float, aid_station: Dict) -> float:
        """Calculate distance to aid station"""
        return abs(mile - aid_station['distance_miles'])
    
    def _infer_rest_reason(self, pace_ratio: float, nearby_aid: Optional[Dict]) -> str:
        """Infer likely reason for rest period"""
        if nearby_aid:
            if pace_ratio > 5.0:
                return "Extended aid station stop"
            elif pace_ratio > 3.0:
                return "Aid station resupply"
            else:
                return "Brief aid station stop"
        else:
            if pace_ratio > 4.0:
                return "Medical/equipment issue"
            elif pace_ratio > 2.5:
                return "Rest break"
            else:
                return "Terrain difficulty"
    
    def _calculate_elevation_tolerance(self, segment_performance: List[Dict]) -> str:
        """Calculate runner's tolerance for elevation changes"""
        elevation_performance = [(s.get('elevation_gain_feet', 0), s['performance_score']) 
                               for s in segment_performance if s.get('elevation_gain_feet', 0) > 0]
        
        if len(elevation_performance) < 2:
            return "Insufficient data"
        
        # Simple correlation between elevation and performance
        elevations = [e[0] for e in elevation_performance]
        performances = [e[1] for e in elevation_performance]
        
        correlation = np.corrcoef(elevations, performances)[0, 1]
        
        if correlation > 0.1:
            return "Strong uphill runner"
        elif correlation > -0.1:
            return "Moderate elevation tolerance"
        else:
            return "Struggles with elevation"
    
    def _generate_strategy_text(self, segment: Dict, effort: float) -> str:
        """Generate strategy text for a segment"""
        terrain = segment['terrain_type']
        difficulty = segment['difficulty_rating']
        elevation_gain = segment.get('elevation_gain_feet', 0)
        
        # Ultra-endurance appropriate effort descriptions
        if effort > 0.73:
            effort_text = "Steady, sustainable effort"
        elif effort > 0.68:
            effort_text = "Moderate, controlled pace"
        elif effort > 0.62:
            effort_text = "Conservative, energy-saving approach"
        else:
            effort_text = "Very conservative, recovery focus"
        
        # Add terrain-specific ultra advice
        if difficulty >= 4.5:
            terrain_advice = "Focus on form and nutrition during this challenging section"
        elif elevation_gain > 2000:
            terrain_advice = "Power hike climbs, save legs for later"
        elif difficulty <= 2:
            terrain_advice = "Good section for nutrition and mental recovery"
        else:
            terrain_advice = f"Maintain rhythm through {terrain} terrain"
        
        return f"{effort_text}. {terrain_advice}"
    
    def _generate_overall_strategy(self, fatigue_analysis: Dict, course_analysis: Dict) -> str:
        """Generate overall race strategy recommendation"""
        avg_fatigue = fatigue_analysis.get('average_fatigue', 1.0)
        best_terrain = course_analysis.get('strongest_terrain', 'unknown')
        worst_terrain = course_analysis.get('weakest_terrain', 'unknown')
        
        strategy = []
        
        # Ultra-endurance specific overall strategy
        strategy.append("Prioritize consistency and sustainability over speed")
        
        if avg_fatigue > 1.2:
            strategy.append("Focus on damage control and energy management in later sections")
        else:
            strategy.append("Maintain steady effort with emphasis on nutrition and hydration")
        
        strategy.append(f"Leverage strengths on {best_terrain} terrain for mental boosts")
        strategy.append(f"Prepare for {worst_terrain} sections with extra nutrition and patience")
        strategy.append("Remember: finishing strong is more valuable than early time gains")
        
        return ". ".join(strategy) + "."
    
    def _identify_critical_segments(self, segments: List[Dict], course_analysis: Dict) -> List[str]:
        """Identify the most critical race segments"""
        critical = []
        
        # High difficulty segments
        high_difficulty = [s['segment_name'] for s in segments if s['difficulty_rating'] >= 4]
        critical.extend(high_difficulty)
        
        # Segments with poor historical performance (adjusted for new scoring scale)
        segment_analysis = course_analysis.get('segment_analysis', [])
        poor_performance = [s['segment_name'] for s in segment_analysis 
                          if s['performance_score'] < 0.4]  # Below average performance
        critical.extend(poor_performance)
        
        return list(set(critical))  # Remove duplicates
    
    def _analyze_aid_station_stop(self, aid_station: Optional[Dict], pace_increase: float, 
                                rest_duration: float, current_split: Dict, 
                                all_splits: List[Dict], split_index: int) -> Dict:
        """Analyze the nature of an aid station stop with enhanced context from page 26"""
        if not aid_station:
            return {
                'reason': 'Trail issue or unplanned stop',
                'confidence': 'low',
                'rest_type': 'unknown'
            }
        
        station_name = aid_station['name']
        is_sleep_station = aid_station.get('sleep_station') == 1
        has_crew_access = aid_station.get('crew_access') == 1
        has_medic = aid_station.get('has_medic') == 1
        has_drop_bags = aid_station.get('drop_bags') == 1
        is_gear_check = aid_station.get('gear_check', '') != '' and aid_station.get('gear_check', '') != 'No'
        has_pacer_access = aid_station.get('pacer_access') == 1
        
        # Enhanced analysis using GPS-corrected aid station context
        if rest_duration > 60 and is_sleep_station:  # >1 hour at official sleep station
            return {
                'reason': f'Extended rest/sleep at {station_name} sleep station',
                'confidence': 'high',
                'rest_type': 'sleep'
            }
        elif rest_duration > 90 and has_crew_access:  # >1.5 hours at crew-accessible station - likely sleep with crew
            return {
                'reason': f'Crew-supported sleep rest at {station_name}',
                'confidence': 'high',
                'rest_type': 'crew_sleep'
            }
        elif rest_duration > 60 and has_crew_access:  # 1-1.5 hours at crew-accessible station
            return {
                'reason': f'Extended crew rest at {station_name}',
                'confidence': 'high',
                'rest_type': 'crew_extended_rest'
            }
        elif rest_duration > 30 and is_sleep_station:  # 30-60 min at sleep station
            return {
                'reason': f'Long rest at {station_name} sleep station',
                'confidence': 'high',
                'rest_type': 'extended_rest'
            }
        elif rest_duration > 45 and has_crew_access:  # 45+ min at crew-accessible station
            return {
                'reason': f'Significant crew support at {station_name}',
                'confidence': 'medium',
                'rest_type': 'crew_support'
            }
        elif rest_duration > 20 and has_medic:  # Medical attention at station with medic
            return {
                'reason': f'Medical attention at {station_name}',
                'confidence': 'medium',
                'rest_type': 'medical'
            }
        elif rest_duration > 20 and has_drop_bags:  # Drop bag organization/gear change
            return {
                'reason': f'Drop bag organization at {station_name}',
                'confidence': 'medium', 
                'rest_type': 'drop_bag_stop'
            }
        elif rest_duration > 15 and is_gear_check:  # Mandatory gear check
            return {
                'reason': f'Mandatory gear check at {station_name}',
                'confidence': 'high',
                'rest_type': 'gear_check'
            }
        elif rest_duration > 15 and has_crew_access:
            return {
                'reason': f'Crew resupply/support at {station_name}',
                'confidence': 'medium',
                'rest_type': 'crew_resupply'
            }
        elif rest_duration > 10:
            return {
                'reason': f'Standard aid station stop at {station_name}',
                'confidence': 'medium',
                'rest_type': 'aid_stop'
            }
        else:
            return {
                'reason': f'Quick stop at {station_name}',
                'confidence': 'low',
                'rest_type': 'quick_stop'
            }
    
    def _analyze_aid_station_patterns(self, aid_station_stops: List[Dict]) -> Dict:
        """Analyze patterns in aid station usage"""
        if not aid_station_stops:
            return {}
        
        total_stops = len(aid_station_stops)
        sleep_stops = [stop for stop in aid_station_stops if stop['is_sleep_station']]
        sleep_station_usage = len(sleep_stops)
        
        # Count potential sleep locations (official sleep stations + crew aid stations)
        crew_sleep_opportunities = 10  # 4 official sleep stations + 6 crew aid stations
        
        # Calculate average rest times by station type
        regular_stops = [stop for stop in aid_station_stops if not stop['is_sleep_station']]
        avg_regular_rest = np.mean([stop['rest_duration_minutes'] for stop in regular_stops]) if regular_stops else 0
        avg_sleep_rest = np.mean([stop['rest_duration_minutes'] for stop in sleep_stops]) if sleep_stops else 0
        
        # Identify longest rest
        longest_rest = max(aid_station_stops, key=lambda x: x['rest_duration_minutes']) if aid_station_stops else None
        
        # Count crew-assisted rest periods
        crew_rest_count = len([stop for stop in aid_station_stops 
                             if stop.get('rest_type', '').startswith('crew')])
        
        return {
            'total_aid_station_stops': total_stops,
            'sleep_station_usage': sleep_station_usage,
            'crew_rest_usage': crew_rest_count,
            'sleep_opportunity_utilization_rate': (sleep_station_usage + crew_rest_count) / crew_sleep_opportunities,
            'official_sleep_station_rate': sleep_station_usage / 4.0,  # 4 official sleep stations
            'crew_aid_utilization_rate': crew_rest_count / 6.0,  # 6 crew aid stations
            'average_regular_stop_minutes': avg_regular_rest,
            'average_sleep_stop_minutes': avg_sleep_rest,
            'longest_rest_station': longest_rest['station_name'] if longest_rest else None,
            'longest_rest_duration': longest_rest['rest_duration_minutes'] if longest_rest else 0,
            'rest_strategy': self._infer_rest_strategy(aid_station_stops)
        }
    
    def _infer_rest_strategy(self, aid_station_stops: List[Dict]) -> str:
        """Infer the runner's overall rest strategy"""
        if not aid_station_stops:
            return 'minimal_stops'
        
        sleep_stops = [stop for stop in aid_station_stops if stop['is_sleep_station']]
        crew_sleep_stops = [stop for stop in aid_station_stops 
                           if stop.get('rest_type', '').startswith('crew_sleep') or 
                              stop.get('rest_type', '').startswith('crew_extended_rest')]
        
        total_sleep_opportunities = len(sleep_stops) + len(crew_sleep_stops)
        avg_sleep_time = np.mean([stop['rest_duration_minutes'] for stop in sleep_stops + crew_sleep_stops]) if sleep_stops or crew_sleep_stops else 0
        
        crew_usage = len([stop for stop in aid_station_stops 
                         if stop.get('rest_type', '').startswith('crew')])
        
        if total_sleep_opportunities >= 3 and avg_sleep_time > 60:
            return 'conservative_with_sleep'
        elif total_sleep_opportunities >= 2 and avg_sleep_time > 30:
            return 'planned_rest_stops'
        elif total_sleep_opportunities == 1 and avg_sleep_time > 60:
            return 'single_long_sleep'
        elif crew_usage >= 4:
            return 'crew_dependent_strategy'
        elif crew_usage >= 2:
            return 'crew_assisted_strategy'
        elif len(aid_station_stops) > 10:
            return 'frequent_aid_usage'
        else:
            return 'minimal_aid_usage'
    
    def _get_segment_benchmarks(self, race_id: int, segments: List[Dict]) -> Dict:
        """
        Get benchmark performance data for each segment:
        - Segment leader (fastest pace on this segment)
        - Overall race winner's pace on this segment
        - Field average pace on this segment
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get all runners' data for comparison
        cursor.execute("""
            SELECT r.id as runner_id, r.first_name, r.last_name, 
                   s.mile_number, 
                   CASE 
                       WHEN s.split_time_seconds > 0 THEN s.split_time_seconds / 60.0
                       ELSE 12.0 
                   END as pace_per_mile,
                   s.cumulative_time_seconds
            FROM runners r
            JOIN race_results rr ON r.id = rr.runner_id
            JOIN splits s ON rr.id = s.race_result_id
            WHERE rr.race_id = ? AND s.split_time_seconds > 0
            ORDER BY r.id, s.mile_number
        """, (race_id,))
        
        all_splits_data = cursor.fetchall()
        conn.close()
        
        # Group by runner
        runners_data = {}
        for row in all_splits_data:
            runner_id = row['runner_id']
            if runner_id not in runners_data:
                runners_data[runner_id] = {
                    'name': f"{row['first_name']} {row['last_name']}",
                    'splits': [],
                    'total_time': 0
                }
            runners_data[runner_id]['splits'].append({
                'mile_number': row['mile_number'],
                'pace_per_mile': row['pace_per_mile'],
                'cumulative_time': row['cumulative_time_seconds'] or 0
            })
        
        # Find overall race winner (fastest total time)
        race_winner_id = None
        fastest_time = float('inf')
        for runner_id, data in runners_data.items():
            if data['splits']:
                final_time = max([s['cumulative_time'] for s in data['splits']])
                if final_time > 0 and final_time < fastest_time:
                    fastest_time = final_time
                    race_winner_id = runner_id
        
        benchmarks = {}
        
        for segment in segments:
            start_mile = segment['start_mile']
            end_mile = segment['end_mile']
            segment_name = segment['segment_name']
            
            # Collect all runners' performance on this segment
            segment_paces = []
            race_winner_pace = None
            segment_leader_pace = None
            
            for runner_id, data in runners_data.items():
                runner_splits = data['splits']
                
                # Get splits within this segment
                segment_splits = [s for s in runner_splits 
                                if start_mile <= s['mile_number'] < end_mile]
                
                if segment_splits:
                    avg_pace = np.mean([s['pace_per_mile'] for s in segment_splits])
                    segment_paces.append(avg_pace)
                    
                    # Track race winner's performance on this segment
                    if runner_id == race_winner_id:
                        race_winner_pace = avg_pace
            
            # Calculate benchmarks
            if segment_paces:
                segment_leader_pace = min(segment_paces)  # Fastest pace (lowest number)
                field_average = np.mean(segment_paces)
                field_median = np.median(segment_paces)
                
                benchmarks[segment_name] = {
                    'segment_leader_pace': segment_leader_pace,
                    'race_winner_pace': race_winner_pace or segment_leader_pace,
                    'field_average_pace': field_average,
                    'field_median_pace': field_median,
                    'field_size': len(segment_paces)
                }
        
        return benchmarks
    
    def _calculate_relative_performance_score(self, runner_pace: float, 
                                           segment: Dict, benchmark: Dict) -> float:
        """
        Calculate a more nuanced performance score (0.0 to 1.0+) that considers:
        - How runner performed vs segment leader
        - How runner performed vs race winner
        - How runner performed vs field average
        - Terrain difficulty adjustments
        
        Score interpretation:
        1.0+ = Elite performance (better than segment leader)
        0.8-1.0 = Excellent performance (top 20%)
        0.6-0.8 = Good performance (above average)
        0.4-0.6 = Average performance (middle of pack)
        0.2-0.4 = Below average performance
        0.0-0.2 = Poor performance
        """
        if runner_pace <= 0 or not benchmark:
            return 0.0
        
        segment_leader_pace = benchmark.get('segment_leader_pace', runner_pace)
        race_winner_pace = benchmark.get('race_winner_pace', runner_pace)
        field_average_pace = benchmark.get('field_average_pace', runner_pace)
        
        # Base score: how close runner is to segment leader (inverted for pace)
        if segment_leader_pace > 0:
            leader_ratio = segment_leader_pace / runner_pace
        else:
            leader_ratio = 0.5
        
        # Bonus for being faster than race winner on this segment
        race_winner_bonus = 0.0
        if race_winner_pace > 0:
            if runner_pace < race_winner_pace:
                race_winner_bonus = 0.1 * (race_winner_pace - runner_pace) / race_winner_pace
        
        # Field position component (how much better than average)
        field_position_score = 0.0
        if field_average_pace > 0:
            if runner_pace < field_average_pace:  # Better than average
                field_position_score = 0.3 * (field_average_pace - runner_pace) / field_average_pace
            else:  # Worse than average
                field_position_score = -0.2 * (runner_pace - field_average_pace) / field_average_pace
        
        # Terrain difficulty adjustment - give credit for performing well on hard terrain
        difficulty_rating = segment.get('difficulty_rating', 3)
        difficulty_bonus = 0.0
        if difficulty_rating > 3 and leader_ratio > 0.8:  # Good performance on hard terrain
            difficulty_bonus = 0.05 * (difficulty_rating - 3) * leader_ratio
        
        # Combine components
        final_score = leader_ratio + race_winner_bonus + field_position_score + difficulty_bonus
        
        # Cap at reasonable bounds (allow scores above 1.0 for exceptional performance)
        return max(0.0, min(1.5, final_score))
    
    def _calculate_segment_performance_metrics(self, race_id: int, aid_stations: List[Dict]) -> Dict:
        """
        Calculate performance metrics for each segment to inform difficulty rating.
        Returns data about how runners actually performed on each segment.
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Get all runners' split data
        cursor.execute("""
            SELECT r.id as runner_id, s.mile_number, 
                   CASE 
                       WHEN s.split_time_seconds > 0 THEN s.split_time_seconds / 60.0
                       ELSE 12.0 
                   END as pace_per_mile
            FROM runners r
            JOIN race_results rr ON r.id = rr.runner_id
            JOIN splits s ON rr.id = s.race_result_id
            WHERE rr.race_id = ? AND s.split_time_seconds > 0
            ORDER BY r.id, s.mile_number
        """, (race_id,))
        
        all_splits = cursor.fetchall()
        conn.close()
        
        # Group by runner
        runners_data = {}
        for row in all_splits:
            runner_id = row['runner_id']
            if runner_id not in runners_data:
                runners_data[runner_id] = []
            runners_data[runner_id].append({
                'mile_number': row['mile_number'],
                'pace_per_mile': row['pace_per_mile']
            })
        
        # Calculate segment metrics
        segment_metrics = {}
        
        for i in range(len(aid_stations) - 1):
            start_mile = aid_stations[i]['distance_miles']
            end_mile = aid_stations[i + 1]['distance_miles']
            segment_name = f"{aid_stations[i]['name']} to {aid_stations[i + 1]['name']}"
            
            segment_paces = []
            pace_increases = []  # How much slower compared to runner's baseline
            
            for runner_id, splits in runners_data.items():
                # Get splits for this segment
                segment_splits = [s for s in splits 
                                if start_mile <= s['mile_number'] < end_mile]
                
                if segment_splits:
                    avg_segment_pace = np.mean([s['pace_per_mile'] for s in segment_splits])
                    segment_paces.append(avg_segment_pace)
                    
                    # Calculate baseline pace from early race (first 20% of splits)
                    early_splits = splits[:max(1, len(splits) // 5)]
                    if early_splits:
                        baseline_pace = np.mean([s['pace_per_mile'] for s in early_splits])
                        pace_increase = avg_segment_pace / baseline_pace if baseline_pace > 0 else 1.0
                        pace_increases.append(pace_increase)
            
            # Calculate segment metrics
            if segment_paces and pace_increases:
                segment_metrics[segment_name] = {
                    'average_pace': np.mean(segment_paces),
                    'pace_variance': np.var(segment_paces),
                    'median_pace': np.median(segment_paces),
                    'average_pace_increase': np.mean(pace_increases),  # Key difficulty indicator
                    'pace_increase_variance': np.var(pace_increases),
                    'runner_count': len(segment_paces),
                    'distance': end_mile - start_mile
                }
        
        return segment_metrics
    
    def _calculate_segment_difficulty(self, start_mile: float, end_mile: float, 
                                    segment_name: str, start_aid: Dict, end_aid: Dict,
                                    performance_data: Dict) -> float:
        """Wrapper method that returns just the difficulty score for backward compatibility"""
        result = self._calculate_segment_difficulty_detailed(start_mile, end_mile, segment_name, start_aid, end_aid, performance_data)
        print(f"Simple difficulty method called for {segment_name}, returning: {result['difficulty']}")
        return result['difficulty']
    
    def _calculate_segment_difficulty_detailed(self, start_mile: float, end_mile: float, 
                                    segment_name: str, start_aid: Dict, end_aid: Dict,
                                    performance_data: Dict) -> Dict:
        """
        Calculate difficulty rating (1.0-5.0) based on multiple factors:
        - Elevation gain/loss (primary factor - feet per mile)
        - Performance data (how much runners slow down)  
        - Distance factors (longer segments are harder)
        - Race position (fatigue accumulation)
        - Aid station characteristics (technical terrain indicators)
        - Known challenging segments (Cocodona-specific)
        
        Scale:
        1.0-1.5 = Very Easy (flat, fast runnable terrain)
        1.5-2.5 = Easy (minimal elevation, mostly runnable)
        2.5-3.5 = Moderate (some climbing, mixed terrain)
        3.5-4.5 = Hard (significant elevation gain/technical terrain)  
        4.5-5.0 = Extreme (very steep climbs, major elevation changes)
        """
        
        # Base difficulty starts at moderate
        difficulty = 3.0
        factors = []
                
        # Ensure aid station data is not None
        if start_aid is None:
            start_aid = {}
        if end_aid is None:
            end_aid = {}
        
        # Factor 1: Elevation gain (primary difficulty factor)
        try:
            elevation_change = self._calculate_elevation_change(start_mile, end_mile)
            elevation_gain = elevation_change.get('gain', 0) if elevation_change else 0
            elevation_loss = elevation_change.get('loss', 0) if elevation_change else 0
        except Exception as e:
            print(f"Error calculating elevation change for {segment_name}: {e}")
            elevation_gain = 0
            elevation_loss = 0
            elevation_change = {'gain': 0, 'loss': 0}
        
        segment_distance = end_mile - start_mile
        
        elevation_adjustments = []
        if segment_distance > 0:
            # Calculate elevation gain per mile (feet/mile)
            gain_per_mile = elevation_gain / segment_distance
            loss_per_mile = elevation_loss / segment_distance
            
            # Elevation gain difficulty (major factor)
            if gain_per_mile > 400:  # Very steep climb (>400 ft/mile)
                difficulty += 1.8
                elevation_adjustments.append(f"Very steep climb ({gain_per_mile:.0f} ft/mi): +1.8")
            elif gain_per_mile > 250:  # Steep climb (250-400 ft/mile)
                difficulty += 1.2
                elevation_adjustments.append(f"Steep climb ({gain_per_mile:.0f} ft/mi): +1.2")
            elif gain_per_mile > 150:  # Moderate climb (150-250 ft/mile)
                difficulty += 0.8
                elevation_adjustments.append(f"Moderate climb ({gain_per_mile:.0f} ft/mi): +0.8")
            elif gain_per_mile > 75:   # Gentle climb (75-150 ft/mile)
                difficulty += 0.4
                elevation_adjustments.append(f"Gentle climb ({gain_per_mile:.0f} ft/mi): +0.4")
            elif gain_per_mile < 25:   # Mostly flat
                difficulty -= 0.2
                elevation_adjustments.append(f"Mostly flat ({gain_per_mile:.0f} ft/mi): -0.2")
            else:
                elevation_adjustments.append(f"Minor elevation gain ({gain_per_mile:.0f} ft/mi): +0.0")
                
            # Steep descents also add difficulty (technical, harder on legs)
            if loss_per_mile > 300:    # Very steep descent
                difficulty += 0.6
                elevation_adjustments.append(f"Very steep descent ({loss_per_mile:.0f} ft/mi): +0.6")
            elif loss_per_mile > 150:  # Moderate descent
                difficulty += 0.3
                elevation_adjustments.append(f"Moderate descent ({loss_per_mile:.0f} ft/mi): +0.3")
                
            # Major elevation swings (both up and down) add complexity
            if gain_per_mile > 100 and loss_per_mile > 100:
                difficulty += 0.4  # Rolling terrain bonus
                elevation_adjustments.append("Rolling terrain (high gain + loss): +0.4")
                
        factors.append({
            'category': 'Elevation',
            'details': elevation_adjustments
        })
        
        # Factor 2: Performance-based difficulty
        performance_adjustments = []
        if performance_data:
            pace_increase = performance_data.get('average_pace_increase', 1.0)
            pace_variance = performance_data.get('pace_increase_variance', 0.0)
            
            # High pace increase = harder segment (but weight less than elevation)
            if pace_increase > 1.4:  # 40% slower than baseline
                difficulty += 1.0
                performance_adjustments.append(f"Runners 40%+ slower: +1.0")
            elif pace_increase > 1.2:  # 20% slower than baseline  
                difficulty += 0.7
                performance_adjustments.append(f"Runners 20%+ slower: +0.7")
            elif pace_increase > 1.1:  # 10% slower than baseline
                difficulty += 0.4
                performance_adjustments.append(f"Runners 10%+ slower: +0.4")
            elif pace_increase < 0.95:  # Actually faster (downhill/easy)
                difficulty -= 0.3
                performance_adjustments.append(f"Runners faster than baseline: -0.3")
            
            # High variance = inconsistent/technical terrain
            if pace_variance > 0.3:
                difficulty += 0.2
                performance_adjustments.append(f"High pace variance (technical): +0.2")
        
        if performance_adjustments:
            factors.append({'category': 'Performance Data', 'details': performance_adjustments})
        
        # Factor 3: Distance factor (longer segments are harder)
        distance_adjustments = []
        if segment_distance > 20:
            difficulty += 0.5
            distance_adjustments.append(f"Very long segment ({segment_distance:.1f} mi): +0.5")
        elif segment_distance > 15:
            difficulty += 0.3
            distance_adjustments.append(f"Long segment ({segment_distance:.1f} mi): +0.3")
        elif segment_distance < 5:
            difficulty -= 0.2
            distance_adjustments.append(f"Short segment ({segment_distance:.1f} mi): -0.2")
        
        if distance_adjustments:
            factors.append({'category': 'Distance', 'details': distance_adjustments})
        
        # Factor 4: Race position factor (fatigue accumulation)
        fatigue_adjustments = []
        if start_mile > 200:  # Final 56 miles - extreme fatigue
            difficulty += 0.8
            fatigue_adjustments.append(f"Final stretch (mile {start_mile:.0f}): +0.8")
        elif start_mile > 150:  # Late race fatigue
            difficulty += 0.5
            fatigue_adjustments.append(f"Late race fatigue (mile {start_mile:.0f}): +0.5")
        elif start_mile > 100:  # Mid-race fatigue building
            difficulty += 0.3
            fatigue_adjustments.append(f"Mid-race fatigue (mile {start_mile:.0f}): +0.3")
        elif start_mile < 20:  # Early race - fresh legs
            difficulty -= 0.2
            fatigue_adjustments.append(f"Early race - fresh legs (mile {start_mile:.0f}): -0.2")
        
        if fatigue_adjustments:
            factors.append({'category': 'Race Position', 'details': fatigue_adjustments})
        
        # Factor 5: Aid station characteristics (terrain indicators)
        aid_station_adjustments = []
        if end_aid.get('sleep_station') and start_mile > 30:  # Not at start
            difficulty += 0.3
            aid_station_adjustments.append("Sleep station (challenging terrain): +0.3")
        
        # Gear check stations indicate challenging terrain ahead
        gear_check = end_aid.get('gear_check', '')
        if gear_check and gear_check != 'No' and 'Cap' not in gear_check:
            difficulty += 0.2
            aid_station_adjustments.append("Gear check station: +0.2")
        
        # Medical stations often at challenging points
        if end_aid.get('has_medic'):
            difficulty += 0.1
            aid_station_adjustments.append("Medical station: +0.1")
        
        if aid_station_adjustments:
            factors.append({'category': 'Aid Station Features', 'details': aid_station_adjustments})
        
        # Factor 6: Specific segment knowledge (Cocodona-specific)
        known_adjustments = []
        segment_lower = segment_name.lower()
        
        # Known challenging segments
        if 'mingus mountain' in segment_lower or 'mingus' in segment_lower:
            difficulty += 0.5  # Major climb
            known_adjustments.append("Mingus Mountain (major climb): +0.5")
        elif 'jerome' in segment_lower:
            difficulty += 0.3  # Technical descent into town
            known_adjustments.append("Jerome descent (technical): +0.3")
        elif 'sedona' in segment_lower and 'posse' in segment_lower:
            difficulty += 0.2  # Red rock technical terrain
            known_adjustments.append("Sedona red rock terrain: +0.2")
        elif 'wildcat hill' in segment_lower:
            difficulty += 0.4  # Late race challenging climb
            known_adjustments.append("Wildcat Hill (challenging climb): +0.4")
        elif 'water station' in segment_lower:
            difficulty -= 0.3  # Usually easier, shorter segments
            known_adjustments.append("Water station (easier segment): -0.3")
        
        if known_adjustments:
            factors.append({'category': 'Known Challenges', 'details': known_adjustments})
        
        # Cap at reasonable bounds
        final_difficulty = max(1.0, min(5.0, difficulty))
        
        result = {
            'difficulty': final_difficulty,
            'base_difficulty': 3.0,
            'factors': factors,
            'final_adjustment': final_difficulty - 3.0
        }
                
        return result
    
    def _determine_terrain_type(self, start_aid: Dict, end_aid: Dict, difficulty: float) -> str:
        """Determine terrain type based on aid stations and difficulty"""
        
        # Use difficulty as primary indicator
        if difficulty >= 4.5:
            return 'technical'
        elif difficulty >= 3.5:
            return 'mountain'  
        elif difficulty >= 2.5:
            return 'mixed'
        elif difficulty >= 1.5:
            return 'runnable'
        else:
            return 'fast'
    
    def _determine_conditions(self, start_mile: float, end_mile: float) -> str:
        """Determine typical conditions based on course position"""
        
        avg_mile = (start_mile + end_mile) / 2
        
        # Cocodona-specific conditions based on course knowledge
        if avg_mile < 40:
            return 'desert_heat'  # Sonoran desert section
        elif avg_mile < 80:
            return 'mountain_cool'  # Bradshaw Mountains
        elif avg_mile < 130:
            return 'mountain_technical'  # Mingus area
        elif avg_mile < 170:
            return 'desert_variable'  # Verde Valley/Sedona
        elif avg_mile < 220:
            return 'high_altitude'  # Coconino Plateau
        else:
            return 'alpine'  # Mount Elden area