from dotenv import load_dotenv
import os
import streamlit as st

def load_environment():
    """Load environment variables from .env file"""
    load_dotenv()
    
    # Check if API keys are set
    openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
    tomtom_api_key = os.getenv("TOMTOM_API_KEY")
    here_api_key = os.getenv("HERE_API_KEY")
    
    missing_keys = []
    if not openrouter_api_key:
        missing_keys.append("OPENROUTER_API_KEY")
    if not tomtom_api_key:
        missing_keys.append("TOMTOM_API_KEY")
    if not here_api_key:
        missing_keys.append("HERE_API_KEY")
    
    # Display warning if any keys are missing
    if missing_keys:
        keys_str = ", ".join(missing_keys)
        st.error(f"Missing API keys: {keys_str}. Please add them to your .env file.")
        st.stop()
    
    return {
        "OPENROUTER_API_KEY": openrouter_api_key,
        "TOMTOM_API_KEY": tomtom_api_key,
        "HERE_API_KEY": here_api_key
    }