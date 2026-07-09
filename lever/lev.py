"""
Lever API Test Script
Tests read operations for postings and candidates/opportunities
"""

import os
import requests
from dotenv import load_dotenv
from typing import Dict, List, Optional
import json

# Load environment variables
load_dotenv()

class LeverAPIClient:
    """Client for interacting with Lever API"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.lever.co/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def get_postings(self, limit: int = 10) -> Dict:
        """
        Retrieve all job postings
        
        Args:
            limit: Maximum number of postings to retrieve
            
        Returns:
            Dictionary containing postings data
        """
        endpoint = f"{self.base_url}/postings"
        params = {"limit": limit}
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status_code": getattr(e.response, 'status_code', None)}
    
    def get_posting_by_id(self, posting_id: str) -> Dict:
        """
        Get detailed information about a specific posting
        
        Args:
            posting_id: Lever posting ID
            
        Returns:
            Dictionary containing posting details
        """
        endpoint = f"{self.base_url}/postings/{posting_id}"
        
        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status_code": getattr(e.response, 'status_code', None)}
    
    def get_opportunities(self, limit: int = 10, expand: Optional[List[str]] = None) -> Dict:
        """
        Retrieve candidates/opportunities
        
        Args:
            limit: Maximum number of opportunities to retrieve
            expand: List of fields to expand (e.g., ['applications', 'stage'])
            
        Returns:
            Dictionary containing opportunities data
        """
        endpoint = f"{self.base_url}/opportunities"
        params = {"limit": limit}
        
        if expand:
            params["expand"] = ",".join(expand)
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status_code": getattr(e.response, 'status_code', None)}
    
    def get_opportunity_by_id(self, opportunity_id: str, expand: Optional[List[str]] = None) -> Dict:
        """
        Get detailed information about a specific candidate/opportunity
        
        Args:
            opportunity_id: Lever opportunity ID
            expand: List of fields to expand
            
        Returns:
            Dictionary containing opportunity details
        """
        endpoint = f"{self.base_url}/opportunities/{opportunity_id}"
        params = {}
        
        if expand:
            params["expand"] = ",".join(expand)
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status_code": getattr(e.response, 'status_code', None)}
    
    def get_stages(self) -> Dict:
        """
        Retrieve all pipeline stages
        
        Returns:
            Dictionary containing stages data
        """
        endpoint = f"{self.base_url}/stages"
        
        try:
            response = requests.get(endpoint, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status_code": getattr(e.response, 'status_code', None)}
    
    def get_users(self, limit: int = 10) -> Dict:
        """
        Retrieve users (recruiters, hiring managers)
        
        Args:
            limit: Maximum number of users to retrieve
            
        Returns:
            Dictionary containing users data
        """
        endpoint = f"{self.base_url}/users"
        params = {"limit": limit}
        
        try:
            response = requests.get(endpoint, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e), "status_code": getattr(e.response, 'status_code', None)}


def print_section(title: str):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def pretty_print_json(data: Dict, max_items: int = 3):
    """Pretty print JSON data with limiting"""
    if "error" in data:
        print(f"❌ Error: {data['error']}")
        if data.get('status_code'):
            print(f"   Status Code: {data['status_code']}")
        return
    
    # Handle paginated responses (list of items)
    if "data" in data and isinstance(data["data"], list):
        items = data["data"]
        print(f"✅ Found {len(items)} items")
        print(f"   Showing first {min(max_items, len(items))} items:\n")
        
        for i, item in enumerate(items[:max_items], 1):
            print(f"   [{i}] {json.dumps(item, indent=6)}")
        
        if len(items) > max_items:
            print(f"\n   ... and {len(items) - max_items} more items")
        
        # Print pagination info if available
        if data.get("hasNext"):
            print(f"\n   📄 Has more pages available")
    # Handle single item response
    elif "data" in data and isinstance(data["data"], dict):
        print(f"✅ Retrieved single item:\n")
        print(json.dumps(data["data"], indent=2))
    else:
        # Fallback for other response structures
        print(json.dumps(data, indent=2))


def main():
    """Main test function"""
    
    # Get API key from environment
    api_key = os.getenv("LEVER_API_KEY")
    
    if not api_key:
        print("❌ Error: LEVER_API_KEY not found in .env file")
        print("   Please create a .env file with: LEVER_API_KEY=your_api_key_here")
        return
    
    print("\n🚀 Starting Lever API Tests...")
    print(f"   Using API key: {api_key[:10]}...{api_key[-4:]}")
    
    # Initialize client
    client = LeverAPIClient(api_key)
    
    # Test 1: Get Postings
    print_section("TEST 1: Get Job Postings")
    postings = client.get_postings(limit=5)
    pretty_print_json(postings)
    
    # Test 2: Get Specific Posting (if we have postings)
    if "data" in postings and len(postings["data"]) > 0:
        print_section("TEST 2: Get Specific Posting Details")
        posting_id = postings["data"][0]["id"]
        print(f"Fetching details for posting ID: {posting_id}\n")
        posting_detail = client.get_posting_by_id(posting_id)
        pretty_print_json(posting_detail)
    
    # Test 3: Get Opportunities (Candidates)
    print_section("TEST 3: Get Opportunities (Candidates)")
    opportunities = client.get_opportunities(limit=5, expand=["applications", "stage"])
    pretty_print_json(opportunities)
    
    # Test 4: Get Specific Opportunity (if we have opportunities)
    if "data" in opportunities and len(opportunities["data"]) > 0:
        print_section("TEST 4: Get Specific Candidate Details")
        opportunity_id = opportunities["data"][0]["id"]
        print(f"Fetching details for opportunity ID: {opportunity_id}\n")
        opportunity_detail = client.get_opportunity_by_id(
            opportunity_id, 
            expand=["applications", "stage", "resume"]
        )
        pretty_print_json(opportunity_detail)
    
    # Test 5: Get Pipeline Stages
    print_section("TEST 5: Get Pipeline Stages")
    stages = client.get_stages()
    pretty_print_json(stages)
    
    # Test 6: Get Users
    print_section("TEST 6: Get Users (Recruiters/Hiring Managers)")
    users = client.get_users(limit=5)
    pretty_print_json(users)
    
    print_section("✅ All Tests Completed")
    print("Check the results above for any errors or successful data retrieval.\n")


if __name__ == "__main__":
    main()