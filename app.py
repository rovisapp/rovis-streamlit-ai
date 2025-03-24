#source venv/bin/activate && streamlit run app.py
import streamlit as st
import folium
from streamlit_folium import folium_static
import os
import datetime
from typing import List, Dict, Any, Tuple, Optional

# Import custom modules
from agent_handler import TripPlannerAgent
from api_wrappers import TomTomAPI, HereAPI
import map_utils
from load_env import load_environment
from place_components import display_places_sidebar, display_route_info, display_trip_summary
from travel_components import (
    format_time_duration, format_distance, create_daily_itinerary_card,
    display_trip_planner_form, add_location_markers_with_routes, create_poi_marker_cluster
)
import requests

# Set page configuration
st.set_page_config(page_title="Rovis Streamlit AI", layout="wide")

# Load environment variables from .env file
env_vars = load_environment()
OPENROUTER_API_KEY = env_vars["OPENROUTER_API_KEY"]
TOMTOM_API_KEY = env_vars["TOMTOM_API_KEY"]
HERE_API_KEY = env_vars["HERE_API_KEY"]

# Initialize session state variables
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.messages = []
    st.session_state.route = None
    st.session_state.locations = []
    st.session_state.temp_places = []
    st.session_state.selected_places = []
    st.session_state.user_info = {
        'start_location': None,
        'destinations': None,
        'time_constraints': None,
        'driving_hours_per_day': None,
        'walking_time': None
    }
    st.session_state.draw_data = None
    st.session_state.last_message = None
    st.session_state.last_response = None
    # Add welcome message
    welcome_msg = (
        "I can help you plan your travel. Please answer these questions:\n"
        "- What is the start location (Type in the address / location name / city etc)?\n"
        "- Which places are you visiting?\n"
        "- What are your time constraints?\n"
        "- How many hours you can drive per day?\n"
        "- How many minutes or hours per day you can walk?"
    )
    st.session_state.messages.append({"role": "assistant", "content": welcome_msg})

# Initialize API clients
@st.cache_resource
def get_api_clients():
    tomtom_api = TomTomAPI(TOMTOM_API_KEY)
    here_api = HereAPI(HERE_API_KEY)
    return tomtom_api, here_api

tomtom_api, here_api = get_api_clients()

# Initialize LLM agent
@st.cache_resource
def get_agent():
    agent = TripPlannerAgent(
        api_key=OPENROUTER_API_KEY,
        geocode_fn=tomtom_api.geocode,
        route_fn=tomtom_api.calculate_route,
        search_places_fn=here_api.search_places
    )
    return agent

agent = get_agent()

# Function to process user message and update state
def process_message(message: str):
    # Only process if this is a new message
    if message == st.session_state.last_message:
        return
        
    # Update last message
    st.session_state.last_message = message
    
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": message})
    
    # Process any drawn markers
    if st.session_state.draw_data:
        coords = map_utils.extract_coordinates_from_draw_data(st.session_state.draw_data)
        if coords:
            message += f"\nI've marked a location on the map at coordinates {coords[0]}, {coords[1]}."
            st.session_state.draw_data = None
    
    # Process pin selection
    pin_idx = map_utils.parse_pin_selection(message)
    if pin_idx is not None and 0 <= pin_idx < len(st.session_state.temp_places):
        selected_place = st.session_state.temp_places[pin_idx]
        st.session_state.selected_places.append(selected_place)
        
        # Add selected place to locations for routing
        location = {
            'lat': selected_place['position'][0],
            'lon': selected_place['position'][1],
            'display_name': selected_place['title']
        }
        st.session_state.locations.append(location)
        
        # Clear temporary places after selection
        st.session_state.temp_places = []
    
    try:
        # Send message to agent
        response, updated_info = agent.chat(message, st.session_state.user_info)
        
        # Update user info
        st.session_state.user_info = updated_info
        
        # Store the response
        st.session_state.last_response = response
        
        # Add assistant message to chat
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Handle route updates
        if updated_info.get('route_updated') and len(st.session_state.locations) >= 2:
            start = (st.session_state.locations[0]['lat'], st.session_state.locations[0]['lon'])
            end = (st.session_state.locations[-1]['lat'], st.session_state.locations[-1]['lon'])
            
            waypoints = []
            if len(st.session_state.locations) > 2:
                waypoints = [
                    (loc['lat'], loc['lon']) for loc in st.session_state.locations[1:-1]
                ]
            
            route_data = tomtom_api.calculate_route(start, end, waypoints)
            if route_data:
                route_summary = tomtom_api.extract_route_summary(route_data)
                polyline = map_utils.extract_polyline_from_route(route_data)
                
                if polyline and len(polyline) > 0:
                    st.session_state.route = polyline
                    st.session_state.route_summary = route_summary
        
        # Handle place searches
        if updated_info.get('showing_places'):
            current_location = find_current_location()
            if current_location:
                if "rest" in message.lower() or "stop" in message.lower():
                    places_data = here_api.search_rest_areas(current_location)
                elif "eat" in message.lower() or "food" in message.lower() or "restaurant" in message.lower():
                    places_data = here_api.search_meal_places(current_location)
                elif "hotel" in message.lower() or "stay" in message.lower() or "motel" in message.lower():
                    places_data = here_api.search_hotels(current_location)
                elif "gas" in message.lower() or "fuel" in message.lower():
                    places_data = here_api.search_gas_stations(current_location)
                else:
                    places_data = here_api.search_places(current_location)
                
                st.session_state.temp_places = map_utils.format_places_from_here_api(places_data)
        
        # Clear temporary places if a place was selected
        if updated_info.get('selected_place'):
            st.session_state.temp_places = []
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.session_state.messages.append({
            "role": "assistant",
            "content": "I apologize, but I encountered an error. Please try again."
        })

def find_current_location() -> Optional[Tuple[float, float]]:
    """Find the current location based on the most recent location or the map center"""
    if st.session_state.locations:
        latest_location = st.session_state.locations[-1]
        return (latest_location['lat'], latest_location['lon'])
    
    # Default to map center if no locations yet
    return (37.0902, -95.7129)

# Create a two-column layout
col1, col2 = st.columns([2, 3])

# Show trip planner form if no messages yet
if not st.session_state.messages:
    with st.expander("Quick Trip Planner", expanded=True):
        submitted, trip_info = display_trip_planner_form()
        if submitted:
            # Update user info
            st.session_state.user_info = trip_info
            
            # Geocode start location
            start_loc_data = tomtom_api.geocode(trip_info["start_location"])
            if start_loc_data:
                st.session_state.locations.append(start_loc_data)
            
            # Create a message from the form inputs
            form_message = (
                f"I want to plan a trip from {trip_info['start_location']} to " +
                f"{', '.join(trip_info['destinations'])}. " +
                f"My time constraints are {trip_info['time_constraints']}. " +
                f"I can drive {trip_info['driving_hours_per_day']} hours per day and " +
                f"walk {trip_info['walking_time']} minutes per day."
            )
            
            # Process the message
            process_message(form_message)
            
            # Rerun to show the updated UI
            st.rerun()

# Map column (right)
with col2:
    st.header("Trip Map")
    
    # Create a map centered on the US
    map_center = [37.0902, -95.7129]
    zoom_level = 4
    
    # If we have locations, center on the first one
    if st.session_state.locations:
        map_center = [st.session_state.locations[0]['lat'], st.session_state.locations[0]['lon']]
        zoom_level = 6
    
    m = map_utils.create_map(map_center, zoom_level)
    
    # Add locations to the map
    m = map_utils.add_locations_to_map(m, st.session_state.locations)
    
    # Add temporary places to the map
    m = map_utils.add_places_to_map(m, st.session_state.temp_places, "green")
    
    # Add selected places to the map
    m = map_utils.add_places_to_map(m, st.session_state.selected_places, "red")
    
    # Add route to the map if exists
    if st.session_state.route:
        m = map_utils.add_route_to_map(m, st.session_state.route)
    
    # Add draw plugin to allow user to place markers
    m = map_utils.add_draw_plugin(m)
    
    # Display the map
    output = map_utils.display_map(m, 700, 500)
    
    # Capture draw data
    if 'last_active_drawing' in st.session_state:
        st.session_state.draw_data = st.session_state.last_active_drawing

# Chat column (left)
with col1:
    st.header("Trip Maker AI")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        process_message(prompt)
        st.rerun()

# Add styling
st.markdown("""
<style>
.stChat {
    height: 500px;
    overflow-y: auto;
}
</style>
""", unsafe_allow_html=True)

# Additional UI elements for map interaction and trip info
with col2:
    st.caption("You can place markers on the map by clicking the marker tool and then clicking on the map.")
    
    # Show tabs for places and trip info
    tab1, tab2 = st.tabs(["Places", "Trip Info"])
    
    with tab1:
        if st.session_state.temp_places:
            st.info(f"I found {len(st.session_state.temp_places)} places. Refer to them as Pin 1, Pin 2, etc. in your message.")
            
            # Display places in a more visual format
            for idx, place in enumerate(st.session_state.temp_places):
                cols = st.columns([1, 4])
                with cols[0]:
                    st.markdown(f"### Pin {idx+1}")
                with cols[1]:
                    st.markdown(f"**{place.get('title', 'Unknown')}**")
                    st.markdown(f"_{place.get('address', {}).get('label', 'Address not available')}_")
                    if 'categories' in place and len(place['categories']) > 0:
                        categories = [cat.get('name', '') for cat in place['categories'] if 'name' in cat]
                        st.markdown(f"Categories: {', '.join(categories)}")
                st.markdown("---")
        else:
            st.write("No places currently displayed on the map. Ask about restaurants, hotels, or attractions near a location to see options.")
    
    with tab2:
        if st.session_state.route and len(st.session_state.locations) >= 2:
            # Get route summary
            start = (st.session_state.locations[0]['lat'], st.session_state.locations[0]['lon'])
            end = (st.session_state.locations[-1]['lat'], st.session_state.locations[-1]['lon'])
            
            waypoints = []
            if len(st.session_state.locations) > 2:
                waypoints = [
                    (loc['lat'], loc['lon']) for loc in st.session_state.locations[1:-1]
                ]
            
            route_data = tomtom_api.calculate_route(start, end, waypoints)
            route_summary = tomtom_api.extract_route_summary(route_data)
            
            # Display route info
            display_route_info(route_summary)
            
            # Display trip summary
            display_trip_summary(st.session_state.locations)
        else:
            st.write("No route has been calculated yet. Provide a start location and destinations to see trip information.")