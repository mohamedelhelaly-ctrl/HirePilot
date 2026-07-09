import os
import requests
from dotenv import load_dotenv
from typing import Optional, Dict, Any
import json

# Load environment variables
load_dotenv()

class LeverAPITester:
    """Test Lever API access for postings"""
    
    def __init__(self):
        self.api_key = os.getenv("LEVER_API_KEY")
        
        if not self.api_key:
            raise ValueError("LEVER_API_KEY not found in .env file")
        
        # Lever API base URL
        self.base_url = "https://api.lever.co/v1"
        
        # Setup authentication (Basic Auth with API key as username, empty password)
        self.auth = (self.api_key, '')
        
        print("✓ API Key loaded successfully")
        print(f"✓ Testing connection to: {self.base_url}\n")
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[Any, Any]]:
        """Make GET request to Lever API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            print(f"→ Calling: {endpoint}")
            if params:
                print(f"  Parameters: {params}")
            response = requests.get(url, auth=self.auth, params=params)
            
            # Print response status
            print(f"  Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print(f"  ✓ Success!")
                return response.json()
            elif response.status_code == 401:
                print(f"  ✗ Authentication failed - check your API key")
                return None
            elif response.status_code == 403:
                print(f"  ✗ Forbidden - API key lacks permission for this endpoint")
                return None
            else:
                print(f"  ✗ Error: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"  ✗ Request failed: {str(e)}")
            return None
    
    def test_postings(self, limit: int = 50):
        """Test access to postings endpoint with limit
        
        Args:
            limit: Maximum number of postings to retrieve (default: 50)
        """
        print("\n" + "="*60)
        print(f"TESTING: Postings Endpoint (Limit: {limit})")
        print("="*60)
        
        # Try with just limit parameter first
        params = {
            'limit': limit
        }
        
        data = self._make_request("/postings", params=params)
        
        if data:
            postings = data.get('data', [])
            has_next = data.get('hasNext', False)
            
            print(f"\n✓ Retrieved {len(postings)} postings")
            if has_next:
                print(f"  ℹ More postings available beyond the limit")
            print()
            
            # Sort by creation date to ensure most recent first
            postings_sorted = sorted(
                postings, 
                key=lambda x: x.get('createdAt', 0), 
                reverse=True
            )
            
            # Take only the most recent 50
            postings_limited = postings_sorted[:limit]
            
            print(f"Showing {min(len(postings_limited), 3)} of {len(postings_limited)} most recent postings:\n")
            
            # Display first 3 postings
            for i, post in enumerate(postings_limited[:3], 1):
                print(f"Posting #{i}:")
                print(f"  ID: {post.get('id')}")
                print(f"  Text: {post.get('text', 'N/A')}")
                print(f"  State: {post.get('state', 'N/A')}")
                print(f"  Requisition ID: {post.get('requisitionId', 'N/A')}")
                print(f"  Created: {post.get('createdAt', 'N/A')}")
                
                # Show job description preview if available
                content = post.get('content', {})
                description = content.get('description', '')
                if description:
                    preview = description[:150] + "..." if len(description) > 150 else description
                    print(f"  Description: {preview}")
                print()
            
            if len(postings_limited) > 3:
                print(f"... and {len(postings_limited) - 3} more postings")
            
            return postings_limited
        
        return None
    
    def save_response_to_file(self, data: Dict, filename: str):
        """Save API response to JSON file for inspection"""
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\n✓ Full response saved to: {filename}")


def main():
    """Main test function"""
    print("\n" + "="*60)
    print("LEVER API ACCESS TESTER - POSTINGS ONLY")
    print("="*60)
    
    try:
        # Initialize tester
        tester = LeverAPITester()
        
        # Test postings with limit of 50 most recent
        postings = tester.test_postings(limit=50)
        
        # Save full response to file for detailed inspection
        if postings:
            tester.save_response_to_file(
                {"data": postings, "count": len(postings)}, 
                "lever_postings_response.json"
            )
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Postings Access: {'✓ YES' if postings else '✗ NO'}")
        if postings:
            print(f"Postings Retrieved: {len(postings)} (most recent, limited to 50)")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        raise


if __name__ == "__main__":
    main()