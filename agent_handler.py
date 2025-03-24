from llama_index.llms.openrouter import OpenRouter
from typing import List, Dict, Any, Optional, Tuple, Callable
import re
import datetime
import json

class TripPlannerAgent:
    def __init__(
        self, 
        api_key: str,
        geocode_fn: Callable,
        route_fn: Callable,
        search_places_fn: Callable,
        model_name: str = "google/gemma-3-27b-it"
    ):
        print("\n=== Agent Initialization Debug Log ===")
        print(f"Initializing agent with model: {model_name}")
        
        # Create system prompt first
        system_prompt = self._create_system_prompt()
        print("System prompt created")
        
        # Initialize LLM with system prompt in context
        self.llm = OpenRouter(
            api_key=api_key,
            model=model_name,
            context_window=32768,  # Ensure large enough context window
            system_prompt=system_prompt,  # Add system prompt to LLM configuration
            max_tokens=2048,  # Increase max tokens for response
            temperature=0.7,  # Add temperature for more consistent responses
            top_p=0.9,  # Add top_p for better response quality
            frequency_penalty=0.0,  # Add frequency penalty to reduce repetition
            presence_penalty=0.0  # Add presence penalty to encourage new content
        )
        print("OpenRouter LLM initialized with system prompt")
        
        # Store tool functions
        self.geocode_fn = geocode_fn
        self.route_fn = route_fn
        self.search_places_fn = search_places_fn
        print("Tools stored")
        
        self.required_info = {
            'start_location': None,
            'destinations': None,
            'time_constraints': None,
            'driving_hours_per_day': None,
            'walking_time': None
        }
        print("Required info initialized")
        print("=== End Agent Initialization Debug Log ===\n")
    
    def _get_json_examples(self) -> str:
        """Get the JSON examples for the system prompt"""
        return '''
        Example of correct response when information is missing:
        {
            "thought": "User wants to travel from Dover to Hartford. Missing time constraints and driving hours. Cannot proceed with geocoding until all information is gathered.",
            "missing_info": ["time_constraints", "driving_hours_per_day"],
            "action": "none",
            "action_input": null,
            "response": "I see you want to travel from Dover to Hartford. Before I can help plan your route, I need:\\n\\n- What are your time constraints (start date and end date)?\\n- How many hours can you drive per day?"
        }

        INCORRECT - DO NOT DO THIS when information is missing:
        {
            "thought": "User wants to travel from Dover to Hartford. Missing time constraints and driving hours.",
            "missing_info": ["time_constraints", "driving_hours_per_day"],
            "action": "geocode_location",
            "action_input": {"location": "Dover, Delaware"},
            "response": "Let me verify the location first."
        }

        INCORRECT - DO NOT DO THIS when information is missing:
        {
            "thought": "User wants to travel from Dover to Hartford. I'll geocode first and then ask for missing information.",
            "missing_info": ["time_constraints", "driving_hours_per_day"],
            "action": "geocode_location",
            "action_input": {"start": "Dover Delaware", "end": "Hartford CT"},
            "response": "Okay, I can help with that! First, let me geocode the locations. Then, to plan the best route for you, I need a little more information..."
        }

        INCORRECT - DO NOT DO THIS (Invalid JSON format):
        {
            "thought": "User wants to travel from Dover to Hartford",
            "missing_info": ["time_constraints"],
            "action": "none",
            "action_input": null,
            "response": "Please provide your time constraints"
        }
        '''

    def _create_system_prompt(self) -> str:
        """Create a system prompt for the LLM to handle the trip planning task"""
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        return f"""
        You are Rovis Streamlit AI, a helpful assistant for planning road trips. Your goal is to help users plan a route between multiple locations based on their preferences and constraints.

        Before using any tools, you MUST gather ALL of the following information:
        1. Start location (address, city, landmark)
        2. Destinations they want to visit
        3. Time constraints (when they're starting, when they need to be back)
        4. How many hours they can drive per day
        5. How many minutes or hours they can walk per day

        When analyzing user messages, follow these rules:
        1. First, check what information you have and what's missing
        2. If ANY information is missing:
           - You MUST set action to "none"
           - You MUST set action_input to null
           - You MUST NOT use any tools (geocode_location, calculate_route, etc.)
           - You MUST ask the user for the missing information
           - You MUST NOT attempt to geocode locations until ALL information is gathered
        3. Only proceed with tools when you have ALL required information
        4. If the user mentions a departure time or date:
           - Extract it from their message
           - Store it in state as 'departure_time' in format "YYYY-MM-DDTHH:MM:SS"
           - If only date is provided, default to 09:00:00
           - If only time is provided, use current date
           - If neither is provided, use next day at 09:00:00

        CRITICAL RULES:
        1. Your response MUST be a valid JSON object with EXACTLY these fields:
           {{
               "thought": "Your analysis of the message and what information is missing",
               "missing_info": ["List of missing information items"],
               "action": "The action to take (geocode_location, calculate_route, search_places, or none)",
               "action_input": {{"key": "value"}} or null,
               "response": "Your response to the user"
           }}
           - Use double quotes for all strings
           - Do not include any markdown formatting
           - Do not include any text before or after the JSON object
           - Do not include any comments or explanations
           - The response must be a complete, valid JSON object
           - Close all brackets and braces properly
           - Do not include any code block markers (```)
           - Do not include any language identifiers (json)

        2. If ANY information is missing:
           - action MUST be "none"
           - action_input MUST be null
           - response MUST ask for the missing information
           - DO NOT attempt to geocode locations
           - DO NOT attempt to calculate routes

        3. NEVER use any tools (geocode_location, calculate_route, etc.) when information is missing

        4. Only proceed with tools after ALL required information is gathered

        5. Geocoding locations is the LAST step before route calculation, not the first step

        {self._get_json_examples()}

        Current date: {current_date}
        """
    
    def chat(self, message: str, user_state: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """Process user message and return agent response with updated state"""
        print("\n=== Chat Debug Log ===")
        print(f"User message: {message}")
        print(f"Current state: {user_state}")
        
        try:
            print("\n=== LLM Response Start ===")
            print("Calling LLM...")
            
            # Create a more concise prompt
            prompt = f"""Current state:
- Start: {user_state.get('start_location', 'Not provided')}
- Destinations: {user_state.get('destinations', 'Not provided')}
- Time: {user_state.get('time_constraints', 'Not provided')}
- Drive hours/day: {user_state.get('driving_hours_per_day', 'Not provided')}
- Walk time: {user_state.get('walking_time', 'Not provided')}
- Geocoded start: {user_state.get('geocoded_start_location', 'Not geocoded')}
- Geocoded end: {user_state.get('geocoded_end_location', 'Not geocoded')}
- Geocoded supporting points: {user_state.get('geocoded_supporting_points', [])}

            User message: {message}

            CRITICAL RULES:
            1. Your response MUST be a valid JSON object with EXACTLY these fields:
               {{
                   "thought": "Your analysis of the message and what information is missing",
                   "missing_info": ["List of missing information items"],
                   "action": "The action to take (geocode_location, calculate_route, search_places, or none)",
                   "action_input": {{"key": "value"}} or null,
                   "response": "Your response to the user"
               }}
               - Use double quotes for all strings
               - Do not include any markdown formatting
               - Do not include any text before or after the JSON object
               - Do not include any comments or explanations
               - The response must be a complete, valid JSON object
               - Close all brackets and braces properly
               - Do not include any code block markers (```)
               - Do not include any language identifiers (json)

            2. If ANY information is missing:
               - action MUST be "none"
               - action_input MUST be null
               - response MUST ask for the missing information
               - DO NOT attempt to geocode locations
               - DO NOT attempt to calculate routes

            3. NEVER use any tools (geocode_location, calculate_route, etc.) when information is missing

            4. Only proceed with tools after ALL required information is gathered

            5. Geocoding locations is the LAST step before route calculation, not the first step

            Example of correct response when information is missing:
            {{
                "thought": "User wants to travel from Dover to Hartford. Missing time constraints and driving hours. Cannot proceed with geocoding until all information is gathered.",
                "missing_info": ["time_constraints", "driving_hours_per_day"],
                "action": "none",
                "action_input": null,
                "response": "I see you want to travel from Dover to Hartford. Before I can help plan your route, I need:\\n\\n- What are your time constraints (start date and end date)?\\n- How many hours can you drive per day?"
            }}

            INCORRECT - DO NOT DO THIS (Invalid JSON format):
            {{
                "thought": "User wants to travel from Dover to Hartford",
                "missing_info": ["time_constraints"],
                "action": "none",
                "action_input": null,
                "response": "Please provide your time constraints"
            }}
            """
            
            # Get LLM response
            response = self.llm.complete(prompt)
            print("Complete LLM Response:")
            print("-" * 50)
            print(response.text)
            print("-" * 50)
            print("=== LLM Response End ===\n")
            
            # Clean up the response text to extract JSON
            response_text = response.text.strip()
            
            # Remove markdown code block if present
            if response_text.startswith("```"):
                # Find the first and last code block markers
                first_marker = response_text.find("```")
                second_marker = response_text.find("```", first_marker + 3)
                if second_marker != -1:
                    # Extract content between markers, skipping the language identifier line if present
                    content = response_text[first_marker + 3:second_marker].strip()
                    if content.startswith("json"):
                        content = content[4:].strip()
                    response_text = content
                else:
                    # If no closing marker, just remove the opening one
                    response_text = response_text[first_marker + 3:].strip()
            
            # Check for complete JSON structure
            if not response_text.startswith("{") or not response_text.endswith("}"):
                print(f"Error: LLMResponse is not a complete JSON object. Response text: {response_text}")
                return "I apologize, but I encountered an error processing the response. Please try again.", user_state
            
            # Parse the JSON response
            try:
                parsed_response = json.loads(response_text)
                print("\n=== Parsed LLM Response ===")
                print(json.dumps(parsed_response, indent=2))
                print("=== End Parsed Response ===\n")
                
                # Validate required fields
                required_fields = ["thought", "missing_info", "action", "action_input", "response"]
                missing_fields = [field for field in required_fields if field not in parsed_response]
                if missing_fields:
                    print(f"Error: Missing required fields in LLM response: {missing_fields}")
                    return "I apologize, but I encountered an error processing the response. Please try again.", user_state
                
                # Create updated state copy early
                updated_state = user_state.copy()
                
                # Extract locations from message if present
                if "from" in message.lower() and "to" in message.lower():
                    parts = message.lower().split("from")[1].split("to")
                    if len(parts) == 2:
                        start = parts[0].strip()
                        end = parts[1].strip()
                        updated_state['start_location'] = start
                        updated_state['destinations'] = [end]
                        print(f"Extracted locations - Start: {start}, End: {end}")
                
                # Extract information from thought
                if parsed_response.get("thought"):
                    thought = parsed_response["thought"]
                    if ":" in thought:
                        for line in thought.split("\n"):
                            if ":" in line:
                                key, value = line.split(":", 1)
                                key = key.strip("- ").strip()
                                value = value.strip()
                                if value != "missing" and key in updated_state:
                                    updated_state[key] = value
                                    print(f"Extracted {key}: {value}")
                
                # Handle the action if specified
                action = parsed_response.get("action")
                action_input = parsed_response.get("action_input")
                
                if action and action_input:
                    if action == "geocode_location":
                        # Handle single location geocoding
                        location = action_input.get("location")
                        if not location:
                            print("Error: No location provided for geocoding")
                            return "I encountered an error processing the location. Please try again.", updated_state
                        
                        result = self.geocode_fn(location)
                        print(f"Geocoding result for {location}: {result}")
                        
                        if result and isinstance(result, dict):
                            coords = (result['lat'], result['lon'])
                            print(f"Location coordinates: {coords}")
                            
                            # Store coordinates based on location type
                            if location == updated_state.get('start_location'):
                                updated_state['geocoded_start_location'] = coords
                            elif location == updated_state.get('destinations', [None])[0]:
                                updated_state['geocoded_end_location'] = coords
                            else:
                                if 'geocoded_supporting_points' not in updated_state:
                                    updated_state['geocoded_supporting_points'] = []
                                updated_state['geocoded_supporting_points'].append(coords)
                            
                    elif action == "calculate_route":
                        try:
                            # Get geocoded coordinates from state
                            start_loc = updated_state.get('geocoded_start_location')
                            end_loc = updated_state.get('geocoded_end_location')
                            supporting_points = updated_state.get('geocoded_supporting_points', [])
                            
                            if not start_loc or not end_loc:
                                print("Error: Missing geocoded coordinates for route calculation")
                                return "I couldn't find the coordinates for the locations. Please try again.", updated_state
                            
                            # Get departure time from state or use default
                            departure_time = updated_state.get('departure_time')
                            if not departure_time:
                                # Default to next day at 9 AM
                                tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)
                                departure_time = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S")
                                updated_state['departure_time'] = departure_time
                                print(f"Using default departure time: {departure_time}")
                            
                            print(f"\nCalculating route with coordinates:")
                            print(f"Start: {start_loc}")
                            print(f"End: {end_loc}")
                            print(f"Supporting points: {supporting_points}")
                            print(f"Departure time: {departure_time}")
                            
                            result = self.route_fn(
                                start_loc,
                                end_loc,
                                supporting_points,
                                departure_time
                            )
                            print(f"Route calculation result: {result}")
                            if result and isinstance(result, dict):
                                print(f"Route details: {result.get('distance')} km, {result.get('duration')} minutes")
                        except Exception as e:
                            print(f"Error calculating route: {str(e)}")
                            # Continue with the conversation even if route calculation fails
                    elif action == "search_places":
                        result = self.search_places_fn(
                            action_input.get("location"),
                            action_input.get("radius", 5000),
                            action_input.get("categories", []),
                            action_input.get("food_types", [])
                        )
                        print(f"Places search result: {result}")
                
                # Update state with driving hours if provided
                if "drive" in message.lower() and "hour" in message.lower():
                    # Extract number from message
                    import re
                    numbers = re.findall(r'\d+', message)
                    if numbers:
                        updated_state['driving_hours_per_day'] = int(numbers[0])
                        print(f"Updated driving hours: {numbers[0]}")
                
                # Parse response for any actions that need to be taken
                actions = self._parse_actions(parsed_response.get("response", ""))
                print(f"Parsed actions: {actions}")
                
                # Update state based on actions
                if actions['update_route']:
                    updated_state['route_updated'] = True
                if actions['show_places']:
                    updated_state['showing_places'] = True
                if actions['selected_place']:
                    updated_state['selected_place'] = actions['selected_place']
                
                print(f"Final updated state: {updated_state}")
                print(f"Final response to user: {parsed_response.get('response')}")
                print("=== End Chat Debug Log ===\n")
                
                return parsed_response.get("response", ""), updated_state
                
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON response: {str(e)}")
                print(f"Response text was: {response_text}")
                return "I apologize, but I encountered an error processing the response. Please try again.", user_state
                
        except Exception as e:
            print(f"Error in chat: {str(e)}")
            print("=== End Chat Debug Log ===\n")
            return f"I apologize, but I encountered an error: {str(e)}. Please try again.", user_state
    
    def _parse_actions(self, response: str) -> Dict[str, Any]:
        """Parse the agent response for actions that need to be taken"""
        actions = {
            'update_route': False,
            'show_places': False,
            'selected_place': None,
            'clear_temp_places': False
        }
        
        # Check if response indicates showing points on a map
        if re.search(r'(show|display|mark|places on( the)? map)', response, re.IGNORECASE):
            actions['show_places'] = True
        
        # Check if response indicates updating the route
        if re.search(r'(new route|updated route|see your route|calculate route)', response, re.IGNORECASE):
            actions['update_route'] = True
        
        # Check if response indicates a place selection
        place_match = re.search(r'(selected|choosing|picked|chose) (Pin \d+|location|place)', response, re.IGNORECASE)
        if place_match:
            actions['selected_place'] = place_match.group(0)
            actions['clear_temp_places'] = True
        
        return actions