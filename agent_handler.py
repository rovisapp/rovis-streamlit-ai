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

# Load environment variables
env_vars = load_environment()
TOMTOM_API_KEY = env_vars["TOMTOM_API_KEY"]
HERE_API_KEY = env_vars["HERE_API_KEY"]

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

    async def async_chat(self, message: Dict[str, str], history) -> str:
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
                ctx=ctx
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
        
        # Initialize conversation log if it doesn't exist
        if 'conversation_log' not in app_state:
            app_state['conversation_log'] = ""
        
        # Append new conversation to the log
        app_state['conversation_log'] += conversation + "\n"
        StateManager.update_app_state(app_state)

    @step
    async def execute_prompt(self, ctx: Context, ev: StartEvent) -> StopEvent:
        """Execute the one-shot prompt and handle the response."""
        print(f"Execute prompt ev: {ev}")
        message = ev.message
        
        # Get the current state from context or initialize empty
        previous_state = await ctx.get("state", {})
        # print(f"Previous state: {previous_state}")
        
        # Get conversation history from app state
        app_state = StateManager.get_app_state()
        conversation_history = app_state.get('conversation_log', "")
        
        # Format the prompt with current state and conversation history
        prompt = PROMPT_ONE_SHOT.strip().replace(
            "{{state}}", json.dumps(previous_state)
        ).replace(
            "{{conversation_history}}", conversation_history
        ) + "\n\nCurrent User Message: " + message
        
        # Execute the prompt
        result = self.llm.complete(prompt)
        
        # Parse the JSON response
        try:
            print(f"Result: {result}")
            parsed_result = self.extract_json_from_text(str(result))
            
            # Store the new state in context
            if parsed_result:
                await ctx.set("state", parsed_result)
            
            # Log the conversation
            userMsg = f"<start_of_turn_user>user\n{message}</end_of_turn>"
            modelMsg = f"<start_of_turn_user>model\n{parsed_result['response']}</end_of_turn>"
            self.log_conversation(userMsg, modelMsg)
            
            # TODO: Handle function requests from result.functions
            # For now, just publish events for each function request
            if "functions" in parsed_result:
                for request in parsed_result["functions"]:
                    # TODO: Implement proper event handling for function requests
                    print(f"Function request: {request}")
            
            return StopEvent(result=parsed_result["response"])
            
        except json.JSONDecodeError as e:
            print(f"Error parsing LLM response: {e}")
            return StopEvent(result="I apologize, but I encountered an error processing the response. Please try again.")
