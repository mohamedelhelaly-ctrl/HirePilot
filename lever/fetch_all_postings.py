"""
Lever API - Fetch All Job Postings
Author: SaiffMoh
Date: 2025-11-14 18:46:40 UTC
Description: Fetches all job postings from Lever API with full details
"""

import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Configuration
API_KEY = os.getenv('LEVER_API_KEY')
BASE_URL = "https://api.lever.co/v1"

if not API_KEY:
    raise ValueError("❌ LEVER_API_KEY not found in .env file")

def fetch_all_postings():
    """
    Fetch all job postings from Lever API with pagination support
    """
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("           LEVER API - ALL JOB POSTINGS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"User: SaiffMoh")
    print(f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    all_postings = []
    offset = 0
    limit = 100  # Max per request
    
    while True:
        print(f"📥 Fetching postings (offset: {offset}, limit: {limit})...")
        
        try:
            response = requests.get(
                f"{BASE_URL}/postings",
                auth=HTTPBasicAuth(API_KEY, ''),
                params={
                    'limit': limit,
                    'offset': offset,
                    'state': 'published',  # published, internal, or rejected
                    'include': 'owner,hiringManager'  # Include additional details
                },
                timeout=30
            )
            
            if response.status_code != 200:
                print(f"❌ Error {response.status_code}: {response.text}")
                break
            
            data = response.json()
            postings = data.get('data', [])
            
            if not postings:
                print("✅ No more postings found\n")
                break
            
            all_postings.extend(postings)
            print(f"   Retrieved {len(postings)} postings")
            
            # Check if there are more results
            has_next = data.get('hasNext', False)
            if not has_next:
                break
            
            offset += limit
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error: {e}")
            break
    
    return all_postings


def display_postings(postings):
    """
    Display all postings in a readable format
    """
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"         TOTAL POSTINGS FOUND: {len(postings)}")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    for idx, posting in enumerate(postings, 1):
        print(f"┌─ POSTING #{idx} {'─' * 50}")
        print(f"│")
        print(f"│ 📋 Title: {posting.get('text', 'N/A')}")
        print(f"│ 🆔 ID: {posting.get('id', 'N/A')}")
        print(f"│ 🔗 URL: https://jobs.lever.co/YOUR_COMPANY/{posting.get('id', '')}")
        print(f"│")
        print(f"│ 📊 State: {posting.get('state', 'N/A').upper()}")
        print(f"│ 📅 Created: {format_timestamp(posting.get('createdAt'))}")
        print(f"│ 🔄 Updated: {format_timestamp(posting.get('updatedAt'))}")
        print(f"│")
        
        # Categories (teams/departments)
        categories = posting.get('categories', {})
        if categories:
            print(f"│ 🏢 Department: {categories.get('department', 'N/A')}")
            print(f"│ 📍 Location: {categories.get('location', 'N/A')}")
            print(f"│ 👥 Team: {categories.get('team', 'N/A')}")
            print(f"│ 💼 Commitment: {categories.get('commitment', 'N/A')}")
        
        # Description preview
        description = posting.get('description', '')
        if description:
            desc_preview = description[:200].replace('\n', ' ')
            print(f"│")
            print(f"│ 📝 Description (preview):")
            print(f"│    {desc_preview}...")
        
        # Distribution channels
        channels = posting.get('distributionChannels', [])
        if channels:
            channel_names = ', '.join(channels)
            print(f"│")
            print(f"│ 📡 Distribution: {channel_names}")
        
        # Owner info
        owner = posting.get('user')
        if owner:
            print(f"│")
            print(f"│ 👤 Owner: {owner.get('name', 'N/A')}")
        
        print(f"│")
        print(f"└{'─' * 60}\n")


def format_timestamp(timestamp):
    """
    Format Unix timestamp (milliseconds) to readable date
    """
    if not timestamp:
        return "N/A"
    
    try:
        dt = datetime.fromtimestamp(timestamp / 1000)
        return dt.strftime('%Y-%m-%d %H:%M:%S UTC')
    except:
        return str(timestamp)


def save_to_json(postings, filename="lever_postings.json"):
    """
    Save postings to JSON file
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(postings, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved {len(postings)} postings to: {filename}")
    except Exception as e:
        print(f"❌ Error saving to file: {e}")


def print_summary_stats(postings):
    """
    Print summary statistics about postings
    """
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("                  SUMMARY STATISTICS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    # Count by state
    states = {}
    for p in postings:
        state = p.get('state', 'unknown')
        states[state] = states.get(state, 0) + 1
    
    print("📊 By State:")
    for state, count in states.items():
        print(f"   {state.upper():<15} {count:>3} postings")
    
    # Count by department
    departments = {}
    for p in postings:
        dept = p.get('categories', {}).get('department', 'Uncategorized')
        departments[dept] = departments.get(dept, 0) + 1
    
    print("\n🏢 By Department:")
    for dept, count in sorted(departments.items(), key=lambda x: x[1], reverse=True):
        print(f"   {dept:<30} {count:>3} postings")
    
    # Count by location
    locations = {}
    for p in postings:
        loc = p.get('categories', {}).get('location', 'Unspecified')
        locations[loc] = locations.get(loc, 0) + 1
    
    print("\n📍 By Location:")
    for loc, count in sorted(locations.items(), key=lambda x: x[1], reverse=True):
        print(f"   {loc:<30} {count:>3} postings")
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")


def main():
    """
    Main execution function
    """
    # Fetch all postings
    postings = fetch_all_postings()
    
    if not postings:
        print("⚠️  No postings found or error occurred")
        return
    
    # Display postings
    display_postings(postings)
    
    # Print summary stats
    print_summary_stats(postings)
    
    # Save to JSON
    save_to_json(postings)
    
    print("\n✅ Script completed successfully!")
    print(f"📊 Total postings retrieved: {len(postings)}")


if __name__ == "__main__":
    main()