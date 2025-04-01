from llama_index.utils.workflow import draw_all_possible_flows
from llama_index.core.workflow import Event
from llama_index.core.workflow import (
    Workflow,
    Context,
    StartEvent,
    StopEvent,
    step,
)

from llama_index.core.llms import LLM
from llama_index.llms.openrouter import OpenRouter
from llama_index.core.llms import ChatMessage
from llama_index.core.agent.workflow import AgentOutput
from typing import Dict, Any, Optional, Tuple, List
import json
from datetime import datetime
import os
from prompt_data import  PROMPT_EXTRACT_ROUTE_INFO, PROMPT_EXTRACT_SEARCH_PLACES_INFO
from state_manager import StateManager
from load_env import load_environment
from api_wrappers import TomTomAPI, HereAPI

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
    route_info: Dict[str, Any]
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
        super().__init__(verbose=True)
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
        draw_all_possible_flows(self, filename="workflowviz.html")

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
        prompt = f"""Categorize the intent of this message as either ONTOPIC or OFFTOPIC:
        ONTOPIC: If the message contains information or intention about trip planning, travel itinerary, or general question about geographical locations
        OFFTOPIC: For all other messages
        
        Message: {message}
        
        IF you categorize it as 'OFFTOPIC',
        Your response should be a complete response to the message . Dont include the word 'OFFTOPIC' in your response.
        IF you categorize it as 'ONTOPIC',
        You response should be a single word 'ONTOPIC' if you categorize it as 'ONTOPIC'.
        """
        
        result = self.llm.complete(prompt)
        print(f"Determine intent result: {result}")
        return IntentEvent(message=message, result=str(result).strip())

    @step
    async def convo_offtopic(self, ctx: Context, ev: IntentEvent) -> SearchPlacesInfoEvent | StopEvent:
        """Stop conversation if number of off-topic messages is too high. Otherwise, check if the user is asking to search for a place."""
        print(f"Convo offtopic ev: {ev}")
        if ev.result == "ONTOPIC":
            await ctx.set("off_topic_count", 0 )  # reset off-topic count
            return SearchPlacesInfoEvent(message=ev.message)
            
        # Get off-topic count from context
        off_topic_count = await ctx.get("off_topic_count", 0) + 1
        await ctx.set("off_topic_count", off_topic_count)
        
        
        if off_topic_count >= 8:
            denymessage="I am sorry, I cannot continue in this offtopic conversation. Please ask about trip planning."
        elif off_topic_count >= 5:
            denymessage=ev.result + "\n\nThis conversation is going offtopic. Please ask about trip planning."
        else:
            denymessage=ev.result
        print(f"Convo offtopic deny message: {denymessage}")
        return StopEvent(result=denymessage)

    @step
    async def extract_search_places_info(self, ctx: Context, ev: SearchPlacesInfoEvent) -> SearchPlacesExamineEvent | RouteInfoEvent | StopEvent:
        """If the user is asking to search for a place, pass the message to the search places API call step.
        Otherwise, pass the message to the route information extraction step."""
        print(f"Extract search places info ev: {ev}")
        message = ev.message
        prompt = f"The user has posted the following message:\nMessage: {message}\n\n{PROMPT_EXTRACT_SEARCH_PLACES_INFO}\n\n"
        
        
        result = self.llm.complete(prompt)
        try:
            info = json.loads(str(result))
            if info:
                if info["location"] and info["place_type"]:
                    return SearchPlacesExamineEvent(**info, message=message)
                else:
                    return RouteInfoEvent(message=ev.message)
            else:
                return RouteInfoEvent(message=ev.message)
        except:
            print(f"Error in extract_search_places_info: {result}")
            return StopEvent(result="There was an error in extract_search_places_info. Please try again.")

    @step
    async def examine_search_places_call(self, ctx: Context, ev: SearchPlacesExamineEvent) -> SearchPlacesCallEvent | StopEvent:
        """Examine if search places API call can be made. if not, stop the conversation."""
        print(f"Examine search places call ev: {ev}")
        if not ev.location or not ev.place_type:
            return StopEvent(result=str(ev.thought))
            
        valid_types = ["restaurant", "rest_area", "hotel"]
        if ev.place_type not in valid_types:
            return StopEvent(result=str(ev.thought))
            
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
    async def extract_route_info(self, ctx: Context, ev: RouteInfoEvent ) -> RouteExamineEvent | StopEvent:
        
        """Extract route request parameters from user message. Update the app state with the route information."""
        print(f"Extract route info ev: {ev}")
        message = ev.message
        
        prompt = f"The user has posted the following message:\nMessage: {message}\n\n{PROMPT_EXTRACT_ROUTE_INFO}\n\n"
        
        result = self.llm.complete(prompt)
        try:
            route_info = json.loads(str(result))

            return RouteExamineEvent(route_info=route_info, message=message)
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
        
        return StopEvent(result=str(result))
        
