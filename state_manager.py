from typing import Any, Dict
import asyncio

import streamlit as st


class StateManager:
    """Manages the application state."""
    
    @staticmethod
    def init_session_state():
        """Initialize session state if not already initialized"""
        if 'chat_state' not in st.session_state:
            st.session_state.chat_state = {}
        if 'app_state' not in st.session_state:
            st.session_state.app_state = {}
        if 'event_listeners' not in st.session_state:
            st.session_state.event_listeners = {}
    
    @staticmethod
    def get_chat_state() -> dict:
        """Get the current chat state"""
        return st.session_state.get('chat_state', {})
    
    @staticmethod
    def get_app_state() -> dict:
        """Get the current application state"""
        return st.session_state.get('app_state', {})
    
    @staticmethod
    def get_session_state() -> dict:
        """Get the current application state"""
        return st.session_state
    
    @staticmethod
    def update_chat_state(new_state: dict):
        """Update chat state with new state"""
        # Update the chat state
        st.session_state.chat_state = new_state
    
    @staticmethod
    def update_app_state(new_state: dict):
        """Update app state with new state"""
        # Simply update the app state with the new state
        st.session_state.app_state = new_state
    
    @staticmethod
    def add_event_listener(event_type: str, callback: callable):
        """Add a listener for events."""
        if event_type not in st.session_state.event_listeners:
            st.session_state.event_listeners[event_type] = []
        st.session_state.event_listeners[event_type].append(callback)
    
    @staticmethod
    async def emit_event(event_type: str, data: Any):
        """Emit an event to all listeners."""
        if event_type in st.session_state.event_listeners:
            for callback in st.session_state.event_listeners[event_type]:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
