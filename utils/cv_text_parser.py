import os
import re
import PyPDF2

def extract_text_from_pdf(pdf_path: str) -> dict:
    """Extract text and LinkedIn URL from PDF"""
    extracted_text = ""
    extracted_links = []
    
    try:
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            
            # Extract text from pages
            extracted_text = "\n".join([
                page.extract_text() for page in reader.pages if page.extract_text()
            ])
            
            # Extract hyperlinks from annotations
            for page in reader.pages:
                if "/Annots" in page:
                    for annot in page["/Annots"]:
                        obj = annot.get_object()
                        if "/A" in obj and "/URI" in obj["/A"]:
                            extracted_links.append(obj["/A"]["/URI"])
        
        # Extract URLs from text
        url_patterns = [
            r'(https?://)?(www\.)?linkedin\.com/in/[A-Za-z0-9\-_/\s]+',
            r'https?://[\w\.-]+/in/[A-Za-z0-9\-_/]+',
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, extracted_text, re.IGNORECASE)
            if matches and isinstance(matches[0], tuple):
                matches = [''.join(match) for match in matches]
            extracted_links.extend(matches)
        
        # Deduplicate and clean LinkedIn URLs
        extracted_links = list(set(extracted_links))
        linkedin_links = []
        
        for link in extracted_links:
            if "linkedin.com/in/" in link.lower():
                link = re.sub(r'\s+', '', link)
                if not link.startswith(('http://', 'https://')):
                    link = 'https://' + link.lstrip('/')
                linkedin_links.append(link)
        
        linkedin_url = linkedin_links[0] if linkedin_links else None
        
        return {
            "text": extracted_text.strip(),
            "linkedin": linkedin_url
        }
    
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return {"text": "", "linkedin": None}