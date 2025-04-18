#source venv/bin/activate && streamlit run app.py
import asyncio
import datetime
import os
from typing import Any, Dict, List, Optional, Tuple

import folium
import streamlit as st
from streamlit_folium import st_folium

# Import custom modules
from agent_handler import TripPlannerAgent
from load_env import load_environment
from state_manager import StateManager

# Set page configuration
st.set_page_config(page_title="Rovis Streamlit AI", layout="wide")

# Load environment variables from .env file
env_vars = load_environment()
OPENROUTER_API_KEY = env_vars["OPENROUTER_API_KEY"]

# Initialize session state
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.messages = []
    st.session_state.off_topic_count = 0  # Initialize off-topic count
    StateManager.init_session_state()
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

# Initialize LLM agent
@st.cache_resource
def get_agent():
    agent = TripPlannerAgent(
        api_key=OPENROUTER_API_KEY
    )
    return agent

agent = get_agent()

# Main chat interface
st.header("Rovis")

# Create two columns
col1, col2 = st.columns([1, 1])

# Chat interface in first column
with col1:
    # Create a container for chat messages
    chat_container = st.empty()

    # Display chat messages
    with chat_container.container():
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Chat input
    if message := st.chat_input("Type your message here..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": message})
        
        # Update chat display immediately
        with chat_container.container():
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        try:
            # Send message to agent
            response = asyncio.run(agent.async_chat(message, st.session_state.messages))
            
            # Add assistant message to chat
            st.session_state.messages.append({"role": "assistant", "content": response})
            
            # Update chat display immediately
            with chat_container.container():
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                    
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
            st.session_state.messages.append({
                "role": "assistant",
                "content": "I apologize, but I encountered an error. Please try again."
            })
            # Update chat display immediately
            with chat_container.container():
                for message in st.session_state.messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])

# Map in second column
with col2:
    # Create and display a basic map centered on the US
    m = folium.Map(location=[37.0902, -95.7129], zoom_start=4)
    st_folium(m, width=700, height=500)

# Add styling
st.markdown("""
<style>
.stChat {
    height: 500px;
    overflow-y: auto;
}
</style>
""", unsafe_allow_html=True)