from llama_index.core.workflow import (
    Workflow,
    Context,
    StartEvent,
    StopEvent,
    step,
)
from llama_index.core.agent.workflow import AgentOutput
from llama_index.core.llms import LLM
from llama_index.llms.openrouter import OpenRouter
from typing import Dict, Any, Tuple, List, Optional
import json
from prompt import PROMPT_ONE_SHOT
from state_manager import StateManager
from load_env import load_environment
import re
import streamlit as st
import asyncio

# Constants
CONVERSATION_HISTORY_LIMIT = 50

# Load environment variables
env_vars = load_environment()
TOMTOM_API_KEY = env_vars["TOMTOM_API_KEY"]
HERE_API_KEY = env_vars["HERE_API_KEY"]

class TripPlannerAgent(Workflow):
    """Trip planner workflow implementation."""

    def __init__(self, api_key: str, model_name: str = "google/gemma-3-27b-it"):
        super().__init__(verbose=True, timeout=None)
        self.llm = OpenRouter(
            api_key=api_key,
            model=model_name,
            max_tokens=2048,
            temperature=0.7,
            top_p=0.9,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )

    async def handle_function_request(self, request: Dict[str, Any]):
        """Handle function requests based on the function name"""
        try:
            result = None
            result_short = None
            # Simulate API call delay
            # await asyncio.sleep(3)
            match request.get('name'):
                case 'search_place':
                    # Extract parameters from request
                    location = request.get('parameters', {}).get('location')
                    radius = request.get('parameters', {}).get('radius', 8047)
                    type = request.get('parameters', {}).get('type', '')
                    
                    # Call search_places_fn with parameters
                    result = await self.search_places_fn(location, radius, type)
                    # Format results as XML
                    items_xml = "<items>"
                    for item in result.get('items', []):
                        items_xml += f"""
<item>
    <title>{item.get('title', '')}</title>
    <id>{item.get('id', '')}</id>
    <address>{item.get('address', {}).get('label', '')}</address>
    <position>
        <lat>{item.get('position', {}).get('lat', '')}</lat>
        <lng>{item.get('position', {}).get('lng', '')}</lng>
    </position>
</item>"""
                    items_xml += "\n</items>"
                    result_short = items_xml
                
                case 'route':
                    # Extract parameters from request
                    start = request.get('parameters', {}).get('start')
                    end = request.get('parameters', {}).get('end')
                    waypoints = request.get('parameters', {}).get('waypoints', [])
                    depart_at = request.get('parameters', {}).get('depart_at')
                    
                    # Call calculate_route_fn with parameters
                    result = await self.calculate_route_fn(start, end, waypoints, depart_at)
                    # Process route results
                    result_short = "<guidances>"
                    for route in result.get('routes', []):
                        for instruction_group in route.get('guidance', {}).get('instructionGroups', []):
                            result_short += f"""
<guidance>
    <message>{instruction_group.get('groupMessage', '')}</message>
    <length>{instruction_group.get('groupLengthInMeters', '')}</length>
</guidance>"""
                    result_short += "\n</guidances>"
                
                case _:
                    print(f"Unknown function request: {request.get('name')}")
            
            # Update function result in app state if we have a result
            if result is not None:
                self.update_function_result(request.get('requestId'), result, result_short)
                
                # Notify AI about function completion
                system_message = f"<system_message>Function request {request.get('requestId')} completed: {result_short}</system_message>"
                st.session_state.messages.append({"role": "user", "content": system_message})
                response = await self.async_chat({"role": "user", "content": system_message}, st.session_state.messages, 1) # 1 means this prompt is running inside a function call and not a top level prompt
                
                # Add assistant message to chat
                st.session_state.messages.append({"role": "assistant", "content": response})
        
        except Exception as e:
            print(f"Error handling function request: {e}")

    def update_function_result(self, request_id: str, result: Dict[str, Any], result_short: Dict[str, Any]):
        """Update function result in application state"""
        app_state = StateManager.get_app_state()
        if 'functions' in app_state:
            # Find the function with matching requestId and update its result
            for func in app_state['functions']:
                if func.get('requestId') == request_id:
                    func['result'] = result
                    func['result_short'] = result_short
                    break
            # Update the app state
            StateManager.update_app_state(app_state)

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

    async def async_chat(self, message: Dict[str, str], history, nesting_level: int = 0) -> str:
        """Process user message and return agent response"""
        print(f"\nUser message: {message}")
        
        try:
            # Create context with functions
            ctx = Context(self)
            
            # Get existing chat state from session
            chat_state = StateManager.get_chat_state()
            if chat_state:
                await ctx.set("state", chat_state)
            
            # Run workflow with streaming
            handler = self.run(
                message=message['content'],
                ctx=ctx,
                nesting_level=nesting_level
            )

            # Process streaming events
            async for event in handler.stream_events():
                if isinstance(event, AgentOutput):
                    print("Agent output: ", event.response)
            
            # Get final response and update chat state
            final_state = await ctx.get("state", {})
            StateManager.update_chat_state(final_state)
            
            return str(await handler)
                
        except Exception as e:
            print(f"Error in async_chat: {e}")
            return "I apologize, but I encountered an error. Please try again."

    def log_conversation(self, userMsg: str, modelMsg: str):
        """Log conversation in XML format"""
        conversation = f"{userMsg}\n{modelMsg}"
        app_state = StateManager.get_app_state()
        
        # Initialize conversation log as array if it doesn't exist
        if 'conversation_log' not in app_state:
            app_state['conversation_log'] = []
        
        # Append new conversation to the log array
        app_state['conversation_log'].append(conversation)
        StateManager.update_app_state(app_state)

    def log_function_requests(self, request: Dict[str, Any]):
        """Log function request to application state"""
        app_state = StateManager.get_app_state()
        
        # Initialize functions array if it doesn't exist
        if 'functions' not in app_state:
            app_state['functions'] = []
        
        # Add new function to the state
        app_state['functions'].append(request)
        StateManager.update_app_state(app_state)

    @step
    async def execute_prompt(self, ctx: Context, ev: StartEvent) -> StopEvent:
        """Execute the one-shot prompt and handle the response."""
        print(f"Execute prompt ev: {ev}")
        message = ev.message
        userMsg = f"<start_of_turn_user>user\n{message}</end_of_turn>"
        modelMsg = ""

        # Get the current state from context or initialize empty
        previous_state = await ctx.get("state", {})
        
        # Get conversation history from app state
        app_state = StateManager.get_app_state()
        conversation_log = app_state.get('conversation_log', [])
        # Get most recent messages and join with newlines
        conversation_history = "\n".join(conversation_log[-CONVERSATION_HISTORY_LIMIT:]) if conversation_log else ""
        
        # Format the prompt with current state and conversation history
        prompt = PROMPT_ONE_SHOT.strip().replace(
            "{{state}}", json.dumps(previous_state)
        ).replace(
            "{{conversation_history}}", conversation_history
        ) + "\n\nCurrent User Message: " + str(message)
        
        # Execute the prompt
        result = self.llm.complete(prompt)
        
        # Parse the JSON response
        try:
            print(f"Result: {result}")
            parsed_result = self.extract_json_from_text(str(result))
            model_response = ''
            if parsed_result:
                # Store the new state in context
                await ctx.set("state", parsed_result)
                model_response = parsed_result['response']
                modelMsg = f"<start_of_turn_user>model\n{str(model_response)}</end_of_turn>"
                self.log_conversation(userMsg, modelMsg)
                # Handle function requests if this is the top level prompt
                # dont let function call another another function call recursively
                if "functions" in parsed_result and ev.nesting_level == 0:
                    
                    st.session_state.messages.append({"role": "assistant", "content": model_response}) # chat messages are added here because function calls are going to be adding messages to the chat in synchronous manner in the same thread
                    for request in parsed_result["functions"]:
                        print(f"Function Call requested: {request}")
                        # Store the function request in the application state, because the function request handler will need it later to pull the results
                        self.log_function_requests(request)
                        # Handle function request directly
                        await self.handle_function_request(request)
                    return StopEvent(result="") # Dont print a StopEvent message for function calls, because the chatmessage is handled uptop to keep the chat messages in sequence
                # Set model message for successful response
                else:
                   
                    return StopEvent(result=model_response)
                
        except Exception as e:
            print(f"Error processing response: {e}")
            # Set model message for error case
            modelMsg = f"<start_of_turn_user>model\nError: {str(e)}</end_of_turn>"
            self.log_conversation(userMsg, modelMsg)
            return StopEvent(result="I apologize, but I encountered an error processing the response. Please try again.")
         
