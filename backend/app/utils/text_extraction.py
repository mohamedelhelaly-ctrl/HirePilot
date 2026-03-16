import os
import logging
import fitz
import zipfile
import xml.etree.ElementTree as ET


# pdf --> txt
def extract_text_from_pdf(file_path: str) -> list:
    """Extract text from PDF file using PyMuPDF (fitz) with better error handling."""
    texts = []
    try:
        doc = fitz.open(file_path)
        full_text = ""  # Accumulate all page texts

        for page_num, page in enumerate(doc):
            try:
                text = page.get_text("text")
                if text:
                    full_text += text.strip() + "\n"  # Keep content even if only whitespace
                    if text.strip():
                        texts.append({
                            'text': text.lower(),
                            'page': page_num,
                            'source': os.path.basename(file_path)
                        })
            except Exception as page_error:
                logging.warning(f"Error reading page {page_num} from {file_path}: {page_error}")
                continue
        
        # Also return the full extracted text as a single entry (for completeness)
        if full_text.strip():
            texts.insert(0, {
                'text': full_text.strip().lower(),
                'page': None,  # or -1 to indicate full document
                'source': os.path.basename(file_path)
            })

        doc.close()
        
    except Exception as e:
        logging.error(f"Error extracting text from PDF {file_path}: {e}")
    
    return texts


# docx --> txt
def extract_text_from_docx(file_path: str) -> list:
    """Extract text from DOCX file by parsing XML directly."""
    texts = []
    try:
        # DOCX files are ZIP archives containing XML files
        with zipfile.ZipFile(file_path, 'r') as docx_zip:
            # Read the main document XML
            xml_content = docx_zip.read('word/document.xml')
            
            # Parse XML
            tree = ET.fromstring(xml_content)
            
            # Define namespace
            namespace = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            # Extract all text elements
            paragraphs = []
            for paragraph in tree.findall('.//w:p', namespace):
                texts_in_para = paragraph.findall('.//w:t', namespace)
                paragraph_text = ''.join([t.text for t in texts_in_para if t.text])
                if paragraph_text.strip():
                    paragraphs.append(paragraph_text)
            
            if paragraphs:
                texts.append({
                    'text': '\n'.join(p.lower() for p in paragraphs),
                    'page': 0,
                    'source': os.path.basename(file_path)
                })
    except Exception as e:
        logging.error(f"Error extracting text from DOCX: {e}")
    
    return texts

