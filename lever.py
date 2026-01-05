"""
Lever API - Sandbox Permissions Test (CORRECTED)
Author: SaiffMoh
Date: 2025-12-10
Description: CORRECTED SCRIPT. Fixes the typo for 'opportunities' endpoints
             and uses the correct POST method for updating a posting.
"""

import os
import requests
import json
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

# Load environment variables from a .env file
load_dotenv()

# --- Configuration ---
API_KEY = os.getenv('LEVER_API_KEY')
BASE_URL = "https://api.lever.co/v1"
SANDBOX_POSTING_ID = "97086bc6-6b08-4aff-96c5-6b9ef4eb237e"

# --- Global variables ---
sandbox_opportunity_id = None
permissions_summary = {
    'postings:read': False,
    'postings:write': False,
    'opportunities:read': False,
    'opportunities:write': False,
    'users:read': False,
    'stages:read': False,
    'archive_reasons:read': False,
    'sources:read': False,
    'feedback_templates:read': False,
    'webhooks:read': False
}

def print_header(title):
    print("\n" + "━" * 80)
    print(f" {title}")
    print("━" * 80)

def test_read_endpoint(name, url, permission_key, params=None):
    global permissions_summary
    print(f"▶️  Testing: {name}...")
    try:
        response = requests.get(url, auth=HTTPBasicAuth(API_KEY, ''), params=params, timeout=20)
        if response.status_code == 200:
            print(f"   ✅ SUCCESS (Status {response.status_code}): You have read access.")
            permissions_summary[permission_key] = True
            return response.json()
        elif response.status_code == 403:
            print(f"   ❌ FORBIDDEN (Status {response.status_code}): Your API key lacks the required '{permission_key}' permission.")
        else:
            print(f"   ⚠️  UNEXPECTED (Status {response.status_code}): The request failed. Response: {response.text[:100]}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ NETWORK ERROR: Could not connect to the API. {e}")
    return None

def test_safe_write_endpoint(name, url, permission_key, method="POST"):
    global permissions_summary
    print(f"▶️  Testing (Safe Write): {name}...")
    try:
        # **NOTE: For updating a posting, the API uses POST, not PUT**
        if method.upper() == "POST":
            response = requests.post(url, auth=HTTPBasicAuth(API_KEY, ''), json={}, timeout=20)
        elif method.upper() == "PUT": # Kept for other endpoints that might use PUT
             response = requests.put(url, auth=HTTPBasicAuth(API_KEY, ''), json={}, timeout=20)
        else:
            print(f"   ❌ Invalid method '{method}' for write test.")
            return

        if response.status_code in [400, 422]:
            print(f"   ✅ SUCCESS (Status {response.status_code}): Write access CONFIRMED. The API rejected the empty data as expected.")
            permissions_summary[permission_key] = True
        elif response.status_code == 403:
            print(f"   ❌ FORBIDDEN (Status {response.status_code}): Your API key lacks the required '{permission_key}' permission.")
        elif response.status_code in [200, 201]:
            print(f"   ⚠️  UNEXPECTED SUCCESS (Status {response.status_code}): A resource may have been created/updated. Please check your Lever dashboard.")
        else:
            print(f"   ⚠️  UNEXPECTED (Status {response.status_code}): The request failed. Response: {response.text[:100]}")
    except requests.exceptions.RequestException as e:
        print(f"   ❌ NETWORK ERROR: Could not connect to the API. {e}")

def run_tests():
    global sandbox_opportunity_id
    if not API_KEY:
        raise ValueError("❌ LEVER_API_KEY not found in your .env file.")

    print_header("PHASE 1: General Read Permissions")
    test_read_endpoint("List Users", f"{BASE_URL}/users", "users:read", params={'limit': 1})
    test_read_endpoint("List Stages", f"{BASE_URL}/stages", "stages:read", params={'limit': 1})
    test_read_endpoint("List Sources", f"{BASE_URL}/sources", "sources:read", params={'limit': 1})
    test_read_endpoint("List Archive Reasons", f"{BASE_URL}/archive_reasons", "archive_reasons:read", params={'limit': 1})
    test_read_endpoint("List Feedback Templates", f"{BASE_URL}/feedback_templates", "feedback_templates:read", params={'limit': 1})
    test_read_endpoint("List Webhooks", f"{BASE_URL}/webhooks", "webhooks:read")

    print_header(f"PHASE 2: Read Tests on Sandbox Posting ID: ...{SANDBOX_POSTING_ID[-12:]}")
    test_read_endpoint("Get Posting Details", f"{BASE_URL}/postings/{SANDBOX_POSTING_ID}", "postings:read")

    # **FIXED URL HERE: 'opportunities' is spelled correctly**
    data = test_read_endpoint(
        "List Opportunities for Posting",
        f"{BASE_URL}/postings/{SANDBOX_POSTING_ID}/opportunities",
        "opportunities:read"
    )
    if data and data.get('data'):
        sandbox_opportunity_id = data['data'][0]['id']
        print(f"   ✅ Found an existing candidate. Will use Opportunity ID: ...{sandbox_opportunity_id[-12:]} for further tests.")
    else:
        print("   ℹ️  No existing candidates found for this posting. Some opportunity-specific tests will be skipped.")

    print_header(f"PHASE 3: Write Tests on Sandbox Posting ID: ...{SANDBOX_POSTING_ID[-12:]}")
    # **FIXED METHOD HERE: Using POST for update as per Lever docs**
    test_safe_write_endpoint(
        "Update Posting",
        f"{BASE_URL}/postings/{SANDBOX_POSTING_ID}",
        "postings:write",
        method="POST"
    )

    print_header("PHASE 4: Opportunity (Candidate) Permissions Tests")
    if sandbox_opportunity_id:
        test_read_endpoint("Get Opportunity Details", f"{BASE_URL}/opportunities/{sandbox_opportunity_id}", "opportunities:read")
        test_safe_write_endpoint("Add a Note to Opportunity", f"{BASE_URL}/opportunities/{sandbox_opportunity_id}/notes", "opportunities:write", method="POST")
    else:
        print("   ℹ️  Skipping tests that require an existing candidate ID.")
        # **FIXED URL HERE: 'opportunities' is spelled correctly**
        test_safe_write_endpoint(
            "Create New Opportunity for Posting",
            f"{BASE_URL}/postings/{SANDBOX_POSTING_ID}/opportunities",
            "opportunities:write",
            method="POST"
        )

def print_final_summary():
    print_header("FINAL PERMISSIONS SUMMARY")
    print("Based on the tests, your API key appears to have the following permissions:")
    verified_permissions = [key for key, value in permissions_summary.items() if value]
    if not verified_permissions:
        print("\n   ❌ No permissions could be successfully verified.")
    else:
        for perm in sorted(verified_permissions):
            print(f"   ✅ {perm}")
    print("\n" + "━" * 80)
    print("Test complete.")

if __name__ == "__main__":
    run_tests()
    print_final_summary()