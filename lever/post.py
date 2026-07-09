"""
Lever API - Fetch All Postings
Author: SaiffMoh
Date: 2025-12-10
Description: Fetches ALL job postings across all pages from the Lever API
             and saves the complete results to a single JSON file.
"""

import os
import requests
import json
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from datetime import datetime, timezone

# Load environment variables from a .env file
load_dotenv()

# --- Configuration ---
API_KEY = os.getenv('LEVER_API_KEY')
BASE_URL = "https://api.lever.co/v1"
OUTPUT_FILENAME = "lever_postings_all.json"

# --- Main Script Logic ---

def convert_timestamp_to_datetime(timestamp_ms):
    """
    Converts a Unix timestamp in milliseconds to a readable datetime string.
    
    Args:
        timestamp_ms (int): Unix timestamp in milliseconds
    
    Returns:
        str: Formatted datetime string (ISO 8601 format)
    """
    if timestamp_ms:
        dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        return dt.isoformat()
    return None


def convert_posting_timestamps(posting):
    """
    Converts all timestamp fields in a posting to readable datetime strings.
    
    Args:
        posting (dict): The posting object
    
    Returns:
        dict: The posting with converted timestamps
    """
    # Fields that contain timestamps in milliseconds
    timestamp_fields = ['createdAt', 'updatedAt']
    
    for field in timestamp_fields:
        if field in posting and posting[field]:
            posting[f'{field}_readable'] = convert_timestamp_to_datetime(posting[field])
    
    return posting


def fetch_all_postings(state=None, confidentiality=None):
    """
    Fetches all job postings from all pages without any filters.
    
    Args:
        state (str): Optional filter by state ('published', 'internal', 'closed', 'draft', 'pending', 'rejected')
        confidentiality (str): Optional filter by confidentiality ('confidential', 'non-confidential')

    Returns:
        list: A list of dictionaries, where each dictionary is a job posting.
    """
    if not API_KEY:
        raise ValueError("❌ LEVER_API_KEY not found in your .env file. Please create it.")

    filter_msg = []
    if state:
        filter_msg.append(f"state={state}")
    if confidentiality:
        filter_msg.append(f"confidentiality={confidentiality}")
    
    if filter_msg:
        print(f"🚀 Starting to fetch postings with filters: {', '.join(filter_msg)}...")
    else:
        print("🚀 Starting to fetch ALL postings from the beginning of time...")
    
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    all_postings = []
    
    # Initial parameters for the API request. 'limit=100' is the maximum allowed per page.
    params = {
        'limit': 100
    }
    
    # Add optional filters
    if state:
        params['state'] = state
    if confidentiality:
        params['confidentiality'] = confidentiality
    
    url = f"{BASE_URL}/postings"
    page_count = 0

    # Loop continuously until there are no more pages of results
    while True:
        page_count += 1
        print(f"📄 Fetching page {page_count} of postings...")
        
        try:
            response = requests.get(
                url,
                auth=HTTPBasicAuth(API_KEY, ''),
                params=params,
                timeout=30  # 30-second timeout for the request
            )
            # Raise an HTTPError for bad responses (4xx or 5xx)
            response.raise_for_status()
            
            data = response.json()
            
            # Add the postings from the current page to our master list
            if 'data' in data and data['data']:
                postings_on_page = data['data']
                
                # Convert timestamps to readable format
                for posting in postings_on_page:
                    posting = convert_posting_timestamps(posting)
                
                all_postings.extend(postings_on_page)
                print(f"   ✓ Found {len(postings_on_page)} postings on this page (Total: {len(all_postings)})")
            else:
                # This can happen if the last page is empty
                print("   ⚠️ No postings found on this page.")

            # Check if the 'hasNext' field is true to determine if we should continue
            if data.get('hasNext'):
                # The 'next' value is the cursor (offset) for the next page
                params['offset'] = data['next']
            else:
                # If 'hasNext' is false or absent, we've reached the end
                print("\n🏁 Reached the last page. All postings have been fetched.")
                break
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"❌ HTTP Error 403: Forbidden. Check if your API key has 'postings:read' permissions.")
            else:
                print(f"❌ An HTTP error occurred: {e}")
            break
        except requests.exceptions.RequestException as e:
            print(f"❌ A network error occurred: {e}")
            break
            
    return all_postings

def save_data_to_json(data_list, filename):
    """
    Saves a list of dictionaries to a JSON file with metadata.
    """
    if not data_list:
        print(f"⚠️ No data was fetched. The file '{filename}' will not be created.")
        return

    # Add metadata to the output
    output_data = {
        "metadata": {
            "fetched_at": datetime.now().isoformat(),
            "total_postings": len(data_list),
            "source": "Lever API v1"
        },
        "postings": data_list
    }

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\n✅ Success! All {len(data_list)} postings have been saved to '{filename}'")
        print(f"📊 File size: {os.path.getsize(filename) / 1024:.2f} KB")
    except IOError as e:
        print(f"❌ Failed to write to file '{filename}'. Error: {e}")


if __name__ == "__main__":
    print("="*70)
    print("LEVER POSTINGS FETCH SCRIPT")
    print("="*70 + "\n")
    
    # Ask user for filters
    print("Available filters:")
    print("  States: published, internal, closed, draft, pending, rejected")
    print("  Confidentiality: confidential, non-confidential")
    print("  (Press Enter to skip any filter)\n")
    
    state_filter = input("Filter by state (or press Enter for all): ").strip().lower() or None
    confidentiality_filter = input("Filter by confidentiality (or press Enter for all): ").strip().lower() or None
    
    # Validate inputs
    valid_states = ['published', 'internal', 'closed', 'draft', 'pending', 'rejected']
    valid_confidentiality = ['confidential', 'non-confidential']
    
    if state_filter and state_filter not in valid_states:
        print(f"⚠️ Invalid state. Using no filter. Valid options: {', '.join(valid_states)}")
        state_filter = None
    
    if confidentiality_filter and confidentiality_filter not in valid_confidentiality:
        print(f"⚠️ Invalid confidentiality. Using no filter. Valid options: {', '.join(valid_confidentiality)}")
        confidentiality_filter = None
    
    print()
    
    # 1. Fetch all posting data from the API
    postings_data = fetch_all_postings(state=state_filter, confidentiality=confidentiality_filter)
    
    # 2. Generate filename based on filters
    filename_parts = ["lever_postings"]
    if state_filter:
        filename_parts.append(state_filter)
    if confidentiality_filter:
        filename_parts.append(confidentiality_filter)
    if len(filename_parts) == 1:
        filename_parts.append("all")
    
    output_filename = "_".join(filename_parts) + ".json"
    
    # 3. Save the complete dataset to a JSON file
    save_data_to_json(postings_data, output_filename)
    
    print(f"\n⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")