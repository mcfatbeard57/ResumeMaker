"""
PDF Reader — Extract text and structure from resume PDFs using PyMuPDF.
"""
import fitz  # PyMuPDF


def extract_resume_text(path: str) -> str:
    """Extract raw text from a PDF file, page by page."""
    doc = fitz.open(path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def extract_text_with_positions(path: str) -> list[dict]:
    """
    Extract every text span with its position, font, size, and color.
    Returns list of dicts: {x0, y0, x1, y1, font, size, color, text, block_no, line_no}
    """
    doc = fitz.open(path)
    spans = []
    for page_num, page in enumerate(doc):
        blocks = page.get_text("dict")["blocks"]
        for block_idx, block in enumerate(blocks):
            if "lines" not in block:
                continue
            for line_idx, line in enumerate(block["lines"]):
                for span in line["spans"]:
                    spans.append({
                        "page": page_num,
                        "x0": span["bbox"][0],
                        "y0": span["bbox"][1],
                        "x1": span["bbox"][2],
                        "y1": span["bbox"][3],
                        "font": span["font"],
                        "size": span["size"],
                        "color": span["color"],
                        "text": span["text"],
                        "block_no": block_idx,
                        "line_no": line_idx,
                    })
    doc.close()
    return spans


def extract_resume_sections(path: str) -> dict:
    """
    Extract structured sections from the resume using font-size heuristics.
    
    Section headers are detected by Arial-Black font at size >= 10.
    Body text is ArialMT or Arial-BoldMT at size 9-10.
    
    Returns dict: {section_name: [list of bullet points / lines]}
    """
    spans = extract_text_with_positions(path)
    
    sections = {}
    current_section = "Header"
    current_lines = []
    current_line_text = ""
    current_line_no = -1
    current_block_no = -1
    
    for span in spans:
        is_section_header = (
            "Black" in span["font"] and 
            span["size"] >= 10 and
            len(span["text"].strip()) > 2 and
            span["text"].strip() not in ("", " ")
        )
        
        # Accumulate spans into lines
        if span["block_no"] != current_block_no or span["line_no"] != current_line_no:
            # Save previous line
            if current_line_text.strip():
                current_lines.append(current_line_text.strip())
            current_line_text = span["text"]
            current_line_no = span["line_no"]
            current_block_no = span["block_no"]
        else:
            current_line_text += span["text"]
        
        if is_section_header:
            # Save previous section
            # Remove the header text from current_lines if it got added
            if current_lines:
                sections[current_section] = current_lines
            
            current_section = span["text"].strip()
            current_lines = []
            current_line_text = ""
    
    # Save last accumulated line and section
    if current_line_text.strip():
        current_lines.append(current_line_text.strip())
    if current_lines:
        sections[current_section] = current_lines
    
    return sections


def get_page_dimensions(path: str) -> tuple[float, float]:
    """Get page width and height."""
    doc = fitz.open(path)
    page = doc[0]
    w, h = page.rect.width, page.rect.height
    doc.close()
    return w, h
