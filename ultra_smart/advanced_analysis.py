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

class AdvancedAnalyzer:
    """Advanced analysis engine for ultra-endurance race data"""
    
    def __init__(self, database):
        self.db = database
    
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
                'elevation_gain': segment.get('elevation_gain_feet', 0) if segment else 0,
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
            
            # Look for significant pace increases (indicating slower movement/rest)
            if current_pace > 0 and prev_pace > 0:
                pace_increase = current_pace / prev_pace
                mile = current_split.get('mile_number', i + 1)
                
                # Find nearby aid stations (within 1 mile for more precision)
                nearby_aid = self._find_nearby_aid_station(mile, aid_stations, radius=1.0)
                
                # Significant slowdown (>1.5x normal pace, more sensitive)
                if pace_increase > 1.5:
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
        impact individual runner performance.
        """
        splits = self._get_runner_splits(runner_id, race_id)
        segments = self._get_course_segments(race_id)
        
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
            
            # Calculate performance relative to terrain difficulty
            expected_pace_multiplier = 1.0 + (segment['difficulty_rating'] - 3) * 0.15
            performance_score = 1.0 / (avg_pace * expected_pace_multiplier) if avg_pace > 0 else 0
            
            segment_performance.append({
                'segment_name': segment['segment_name'],
                'start_mile': start_mile,
                'end_mile': end_mile,
                'terrain_type': segment['terrain_type'],
                'difficulty_rating': segment['difficulty_rating'],
                'elevation_gain': segment['elevation_gain_feet'],
                'average_pace': avg_pace,
                'pace_consistency': 1.0 / pace_variance if pace_variance > 0 else 1.0,
                'performance_score': performance_score,
                'typical_conditions': segment['typical_conditions']
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
                recommended_effort = min(0.9, max(0.6, avg_performance))
            else:
                recommended_effort = max(0.8 - (difficulty - 3) * 0.1, 0.6)
            
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
        """Get course segment data - simplified fallback without course_segments table"""
        # Create basic segments based on aid stations if course_segments table doesn't exist
        aid_stations = self._get_aid_stations(race_id)
        
        if not aid_stations:
            return []
        
        segments = []
        for i in range(len(aid_stations) - 1):
            start_mile = aid_stations[i]['distance_miles']
            end_mile = aid_stations[i + 1]['distance_miles']
            
            segments.append({
                'segment_name': f"{aid_stations[i]['name']} to {aid_stations[i + 1]['name']}",
                'start_mile': start_mile,
                'end_mile': end_mile,
                'terrain_type': 'mixed',
                'difficulty_rating': 3,  # Default moderate difficulty
                'elevation_gain_feet': 0,  # Unknown
                'elevation_loss_feet': 0,  # Unknown
                'typical_conditions': 'variable'
            })
        
        return segments
    
    def _get_aid_stations(self, race_id: int) -> List[Dict]:
        """Get aid station data with enhanced information including all context from page 26"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name, distance_miles, 
                   COALESCE(sleep_station, 0) as sleep_station,
                   COALESCE(crew_access, 0) as crew_access,
                   0 as pacer_access,
                   COALESCE(drop_bag_access, 0) as drop_bags,
                   0 as gear_check,
                   0 as has_medic
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
        elevation_performance = [(s['elevation_gain'], s['performance_score']) 
                               for s in segment_performance if s['elevation_gain'] > 0]
        
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
        
        if effort > 0.85:
            effort_text = "Push pace"
        elif effort > 0.75:
            effort_text = "Maintain effort"
        else:
            effort_text = "Conservative approach"
        
        if difficulty >= 4:
            return f"{effort_text}, expect challenging {terrain} terrain"
        else:
            return f"{effort_text}, good opportunity to make time"
    
    def _generate_overall_strategy(self, fatigue_analysis: Dict, course_analysis: Dict) -> str:
        """Generate overall race strategy recommendation"""
        avg_fatigue = fatigue_analysis.get('average_fatigue', 1.0)
        best_terrain = course_analysis.get('strongest_terrain', 'unknown')
        worst_terrain = course_analysis.get('weakest_terrain', 'unknown')
        
        strategy = []
        
        if avg_fatigue > 1.2:
            strategy.append("Focus on consistent pacing to manage fatigue buildup")
        else:
            strategy.append("Solid pacing control allows for strategic pushes")
        
        strategy.append(f"Maximize time on {best_terrain} terrain")
        strategy.append(f"Use conservative approach on {worst_terrain} sections")
        
        return "; ".join(strategy)
    
    def _identify_critical_segments(self, segments: List[Dict], course_analysis: Dict) -> List[str]:
        """Identify the most critical race segments"""
        critical = []
        
        # High difficulty segments
        high_difficulty = [s['segment_name'] for s in segments if s['difficulty_rating'] >= 4]
        critical.extend(high_difficulty)
        
        # Segments with poor historical performance
        segment_analysis = course_analysis.get('segment_analysis', [])
        poor_performance = [s['segment_name'] for s in segment_analysis 
                          if s['performance_score'] < 0.7]
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
        is_gear_check = aid_station.get('gear_check') == 1
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