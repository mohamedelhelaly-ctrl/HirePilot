from datetime import datetime
from typing import List, Dict, Optional

def parse_date(date_str: str) -> Optional[tuple]:
    """Parse date string to (year, month) tuple"""
    if not date_str:
        return None
    
    date_str = str(date_str).strip()
    current_date = datetime.now()
    
    # Handle "Present" or "Current"
    if date_str.lower() in ["present", "current", "now", "ongoing", "till now", "till date"]:
        return (current_date.year, current_date.month)
    
    # Numeric format: "3/2024" or "03/2024"
    if "/" in date_str:
        try:
            parts = date_str.split("/")
            month = int(parts[0])
            year = int(parts[1])
            return (year, month)
        except:
            pass
    
    # Dash format: "2024-03" or "03-2024"
    if "-" in date_str and len(date_str.split("-")) == 2:
        try:
            parts = date_str.split("-")
            if len(parts[0]) == 4:  # YYYY-MM
                year = int(parts[0])
                month = int(parts[1])
            else:  # MM-YYYY
                month = int(parts[0])
                year = int(parts[1])
            return (year, month)
        except:
            pass
    
    # Month name mapping
    month_map = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12
    }
    
    # Try month name + year
    parts = date_str.lower().split()
    if len(parts) == 2:
        month_str, year_str = parts
        month = month_map.get(month_str)
        if month:
            try:
                year = int(year_str)
                return (year, month)
            except:
                pass
    
    # Year only
    try:
        year = int(date_str)
        return (year, 1)
    except:
        pass
    
    return None


def calculate_duration_months(start_date: str, end_date: str) -> int:
    """Calculate duration in months between two dates"""
    start = parse_date(start_date)
    end = parse_date(end_date)
    
    if not start or not end:
        return 0
    
    start_year, start_month = start
    end_year, end_month = end
    
    total_months = (end_year - start_year) * 12 + (end_month - start_month) + 1
    return max(0, total_months)


def dates_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
    """Check if two date ranges overlap (not just touch at boundaries)"""
    s1 = parse_date(start1)
    e1 = parse_date(end1)
    s2 = parse_date(start2)
    e2 = parse_date(end2)
    
    if not all([s1, e1, s2, e2]):
        return False
    
    s1_months = s1[0] * 12 + s1[1]
    e1_months = e1[0] * 12 + e1[1]
    s2_months = s2[0] * 12 + s2[1]
    e2_months = e2[0] * 12 + e2[1]
    
    # True overlap: start1 < end2 AND start2 < end1
    return s1_months < e2_months and s2_months < e1_months


def is_professional_role(role_title: str, company: str) -> bool:
    """
    Determine if a role is professional (counts toward experience)
    Returns True for full-time professional roles, False for internships/trainee/student roles
    """
    if not role_title:
        return False
    
    role_lower = role_title.lower()
    company_lower = company.lower() if company else ""
    
    # Exclude keywords
    exclude_keywords = [
        "intern", "internship", "trainee", "training", "student", 
        "volunteer", "teaching assistant", "ta", "research assistant"
    ]
    
    # Check role title
    for keyword in exclude_keywords:
        if keyword in role_lower:
            return False
    
    # Check company (some companies indicate non-professional work)
    university_indicators = ["university", "college", "school", "academy"]
    for indicator in university_indicators:
        if indicator in company_lower and "research" not in role_lower:
            return False
    
    # Must have substantial role name (not just "Developer" alone)
    return len(role_lower) > 3


def remove_overlapping_roles(work_history: List[Dict]) -> List[Dict]:
    """
    Remove overlapping roles, keeping the most relevant one
    Priority: More recent > Longer duration
    """
    if not work_history or len(work_history) <= 1:
        return work_history
    
    filtered_jobs = []
    
    for job in work_history:
        is_duplicate = False
        
        for idx, existing_job in enumerate(filtered_jobs):
            if dates_overlap(
                job.get("start_date", ""),
                job.get("end_date", ""),
                existing_job.get("start_date", ""),
                existing_job.get("end_date", "")
            ):
                # Keep the more recent role
                job_end = parse_date(job.get("end_date", ""))
                existing_end = parse_date(existing_job.get("end_date", ""))
                
                if job_end and existing_end:
                    job_end_months = job_end[0] * 12 + job_end[1]
                    existing_end_months = existing_end[0] * 12 + existing_end[1]
                    
                    if job_end_months > existing_end_months:
                        # New job is more recent, replace existing
                        filtered_jobs[idx] = job
                        is_duplicate = True
                        break
                    else:
                        # Existing job is more recent, skip new job
                        is_duplicate = True
                        break
        
        if not is_duplicate:
            filtered_jobs.append(job)
    
    return filtered_jobs


def calculate_total_experience(work_history: List[Dict]) -> int:
    """
    Calculate total professional experience in years (rounded to nearest integer)
    
    Args:
        work_history: List of job dictionaries with role, company, start_date, end_date
    
    Returns:
        Integer years of professional experience
    """
    if not work_history:
        return 0
    
    # Filter professional roles only
    professional_roles = []
    for job in work_history:
        role = job.get("role", "")
        company = job.get("company", "")
        
        if is_professional_role(role, company):
            professional_roles.append(job)
    
    if not professional_roles:
        return 0
    
    # Remove overlapping roles
    filtered_roles = remove_overlapping_roles(professional_roles)
    
    # Calculate total months
    total_months = 0
    for job in filtered_roles:
        months = calculate_duration_months(
            job.get("start_date", ""),
            job.get("end_date", "")
        )
        total_months += months
    
    # Convert to years and round
    total_years = round(total_months / 12)
    
    return max(0, total_years)