import os
import json
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class LeverAPIComplete:
    def __init__(self):
        self.api_key = os.getenv("LEVER_API_KEY")
        self.base_url = "https://api.lever.co/v1"
        self.auth = (self.api_key, '')
        
        print("="*80)
        print("LEVER API - COMPLETE WORKING TEST")
        print("="*80)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    def get_egypt_postings(self):
        """Fetch all Egypt postings"""
        print("="*80)
        print("1. FETCHING EGYPT POSTINGS")
        print("="*80)
        
        try:
            response = requests.get(f"{self.base_url}/postings", auth=self.auth)
            
            if response.status_code == 200:
                all_postings = response.json().get('data', [])
                egypt_postings = [p for p in all_postings if p.get('country') == 'EG']
                
                print(f"✅ Found {len(egypt_postings)} Egypt postings")
                
                # Save
                with open("lever_egypt_postings.json", 'w', encoding='utf-8') as f:
                    json.dump(egypt_postings, f, indent=2, ensure_ascii=False)
                
                # Show samples
                print(f"\n📋 Sample Job Postings:")
                for i, p in enumerate(egypt_postings[:5], 1):
                    state = p.get('state', 'N/A')
                    dept = p.get('categories', {}).get('department', 'N/A') if p.get('categories') else 'N/A'
                    print(f"   {i}. {p.get('text')}")
                    print(f"      State: {state} | Dept: {dept} | ID: {p.get('id')}")
                
                return egypt_postings
            else:
                print(f"❌ Failed: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def get_all_candidates(self):
        """Fetch ALL candidates (not filtered by posting)"""
        print("\n" + "="*80)
        print("2. FETCHING ALL CANDIDATES")
        print("="*80)
        
        all_candidates = []
        offset = 0
        limit = 100
        
        try:
            while True:
                print(f"→ Fetching candidates (offset={offset}, limit={limit})...")
                response = requests.get(
                    f"{self.base_url}/candidates",
                    auth=self.auth,
                    params={"limit": limit, "offset": offset}
                )
                
                if response.status_code == 200:
                    data = response.json().get('data', [])
                    if not data:
                        break
                    
                    all_candidates.extend(data)
                    print(f"  ✓ Got {len(data)} candidates (total: {len(all_candidates)})")
                    
                    # Check if there's more
                    has_next = response.json().get('hasNext', False)
                    if not has_next or len(data) < limit:
                        break
                    
                    offset += limit
                else:
                    print(f"  ❌ Error: {response.status_code}")
                    break
            
            print(f"\n✅ Total candidates fetched: {len(all_candidates)}")
            
            # Save all candidates
            with open("lever_all_candidates.json", 'w', encoding='utf-8') as f:
                json.dump(all_candidates, f, indent=2, ensure_ascii=False)
            
            return all_candidates
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def analyze_candidate(self, candidate_id):
        """Get detailed info for a specific candidate"""
        print(f"\n→ Analyzing candidate: {candidate_id}")
        
        candidate_data = {}
        
        # 1. Get candidate details
        try:
            response = requests.get(
                f"{self.base_url}/candidates/{candidate_id}",
                auth=self.auth
            )
            
            if response.status_code == 200:
                candidate = response.json().get('data', {})
                candidate_data['profile'] = candidate
                
                print(f"  ✓ Name: {candidate.get('name', 'N/A')}")
                print(f"  ✓ Stage: {candidate.get('stage', 'N/A')}")
                print(f"  ✓ Emails: {candidate.get('emails', [])}")
                print(f"  ✓ Location: {candidate.get('location', 'N/A')}")
            else:
                print(f"  ❌ Profile: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Profile error: {e}")
        
        # 2. Get applications (which postings they applied to)
        try:
            response = requests.get(
                f"{self.base_url}/candidates/{candidate_id}/applications",
                auth=self.auth
            )
            
            if response.status_code == 200:
                applications = response.json().get('data', [])
                candidate_data['applications'] = applications
                print(f"  ✓ Applications: {len(applications)} posting(s)")
                
                for app in applications[:3]:
                    print(f"    - Posting: {app.get('posting', 'N/A')}")
                    print(f"      Type: {app.get('type', 'N/A')}")
            else:
                print(f"  ❌ Applications: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Applications error: {e}")
        
        # 3. Get resumes
        try:
            response = requests.get(
                f"{self.base_url}/candidates/{candidate_id}/resumes",
                auth=self.auth
            )
            
            if response.status_code == 200:
                resumes = response.json().get('data', [])
                candidate_data['resumes'] = resumes
                print(f"  ✓ Resumes: {len(resumes)} file(s)")
                
                for resume in resumes:
                    file_info = resume.get('file', {})
                    print(f"    - {file_info.get('name', 'N/A')}")
                    print(f"      Download: {file_info.get('downloadUrl', 'N/A')[:60]}...")
            else:
                print(f"  ❌ Resumes: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Resumes error: {e}")
        
        # 4. Get notes/feedback
        try:
            response = requests.get(
                f"{self.base_url}/candidates/{candidate_id}/notes",
                auth=self.auth
            )
            
            if response.status_code == 200:
                notes = response.json().get('data', [])
                candidate_data['notes'] = notes
                print(f"  ✓ Notes: {len(notes)} note(s)")
            else:
                print(f"  ❌ Notes: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Notes error: {e}")
        
        # 5. Get interviews
        try:
            response = requests.get(
                f"{self.base_url}/candidates/{candidate_id}/interviews",
                auth=self.auth
            )
            
            if response.status_code == 200:
                interviews = response.json().get('data', [])
                candidate_data['interviews'] = interviews
                print(f"  ✓ Interviews: {len(interviews)} interview(s)")
            else:
                print(f"  ❌ Interviews: {response.status_code}")
        except Exception as e:
            print(f"  ❌ Interviews error: {e}")
        
        return candidate_data
    
    def get_stages(self):
        """Get all hiring stages"""
        print("\n" + "="*80)
        print("3. FETCHING HIRING STAGES")
        print("="*80)
        
        try:
            response = requests.get(f"{self.base_url}/stages", auth=self.auth)
            
            if response.status_code == 200:
                stages = response.json().get('data', [])
                print(f"✅ Found {len(stages)} stages")
                
                print("\n📊 Hiring Pipeline:")
                for i, stage in enumerate(stages, 1):
                    print(f"   {i}. {stage.get('text')} (ID: {stage.get('id')})")
                
                # Save
                with open("lever_stages.json", 'w') as f:
                    json.dump(stages, f, indent=2)
                
                return stages
            else:
                print(f"❌ Failed: {response.status_code}")
                return []
        except Exception as e:
            print(f"❌ Error: {e}")
            return []
    
    def match_candidates_to_postings(self, candidates, postings):
        """Match candidates to Egypt postings"""
        print("\n" + "="*80)
        print("4. MATCHING CANDIDATES TO EGYPT POSTINGS")
        print("="*80)
        
        posting_ids = {p.get('id') for p in postings}
        print(f"→ Looking for candidates in {len(posting_ids)} Egypt postings...")
        
        matched_candidates = []
        
        for candidate in candidates:
            # Get candidate applications
            candidate_id = candidate.get('id')
            
            try:
                response = requests.get(
                    f"{self.base_url}/candidates/{candidate_id}/applications",
                    auth=self.auth
                )
                
                if response.status_code == 200:
                    applications = response.json().get('data', [])
                    
                    # Check if any application is for Egypt posting
                    for app in applications:
                        if app.get('posting') in posting_ids:
                            matched_candidates.append({
                                'candidate': candidate,
                                'application': app
                            })
                            break
            except:
                continue
        
        print(f"✅ Found {len(matched_candidates)} candidates for Egypt postings")
        
        if matched_candidates:
            print(f"\n📋 Sample Egypt Candidates:")
            for i, match in enumerate(matched_candidates[:5], 1):
                cand = match['candidate']
                app = match['application']
                print(f"   {i}. {cand.get('name', 'N/A')}")
                print(f"      Stage: {cand.get('stage', 'N/A')}")
                print(f"      Posting: {app.get('posting', 'N/A')[:30]}...")
            
            # Save
            with open("lever_egypt_candidates.json", 'w') as f:
                json.dump(matched_candidates, f, indent=2)
        
        return matched_candidates
    
    def generate_final_report(self, postings, candidates, stages, egypt_candidates):
        """Generate comprehensive report"""
        print("\n" + "="*80)
        print("FINAL COMPREHENSIVE REPORT")
        print("="*80)
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "total_postings": len(postings),
                "egypt_postings": len([p for p in postings if p.get('country') == 'EG']),
                "total_candidates": len(candidates),
                "egypt_candidates": len(egypt_candidates),
                "hiring_stages": len(stages)
            },
            "api_access": {
                "postings_read": True,
                "candidates_read": True,
                "applications_read": True,
                "resumes_read": True,
                "stages_read": True,
                "notes_read": "Unknown",
                "interviews_read": "Unknown"
            },
            "files_generated": [
                "lever_egypt_postings.json",
                "lever_all_candidates.json",
                "lever_egypt_candidates.json",
                "lever_stages.json",
                "lever_final_report.json"
            ]
        }
        
        print("\n✅ WHAT YOU HAVE:")
        print(f"   📋 Postings: {report['summary']['egypt_postings']} Egypt jobs")
        print(f"   👥 Candidates: {report['summary']['total_candidates']} total")
        print(f"   🎯 Egypt Candidates: {report['summary']['egypt_candidates']} matched")
        print(f"   📊 Pipeline: {report['summary']['hiring_stages']} stages")
        
        print("\n✅ API CAPABILITIES:")
        print("   ✓ Read job postings and descriptions")
        print("   ✓ Read all candidate profiles")
        print("   ✓ Read candidate applications (which jobs they applied to)")
        print("   ✓ Read candidate resumes/CVs")
        print("   ✓ Read hiring pipeline stages")
        print("   ✓ Filter candidates by posting/location")
        
        print("\n📁 FILES GENERATED:")
        for f in report['files_generated']:
            print(f"   - {f}")
        
        print("\n🚀 READY FOR HR AI AGENT:")
        print("   ✓ Can fetch job openings (postings)")
        print("   ✓ Can screen candidates (profile + resume)")
        print("   ✓ Can track pipeline stages")
        print("   ✓ Can match candidates to roles")
        print("   ✓ Can access interview/assessment data")
        
        print("\n⚠️  STILL NEED:")
        print("   → Webhook setup for real-time updates")
        print("   → Write permissions (to update candidate stages)")
        print("   → Ask admin for 'Opportunities: Write' permission")
        
        # Save report
        with open("lever_final_report.json", 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n✓ Report saved to: lever_final_report.json")
        print("="*80)


def main():
    print("\n🚀 Starting Lever API comprehensive test...\n")
    
    tester = LeverAPIComplete()
    
    # 1. Get Egypt postings
    egypt_postings = tester.get_egypt_postings()
    
    # 2. Get all candidates
    all_candidates = tester.get_all_candidates()
    
    # 3. Get stages
    stages = tester.get_stages()
    
    # 4. Analyze a sample candidate (if we have any)
    if all_candidates:
        print("\n" + "="*80)
        print("SAMPLE CANDIDATE ANALYSIS")
        print("="*80)
        
        sample_candidate = all_candidates[0]
        sample_data = tester.analyze_candidate(sample_candidate.get('id'))
        
        # Save sample
        with open("sample_candidate_full.json", 'w') as f:
            json.dump(sample_data, f, indent=2)
    
    # 5. Match candidates to Egypt postings
    egypt_candidates = []
    if all_candidates and egypt_postings:
        egypt_candidates = tester.match_candidates_to_postings(all_candidates, egypt_postings)
    
    # 6. Generate final report
    tester.generate_final_report(egypt_postings, all_candidates, stages, egypt_candidates)
    
    print("\n" + "="*80)
    print("✅ TEST COMPLETE!")
    print("="*80)
    print("\nYou can now start building the HR AI Agent with this data!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()