import requests
from typing import List, Dict, Any, Tuple, Optional
import json

class TomTomAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.tomtom.com"
    
    def geocode(self, location: str) -> Dict[str, Any]:
        """Geocode a location string to get latitude and longitude"""
        url = f"{self.base_url}/search/2/geocode/{location}.json"
        params = {
            "key": self.api_key
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if 'results' in data and len(data['results']) > 0:
                position = data['results'][0]['position']
                return {
                    'lat': position['lat'],
                    'lon': position['lon'],
                    'display_name': data['results'][0].get('address', {}).get('freeformAddress', location)
                }
            return None
        except (requests.RequestException, json.JSONDecodeError, KeyError) as e:
            print(f"Error geocoding location: {str(e)}")
            return None
    
    def calculate_route(
        self, 
        start_location: Tuple[float, float], 
        end_location: Tuple[float, float], 
        supporting_points: List[Tuple[float, float]] = None,
        departure_time: str = None
    ) -> Dict[str, Any]:
        """Calculate a route using TomTom API"""
        start_str = f"{start_location[0]},{start_location[1]}"
        end_str = f"{end_location[0]},{end_location[1]}"
        
        url = f"{self.base_url}/routing/1/calculateRoute/{start_str}:{end_str}/json"
        
        params = {
            "instructionsType": "text",
            "routeRepresentation": "polyline",
            "computeTravelTimeFor": "all",
            "routeType": "fastest",
            "traffic": "true",
            "extendedRouteRepresentation": "travelTime",
            "key": self.api_key
        }
        
        if departure_time:
            params["departAt"] = departure_time
        
        data = {}
        if supporting_points and len(supporting_points) > 0:
            data["supportingPoints"] = [
                {"latitude": lat, "longitude": lon} for lat, lon in supporting_points
            ]
        
        print(f"\nRoute API call:")
        print(f"URL: {url}")
        print(f"Params: {params}")
        print(f"Data: {data}")
        
        try:
            response = requests.post(url, params=params, json=data if data else None)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"Error calculating route API: {str(e)}")
            return {}
    
    def extract_route_summary(self, route_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract summary information from a route"""
        summary = {
            'distance': None,
            'travel_time': None,
            'arrival_time': None,
            'departure_time': None,
            'has_traffic': False
        }
        
        if 'routes' in route_data and len(route_data['routes']) > 0:
            route = route_data['routes'][0]
            
            if 'summary' in route:
                route_summary = route['summary']
                summary['distance'] = route_summary.get('lengthInMeters')
                summary['travel_time'] = route_summary.get('travelTimeInSeconds')
                summary['has_traffic'] = 'trafficDelayInSeconds' in route_summary
                
                if summary['has_traffic']:
                    summary['traffic_delay'] = route_summary.get('trafficDelayInSeconds')
            
            # Extract arrival and departure times if available
            if 'legs' in route and len(route['legs']) > 0:
                first_leg = route['legs'][0]
                last_leg = route['legs'][-1]
                
                if 'departure' in first_leg and 'time' in first_leg['departure']:
                    summary['departure_time'] = first_leg['departure']['time']
                
                if 'arrival' in last_leg and 'time' in last_leg['arrival']:
                    summary['arrival_time'] = last_leg['arrival']['time']
        
        return summary

class HereAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://browse.search.hereapi.com/v1"
        
        # Common category groups
        self.meal_categories = [
            "100", "100-1000-0000", "100-1000-0001", "100-1000-0002", "100-1000-0003", 
            "100-1000-0004", "100-1000-0005", "100-1000-0006", "100-1000-0007", 
            "100-1000-0008", "100-1000-0009", "100-1000-0050", "100-1100-0000", 
            "100-1100-0010", "100-1100-0331"
        ]
        
        self.rest_categories = [
            "400-4300", "550", "800-8500", "800-8300", "700-7600", "600-6000", 
            "600-6100", "600-6200", "600-6300-0066", "600-6400", "600-6600", 
            "600-6900-0247", "700-7460", "700-7850", "700-7900", "900-9200"
        ]
        
        self.hotel_categories = [
            "550", "500-5000-0000", "500-5000-0053", "500-5000-0054", "500-5100-0000", 
            "500-5100-0055", "500-5100-0056", "500-5100-0057", "500-5100-0058", 
            "500-5100-0059", "500-5100-0060", "500-5100-0061", "550-5510-0000", 
            "550-5510-0202", "550-5510-0203", "550-5510-0204", "550-5510-0205", 
            "550-5510-0206", "550-5510-0227", "550-5510-0242", "550-5510-0358", 
            "550-5510-0359", "550-5510-0374", "550-5510-0378", "550-5510-0379", 
            "550-5510-0380", "550-5510-0387", "550-5520-0000", "550-5520-0207", 
            "550-5520-0208", "550-5520-0209", "550-5520-0210", "550-5520-0211", 
            "550-5520-0212", "550-5520-0228", "550-5520-0357"
        ]
        
        self.gas_stations = ["700-7600"]
    
    def search_places(
        self,
        location: Tuple[float, float], 
        radius: int = 8047,  # 5 miles in meters
        categories: List[str] = None,
        food_types: List[str] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search for places near a location"""
        lat, lon = location
        url = f"{self.base_url}/browse"
        
        params = {
            "at": f"{lat},{lon}",
            "in": f"circle:{lat},{lon};r={radius}",
            "limit": limit,
            "apiKey": self.api_key
        }
        
        if categories:
            params["categories"] = ",".join(categories)
        
        if food_types:
            params["foodTypes"] = ",".join(food_types)
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"Error searching places: {str(e)}")
            return {"items": []}
    
    def search_meal_places(
        self, 
        location: Tuple[float, float], 
        radius: int = 8047,
        food_type: str = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search for meal places near a location"""
        categories = self.meal_categories
        food_types = [food_type] if food_type else None
        
        return self.search_places(location, radius, categories, food_types, limit)
    
    def search_rest_areas(
        self, 
        location: Tuple[float, float], 
        radius: int = 8047,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search for rest areas near a location"""
        return self.search_places(location, radius, self.rest_categories, None, limit)
    
    def search_hotels(
        self, 
        location: Tuple[float, float], 
        radius: int = 8047,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search for hotels near a location"""
        return self.search_places(location, radius, self.hotel_categories, None, limit)
    
    def search_gas_stations(
        self, 
        location: Tuple[float, float], 
        radius: int = 8047,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Search for gas stations near a location"""
        return self.search_places(location, radius, self.gas_stations, None, limit)