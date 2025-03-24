# Rovis Streamlit AI

Rovis Streamlit AI is an interactive chatbot application that helps users plan road trips by suggesting routes and places to visit based on their preferences and constraints.

## Features

- Interactive chat interface for planning trips
- Interactive map visualization with routes and points of interest
- Ability to search for restaurants, hotels, rest areas, and attractions
- Custom route planning based on user preferences
- User can place markers on the map to indicate specific locations
- Intelligent responses to user queries using LLM technology

## Prerequisites

- Python 3.8 or higher
- API keys for:
  - OpenRouter.ai (for LLM access)
  - TomTom (for geocoding and routing)
  - HERE.com (for places search)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/rovis-streamlit-ai.git
   cd rovis-streamlit-ai
   ```

2. Create a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```
   python3 -m pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with your API keys:
   ```
   OPENROUTER_API_KEY=your_openrouter_api_key
   TOMTOM_API_KEY=your_tomtom_api_key
   HERE_API_KEY=your_here_api_key
   ```

## Running the Application

1. Run the Streamlit application:
   ```
   python3 -m streamlit run app.py
   ```

2. The application will open in your default web browser.

## How to Use

1. Start by answering the initial questions:
   - Start location
   - Destinations
   - Time constraints
   - Driving hours per day
   - Walking time per day

2. The application will suggest a route based on your preferences.

3. You can interact with the chatbot to:
   - Find places to eat
   - Find places to stay
   - Add or modify stops
   - Get more information about specific locations

4. Use the map to:
   - View the suggested route
   - Place markers at locations of interest
   - Select points of interest (like restaurants, hotels, etc.)

## Project Structure

- `app.py`: Main Streamlit application
- `agent_handler.py`: LLM agent implementation
- `api_wrappers.py`: Wrappers for external APIs
- `map_utils.py`: Map utility functions
- `requirements.txt`: Required Python packages

## API Documentation

The application uses the following APIs:

1. **OpenRouter API**: For LLM functionality (Google's Gemma 3 27b model)
2. **TomTom API**: 
   - Geocoding API to convert addresses to coordinates
   - Routing API to calculate routes between locations
3. **HERE API**:
   - Places API to find restaurants, hotels, and other points of interest

## License

This project is proprietary software. All rights reserved. See the LICENSE file for details.