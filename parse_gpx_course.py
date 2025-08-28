#!/usr/bin/env python3
"""
Parse Cocodona 250 GPX file to extract course data and elevation profile
"""
import xml.etree.ElementTree as ET
import json
import math
import requests
import time
from typing import List, Dict, Tuple

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great circle distance between two points in kilometers"""
    R = 6371  # Earth's radius in kilometers
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c

def miles_to_km(miles: float) -> float:
    return miles * 1.60934

def km_to_miles(km: float) -> float:
    return km / 1.60934

def get_elevation_data(coordinates: List[Tuple[float, float]], batch_size: int = 100) -> List[float]:
    """
    Get elevation data for coordinates using Open Elevation API
    coordinates: List of (lat, lon) tuples
    batch_size: Number of coordinates to process per API call
    Returns: List of elevation values in meters
    """
    elevations = []
    
    print(f"Fetching elevation data for {len(coordinates)} points...")
    
    for i in range(0, len(coordinates), batch_size):
        batch = coordinates[i:i+batch_size]
        
        try:
            # Prepare API request
            locations = []
            for lat, lon in batch:
                locations.append({"latitude": lat, "longitude": lon})
            
            # Make API request to Open Elevation
            response = requests.post(
                'https://api.open-elevation.com/api/v1/lookup',
                json={"locations": locations},
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                batch_elevations = [result['elevation'] for result in data['results']]
                elevations.extend(batch_elevations)
                print(f"  Retrieved elevation for batch {i//batch_size + 1}/{(len(coordinates)-1)//batch_size + 1}")
            else:
                print(f"  API error for batch {i//batch_size + 1}: {response.status_code}")
                # Fill with None values for failed batch
                elevations.extend([None] * len(batch))
            
            # Rate limiting - be respectful to the free API
            if i + batch_size < len(coordinates):
                time.sleep(1)
                
        except Exception as e:
            print(f"  Error fetching elevation for batch {i//batch_size + 1}: {e}")
            # Fill with None values for failed batch
            elevations.extend([None] * len(batch))
    
    print(f"Retrieved elevation data for {len([e for e in elevations if e is not None])} out of {len(coordinates)} points")
    return elevations

def parse_gpx_file(gpx_file_path: str, fetch_elevation: bool = True) -> Dict:
    """Parse GPX file and extract course data with elevation"""
    
    print(f"Parsing GPX file: {gpx_file_path}")
    
    # Parse XML
    tree = ET.parse(gpx_file_path)
    root = tree.getroot()
    
    # Define namespace
    ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}
    
    # Extract waypoints (aid stations)
    waypoints = []
    for wpt in root.findall('gpx:wpt', ns):
        lat = float(wpt.get('lat'))
        lon = float(wpt.get('lon'))
        elevation = None
        
        ele_elem = wpt.find('gpx:ele', ns)
        if ele_elem is not None:
            elevation = float(ele_elem.text)
        
        name_elem = wpt.find('gpx:name', ns)
        name = name_elem.text if name_elem is not None else f"Waypoint at {lat:.4f},{lon:.4f}"
        
        # Extract mile marker from name if present
        mile_marker = None
        if 'M0' in name and ' - ' in name:
            try:
                mile_part = name.split(' - ')[0]
                if mile_part.startswith('M'):
                    mile_marker = float(mile_part[1:])
            except:
                pass
        
        waypoints.append({
            'name': name,
            'lat': lat,
            'lon': lon,
            'elevation_feet': elevation * 3.28084 if elevation else None,  # Convert meters to feet
            'elevation_meters': elevation,
            'mile_marker': mile_marker
        })
    
    # Extract track points
    track_points = []
    total_distance_km = 0.0
    
    for trk in root.findall('gpx:trk', ns):
        for trkseg in trk.findall('gpx:trkseg', ns):
            prev_lat, prev_lon = None, None
            
            for trkpt in trkseg.findall('gpx:trkpt', ns):
                lat = float(trkpt.get('lat'))
                lon = float(trkpt.get('lon'))
                
                elevation = None
                ele_elem = trkpt.find('gpx:ele', ns)
                if ele_elem is not None:
                    elevation = float(ele_elem.text)
                
                # Calculate cumulative distance
                if prev_lat is not None and prev_lon is not None:
                    segment_distance = haversine_distance(prev_lat, prev_lon, lat, lon)
                    total_distance_km += segment_distance
                
                track_points.append({
                    'lat': lat,
                    'lon': lon,
                    'elevation_feet': elevation * 3.28084 if elevation else None,
                    'elevation_meters': elevation,
                    'distance_km': total_distance_km,
                    'distance_miles': km_to_miles(total_distance_km)
                })
                
                prev_lat, prev_lon = lat, lon
    
    print(f"Extracted {len(waypoints)} waypoints and {len(track_points)} track points")
    print(f"Total course distance: {km_to_miles(total_distance_km):.1f} miles")
    
    # Fetch elevation data if not present in GPX and requested
    if fetch_elevation and track_points and track_points[0]['elevation_meters'] is None:
        print("No elevation data found in GPX file. Fetching from Open Elevation API...")
        
        # Sample track points for elevation (every 10th point to reduce API calls)
        sample_interval = max(1, len(track_points) // 1000)  # Sample to ~1000 points max
        sampled_indices = list(range(0, len(track_points), sample_interval))
        sampled_coordinates = [(track_points[i]['lat'], track_points[i]['lon']) for i in sampled_indices]
        
        # Get elevation data for sampled points
        elevations_meters = get_elevation_data(sampled_coordinates, batch_size=50)
        
        # Interpolate elevation for all track points
        for i, track_point in enumerate(track_points):
            # Find nearest sampled point
            nearest_sample_idx = min(range(len(sampled_indices)), 
                                   key=lambda x: abs(sampled_indices[x] - i))
            
            if nearest_sample_idx < len(elevations_meters) and elevations_meters[nearest_sample_idx] is not None:
                elevation_meters = elevations_meters[nearest_sample_idx]
                track_point['elevation_meters'] = elevation_meters
                track_point['elevation_feet'] = elevation_meters * 3.28084
        
        # Also fetch elevation for waypoints
        waypoint_coords = [(w['lat'], w['lon']) for w in waypoints]
        waypoint_elevations = get_elevation_data(waypoint_coords, batch_size=25)
        
        for i, waypoint in enumerate(waypoints):
            if i < len(waypoint_elevations) and waypoint_elevations[i] is not None:
                elevation_meters = waypoint_elevations[i]
                waypoint['elevation_meters'] = elevation_meters
                waypoint['elevation_feet'] = elevation_meters * 3.28084
    
    # Match waypoints to track points to get accurate distances
    matched_waypoints = []
    for waypoint in waypoints:
        closest_point = None
        min_distance = float('inf')
        
        for track_point in track_points:
            distance = haversine_distance(
                waypoint['lat'], waypoint['lon'],
                track_point['lat'], track_point['lon']
            )
            if distance < min_distance:
                min_distance = distance
                closest_point = track_point
        
        if closest_point:
            waypoint['distance_miles'] = closest_point['distance_miles']
            waypoint['distance_km'] = closest_point['distance_km']
            if not waypoint['elevation_feet'] and closest_point['elevation_feet']:
                waypoint['elevation_feet'] = closest_point['elevation_feet']
                waypoint['elevation_meters'] = closest_point['elevation_meters']
        
        matched_waypoints.append(waypoint)
    
    # Create elevation profile summary
    elevation_profile = []
    for i in range(0, len(track_points), max(1, len(track_points) // 100)):  # Sample 100 points
        point = track_points[i]
        if point['elevation_feet']:
            elevation_profile.append({
                'mile': point['distance_miles'],
                'elevation_feet': point['elevation_feet']
            })
    
    # Calculate elevation stats
    elevations = [p['elevation_feet'] for p in track_points if p['elevation_feet']]
    elevation_stats = {
        'min_elevation': min(elevations) if elevations else None,
        'max_elevation': max(elevations) if elevations else None,
        'total_gain': 0,  # Will calculate this separately
        'total_loss': 0   # Will calculate this separately
    }
    
    # Calculate elevation gain/loss
    if elevations:
        prev_elevation = elevations[0]
        for elevation in elevations[1:]:
            if elevation > prev_elevation:
                elevation_stats['total_gain'] += elevation - prev_elevation
            else:
                elevation_stats['total_loss'] += prev_elevation - elevation
            prev_elevation = elevation
    
    return {
        'waypoints': matched_waypoints,
        'track_points': track_points,
        'elevation_profile': elevation_profile,
        'elevation_stats': elevation_stats,
        'course_stats': {
            'total_distance_miles': km_to_miles(total_distance_km),
            'total_distance_km': total_distance_km,
            'num_waypoints': len(waypoints),
            'num_track_points': len(track_points)
        }
    }

def create_web_friendly_data(course_data: Dict) -> Dict:
    """Create web-friendly version of course data for frontend map"""
    
    # Sample track points for web display (reduce to ~500 points for performance)
    track_sample_size = min(500, len(course_data['track_points']))
    step_size = max(1, len(course_data['track_points']) // track_sample_size)
    
    web_track_points = []
    for i in range(0, len(course_data['track_points']), step_size):
        point = course_data['track_points'][i]
        web_track_points.append([
            round(point['lat'], 6),
            round(point['lon'], 6),
            round(point['elevation_feet'], 1) if point['elevation_feet'] else None
        ])
    
    # Waypoints for map markers
    web_waypoints = []
    for waypoint in course_data['waypoints']:
        web_waypoints.append({
            'name': waypoint['name'],
            'lat': round(waypoint['lat'], 6),
            'lon': round(waypoint['lon'], 6),
            'elevation': round(waypoint['elevation_feet'], 1) if waypoint['elevation_feet'] else None,
            'mile': round(waypoint['distance_miles'], 1) if waypoint.get('distance_miles') else waypoint.get('mile_marker')
        })
    
    return {
        'track_points': web_track_points,  # [lat, lon, elevation]
        'waypoints': web_waypoints,
        'bounds': {
            'north': max(p[0] for p in web_track_points),
            'south': min(p[0] for p in web_track_points),
            'east': max(p[1] for p in web_track_points),
            'west': min(p[1] for p in web_track_points)
        },
        'elevation_profile': course_data['elevation_profile'],
        'stats': course_data['elevation_stats']
    }

if __name__ == "__main__":
    gpx_file = "/home/jasongarcia24/Documents/ultra-smart/data/cocodona_250_2025_map.gpx"
    
    try:
        # Parse GPX file with elevation fetching
        course_data = parse_gpx_file(gpx_file, fetch_elevation=True)
        
        # Create web-friendly version
        web_data = create_web_friendly_data(course_data)
        
        # Save detailed data
        with open('/home/jasongarcia24/Documents/ultra-smart/data/cocodona_250_course_data.json', 'w') as f:
            json.dump(course_data, f, indent=2)
        
        # Save web-friendly data
        with open('/home/jasongarcia24/Documents/ultra-smart/data/cocodona_250_map_data.json', 'w') as f:
            json.dump(web_data, f, indent=2)
        
        print(f"\n=== Course Summary ===")
        print(f"Total Distance: {course_data['course_stats']['total_distance_miles']:.1f} miles")
        
        min_elev = course_data['elevation_stats']['min_elevation']
        max_elev = course_data['elevation_stats']['max_elevation']
        total_gain = course_data['elevation_stats']['total_gain']
        total_loss = course_data['elevation_stats']['total_loss']
        
        if min_elev and max_elev:
            print(f"Elevation Range: {min_elev:.0f}ft - {max_elev:.0f}ft")
        else:
            print("Elevation Range: No elevation data available")
            
        if total_gain:
            print(f"Total Elevation Gain: {total_gain:.0f}ft")
        else:
            print("Total Elevation Gain: No elevation data available")
            
        if total_loss:
            print(f"Total Elevation Loss: {total_loss:.0f}ft")
        else:
            print("Total Elevation Loss: No elevation data available")
        print(f"Aid Stations: {len([w for w in course_data['waypoints'] if 'M0' in w['name']])}")
        
        print(f"\n=== Aid Stations by Mile ===")
        aid_stations = [w for w in course_data['waypoints'] if w.get('mile_marker')]
        aid_stations.sort(key=lambda x: x['mile_marker'])
        
        for station in aid_stations:
            elevation = f" ({station['elevation_feet']:.0f}ft)" if station['elevation_feet'] else ""
            print(f"Mile {station['mile_marker']:5.1f}: {station['name'].split(' - ', 1)[1]}{elevation}")
        
        print(f"\nFiles saved:")
        print(f"- Detailed data: /home/jasongarcia24/Documents/ultra-smart/data/cocodona_250_course_data.json")
        print(f"- Web map data: /home/jasongarcia24/Documents/ultra-smart/data/cocodona_250_map_data.json")
        
    except Exception as e:
        print(f"Error parsing GPX file: {e}")
        import traceback
        traceback.print_exc()