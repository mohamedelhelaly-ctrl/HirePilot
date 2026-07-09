"""
Lever API - Complete Opportunities Management
Author: SaiffMoh
Date: 2025-12-10
Description: Comprehensive script for fetching and managing opportunities,
             including filtering by requisition, checking files (CVs, etc.),
             and verifying all required data is present.
"""

import os
import requests
import json
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from datetime import datetime

# Load environment variables from a .env file
load_dotenv()

# --- Configuration ---
API_KEY = os.getenv('LEVER_API_KEY')
BASE_URL = "https://api.lever.co/v1"

# --- Core Opportunity Functions ---

def fetch_all_opportunities(expand_fields=None):
    """
    Fetches all opportunities across all pages.
    
    Args:
        expand_fields (list): Optional list of fields to expand (e.g., ['applications', 'stage'])
    
    Returns:
        list: A list of all opportunities.
    """
    if not API_KEY:
        raise ValueError("❌ LEVER_API_KEY not found in your .env file. Please create it.")

    print("🚀 Fetching ALL opportunities...")
    
    all_opportunities = []
    params = {
        'limit': 100
    }
    
    # Add expand parameter if provided
    if expand_fields:
        params['expand'] = expand_fields
    
    url = f"{BASE_URL}/opportunities"
    page_count = 0

    while True:
        page_count += 1
        print(f"📄 Fetching page {page_count} of opportunities...")
        
        try:
            response = requests.get(
                url,
                auth=HTTPBasicAuth(API_KEY, ''),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' in data and data['data']:
                opportunities_on_page = data['data']
                all_opportunities.extend(opportunities_on_page)
                print(f"   ✓ Found {len(opportunities_on_page)} opportunities on this page (Total: {len(all_opportunities)})")
            else:
                print("   ⚠️ No opportunities found on this page.")

            if data.get('hasNext'):
                params['offset'] = data['next']
            else:
                print("\n🏁 Reached the last page. All opportunities have been fetched.")
                break
                
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"❌ HTTP Error 403: Forbidden. Check if your API key has 'opportunities:read' permissions.")
            else:
                print(f"❌ An HTTP error occurred: {e}")
            break
        except requests.exceptions.RequestException as e:
            print(f"❌ A network error occurred: {e}")
            break
            
    return all_opportunities


def fetch_opportunity_by_id(opportunity_id, expand_fields=None):
    """
    Fetches a specific opportunity by its ID.
    
    Args:
        opportunity_id (str): The unique opportunity ID
        expand_fields (list): Optional list of fields to expand
    
    Returns:
        dict: The opportunity data if found, None otherwise.
    """
    if not API_KEY:
        raise ValueError("❌ LEVER_API_KEY not found in your .env file.")

    print(f"🔍 Fetching opportunity with ID: {opportunity_id}")
    
    url = f"{BASE_URL}/opportunities/{opportunity_id}"
    params = {}
    
    if expand_fields:
        params['expand'] = expand_fields
    
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(API_KEY, ''),
            params=params,
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        if 'data' in data:
            print(f"✅ Opportunity found!")
            return data['data']
        else:
            print(f"⚠️ No opportunity data returned.")
            return None
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"❌ Opportunity not found (404).")
        elif e.response.status_code == 403:
            print(f"❌ Access forbidden (403). Check API key permissions.")
        else:
            print(f"❌ HTTP error occurred: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error occurred: {e}")
        return None


def fetch_opportunities_by_posting(posting_id):
    """
    Fetches all opportunities for a specific posting/requisition.
    
    Args:
        posting_id (str): The posting ID (requisition ID)
    
    Returns:
        list: List of opportunities for the specified posting.
    """
    if not API_KEY:
        raise ValueError("❌ LEVER_API_KEY not found in your .env file.")

    print(f"🔍 Fetching opportunities for posting/requisition: {posting_id}")
    
    all_opportunities = []
    params = {
        'limit': 100,
        'posting_id': posting_id
    }
    
    url = f"{BASE_URL}/opportunities"
    page_count = 0

    while True:
        page_count += 1
        print(f"📄 Fetching page {page_count}...")
        
        try:
            response = requests.get(
                url,
                auth=HTTPBasicAuth(API_KEY, ''),
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            if 'data' in data and data['data']:
                opportunities_on_page = data['data']
                all_opportunities.extend(opportunities_on_page)
                print(f"   ✓ Found {len(opportunities_on_page)} opportunities")
            
            if data.get('hasNext'):
                params['offset'] = data['next']
            else:
                break
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error occurred: {e}")
            break
    
    print(f"✅ Total opportunities for posting {posting_id}: {len(all_opportunities)}")
    return all_opportunities


def fetch_files_for_opportunity(opportunity_id):
    """
    Fetches all files (resumes, CVs, etc.) associated with an opportunity.
    
    Args:
        opportunity_id (str): The opportunity ID
    
    Returns:
        list: List of file objects for the opportunity.
    """
    if not API_KEY:
        raise ValueError("❌ LEVER_API_KEY not found in your .env file.")

    print(f"📎 Fetching files for opportunity: {opportunity_id}")
    
    url = f"{BASE_URL}/opportunities/{opportunity_id}/files"
    
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(API_KEY, ''),
            timeout=30
        )
        response.raise_for_status()
        
        data = response.json()
        
        if 'data' in data:
            files = data['data']
            print(f"✅ Found {len(files)} file(s)")
            return files
        else:
            print(f"⚠️ No files found.")
            return []
            
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"⚠️ No files found (404).")
        else:
            print(f"❌ HTTP error occurred: {e}")
        return []
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error occurred: {e}")
        return []


# --- Analysis Functions ---

def check_opportunity_completeness(opportunity, files=None):
    """
    Checks if an opportunity has all required data fields.
    
    Args:
        opportunity (dict): The opportunity object
        files (list): Optional list of files for the opportunity
    
    Returns:
        dict: A report of missing and present fields.
    """
    required_fields = [
        'id', 'name', 'contact', 'emails', 'phones', 
        'stage', 'confidentiality', 'location', 'createdAt'
    ]
    
    important_fields = [
        'headline', 'origin', 'sourcedBy', 'owner', 'tags', 
        'sources', 'stageChanges', 'archived'
    ]
    
    report = {
        "opportunity_id": opportunity.get('id', 'UNKNOWN'),
        "candidate_name": opportunity.get('name', 'N/A'),
        "missing_required": [],
        "missing_important": [],
        "present_required": [],
        "present_important": [],
        "has_resume": False,
        "file_count": 0,
        "emails": [],
        "phones": [],
        "stage": opportunity.get('stage', 'N/A'),
        "is_complete": True
    }
    
    # Check required fields
    for field in required_fields:
        value = opportunity.get(field)
        if value is None or (isinstance(value, (list, dict, str)) and not value):
            report["missing_required"].append(field)
            report["is_complete"] = False
        else:
            report["present_required"].append(field)
    
    # Check important fields
    for field in important_fields:
        value = opportunity.get(field)
        if value is None or (isinstance(value, (list, dict, str)) and not value):
            report["missing_important"].append(field)
        else:
            report["present_important"].append(field)
    
    # Extract contact info
    if opportunity.get('emails'):
        report["emails"] = opportunity['emails']
    if opportunity.get('phones'):
        report["phones"] = [p.get('value', '') for p in opportunity['phones']]
    
    # Check files
    if files:
        report["file_count"] = len(files)
        for file in files:
            file_name = file.get('name', '').lower()
            if any(keyword in file_name for keyword in ['resume', 'cv', 'curriculum']):
                report["has_resume"] = True
                break
    
    return report


def analyze_opportunities(opportunities, fetch_files=False):
    """
    Analyzes a list of opportunities and generates a comprehensive report.
    
    Args:
        opportunities (list): List of opportunity objects
        fetch_files (bool): Whether to fetch and check files for each opportunity
    
    Returns:
        dict: Comprehensive analysis report
    """
    print(f"\n📊 Analyzing {len(opportunities)} opportunities...")
    
    analysis = {
        "total_opportunities": len(opportunities),
        "complete_opportunities": 0,
        "incomplete_opportunities": 0,
        "opportunities_with_resume": 0,
        "opportunities_without_resume": 0,
        "by_stage": {},
        "missing_fields_summary": {},
        "detailed_reports": []
    }
    
    for idx, opp in enumerate(opportunities, 1):
        print(f"   Analyzing opportunity {idx}/{len(opportunities)}...", end='\r')
        
        files = None
        if fetch_files:
            files = fetch_files_for_opportunity(opp['id'])
        
        report = check_opportunity_completeness(opp, files)
        analysis["detailed_reports"].append(report)
        
        # Update counters
        if report["is_complete"]:
            analysis["complete_opportunities"] += 1
        else:
            analysis["incomplete_opportunities"] += 1
        
        if report["has_resume"]:
            analysis["opportunities_with_resume"] += 1
        else:
            analysis["opportunities_without_resume"] += 1
        
        # Count by stage
        stage = report["stage"]
        if stage not in analysis["by_stage"]:
            analysis["by_stage"][stage] = 0
        analysis["by_stage"][stage] += 1
        
        # Track missing fields
        for field in report["missing_required"]:
            if field not in analysis["missing_fields_summary"]:
                analysis["missing_fields_summary"][field] = 0
            analysis["missing_fields_summary"][field] += 1
    
    print()  # New line after progress
    return analysis


def print_analysis_summary(analysis):
    """
    Prints a formatted summary of the analysis.
    """
    print("\n" + "="*70)
    print("OPPORTUNITIES ANALYSIS SUMMARY")
    print("="*70)
    
    print(f"\n📊 OVERVIEW:")
    print(f"   Total Opportunities: {analysis['total_opportunities']}")
    print(f"   Complete: {analysis['complete_opportunities']} ({analysis['complete_opportunities']/max(analysis['total_opportunities'],1)*100:.1f}%)")
    print(f"   Incomplete: {analysis['incomplete_opportunities']} ({analysis['incomplete_opportunities']/max(analysis['total_opportunities'],1)*100:.1f}%)")
    
    print(f"\n📄 RESUMES/CVs:")
    print(f"   With Resume: {analysis['opportunities_with_resume']}")
    print(f"   Without Resume: {analysis['opportunities_without_resume']}")
    
    if analysis['by_stage']:
        print(f"\n🎯 BY STAGE:")
        for stage, count in sorted(analysis['by_stage'].items(), key=lambda x: x[1], reverse=True):
            print(f"   {stage}: {count}")
    
    if analysis['missing_fields_summary']:
        print(f"\n⚠️ MOST COMMON MISSING FIELDS:")
        for field, count in sorted(analysis['missing_fields_summary'].items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"   {field}: missing in {count} opportunities")
    
    print("="*70 + "\n")


# --- File I/O Functions ---

def save_data_to_json(data, filename):
    """
    Saves data to a JSON file with metadata.
    """
    output_data = {
        "metadata": {
            "fetched_at": datetime.now().isoformat(),
            "source": "Lever API v1"
        },
        "data": data
    }

    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Data saved to '{filename}'")
        print(f"📊 File size: {os.path.getsize(filename) / 1024:.2f} KB")
    except IOError as e:
        print(f"❌ Failed to write to file '{filename}'. Error: {e}")


# --- Main Script ---

if __name__ == "__main__":
    print("="*70)
    print("LEVER OPPORTUNITIES - COMPLETE MANAGEMENT SCRIPT")
    print("="*70 + "\n")
    
    # Menu
    print("Select an option:")
    print("1. Fetch ALL opportunities")
    print("2. Fetch opportunities for a specific posting/requisition")
    print("3. Fetch a specific opportunity by ID")
    print("4. Fetch files for a specific opportunity")
    print("5. Analyze opportunities (check completeness)")
    print()
    
    choice = input("Enter your choice (1-5): ").strip()
    
    if choice == "1":
        # Fetch all opportunities
        opportunities = fetch_all_opportunities(expand_fields=['applications', 'stage'])
        
        if opportunities:
            save_data_to_json(opportunities, "lever_opportunities_all.json")
            
            analyze = input("\nWould you like to analyze these opportunities? (y/n): ").strip().lower()
            if analyze == 'y':
                check_files = input("Check for resume files? (slower) (y/n): ").strip().lower()
                analysis = analyze_opportunities(opportunities, fetch_files=(check_files == 'y'))
                print_analysis_summary(analysis)
                save_data_to_json(analysis, "lever_opportunities_analysis.json")
    
    elif choice == "2":
        # Fetch by posting
        posting_id = input("Enter posting/requisition ID: ").strip()
        if posting_id:
            opportunities = fetch_opportunities_by_posting(posting_id)
            
            if opportunities:
                save_data_to_json(opportunities, f"lever_opportunities_posting_{posting_id}.json")
                
                analyze = input("\nWould you like to analyze these opportunities? (y/n): ").strip().lower()
                if analyze == 'y':
                    check_files = input("Check for resume files? (slower) (y/n): ").strip().lower()
                    analysis = analyze_opportunities(opportunities, fetch_files=(check_files == 'y'))
                    print_analysis_summary(analysis)
                    save_data_to_json(analysis, f"lever_opportunities_analysis_{posting_id}.json")
    
    elif choice == "3":
        # Fetch by ID
        opp_id = input("Enter opportunity ID: ").strip()
        if opp_id:
            opportunity = fetch_opportunity_by_id(opp_id, expand_fields=['applications', 'stage'])
            
            if opportunity:
                save_data_to_json(opportunity, f"lever_opportunity_{opp_id}.json")
                
                print("\n" + "="*70)
                print(f"Opportunity: {opportunity.get('name', 'N/A')}")
                print(f"Stage: {opportunity.get('stage', 'N/A')}")
                print(f"Emails: {', '.join(opportunity.get('emails', []))}")
                print("="*70)
                
                check_files = input("\nFetch files for this opportunity? (y/n): ").strip().lower()
                if check_files == 'y':
                    files = fetch_files_for_opportunity(opp_id)
                    if files:
                        save_data_to_json(files, f"lever_opportunity_{opp_id}_files.json")
    
    elif choice == "4":
        # Fetch files only
        opp_id = input("Enter opportunity ID: ").strip()
        if opp_id:
            files = fetch_files_for_opportunity(opp_id)
            if files:
                save_data_to_json(files, f"lever_opportunity_{opp_id}_files.json")
                print("\n📎 Files found:")
                for file in files:
                    print(f"   - {file.get('name', 'Unnamed')} ({file.get('type', 'unknown')})")
    
    elif choice == "5":
        # Analyze existing data
        filename = input("Enter JSON file with opportunities (or press Enter to fetch fresh): ").strip()
        
        if filename and os.path.exists(filename):
            with open(filename, 'r') as f:
                data = json.load(f)
                opportunities = data.get('data', data.get('opportunities', []))
        else:
            opportunities = fetch_all_opportunities(expand_fields=['applications', 'stage'])
        
        if opportunities:
            check_files = input("Check for resume files? (slower) (y/n): ").strip().lower()
            analysis = analyze_opportunities(opportunities, fetch_files=(check_files == 'y'))
            print_analysis_summary(analysis)
            save_data_to_json(analysis, "lever_opportunities_analysis.json")
    
    else:
        print("❌ Invalid choice")
    
    print("\n✅ Script completed!")
    print(f"⏰ Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")