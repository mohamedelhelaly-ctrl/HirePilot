"""
Lever API - Test Opportunities Access
Author: SaiffMoh
Date: 2025-11-14 19:08:12 UTC
Description: Comprehensive test for opportunities endpoint access
             Run this immediately after super admin grants permissions
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


def print_header():
    """Print test header"""
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("      LEVER API - OPPORTUNITIES ACCESS TEST")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"User: SaiffMoh")
    print(f"Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")


def test_endpoint(name, url, params=None, description=""):
    """
    Test a single endpoint and return results
    """
    print(f"┌─ Testing: {name}")
    print(f"│  {description}")
    print(f"│  URL: {url}")
    if params:
        print(f"│  Params: {params}")
    print(f"│")
    
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(API_KEY, ''),
            params=params,
            timeout=30
        )
        
        status = response.status_code
        
        if status == 200:
            data = response.json()
            records = data.get('data', [])
            has_next = data.get('hasNext', False)
            
            print(f"│  ✅ SUCCESS - Status: {status}")
            print(f"│  📊 Records found: {len(records)}")
            print(f"│  🔄 Has more pages: {has_next}")
            
            if records:
                first_record = records[0]
                print(f"│")
                print(f"│  📋 Sample Record Keys:")
                for key in list(first_record.keys())[:10]:
                    value = first_record[key]
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"│     • {key}: {value}")
                if len(first_record.keys()) > 10:
                    print(f"│     ... and {len(first_record.keys()) - 10} more keys")
            
            print(f"└{'─' * 60}\n")
            return {
                'success': True,
                'status': status,
                'count': len(records),
                'data': data
            }
            
        elif status == 403:
            error_data = response.json()
            print(f"│  ❌ FAILED - Status: {status}")
            print(f"│  🚫 Error: {error_data.get('code', 'Unknown')}")
            print(f"│  💬 Message: {error_data.get('message', 'No message')}")
            print(f"│")
            print(f"│  ⚠️  PERMISSION DENIED - Need super admin to grant access")
            print(f"└{'─' * 60}\n")
            return {
                'success': False,
                'status': status,
                'error': error_data
            }
            
        else:
            error_data = response.json() if response.text else {}
            print(f"│  ❌ FAILED - Status: {status}")
            print(f"│  Error: {error_data}")
            print(f"└{'─' * 60}\n")
            return {
                'success': False,
                'status': status,
                'error': error_data
            }
            
    except requests.exceptions.RequestException as e:
        print(f"│  ❌ NETWORK ERROR")
        print(f"│  {str(e)}")
        print(f"└{'─' * 60}\n")
        return {
            'success': False,
            'error': str(e)
        }


def run_all_tests():
    """
    Run comprehensive tests for opportunities and related endpoints
    """
    results = {}
    
    # Test 1: Basic opportunities list
    results['opportunities_basic'] = test_endpoint(
        name="GET /opportunities (basic)",
        url=f"{BASE_URL}/opportunities",
        params={'limit': 5},
        description="Fetch first 5 opportunities/candidates"
    )
    
    # Test 2: Opportunities with expanded fields
    results['opportunities_expanded'] = test_endpoint(
        name="GET /opportunities (expanded)",
        url=f"{BASE_URL}/opportunities",
        params={
            'limit': 5,
            'expand': 'applications,resumes,stage,owner'
        },
        description="Fetch opportunities with applications, resumes, stage, and owner details"
    )
    
    # Test 3: Opportunities with specific stage filter
    results['opportunities_stage_filter'] = test_endpoint(
        name="GET /opportunities (stage filter)",
        url=f"{BASE_URL}/opportunities",
        params={
            'limit': 5,
            'stage_id': 'lead-new',  # Common stage ID
            'expand': 'stage'
        },
        description="Fetch opportunities in 'new lead' stage"
    )
    
    # Test 4: Opportunities archived (rejected candidates)
    results['opportunities_archived'] = test_endpoint(
        name="GET /opportunities (archived)",
        url=f"{BASE_URL}/opportunities",
        params={
            'limit': 5,
            'archived': 'true'
        },
        description="Fetch archived/rejected candidates"
    )
    
    # Test 5: Single opportunity detail (will use first ID if we get data)
    if results['opportunities_basic']['success'] and results['opportunities_basic']['data'].get('data'):
        first_opp_id = results['opportunities_basic']['data']['data'][0]['id']
        results['opportunity_detail'] = test_endpoint(
            name=f"GET /opportunities/{first_opp_id}",
            url=f"{BASE_URL}/opportunities/{first_opp_id}",
            description="Fetch detailed info for a specific candidate"
        )
        
        # Test 6: Resumes for specific opportunity
        results['opportunity_resumes'] = test_endpoint(
            name=f"GET /opportunities/{first_opp_id}/resumes",
            url=f"{BASE_URL}/opportunities/{first_opp_id}/resumes",
            description="Fetch resume files for a specific candidate"
        )
        
        # Test 7: Applications for specific opportunity
        results['opportunity_applications'] = test_endpoint(
            name=f"GET /opportunities/{first_opp_id}/applications",
            url=f"{BASE_URL}/opportunities/{first_opp_id}/applications",
            description="Fetch job applications for a specific candidate"
        )
        
        # Test 8: Notes for specific opportunity
        results['opportunity_notes'] = test_endpoint(
            name=f"GET /opportunities/{first_opp_id}/notes",
            url=f"{BASE_URL}/opportunities/{first_opp_id}/notes",
            description="Fetch recruiter notes for a specific candidate"
        )
        
        # Test 9: Feedback for specific opportunity
        results['opportunity_feedback'] = test_endpoint(
            name=f"GET /opportunities/{first_opp_id}/feedback",
            url=f"{BASE_URL}/opportunities/{first_opp_id}/feedback",
            description="Fetch interview feedback for a specific candidate"
        )
    else:
        print("⚠️  Skipping sub-endpoint tests (no opportunity ID available)\n")
    
    return results


def print_summary(results):
    """
    Print test summary
    """
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("                    TEST SUMMARY")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    total_tests = len(results)
    successful_tests = sum(1 for r in results.values() if r.get('success', False))
    failed_tests = total_tests - successful_tests
    
    print(f"📊 Total Tests Run: {total_tests}")
    print(f"✅ Successful: {successful_tests}")
    print(f"❌ Failed: {failed_tests}")
    print()
    
    # Group by status
    success_list = []
    failed_403 = []
    failed_other = []
    
    for name, result in results.items():
        if result.get('success'):
            count = result.get('count', 0)
            success_list.append((name, count))
        elif result.get('status') == 403:
            failed_403.append(name)
        else:
            failed_other.append((name, result.get('status', 'Unknown')))
    
    if success_list:
        print("✅ ACCESSIBLE ENDPOINTS:")
        for name, count in success_list:
            print(f"   • {name:<40} ({count} records)")
        print()
    
    if failed_403:
        print("🚫 PERMISSION DENIED (HTTP 403):")
        for name in failed_403:
            print(f"   • {name}")
        print()
        print("   💡 ACTION REQUIRED:")
        print("      Contact your Lever super admin to grant:")
        print("      → opportunities:read")
        print("      → opportunities:write (for future automation)")
        print()
    
    if failed_other:
        print("❌ OTHER ERRORS:")
        for name, status in failed_other:
            print(f"   • {name:<40} (Status: {status})")
        print()
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


def save_results(results, filename="opportunities_test_results.json"):
    """
    Save test results to JSON file
    """
    try:
        # Clean results for JSON serialization
        clean_results = {}
        for key, value in results.items():
            clean_results[key] = {
                'success': value.get('success', False),
                'status': value.get('status'),
                'count': value.get('count', 0),
                'error': value.get('error', {})
            }
        
        output = {
            'test_date': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'),
            'user': 'SaiffMoh',
            'results': clean_results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {filename}")
        
    except Exception as e:
        print(f"\n❌ Error saving results: {e}")


def check_cv_access(results):
    """
    Special check for CV/resume access
    """
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("          CV/RESUME ACCESS CHECK (Critical for AI)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    if results.get('opportunity_resumes', {}).get('success'):
        print("✅ SUCCESS - Can access candidate resumes!")
        print("   → AI CV screening is READY")
        print("   → Can parse resume text for embeddings")
        print("   → Can extract work history, skills, education")
    else:
        print("❌ BLOCKED - Cannot access candidate resumes")
        print("   → AI CV screening is BLOCKED")
        print("   → Cannot perform semantic matching")
        print("   → Core functionality unavailable")
    
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


def print_next_steps(results):
    """
    Print actionable next steps based on results
    """
    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("                    NEXT STEPS")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
    
    has_access = any(r.get('success', False) for r in results.values())
    
    if has_access:
        print("🎉 GREAT NEWS! You have opportunities access!")
        print()
        print("✅ Immediate Actions:")
        print("   1. Run: python fetch_candidates_and_cvs.py")
        print("      → Extract all candidate CVs for AI processing")
        print()
        print("   2. Run: python link_candidates_to_postings.py")
        print("      → Map candidates to job postings")
        print()
        print("   3. Run: python generate_cv_embeddings.py")
        print("      → Create vector embeddings for semantic search")
        print()
        print("   4. Start building LangGraph screening pipeline")
        print("      → cv_screening_node implementation")
        print()
    else:
        print("⚠️  ACCESS STILL BLOCKED")
        print()
        print("🔴 URGENT ACTION REQUIRED:")
        print("   1. Send this test result to your Lever super admin")
        print("   2. Request permissions:")
        print("      → opportunities:read (CRITICAL)")
        print("      → opportunities:write (for automation)")
        print()
        print("   3. Run this script again after permissions granted:")
        print("      python test_opportunities_access.py")
        print()
        print("📧 Email Template:")
        print("   Subject: URGENT - Opportunities Access Needed for AI Project")
        print("   Body: See opportunities_test_results.json")
        print()
    
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")


def main():
    """
    Main execution
    """
    print_header()
    
    print("🚀 Starting comprehensive opportunities access test...")
    print("   This will test all candidate-related endpoints\n")
    
    # Run all tests
    results = run_all_tests()
    
    # Print summary
    print_summary(results)
    
    # Check CV access specifically
    check_cv_access(results)
    
    # Save results
    save_results(results)
    
    # Print next steps
    print_next_steps(results)
    
    print("\n✅ Test completed!")
    print(f"📅 Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"👤 User: SaiffMoh\n")


if __name__ == "__main__":
    main()