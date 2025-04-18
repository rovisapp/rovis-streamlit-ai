import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st
from llama_index.core.agent.workflow import AgentOutput
from llama_index.core.llms import LLM, ChatMessage
from llama_index.core.workflow import (Context, Event, StartEvent, StopEvent,
                                       Workflow, step)
from llama_index.llms.openrouter import OpenRouter
from llama_index.utils.workflow import draw_all_possible_flows

from api_wrappers import HereAPI, TomTomAPI
from load_env import load_environment
from prompt_data import (PROMPT_EXTRACT_ROUTE_INFO,
                         PROMPT_EXTRACT_SEARCH_PLACES_INFO)
from state_manager import StateManager

# Load environment variables
env_vars = load_environment()
TOMTOM_API_KEY = env_vars["TOMTOM_API_KEY"]
HERE_API_KEY = env_vars["HERE_API_KEY"]

# Initialize API clients
# def get_api_clients():
#     tomtom_api = TomTomAPI(TOMTOM_API_KEY)
#     here_api = HereAPI(HERE_API_KEY)
#     return tomtom_api, here_api
# 
# tomtom_api, here_api = get_api_clients()

# Event classes for each step
class IntentEvent(Event):
    """Event for intent determination."""
    message: str
    result: str

class OffTopicEvent(Event):
    """Event for off-topic conversation handling."""
    message: str
    
class SearchPlacesExamineEvent(Event):
    """Event for search places information extraction."""
    location: Optional[Dict[str, float]]
    place_type: Optional[str]
    message: str

class SearchPlacesInfoEvent(Event):
    """Event for search places information extraction."""
    location: Optional[Dict[str, float]]
    place_type: Optional[str]
    message: str

class SearchPlacesCallEvent(Event):
    """Event for search places API call."""
    location: Dict[str, float]
    place_type: str
    message: str

class RouteInfoEvent(Event):
    """Event for route information extraction."""
    route_info: Optional[Dict[str, Any]]
    message: str

class RouteExamineEvent(Event):
    """Event for route information extraction."""
    route_info: Dict[str, Any]
    message: str

class RouteCallEvent(Event):
    """Event for route calculation."""
    route_info: Dict[str, Any]
    message: str

class TripPlannerAgent(Workflow):
    """Trip planner workflow implementation."""

    def __init__(self, api_key: str, model_name: str = "google/gemma-3-27b-it"):
        super().__init__(verbose=True) # TODO: remove verbose=True after testing
        self.llm = OpenRouter(
            api_key=api_key,
            model=model_name,
            max_tokens=2048,
            temperature=0.7,
            top_p=0.9,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        StateManager.init_session_state()
        draw_all_possible_flows(self, filename="workflowviz.html") # Use open workflowviz.html to visualize the workflow, remove after testing

    async def extract_location_and_place_type(self, message: str) -> Tuple[Optional[Dict[str, float]], Optional[str]]:
        """
        Extract location and place type from the user's message.
        This is a placeholder implementation and should be replaced with actual logic.
        """
        # Example logic: This is a very basic example and should be replaced with actual extraction logic
        # You might use regex, a language model, or some other method to extract this information
        location = None
        place_type = None

        # Example: Check if the message contains certain keywords
        if "restaurant" in message:
            place_type = "restaurant"
        elif "hotel" in message:
            place_type = "hotel"
        elif "rest area" in message:
            place_type = "rest_area"

        # Example: Dummy location extraction
        # Replace this with actual logic to extract location coordinates
        if "New York" in message:
            location = {"lat": 40.7128, "lon": -74.0060}

        return location, place_type
    
    async def search_places_fn(self, location: Tuple[float, float], radius: int = 8047, type: str = "") -> Dict[str, Any]:
        """Mock function to simulate search_places API call"""
        print(f"\n=== Mock search_places_fn called ===")
        print(f"Location: {location}")
        print(f"Radius: {radius} meters")
        print(f"Type: {type}")
        print("=== End mock search_places_fn ===\n")
        
        # Real API call would be:
        # result = await here_api.search_places(location, radius, type)
        
        # Read and return the mock location response
        try:
            with open('api-mock/location-response.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading location-response.json: {e}")
            return {"items": []}

    async def calculate_route_fn(self, start: Tuple[float, float], end: Tuple[float, float], waypoints: List[Tuple[float, float]], depart_at: str = None) -> Dict[str, Any]:
        """Mock function to simulate calculate_route API call"""
        print(f"\n=== Mock calculate_route_fn called ===")
        print(f"Start location: {start}")
        print(f"End location: {end}")
        print(f"Waypoints: {waypoints}")
        print(f"Departure time: {depart_at}")
        print("=== End mock calculate_route_fn ===\n")
        
        # Real API call would be:
        # result = await tomtom_api.calculate_route(start, end, waypoints, depart_at)
        
        # Read and return the mock route response
        try:
            with open('api-mock/route-response.json', 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading route-response.json: {e}")
            return {"routes": []}

    async def async_chat(self, message: Dict[str, str]) -> str:
        """Process user message and return agent response"""
        print(f"\nUser message: {message}")
        
        try:
            # Create context with functions
            ctx = Context(self)
            await ctx.set("search_places_fn", self.search_places_fn)
            await ctx.set("calculate_route_fn", self.calculate_route_fn)
            self.verbose = True
            # Run workflow with streaming
            handler = self.run(message=message['content'], ctx=ctx)
            
            # Process streaming events
            async for event in handler.stream_events():
                if isinstance(event, AgentOutput):
                    print("Agent output: ", event.response)
                    print("Tool calls made: ", event.tool_calls)
                    print("Raw LLM response: ", event.raw)
            
            # Get final response
            return str(await handler)
                
        except Exception as e:
            print(f"Error in async_chat: {e}")
            return "I apologize, but I encountered an error. Please try again."

    @step
    async def determine_intent(self, ctx: Context, ev: StartEvent) -> IntentEvent:
        """Determine if the user's message is on-topic or off-topic."""
        print(f"Determine intent ev: {ev}")
        message = ev.message
        prompt = f"""Categorize the intent of this message as either ONTOPIC or OFFTOPIC.
        ONTOPIC: If the message contains information or intention about trip planning, travel itinerary, or general questions about geographical locations.
        OFFTOPIC: For all other messages.

        Message: {message}

        IF you categorize it as 'OFFTOPIC',
        Your response should be a complete response to the message. Do not include the word 'OFFTOPIC' in your response. Provide a friendly and informative reply based on the content of the message.
        IF you categorize it as 'ONTOPIC',
        Your response should be a single word 'ONTOPIC'.
        """
        
        result = self.llm.complete(prompt)
        print(f"Determine intent result: {result}")
        return IntentEvent(message=message, result=str(result).strip())

    @step
    async def convo_offtopic(self, ctx: Context, ev: IntentEvent) -> SearchPlacesInfoEvent | StopEvent:
        """Stop conversation if number of off-topic messages is too high. Otherwise, check if the user is asking to search for a place."""
        print(f"Convo offtopic ev: {ev}")
        
        # Retrieve the current off-topic count from the session state
        off_topic_count = st.session_state.get("off_topic_count", 0)
        
        if ev.result == "ONTOPIC":
            st.session_state["off_topic_count"] = 0  # reset off-topic count

            # Wrap the message in a new SearchPlacesInfoEvent
            info_event = SearchPlacesInfoEvent(message=ev.message, location=None, place_type=None)

            # Pass that to extract_search_places_info
            search_places_event = await self.extract_search_places_info(ctx, info_event)
            if isinstance(search_places_event, SearchPlacesInfoEvent):
                return search_places_event
            else:
                return search_places_event  # This could already be a StopEvent

        
        # Increment the off-topic count
        off_topic_count += 1
        st.session_state["off_topic_count"] = off_topic_count  # Update the session state with the new count
        print(f"Off-topic count: {off_topic_count}")
        
        if off_topic_count >= 3:
            return StopEvent(result=ev.result + "\nWell, well, this is convo is going off topic, how about we stick to trip planning?")
        elif off_topic_count >= 5:
            return StopEvent(result="This is too much of off-topic conversations. Please ask about trip planning. As I won't be able to help you with off topics now until you ask me an ontopic question.")
        else:
            # Provide a friendly response for off-topic messages
            return StopEvent(result=ev.result)

    def extract_json_from_text(self, text: str) -> Optional[Any]:
        """
        Attempts to extract and parse the first JSON object from a string,
        even if surrounded by extra text or malformed.
        """
        try:
            # Try direct parse first (for well-formed JSON)
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Remove any markdown code blocks or whitespace
        cleaned = text.strip("` \n\t")

        # Fix double braces {{...}} -> {...}
        cleaned = re.sub(r"^\{\{(.+?)\}\}$", r"{\1}", cleaned, flags=re.DOTALL)

        # Find the first { ... } block and try parsing it
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            json_str = match.group(0)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON: {e}")
                return None
        return None

    @step
    async def extract_search_places_info(self, ctx: Context, ev: SearchPlacesInfoEvent) -> SearchPlacesExamineEvent | RouteInfoEvent | StopEvent:
        try:
            print(f"Extract search places info ev: {ev}")
            message = ev.message
            prompt = f"The user has posted the following message.\nMessage: {message}\n\n{PROMPT_EXTRACT_SEARCH_PLACES_INFO}\n\n"

            result = self.llm.complete(prompt)
            parsed = self.extract_json_from_text(str(result))

            if parsed is None:
                print(f"Failed to extract JSON from result: {result}")
                return StopEvent(result="Sorry, I couldn't parse your message. Could you try rephrasing it?")

            # If LLM returned a 'thought', it's either not a valid request or needs clarification
            if "thought" in parsed:
                print(f"LLM analysis thought: {parsed['thought']}")

                # Optionally, log ambiguous input
                StateManager.update_app_state("ambiguous", {
                    "original": ev.message,
                    "llm_thought": parsed["thought"]
                })

                print(f"LLM analysis thought: {parsed['thought']}")
                return StopEvent(
                    result=f"Could you specify the city or area you're interested in, and whether you’re looking for restaurants, hotels, or rest stops?"
                )
            
            if "location" in parsed and "place_type" in parsed:
                return SearchPlacesExamineEvent(
                    location=parsed["location"],
                    place_type=parsed["place_type"],
                    message=message
                )
            
            # Validate essential fields
            location = parsed.get("location", {})
            place_type = parsed.get("place_type")
            if not location or not place_type:
                return StopEvent(result="I couldn’t find a clear location or place type. Can you provide a city and let me know if you're looking for restaurants, hotels, or rest stops?")

            lat, lon = location.get("lat"), location.get("lon")
            if lat is None or lon is None:
                return StopEvent(result="The location data seems incomplete. Could you give a more specific place?")

            # Save extracted data to app state
            StateManager.update_app_state("place_search_info", {
                "location": location,
                "place_type": place_type
            })
            
            return RouteInfoEvent(message=message)
        
        except Exception as e:
            print(f"Exception in extract_search_places_info: {e}")
            return StopEvent(result="Oops, something went wrong while processing your request.")


    @step
    async def examine_search_places_call(self, ctx: Context, ev: SearchPlacesExamineEvent) -> SearchPlacesCallEvent | StopEvent:
        """Examine if search places API call can be made. if not, stop the conversation."""
        print(f"Examine search places call ev: {ev}")
        if not ev.location or not ev.place_type:
            return StopEvent(result="I need more information to perform the search. Please specify the location and type of place.")
            
        valid_types = ["restaurant", "rest_area", "hotel"]
        if ev.place_type not in valid_types:
            return StopEvent(result="The type of place is not valid. Please specify if you are looking for a restaurant, rest area, or hotel.")
            
        return SearchPlacesCallEvent(
            location=ev.location,
            place_type=ev.place_type,
            message=ev.message
        )

    @step
    async def call_search_places(self, ctx: Context, ev: SearchPlacesCallEvent) -> StopEvent:
        
        """Make the search places API call. Update the app state with the search results."""
        print(f"Call search places ev: {ev}")
        # Get the search_places function from context
        search_places_fn = await ctx.get("search_places_fn")
        
        # Call the function
        result = await search_places_fn(
            location=(ev.location["lat"], ev.location["lon"]),
            radius=8047,  # 5 miles
            type=ev.place_type
        )
        
        # Update app state with search results
        StateManager.update_app_state("search", {
            'location': ev.location,
            'radius': 8047,
            'type': ev.place_type,
            'results': result
        })
        
        return StopEvent(result=str(result))

    @step
    async def extract_route_info(self, ctx: Context, ev: RouteInfoEvent) -> RouteExamineEvent | StopEvent:
        """Extract route request parameters from user message. Update the app state with the route information."""
        print(f"Extract route info ev: {ev}")
        message = ev.message
        
        prompt = f"The user has posted the following message.\nMessage: {message}\n\n{PROMPT_EXTRACT_ROUTE_INFO}\n\n"
        
        result = self.llm.complete(prompt)
        try:
            route_info = json.loads(str(result))
            if route_info:
                StateManager.update_chat_state(route_info)
                return RouteExamineEvent(route_info=route_info, message=message)
            else:
                return StopEvent(result="I need more information to plan your route. Please provide start and end locations with coordinates, and maximum driving hours per day.")
        except:
            print(f"Error in extract_route_info: {result}")
            return StopEvent(result="There was an error in extract_route_info. Please try again.")

    @step
    async def examine_route_call(self, ctx: Context, ev: RouteExamineEvent) -> RouteCallEvent | StopEvent:
        """Examine if route calculation is feasible."""
        print(f"Examine route call ev: {ev}")
        route_info = ev.route_info
        StateManager.update_chat_state(route_info)
        
        # Check if all required coordinates and maxDrivingHoursPerDay are present
        if not all([
            "start" in route_info and "lat" in route_info["start"] and "lon" in route_info["start"],
            "end" in route_info and "lat" in route_info["end"] and "lon" in route_info["end"],
            "maxDrivingHoursPerDay" in route_info
        ]):
            return StopEvent(result="I need more information to plan your route. Please provide start and end locations with coordinates, and maximum driving hours per day.")
        
        return RouteCallEvent(route_info=route_info, message=ev.message)

    @step
    async def call_route(self, ctx: Context, ev: RouteCallEvent) -> StopEvent:
        """Calculate the route api call. Update the app state with the route results."""
        print(f"Call route ev: {ev}")
        # Get the calculate_route function from context
        calculate_route_fn = await ctx.get("calculate_route_fn")
        
        # Extract coordinates
        start_loc = (ev.route_info["start"]["lat"], ev.route_info["start"]["lon"])
        end_loc = (ev.route_info["end"]["lat"], ev.route_info["end"]["lon"])
        waypoints = [(wp["lat"], wp["lon"]) for wp in ev.route_info.get("waypoints", [])]
        
        # Call the function
        result = await calculate_route_fn(
            start_loc,
            end_loc,
            waypoints,
            ev.route_info.get("departAt", datetime.now().isoformat())
        )
        
        # Update app state with route results
        StateManager.update_app_state("route", {
            'start': ev.route_info.get('start'),
            'end': ev.route_info.get('end'),
            'waypoints': ev.route_info.get('waypoints'),
            'results': result
        })
        
        return StopEvent(result="Your route has been displayed. If you need to make changes, please let me know.")()
            
