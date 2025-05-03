from typing import Any, Dict

import streamlit as st


class StateManager:
    @staticmethod
    def init_session_state():
        """Initialize session state if not already initialized"""
        if 'chat_state' not in st.session_state:
            st.session_state.chat_state = {}
        if 'app_state' not in st.session_state:
            st.session_state.app_state = {}

    @staticmethod
    def get_chat_state() -> dict:
        """Get the current chat state"""
        return st.session_state.get('chat_state', {})

    @staticmethod
    def get_app_state() -> dict:
        """Get the current application state"""
        return st.session_state.get('app_state', {})

    @staticmethod
    def update_chat_state(new_state: dict):
        """Update chat state with new state"""
        st.session_state.chat_state = new_state

    @staticmethod
    def update_app_state(new_state: dict):
        """Update app state with new state"""
        st.session_state.app_state = new_state
