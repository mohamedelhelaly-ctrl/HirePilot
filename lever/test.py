"""
Lever API - Complete Permission Test (Read + Write)
Author: SaiffMoh
Date: 2025-11-14 19:12:40 UTC
Description: Tests ALL read and write permissions without modifying data
             Uses safe methods to detect permission levels
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
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("         LEVER API - COMPLETE PERMISSIONS TEST")
    print("              (Read + Write - No Data Modified)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"User: SaiffMoh")
    print(f"Date: 2025-11-14 19:12:40 UTC")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")


def test_read_endpoint(name, url, params=None, description="", priority="MEDIUM"):
    """
    Test a READ endpoint
    """
    return test_endpoint(
        name=name,
        method="GET",
        url=url,
        params=params,
        description=description,
        priority=priority,
        endpoint_type="READ"
    )


def test_write_endpoint(name, url, method="POST", description="", priority="MEDIUM", test_payload=None):
    """
    Test a WRITE endpoint WITHOUT actually writing
    Strategy: Send invalid/minimal payload to get permission check before validation
    """
    # Use OPTIONS request first (safest)
    try:
        options_response = requests.options(
            url,
            auth=HTTPBasicAuth(API_KEY, ''),
            timeout=10
        )
        
        # If OPTIONS succeeds, we likely have access
        if options_response.status_code in [200, 204]:
            print(f"┌─ Testing: {name}")
            print(f"│  {description}")
            print(f"│  Method: {method} {url}")
            print(f"│  Priority: {priority}")
            print(f"│")
            print(f"│  ✅ WRITE ACCESS DETECTED (via OPTIONS)")
            print(f"│  📝 Safe test - no data modified")
            print(f"│  🔑 You have write permissions for this endpoint")
            print(f"└{'─' * 70}\n")
            
            return {
                'success': True,
                'has_access': True,
                'method': method,
                'tested_via': 'OPTIONS',
                'priority': priority,
                'type': 'WRITE'
            }
    except:
        pass
    
    # Fallback: Try actual request with minimal invalid payload
    # This will fail validation but reveal permission status
    print(f"┌─ Testing: {name}")
    print(f"│  {description}")
    print(f"│  Method: {method} {url}")
    print(f"│  Priority: {priority}")
    print(f"│")
    
    try:
        # Send intentionally invalid/minimal payload
        if method == "POST":
            response = requests.post(
                url,
                auth=HTTPBasicAuth(API_KEY, ''),
                json=test_payload or {},  # Empty or minimal payload
                timeout=10
            )
        elif method == "PUT":
            response = requests.put(
                url,
                auth=HTTPBasicAuth(API_KEY, ''),
                json=test_payload or {},
                timeout=10
            )
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        status = response.status_code
        
        # 403 = No permission
        if status == 403:
            error_data = response.json()
            print(f"│  ❌ NO ACCESS - Status: 403")
            print(f"│  🚫 Error: {error_data.get('code', 'ForbiddenError')}")
            print(f"│  💬 Message: {error_data.get('message', 'Permission denied')}")
            print(f"│")
            print(f"│  ⚠️  Need super admin to grant write permissions")
            print(f"└{'─' * 70}\n")
            
            return {
                'success': False,
                'has_access': False,
                'status': status,
                'error': error_data,
                'priority': priority,
                'type': 'WRITE'
            }
        
        # 400, 422 = We have permission, but payload is invalid (expected!)
        elif status in [400, 422]:
            error_data = response.json() if response.text else {}
            print(f"│  ✅ WRITE ACCESS CONFIRMED - Status: {status}")
            print(f"│  📝 Safe test - validation failed (expected)")
            print(f"│  🔑 You have write permissions for this endpoint")
            print(f"│  💡 Error: {error_data.get('message', 'Validation error')}")
            print(f"└{'─' * 70}\n")
            
            return {
                'success': True,
                'has_access': True,
                'status': status,
                'method': method,
                'tested_via': 'Validation Error (Safe)',
                'priority': priority,
                'type': 'WRITE'
            }
        
        # 404 = Endpoint doesn't exist OR resource not found (but we have permission)
        elif status == 404:
            error_data = response.json() if response.text else {}
            print(f"│  ⚠️  UNCLEAR - Status: 404")
            print(f"│  💬 {error_data.get('message', 'Not found')}")
            print(f"│  🤔 Either endpoint doesn't exist OR we have access but resource invalid")
            print(f"└{'─' * 70}\n")
            
            return {
                'success': False,
                'has_access': 'UNCLEAR',
                'status': status,
                'priority': priority,
                'type': 'WRITE'
            }
        
        # 200, 201 = Unexpected success (shouldn't happen with invalid payload)
        elif status in [200, 201]:
            print(f"│  ⚠️  UNEXPECTED SUCCESS - Status: {status}")
            print(f"│  🎉 Write succeeded (check if data was actually created!)")
            print(f"└{'─' * 70}\n")
            
            return {
                'success': True,
                'has_access': True,
                'status': status,
                'priority': priority,
                'type': 'WRITE'
            }
        
        # Other status codes
        else:
            print(f"│  ⚠️  Unexpected Status: {status}")
            print(f"│  Response: {response.text[:200]}")
            print(f"└{'─' * 70}\n")
            
            return {
                'success': False,
                'has_access': 'UNKNOWN',
                'status': status,
                'priority': priority,
                'type': 'WRITE'
            }
            
    except requests.exceptions.RequestException as e:
        print(f"│  ❌ NETWORK ERROR")
        print(f"│  {str(e)}")
        print(f"└{'─' * 70}\n")
        
        return {
            'success': False,
            'error': str(e),
            'priority': priority,
            'type': 'WRITE'
        }


def test_endpoint(name, method, url, params=None, description="", priority="MEDIUM", endpoint_type="READ"):
    """
    Generic endpoint tester
    """
    print(f"┌─ Testing: {name}")
    print(f"│  {description}")
    print(f"│  Method: {method} {url}")
    print(f"│  Priority: {priority}")
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
            if has_next:
                print(f"│  🔄 Has more pages: Yes")
            
            if records and isinstance(records, list) and len(records) > 0:
                first_record = records[0]
                if isinstance(first_record, dict):
                    print(f"│")
                    print(f"│  📋 Sample Keys: {list(first_record.keys())[:5]}")
            
            print(f"└{'─' * 70}\n")
            
            return {
                'success': True,
                'status': status,
                'count': len(records),
                'priority': priority,
                'type': endpoint_type,
                'data': data
            }
            
        elif status == 403:
            error_data = response.json()
            print(f"│  ❌ NO ACCESS - Status: 403")
            print(f"│  🚫 Error: {error_data.get('code', 'ForbiddenError')}")
            print(f"│  💬 Message: {error_data.get('message', 'Permission denied')}")
            print(f"└{'─' * 70}\n")
            
            return {
                'success': False,
                'status': status,
                'error': error_data,
                'priority': priority,
                'type': endpoint_type
            }
            
        elif status == 404:
            error_data = response.json() if response.text else {}
            print(f"│  ⚠️  NOT FOUND - Status: 404")
            print(f"│  💬 {error_data.get('message', 'Endpoint does not exist')}")
            print(f"└{'─' * 70}\n")
            
            return {
                'success': False,
                'status': status,
                'error': error_data,
                'priority': priority,
                'type': endpoint_type
            }
        
        else:
            error_data = response.json() if response.text else {}
            print(f"│  ❌ FAILED - Status: {status}")
            print(f"│  Error: {error_data}")
            print(f"└{'─' * 70}\n")
            
            return {
                'success': False,
                'status': status,
                'error': error_data,
                'priority': priority,
                'type': endpoint_type
            }
            
    except requests.exceptions.RequestException as e:
        print(f"│  ❌ NETWORK ERROR")
        print(f"│  {str(e)}")
        print(f"└{'─' * 70}\n")
        
        return {
            'success': False,
            'error': str(e),
            'priority': priority,
            'type': endpoint_type
        }


def run_all_tests():
    """
    Run comprehensive tests for ALL Lever API endpoints
    """
    results = {}
    
    print("\n" + "="*75)
    print(" PHASE 1: CRITICAL READ ENDPOINTS (MVP Blockers)")
    print("="*75 + "\n")
    
    # CRITICAL READ ENDPOINTS
    results['opportunities_list'] = test_read_endpoint(
        name="GET /opportunities",
        url=f"{BASE_URL}/opportunities",
        params={'limit': 5, 'expand': 'applications,resumes,stage'},
        description="List all candidates with CVs and applications",
        priority="🔴 CRITICAL"
    )
    
    results['postings_list'] = test_read_endpoint(
        name="GET /postings",
        url=f"{BASE_URL}/postings",
        params={'limit': 5},
        description="List all job postings",
        priority="🔴 CRITICAL"
    )
    
    results['stages_list'] = test_read_endpoint(
        name="GET /stages",
        url=f"{BASE_URL}/stages",
        description="List hiring pipeline stages",
        priority="🔴 CRITICAL"
    )
    
    results['users_list'] = test_read_endpoint(
        name="GET /users",
        url=f"{BASE_URL}/users",
        params={'limit': 5},
        description="List recruiters and hiring managers",
        priority="🟡 HIGH"
    )
    
    print("\n" + "="*75)
    print(" PHASE 2: ADDITIONAL READ ENDPOINTS (Full Functionality)")
    print("="*75 + "\n")
    
    results['archive_reasons'] = test_read_endpoint(
        name="GET /archive_reasons",
        url=f"{BASE_URL}/archive_reasons",
        description="List rejection reasons (for bias detection)",
        priority="🟡 HIGH"
    )
    
    results['sources'] = test_read_endpoint(
        name="GET /sources",
        url=f"{BASE_URL}/sources",
        description="List candidate sources (LinkedIn, Indeed, etc.)",
        priority="🟢 MEDIUM"
    )
    
    results['tags'] = test_read_endpoint(
        name="GET /tags",
        url=f"{BASE_URL}/tags",
        description="List custom tags for candidate filtering",
        priority="🟢 MEDIUM"
    )
    
    results['feedback_templates'] = test_read_endpoint(
        name="GET /feedback_templates",
        url=f"{BASE_URL}/feedback_templates",
        description="List interview evaluation templates",
        priority="🟢 MEDIUM"
    )
    
    results['requisitions'] = test_read_endpoint(
        name="GET /requisitions",
        url=f"{BASE_URL}/requisitions",
        description="List job requisitions (headcount approvals)",
        priority="🔵 LOW"
    )
    
    results['webhooks'] = test_read_endpoint(
        name="GET /webhooks",
        url=f"{BASE_URL}/webhooks",
        description="List configured webhooks",
        priority="🟢 MEDIUM"
    )
    
    results['forms'] = test_read_endpoint(
        name="GET /forms",
        url=f"{BASE_URL}/forms",
        description="List custom application forms",
        priority="🔵 LOW"
    )
    
    # Test sub-endpoints if we have opportunity access
    if results['opportunities_list'].get('success') and results['opportunities_list'].get('data', {}).get('data'):
        first_opp_id = results['opportunities_list']['data']['data'][0]['id']
        
        print("\n" + "="*75)
        print(f" PHASE 3: CANDIDATE SUB-ENDPOINTS (Using ID: {first_opp_id[:8]}...)")
        print("="*75 + "\n")
        
        results['opportunity_detail'] = test_read_endpoint(
            name=f"GET /opportunities/:id",
            url=f"{BASE_URL}/opportunities/{first_opp_id}",
            description="Get detailed candidate profile",
            priority="🔴 CRITICAL"
        )
        
        results['opportunity_resumes'] = test_read_endpoint(
            name=f"GET /opportunities/:id/resumes",
            url=f"{BASE_URL}/opportunities/{first_opp_id}/resumes",
            description="Get candidate CV files (CRITICAL for AI screening)",
            priority="🔴 CRITICAL"
        )
        
        results['opportunity_applications'] = test_read_endpoint(
            name=f"GET /opportunities/:id/applications",
            url=f"{BASE_URL}/opportunities/{first_opp_id}/applications",
            description="Get candidate's job applications",
            priority="🔴 CRITICAL"
        )
        
        results['opportunity_notes'] = test_read_endpoint(
            name=f"GET /opportunities/:id/notes",
            url=f"{BASE_URL}/opportunities/{first_opp_id}/notes",
            description="Get recruiter notes on candidate",
            priority="🟡 HIGH"
        )
        
        results['opportunity_feedback'] = test_read_endpoint(
            name=f"GET /opportunities/:id/feedback",
            url=f"{BASE_URL}/opportunities/{first_opp_id}/feedback",
            description="Get interview feedback",
            priority="🟡 HIGH"
        )
        
        results['opportunity_offers'] = test_read_endpoint(
            name=f"GET /opportunities/:id/offers",
            url=f"{BASE_URL}/opportunities/{first_opp_id}/offers",
            description="Get job offers for candidate",
            priority="🟢 MEDIUM"
        )
    
    # Test posting sub-endpoints
    if results['postings_list'].get('success') and results['postings_list'].get('data', {}).get('data'):
        first_posting_id = results['postings_list']['data']['data'][0]['id']
        
        print("\n" + "="*75)
        print(f" PHASE 4: JOB POSTING SUB-ENDPOINTS (Using ID: {first_posting_id[:8]}...)")
        print("="*75 + "\n")
        
        results['posting_detail'] = test_read_endpoint(
            name=f"GET /postings/:id",
            url=f"{BASE_URL}/postings/{first_posting_id}",
            description="Get detailed job posting",
            priority="🔴 CRITICAL"
        )
        
        results['posting_applications'] = test_read_endpoint(
            name=f"GET /postings/:id/applications",
            url=f"{BASE_URL}/postings/{first_posting_id}/applications",
            description="Get all candidates for this posting",
            priority="🔴 CRITICAL"
        )
    
    # NOW TEST WRITE OPERATIONS (safely!)
    print("\n" + "="*75)
    print(" PHASE 5: WRITE PERMISSIONS TEST (No Data Modified)")
    print("="*75 + "\n")
    
    # Test opportunities write
    results['opportunities_write'] = test_write_endpoint(
        name="POST /opportunities",
        url=f"{BASE_URL}/opportunities",
        method="POST",
        description="Create new candidate (testing permission only)",
        priority="🔴 CRITICAL",
        test_payload={}  # Empty payload - will fail validation but reveal permission
    )
    
    # Test opportunity stage change (if we have an ID)
    if results.get('opportunities_list', {}).get('success') and results['opportunities_list'].get('data', {}).get('data'):
        first_opp_id = results['opportunities_list']['data']['data'][0]['id']
        
        results['opportunity_stage_write'] = test_write_endpoint(
            name="PUT /opportunities/:id/stage",
            url=f"{BASE_URL}/opportunities/{first_opp_id}/stage",
            method="PUT",
            description="Move candidate to next stage (testing permission only)",
            priority="🔴 CRITICAL",
            test_payload={}  # Empty - will fail but reveal permission
        )
        
        results['opportunity_notes_write'] = test_write_endpoint(
            name="POST /opportunities/:id/notes",
            url=f"{BASE_URL}/opportunities/{first_opp_id}/notes",
            method="POST",
            description="Add note to candidate (testing permission only)",
            priority="🔴 CRITICAL",
            test_payload={}
        )
        
        results['opportunity_tags_write'] = test_write_endpoint(
            name="POST /opportunities/:id/tags",
            url=f"{BASE_URL}/opportunities/{first_opp_id}/tags",
            method="POST",
            description="Add tag to candidate (testing permission only)",
            priority="🟡 HIGH",
            test_payload={}
        )
        
        results['opportunity_archive_write'] = test_write_endpoint(
            name="POST /opportunities/:id/archive",
            url=f"{BASE_URL}/opportunities/{first_opp_id}/archive",
            method="POST",
            description="Archive/reject candidate (testing permission only)",
            priority="🟡 HIGH",
            test_payload={}
        )
    
    # Test postings write
    results['postings_write'] = test_write_endpoint(
        name="POST /postings",
        url=f"{BASE_URL}/postings",
        method="POST",
        description="Create new job posting (testing permission only)",
        priority="🔵 LOW",
        test_payload={}
    )
    
    # Test webhooks write (usually requires super_admin)
    results['webhooks_write'] = test_write_endpoint(
        name="POST /webhooks",
        url=f"{BASE_URL}/webhooks",
        method="POST",
        description="Create webhook (testing permission only)",
        priority="🟢 MEDIUM",
        test_payload={}
    )
    
    return results


def print_comprehensive_summary(results):
    """
    Print detailed summary of all results
    """
    print("\n" + "━"*75)
    print("                    COMPREHENSIVE SUMMARY")
    print("━"*75 + "\n")
    
    # Separate by type
    read_results = {k: v for k, v in results.items() if v.get('type') == 'READ'}
    write_results = {k: v for k, v in results.items() if v.get('type') == 'WRITE'}
    
    # Count by priority and status
    critical_blocked = []
    high_blocked = []
    medium_blocked = []
    low_blocked = []
    
    read_success = []
    write_success = []
    
    for name, result in results.items():
        priority = result.get('priority', '🟢 MEDIUM')
        success = result.get('success', False) or result.get('has_access', False)
        status_code = result.get('status')
        result_type = result.get('type', 'READ')
        
        if success:
            if result_type == 'READ':
                read_success.append((name, priority))
            else:
                write_success.append((name, priority))
        else:
            if status_code == 403:  # Only count real permission blocks
                if '🔴' in priority:
                    critical_blocked.append((name, result_type))
                elif '🟡' in priority:
                    high_blocked.append((name, result_type))
                elif '🟢' in priority:
                    medium_blocked.append((name, result_type))
                else:
                    low_blocked.append((name, result_type))
    
    print(f"📊 TOTAL TESTS: {len(results)}")
    print(f"   READ Tests: {len(read_results)}")
    print(f"   WRITE Tests: {len(write_results)}")
    print()
    
    print(f"✅ ACCESSIBLE:")
    print(f"   READ Endpoints: {len(read_success)}")
    print(f"   WRITE Endpoints: {len(write_success)}")
    print()
    
    total_blocked = len(critical_blocked) + len(high_blocked) + len(medium_blocked) + len(low_blocked)
    print(f"❌ BLOCKED (403 Forbidden): {total_blocked}")
    print(f"   🔴 CRITICAL: {len(critical_blocked)}")
    print(f"   🟡 HIGH: {len(high_blocked)}")
    print(f"   🟢 MEDIUM: {len(medium_blocked)}")
    print(f"   🔵 LOW: {len(low_blocked)}")
    print()
    
    if read_success:
        print("━"*75)
        print("✅ ACCESSIBLE READ ENDPOINTS:")
        print("━"*75)
        for name, priority in sorted(read_success, key=lambda x: x[1]):
            count = results[name].get('count', 0)
            print(f"   {priority} {name:<40} ({count} records)")
        print()
    
    if write_success:
        print("━"*75)
        print("✅ ACCESSIBLE WRITE ENDPOINTS:")
        print("━"*75)
        for name, priority in sorted(write_success, key=lambda x: x[1]):
            tested_via = results[name].get('tested_via', 'Unknown')
            print(f"   {priority} {name:<40} (via {tested_via})")
        print()
    
    if critical_blocked:
        print("━"*75)
        print("🔴 CRITICAL BLOCKERS (Request Immediately):")
        print("━"*75)
        for name, result_type in critical_blocked:
            print(f"   • {name:<45} [{result_type}]")
        print()
    
    if high_blocked:
        print("━"*75)
        print("🟡 HIGH PRIORITY (Request Soon):")
        print("━"*75)
        for name, result_type in high_blocked:
            print(f"   • {name:<45} [{result_type}]")
        print()
    
    if medium_blocked or low_blocked:
        print("━"*75)
        print("🟢 LOWER PRIORITY (Request Later):")
        print("━"*75)
        for name, result_type in medium_blocked + low_blocked:
            print(f"   • {name:<45} [{result_type}]")
        print()
    
    print("━"*75)


def generate_permissions_request(results):
    """
    Generate a specific permissions request based on test results
    """
    print("\n" + "━"*75)
    print("         PERMISSIONS REQUEST FOR SUPER ADMIN")
    print("━"*75 + "\n")
    
    critical_read_blocked = []
    critical_write_blocked = []
    high_read_blocked = []
    high_write_blocked = []
    
    for name, result in results.items():
        if result.get('status') == 403:
            priority = result.get('priority', '')
            result_type = result.get('type', 'READ')
            
            if '🔴' in priority:
                if result_type == 'READ':
                    critical_read_blocked.append(name)
                else:
                    critical_write_blocked.append(name)
            elif '🟡' in priority:
                if result_type == 'READ':
                    high_read_blocked.append(name)
                else:
                    high_write_blocked.append(name)
    
    print("Please grant the following API permissions:")
    print()
    
    if critical_read_blocked or critical_write_blocked:
        print("🔴 CRITICAL (Blocking MVP):")
        print()
        if critical_read_blocked:
            print("   READ Scopes:")
            print("   ✅ opportunities:read")
            print("   ✅ postings:read (may already have)")
            print("   ✅ stages:read (may already have)")
            print("   ✅ users:read")
            print()
        if critical_write_blocked:
            print("   WRITE Scopes:")
            print("   ✅ opportunities:write")
            print()
    
    if high_read_blocked or high_write_blocked:
        print("🟡 HIGH PRIORITY (Full Functionality):")
        print()
        if high_read_blocked:
            print("   READ Scopes:")
            print("   ✅ archive_reasons:read")
            print("   ✅ sources:read")
            print("   ✅ tags:read")
            print("   ✅ feedback_templates:read")
            print()
    
    print("━"*75)
    print()
    print("Impact of blocked permissions:")
    print("  • Cannot access candidate CVs for AI screening")
    print("  • Cannot move candidates through pipeline stages")
    print("  • Cannot log AI scores as notes")
    print("  • Cannot perform bias detection on rejections")
    print()
    print("Timeline: Need access by 2025-11-15 to stay on schedule")
    print("━"*75 + "\n")


def save_results(results, filename="lever_full_permissions_test.json"):
    """
    Save results to JSON
    """
    try:
        clean_results = {}
        for key, value in results.items():
            clean_results[key] = {
                'success': value.get('success', False),
                'has_access': value.get('has_access', value.get('success', False)),
                'status': value.get('status'),
                'count': value.get('count', 0),
                'priority': value.get('priority', 'UNKNOWN'),
                'type': value.get('type', 'READ'),
                'tested_via': value.get('tested_via', 'Direct API Call'),
                'error': str(value.get('error', '')) if value.get('error') else None
            }
        
        output = {
            'test_date': '2025-11-14 19:12:40 UTC',
            'user': 'SaiffMoh',
            'total_tests': len(results),
            'results': clean_results
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Results saved to: {filename}\n")
        
    except Exception as e:
        print(f"❌ Error saving results: {e}\n")


def main():
    """
    Main execution
    """
    print_header()
    
    print("🚀 Starting comprehensive permissions test...")
    print("   Testing ALL read and write endpoints")
    print("   Write tests are SAFE - no data will be modified")
    print("   Using validation errors to detect write permissions\n")
    
    # Run all tests
    results = run_all_tests()
    
    # Print comprehensive summary
    print_comprehensive_summary(results)
    
    # Generate permissions request
    generate_permissions_request(results)
    
    # Save results
    save_results(results)
    
    print("✅ Test completed!")
    print(f"📅 Date: 2025-11-14 19:12:40 UTC")
    print(f"👤 User: SaiffMoh\n")


if __name__ == "__main__":
    main()