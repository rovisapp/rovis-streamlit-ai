from typing import Any, Dict

import streamlit as st


class StateManager:
    @staticmethod
    def init_session_state():
        """Initialize session state if not exists"""
        if 'app_state' not in st.session_state:
            st.session_state.app_state = {
                'searches': [],
                'routes': []
            }
        if 'chat_state' not in st.session_state:
            st.session_state.chat_state = {
                'start': None,
                'end': None,
                'endAtStart': False,
                'waypoints': [],
                'userTimeConstraintDescription': None,
                'maxDrivingHoursPerDay': None,
                'maxWalkingTime': None,
                'departAt': None,
                'reachBy': None,
                'thought': None,
                'response': None,
                'action': None
            }

    @staticmethod
    def update_chat_state(route_info: Dict[str, Any]):
        """Update chat state with route information"""
        for key, value in route_info.items():
            if key in st.session_state.chat_state:
                st.session_state.chat_state[key] = value

    @staticmethod
    def update_app_state(action: str, data: Dict[str, Any]):
        """Update app state based on action"""
        if action == "search":
            st.session_state.app_state['searches'].append(data)
        elif action == "route":
            st.session_state.app_state['routes'].append(data) 