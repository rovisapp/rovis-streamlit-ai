import streamlit as st
from typing import Dict, Any, List, Tuple, Optional
import datetime
import folium

def format_time_duration(seconds: int) -> str:
    """Format seconds into a readable time duration (e.g., 2h 30m)"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m"

def format_distance(meters: float) -> str:
    """Format meters into a readable distance (km or m)"""
    if meters >= 1000:
        return f"{meters/1000:.1f} km"
    else:
        return f"{int(meters)} m"

def create_daily_itinerary_card(
    day_number: int,
    start_location: str,
    end_location: str,
    driving_time_seconds: int,
    distance_meters: float,
    stops: List[str] = None,
    activities: List[str] = None
) -> None:
    """Create a card displaying a daily itinerary"""
    with st.container():
        st.subheader(f"Day {day_number}")
        
        cols = st.columns([3, 1])
        
        with cols[0]:
            st.write(f"**From:** {start_location}")
            st.write(f"**To:** {end_location}")
            
            if stops and len(stops) > 0:
                with st.expander("Stops"):
                    for i, stop in enumerate(stops, 1):
                        st.write(f"{i}. {stop}")
            
            if activities and len(activities) > 0:
                with st.expander("Activities"):
                    for i, activity in enumerate(activities, 1):
                        st.write(f"{i}. {activity}")
        
        with cols[1]:
            st.metric("Driving", format_time_duration(driving_time_seconds))
            st.metric("Distance", format_distance(distance_meters))
        
        st.markdown("---")

def display_trip_planner_form() -> Tuple[bool, Dict[str, Any]]:
    """Display a form for planning a trip and return the inputs"""
    with st.form("trip_planner_form"):
        st.subheader("Plan Your Trip")
        
        start_location = st.text_input("Start Location", placeholder="e.g., Las Vegas, NV")
        destinations = st.text_area("Destinations (one per line)", placeholder="e.g., Grand Canyon\nZion National Park")
        
        cols = st.columns(2)
        with cols[0]:
            start_date = st.date_input("Start Date", datetime.datetime.now().date())
            max_driving_hours = st.number_input("Max Driving Hours Per Day", min_value=1, max_value=12, value=5, step=1)
        
        with cols[1]:
            end_date = st.date_input("End Date", datetime.datetime.now().date() + datetime.timedelta(days=7))
            max_walking_mins = st.number_input("Max Walking Minutes Per Day", min_value=0, max_value=480, value=180, step=30)
        
        submitted = st.form_submit_button("Plan Trip")
        
        if submitted:
            # Validate inputs
            if not start_location:
                st.error("Please enter a start location")
                return False, {}
                
            if not destinations:
                st.error("Please enter at least one destination")
                return False, {}
                
            if end_date < start_date:
                st.error("End date must be after start date")
                return False, {}
                
            destinations_list = [d.strip() for d in destinations.split("\n") if d.strip()]
            if not destinations_list:
                st.error("Please enter at least one valid destination")
                return False, {}
            
            return True, {
                "start_location": start_location,
                "destinations": destinations_list,
                "time_constraints": f"{start_date} to {end_date}",
                "driving_hours_per_day": max_driving_hours,
                "walking_time": max_walking_mins
            }
        
        return False, {}

def add_location_markers_with_routes(
    m: folium.Map,
    locations: List[Dict[str, Any]],
    routes: List[List[Tuple[float, float]]],
    colors: List[str] = ["blue", "green", "red", "purple", "orange"]
) -> folium.Map:
    """Add location markers with routes connecting them in different colors"""
    if not locations or len(locations) < 2:
        return m
    
    # Add markers for each location
    for i, location in enumerate(locations):
        if i == 0:  # Start location
            icon = folium.Icon(color="green", icon="play", prefix="fa")
        elif i == len(locations) - 1:  # End location
            icon = folium.Icon(color="red", icon="stop", prefix="fa")
        else:  # Waypoints
            icon = folium.Icon(color="blue", icon="flag", prefix="fa")
        
        folium.Marker(
            location=[location.get("lat"), location.get("lon")],
            popup=location.get("display_name", f"Location {i+1}"),
            tooltip=location.get("display_name", f"Location {i+1}"),
            icon=icon
        ).add_to(m)
    
    # Add routes with different colors
    for i, route in enumerate(routes):
        if route and len(route) > 1:
            folium.PolyLine(
                route,
                color=colors[i % len(colors)],
                weight=4,
                opacity=0.8,
                tooltip=f"Day {i+1}"
            ).add_to(m)
    
    return m

def create_poi_marker_cluster(m: folium.Map, pois: List[Dict[str, Any]]) -> folium.Map:
    """Create a marker cluster for points of interest"""
    if not pois or len(pois) == 0:
        return m
    
    marker_cluster = folium.plugins.MarkerCluster(name="Points of Interest")
    
    for i, poi in enumerate(pois):
        if "position" in poi and len(poi["position"]) == 2:
            popup_html = f"""
            <b>{poi.get('title', 'Unknown')}</b><br>
            {poi.get('address', {}).get('label', 'Address not available')}<br>
            """
            
            if "categories" in poi:
                categories = [cat.get("name", "") for cat in poi.get("categories", []) if "name" in cat]
                if categories:
                    popup_html += f"Categories: {', '.join(categories)}<br>"
            
            folium.Marker(
                location=[poi["position"][0], poi["position"][1]],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{poi.get('title', 'POI')}",
                icon=folium.Icon(color="green", icon="info-sign")
            ).add_to(marker_cluster)
    
    marker_cluster.add_to(m)
    return m