import streamlit as st
from typing import List, Dict, Any
from travel_components import format_time_duration, format_distance

def display_places_sidebar(places: List[Dict[str, Any]]) -> None:
    """Display a list of places in the sidebar"""
    if not places:
        return
        
    st.sidebar.header("Nearby Places")
    for idx, place in enumerate(places):
        with st.sidebar.expander(f"Pin {idx+1}: {place.get('title', 'Place')}"):
            st.write(f"**Address:** {place.get('address', {}).get('label', 'N/A')}")
            if 'distance' in place:
                st.write(f"**Distance:** {format_distance(place['distance'])}")
            
            categories = place.get('categories', [])
            if categories:
                st.write("**Categories:**")
                for cat in categories:
                    st.write(f"- {cat.get('name', '')}")

def display_route_info(route_summary: Dict[str, Any]) -> None:
    """Display route information"""
    if not route_summary:
        return
        
    st.subheader("Route Information")
    cols = st.columns(2)
    
    with cols[0]:
        if route_summary.get('distance') is not None:
            st.metric("Total Distance", format_distance(route_summary['distance']))
        
        if route_summary.get('travel_time') is not None:
            st.metric("Travel Time", format_time_duration(route_summary['travel_time']))
    
    with cols[1]:
        if route_summary.get('has_traffic'):
            traffic_delay = route_summary.get('traffic_delay', 0)
            st.metric("Traffic Delay", format_time_duration(traffic_delay))
            
        if route_summary.get('departure_time'):
            st.metric("Departure", route_summary['departure_time'])
            
        if route_summary.get('arrival_time'):
            st.metric("Arrival", route_summary['arrival_time'])

def display_trip_summary(locations: List[Dict[str, Any]]) -> None:
    """Display trip summary with all locations"""
    if not locations:
        return
        
    st.subheader("Trip Summary")
    for idx, loc in enumerate(locations):
        prefix = "Start" if idx == 0 else "End" if idx == len(locations) - 1 else f"Stop {idx}"
        st.write(f"**{prefix}:** {loc.get('display_name', 'Unknown Location')}") 