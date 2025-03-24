import folium
from folium.plugins import Draw, MarkerCluster
from streamlit_folium import folium_static
import streamlit as st
from typing import List, Dict, Any, Tuple, Optional
import re

def create_map(
    center: List[float] = [37.0902, -95.7129],
    zoom: int = 4
) -> folium.Map:
    """Create a base folium map"""
    m = folium.Map(location=center, zoom_start=zoom)
    return m

def add_locations_to_map(
    m: folium.Map,
    locations: List[Dict[str, Any]],
    color: str = "blue"
) -> folium.Map:
    """Add location markers to the map"""
    for idx, loc in enumerate(locations):
        if 'lat' in loc and 'lon' in loc:
            folium.Marker(
                location=[loc['lat'], loc['lon']],
                popup=loc.get('display_name', f"Location {idx+1}"),
                tooltip=f"Location {idx+1}: {loc.get('display_name', 'Unknown')}",
                icon=folium.Icon(color=color)
            ).add_to(m)
    return m

def add_places_to_map(
    m: folium.Map,
    places: List[Dict[str, Any]],
    color: str = "green"
) -> folium.Map:
    """Add place markers to the map"""
    for idx, place in enumerate(places):
        if 'position' in place and place['position'] and len(place['position']) == 2:
            folium.Marker(
                location=[place['position'][0], place['position'][1]],
                popup=f"<b>{place.get('title', 'Place')}</b><br>{place.get('address', {}).get('label', '')}",
                tooltip=f"Pin {idx+1}: {place.get('title', 'Place')}",
                icon=folium.Icon(color=color)
            ).add_to(m)
    return m

def add_route_to_map(
    m: folium.Map,
    route: List[Tuple[float, float]],
    color: str = "blue",
    weight: int = 5,
    opacity: float = 0.7
) -> folium.Map:
    """Add route polyline to the map"""
    if not route or len(route) < 2:
        return m
        
    try:
        # Validate all coordinates are within valid ranges
        valid_coords = []
        for lat, lon in route:
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                valid_coords.append((lat, lon))
        
        if len(valid_coords) >= 2:
            folium.PolyLine(
                valid_coords,
                color=color,
                weight=weight,
                opacity=opacity
            ).add_to(m)
    except (ValueError, TypeError):
        pass
        
    return m

def add_draw_plugin(m: folium.Map, options: Dict[str, bool] = None) -> folium.Map:
    """Add drawing plugin to the map"""
    if options is None:
        options = {
            'polyline': False,
            'rectangle': False,
            'circle': False,
            'circlemarker': False,
            'polygon': False
        }
    
    draw = Draw(
        export=False,
        position='topright',
        draw_options=options,
    )
    draw.add_to(m)
    return m

def extract_coordinates_from_draw_data(data: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """Extract coordinates from draw data"""
    if not data or not isinstance(data, dict):
        return None
    
    try:
        if 'geometry' in data and 'coordinates' in data['geometry']:
            coords = data['geometry']['coordinates']
            if isinstance(coords, list) and len(coords) == 2:
                # Validate coordinates are within valid ranges
                lat, lon = coords[1], coords[0]  # GeoJSON format has [longitude, latitude]
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return (lat, lon)
    except (KeyError, IndexError, TypeError, ValueError):
        pass
    
    return None

def format_places_for_display(places: List[Dict[str, Any]]) -> str:
    """Format places for display in the chat"""
    if not places or len(places) == 0:
        return "No places found."
    
    formatted = "Here are the places I found:\n\n"
    for idx, place in enumerate(places):
        title = place.get('title', 'Unknown')
        address = place.get('address', {}).get('label', 'Address not available')
        distance = place.get('distance', 'Unknown')
        categories = place.get('categories', [])
        category_names = [cat.get('name', '') for cat in categories if 'name' in cat]
        category_str = ", ".join(category_names) if category_names else "Not specified"
        
        formatted += f"**Pin {idx+1}: {title}**\n"
        formatted += f"- Address: {address}\n"
        formatted += f"- Distance: {distance} meters\n"
        formatted += f"- Category: {category_str}\n\n"
    
    return formatted

def parse_pin_selection(message: str) -> Optional[int]:
    """Parse user message to extract pin selection"""
    # Match patterns like "Pin 3", "pin #3", "I choose pin 3"
    pattern = r"(?:pin|location|place)\s*(?:#|\s+)?(\d+)"
    match = re.search(pattern, message, re.IGNORECASE)
    
    if match:
        try:
            return int(match.group(1)) - 1  # Convert to 0-based index
        except ValueError:
            return None
    return None

def display_map(
    m: folium.Map,
    width: int = 700,
    height: int = 500
) -> None:
    """Display the map in Streamlit"""
    folium_static(m, width=width, height=height)

def extract_polyline_from_route(route_data: Dict[str, Any]) -> List[Tuple[float, float]]:
    """Extract polyline coordinates from TomTom route response"""
    polyline = []
    
    if 'routes' in route_data and len(route_data['routes']) > 0:
        route = route_data['routes'][0]
        
        if 'legs' in route and len(route['legs']) > 0:
            for leg in route['legs']:
                if 'points' in leg:
                    for point in leg['points']:
                        if 'latitude' in point and 'longitude' in point:
                            polyline.append((point['latitude'], point['longitude']))
    
    return polyline

def format_places_from_here_api(places_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Format places from HERE API response"""
    formatted_places = []
    
    if 'items' in places_data:
        for item in places_data['items']:
            place = {
                'title': item.get('title', 'Unknown'),
                'position': [
                    item.get('position', {}).get('lat', 0),
                    item.get('position', {}).get('lng', 0)
                ],
                'address': item.get('address', {}),
                'distance': item.get('distance', 0),
                'categories': item.get('categories', [])
            }
            formatted_places.append(place)
    
    return formatted_places