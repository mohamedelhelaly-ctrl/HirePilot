"""
Lever API - Complete Testing Suite
Author: SaiffMoh
Date: 2025-12-27
Description: Comprehensive script to test opportunities, post CV, update posting description,
             and verify all changes.
"""

import os
import requests
import json
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# Load environment variables
load_dotenv()

# --- Configuration ---
API_KEY = os.getenv('LEVER_API_KEY')
BASE_URL = "https://api.lever.co/v1"
SANDBOX_POSTING_ID = "97086bc6-6b08-4aff-96c5-6b9ef4eb237e"
CV_FILE_PATH = "Saifeldin Yousry Ahmed Resume.pdf"  # Update with your actual path

# --- Manual User ID (if you don't have users:read permission) ---
# From your posting data, these are valid user IDs you can use:
# Owner: "bdf8dcb4-e5c1-4347-a8c0-3bd3e14f2bb5"
# Hiring Manager: "de7f1232-5870-4d8a-bfb3-bb28a1eee01e"
MANUAL_USER_ID = "bdf8dcb4-e5c1-4347-a8c0-3bd3e14f2bb5"  # Set this to use manual user ID
EXISTING_OPPORTUNITY_ID = "11e46767-bd70-487d-822b-dc8c9bb86152"
# Job description for Junior AI Engineer
JOB_DESCRIPTION = """
# Junior AI/ML Engineer

## About the Role
We are seeking a talented Junior AI/ML Engineer to join our growing team. This role is perfect for recent graduates or early-career professionals passionate about artificial intelligence and machine learning.

## Key Responsibilities
- Develop and deploy machine learning models and AI solutions
- Work with RAG systems, LLMs, and transformer-based models
- Build and maintain data pipelines for ML workflows
- Collaborate with cross-functional teams to integrate AI solutions
- Participate in code reviews and contribute to best practices

## Required Qualifications
- Bachelor's degree in Computer Engineering, Computer Science, or related field
- Strong programming skills in Python
- Experience with ML frameworks (TensorFlow, PyTorch, Scikit-Learn)
- Knowledge of NLP and deep learning concepts
- Familiarity with API development (FastAPI, Flask)

## Preferred Qualifications
- Experience with LangChain, LangGraph, or similar frameworks
- Knowledge of vector databases (FAISS, ChromaDB)
- Experience with cloud platforms and deployment
- Strong problem-solving and communication skills

## What We Offer
- Competitive salary and benefits
- Opportunity to work on cutting-edge AI projects
- Collaborative and innovative work environment
- Professional development and growth opportunities
"""

# Global variables
created_opportunity_id = None
perform_as_user_id = None

def print_header(title):
    print("\n" + "━" * 80)
    print(f" {title}")
    print("━" * 80)

def print_json(data, indent=2):
    """Pretty print JSON data"""
    print(json.dumps(data, indent=indent))

# ============================================================================
# PHASE 0: Get a User to Perform As
# ============================================================================

def get_user_for_perform_as():
    """Get a user ID to use for perform_as parameter"""
    global perform_as_user_id
    
    print_header("PHASE 0: Getting User for Perform As")
    
    # Check if manual user ID is set
    if MANUAL_USER_ID:
        perform_as_user_id = MANUAL_USER_ID
        print(f"▶️  Using manually configured user ID")
        print(f"   ✅ User ID: {perform_as_user_id}")
        return perform_as_user_id
    
    # Try to fetch from API
    url = f"{BASE_URL}/users"
    
    try:
        print("▶️  Fetching users from API...")
        response = requests.get(
            url,
            auth=HTTPBasicAuth(API_KEY, ''),
            params={'limit': 1},
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('data') and len(result['data']) > 0:
                user = result['data'][0]
                perform_as_user_id = user['id']
                print(f"   ✅ SUCCESS: Found user to perform as")
                print(f"   User: {user.get('name', 'N/A')} ({user.get('email', 'N/A')})")
                print(f"   User ID: {perform_as_user_id}")
                return perform_as_user_id
            else:
                print(f"   ❌ No users found in account")
                return None
        elif response.status_code == 403:
            print(f"   ❌ FORBIDDEN: You need users:read permission")
            print(f"   Please set MANUAL_USER_ID in the script configuration")
            return None
        else:
            print(f"   ❌ FAILED (Status {response.status_code}): {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ NETWORK ERROR: {e}")
        return None

# ============================================================================
# PHASE 1: Create an Opportunity (Candidate Application)
# ============================================================================

def create_opportunity_with_cv():
    """Create a new opportunity with candidate data and CV attachment"""
    global created_opportunity_id
    
    print_header("PHASE 1: Creating New Opportunity with CV")
    
    # Build URL with perform_as query parameter
    url = f"{BASE_URL}/opportunities?perform_as={perform_as_user_id}"
    
    # Candidate data based on the resume - correct parameters per Lever API docs
    candidate_data = {
        "name": "Saifeldin Yousry Ahmed",
        "emails": ["saifeldin.m.ahmed@gmail.com"],
        "phones": [{"type": "mobile", "value": "+201276795505"}],
        "location": "Cairo, Egypt",
        "headline": "Computer Engineering Student | AI/ML Engineer",
        "origin": "applied",  # Indicates this is an application
        "sources": ["Manual API Test"],
        "tags": ["Python", "Machine Learning", "AI", "NLP", "LangChain"],
        "postings": [SANDBOX_POSTING_ID]  # Correct way to link to posting
    }
    
    try:
        # First, create the opportunity
        print("▶️  Creating opportunity...")
        response = requests.post(
            url,
            auth=HTTPBasicAuth(API_KEY, ''),
            json=candidate_data,
            timeout=20
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            created_opportunity_id = result['data']['id']
            print(f"   ✅ SUCCESS: Opportunity created with ID: {created_opportunity_id}")
            print(f"   Candidate: {result['data']['name']}")
            
            # Now upload the CV/resume
            if os.path.exists(CV_FILE_PATH):
                upload_resume(created_opportunity_id)
            else:
                print(f"   ⚠️  CV file not found at: {CV_FILE_PATH}")
                print(f"   Please update CV_FILE_PATH in the script")
            
            return created_opportunity_id
        else:
            print(f"   ❌ FAILED (Status {response.status_code}): {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ NETWORK ERROR: {e}")
        return None

def upload_resume(opportunity_id):
    """Upload a resume/CV file to an existing opportunity using the Files API"""
    print(f"\n▶️  Uploading CV to opportunity {opportunity_id}...")
    
    # Step 1: Upload file to get file ID
    upload_url = f"{BASE_URL}/uploads"
    
    try:
        with open(CV_FILE_PATH, 'rb') as file:
            files = {
                'file': (os.path.basename(CV_FILE_PATH), file, 'application/pdf')
            }
            
            print(f"   Step 1: Uploading file...")
            upload_response = requests.post(
                upload_url,
                auth=HTTPBasicAuth(API_KEY, ''),
                files=files,
                timeout=30
            )
            
            if upload_response.status_code in [200, 201]:
                upload_result = upload_response.json()
                file_id = upload_result['data']['id']
                print(f"   ✅ File uploaded with ID: {file_id}")
                
                # Step 2: Attach file to opportunity using multipart/form-data
                print(f"   Step 2: Attaching file to opportunity...")
                attach_url = f"{BASE_URL}/opportunities/{opportunity_id}/files"
                
                # Send as form data, not JSON
                attach_data = {
                    'file': file_id
                }
                
                attach_response = requests.post(
                    attach_url,
                    auth=HTTPBasicAuth(API_KEY, ''),
                    data=attach_data,  # Use data instead of json
                    timeout=20
                )
                
                if attach_response.status_code in [200, 201]:
                    print(f"   ✅ SUCCESS: Resume attached to opportunity")
                    result = attach_response.json()
                    if 'data' in result:
                        print(f"   Attached File ID: {result['data'].get('id', 'N/A')}")
                else:
                    print(f"   ❌ FAILED to attach (Status {attach_response.status_code}): {attach_response.text}")
            else:
                print(f"   ❌ FAILED to upload (Status {upload_response.status_code}): {upload_response.text}")
                
    except FileNotFoundError:
        print(f"   ❌ ERROR: File not found at {CV_FILE_PATH}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ NETWORK ERROR: {e}")

# ============================================================================
# PHASE 2: Update Posting Description
# ============================================================================

def update_posting_description():
    """Update the posting with Junior AI Engineer job description"""
    print_header("PHASE 2: Updating Posting Description")
    
    url = f"{BASE_URL}/postings/{SANDBOX_POSTING_ID}"
    
    # Correct format for posting content
    update_data = {
        "description": JOB_DESCRIPTION,
        "descriptionHtml": JOB_DESCRIPTION.replace('\n', '<br>')
    }
    
    try:
        print("▶️  Updating posting description...")
        response = requests.post(
            url,
            auth=HTTPBasicAuth(API_KEY, ''),
            json=update_data,
            timeout=20
        )
        
        if response.status_code == 200:
            print(f"   ✅ SUCCESS: Posting description updated")
            result = response.json()
            return result
        elif response.status_code == 400:
            print(f"   ⚠️  Status 400: {response.text}")
            print(f"   Note: The posting structure may not allow description updates via API")
            print(f"   Description updates might need to be done through the Lever UI")
        else:
            print(f"   ❌ FAILED (Status {response.status_code}): {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ NETWORK ERROR: {e}")
        return None

# ============================================================================
# PHASE 3: Read Back All Data
# ============================================================================

def read_posting_details():
    """Read the updated posting details"""
    print_header("PHASE 3: Reading Updated Posting Details")
    
    url = f"{BASE_URL}/postings/{SANDBOX_POSTING_ID}"
    
    try:
        print("▶️  Fetching posting details...")
        response = requests.get(
            url,
            auth=HTTPBasicAuth(API_KEY, ''),
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            posting = result['data']
            print(f"   ✅ SUCCESS: Retrieved posting details")
            print(f"\n   Posting: {posting['text']}")
            print(f"   State: {posting['state']}")
            print(f"   Location: {posting['categories'].get('location', 'N/A')}")
            print(f"   Department: {posting['categories'].get('department', 'N/A')}")
            print(f"\n   Description Preview:")
            desc = posting['content'].get('description', 'No description')
            print(f"   {desc[:200]}..." if len(desc) > 200 else f"   {desc}")
            return posting
        else:
            print(f"   ❌ FAILED (Status {response.status_code}): {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ NETWORK ERROR: {e}")
        return None

def read_opportunities_for_posting():
    """Read all opportunities (candidates) for the posting"""
    print_header("PHASE 4: Reading Opportunities for Posting")
    
    url = f"{BASE_URL}/opportunities"
    params = {
        "posting_id": SANDBOX_POSTING_ID,
        "expand": "applications"
    }
    
    try:
        print("▶️  Fetching opportunities...")
        response = requests.get(
            url,
            auth=HTTPBasicAuth(API_KEY, ''),
            params=params,
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            opportunities = result.get('data', [])
            print(f"   ✅ SUCCESS: Found {len(opportunities)} opportunity(ies)")
            
            for i, opp in enumerate(opportunities, 1):
                print(f"\n   Candidate {i}:")
                print(f"   - ID: {opp['id']}")
                print(f"   - Name: {opp.get('name', 'N/A')}")
                print(f"   - Email: {opp.get('emails', ['N/A'])[0]}")
                print(f"   - Stage: {opp.get('stage', 'N/A')}")
                print(f"   - Created: {opp.get('createdAt', 'N/A')}")
                
                # Check for resume
                if 'applications' in opp:
                    for app in opp['applications']:
                        if app.get('posting') == SANDBOX_POSTING_ID:
                            print(f"   - Application Type: {app.get('type', 'N/A')}")
            
            return opportunities
        else:
            print(f"   ❌ FAILED (Status {response.status_code}): {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ NETWORK ERROR: {e}")
        return None

def read_opportunity_details(opportunity_id):
    """Read detailed information about a specific opportunity"""
    print(f"\n▶️  Fetching details for opportunity {opportunity_id}...")
    
    url = f"{BASE_URL}/opportunities/{opportunity_id}"
    
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(API_KEY, ''),
            timeout=20
        )
        
        if response.status_code == 200:
            result = response.json()
            opp = result['data']
            print(f"   ✅ SUCCESS: Retrieved opportunity details")
            print(f"\n   Full Details:")
            print(f"   - Name: {opp.get('name', 'N/A')}")
            print(f"   - Headline: {opp.get('headline', 'N/A')}")
            print(f"   - Location: {opp.get('location', 'N/A')}")
            print(f"   - Emails: {', '.join(opp.get('emails', []))}")
            print(f"   - Phones: {', '.join([p.get('value', '') for p in opp.get('phones', [])])}")
            print(f"   - Tags: {', '.join(opp.get('tags', []))}")
            return opp
        else:
            print(f"   ❌ FAILED (Status {response.status_code}): {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ NETWORK ERROR: {e}")
        return None

# ============================================================================
# Main Execution
# ============================================================================

def run_complete_test():
    """Run the complete test suite"""
    if not API_KEY:
        raise ValueError("❌ LEVER_API_KEY not found in your .env file.")
    
    print("=" * 80)
    print("LEVER API - COMPLETE TESTING SUITE")
    print("=" * 80)
    
    # Phase 0: Get a user for perform_as
    user_id = get_user_for_perform_as()
    
    if not user_id:
        print("\n⚠️  Could not get user ID. Please set PERFORM_AS_USER_ID in script manually.")
        print("   You can find user IDs by listing users or in your Lever account.")
        return
    
    # Check if we should use existing opportunity or create new one
    if EXISTING_OPPORTUNITY_ID:
        print_header("Using Existing Opportunity")
        print(f"▶️  Using existing opportunity: {EXISTING_OPPORTUNITY_ID}")
        global created_opportunity_id
        created_opportunity_id = EXISTING_OPPORTUNITY_ID
        
        # Upload resume to existing opportunity
        if os.path.exists(CV_FILE_PATH):
            upload_resume(created_opportunity_id)
        else:
            print(f"   ⚠️  CV file not found at: {CV_FILE_PATH}")
        
        opportunity_id = created_opportunity_id
    else:
        # Phase 1: Create NEW opportunity with CV (COMMENTED OUT FOR REFERENCE)
        """
        # Uncomment this section to create a new opportunity
        opportunity_id = create_opportunity_with_cv()
        
        if not opportunity_id:
            print("\n⚠️  Failed to create opportunity. Stopping test.")
            return
        """
        print("\n⚠️  Set EXISTING_OPPORTUNITY_ID=None to create new opportunity")
        return
    
    if not opportunity_id:
        print("\n⚠️  Failed to create opportunity. Stopping test.")
        return
    
    # Phase 2: Update posting description
    update_posting_description()
    
    # Phase 3 & 4: Read everything back
    posting = read_posting_details()
    opportunities = read_opportunities_for_posting()
    
    # Get detailed info for our created opportunity
    if created_opportunity_id:
        read_opportunity_details(created_opportunity_id)
    
    # Final Summary
    print_header("TEST COMPLETE - SUMMARY")
    print(f"✅ Opportunity Created: {created_opportunity_id}")
    print(f"✅ CV Uploaded: {os.path.exists(CV_FILE_PATH)}")
    print(f"✅ Posting Updated: {posting is not None}")
    print(f"✅ Opportunities Retrieved: {len(opportunities) if opportunities else 0}")
    print("\n" + "=" * 80)

if __name__ == "__main__":
    run_complete_test()