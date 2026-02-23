"""
PDF Writer — Layout-preserving resume editor using PyMuPDF overlay technique.

Strategy:
1. Open the original PDF
2. For each section that has been modified, find the matching text spans
3. Redact (white-out) the old text
4. Insert new text at the same coordinates with the same font/size
5. Save as a new PDF — layout identical, only content differs
"""
import fitz  # PyMuPDF
import os
import re
from utils.pdf_reader import extract_text_with_positions


# Map PDF font names to fitz built-in font names
FONT_MAP = {
    "ArialMT": "helv",           # Helvetica ≈ Arial
    "Arial-BoldMT": "hebo",      # Helvetica Bold
    "Arial-Black": "hebo",       # Closest built-in match
}


def _sanitize_text(text: str) -> str:
    """Replace problematic Unicode characters with ASCII equivalents."""
    replacements = {
        "\u2013": "-",   # en dash
        "\u2014": "-",   # em dash
        "\u2018": "'",   # left single quote
        "\u2019": "'",   # right single quote
        "\u201c": '"',   # left double quote
        "\u201d": '"',   # right double quote
        "\u2026": "...", # ellipsis
        "\u2022": "-",   # bullet
        "\u00a0": " ",   # non-breaking space
        "\u2192": "->",  # right arrow
        "\u2190": "<-",  # left arrow
        "\u2248": "~",   # approx equal
        "\u2265": ">=",  # greater equal
        "\u2264": "<=",  # less equal
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def _find_bullet_spans(spans: list[dict], section_name: str) -> list[list[dict]]:
    """
    Find groups of spans that form bullet points within a given section.
    A bullet point starts with '•' and ends at the next bullet or section header.
    Returns: list of bullet groups, each being a list of spans.
    """
    # Find the section header span
    section_start_idx = None
    for i, span in enumerate(spans):
        if ("Black" in span["font"] and span["size"] >= 10 and
                section_name.lower() in span["text"].lower()):
            section_start_idx = i
            break
    
    if section_start_idx is None:
        return []
    
    # Find next section header to bound the search
    section_end_idx = len(spans)
    for i in range(section_start_idx + 1, len(spans)):
        if ("Black" in spans[i]["font"] and spans[i]["size"] >= 10 and
                len(spans[i]["text"].strip()) > 2):
            section_end_idx = i
            break
    
    # Group spans into bullet points within section bounds
    section_spans = spans[section_start_idx + 1: section_end_idx]
    bullet_groups = []
    current_bullet = []
    
    for span in section_spans:
        text = span["text"].strip()
        if text.startswith("•") or text.startswith("- "):
            if current_bullet:
                bullet_groups.append(current_bullet)
            current_bullet = [span]
        elif current_bullet:
            current_bullet.append(span)
    
    if current_bullet:
        bullet_groups.append(current_bullet)
    
    return bullet_groups


def _get_bullet_text(bullet_spans: list[dict]) -> str:
    """Concatenate spans to get full bullet text."""
    return " ".join(s["text"].strip() for s in bullet_spans).strip()


def generate_updated_resume(
    original_path: str,
    updated_sections: dict[str, list[str]],
    output_path: str,
) -> str:
    """
    Generate an updated resume PDF with layout preserved.
    
    Args:
        original_path: Path to original resume PDF
        updated_sections: dict mapping section names to lists of updated bullet texts
        output_path: Where to save the output PDF
    
    Returns:
        Path to the generated PDF
    """
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    # Get all text spans from original
    all_spans = extract_text_with_positions(original_path)
    
    # Open document for editing
    doc = fitz.open(original_path)
    page = doc[0]  # Single-page resume
    
    for section_name, new_bullets in updated_sections.items():
        bullet_groups = _find_bullet_spans(all_spans, section_name)
        
        if not bullet_groups:
            print(f"  ⚠ Section '{section_name}' not found in PDF, skipping")
            continue
        
        # Match bullets by index
        for i, new_text in enumerate(new_bullets):
            if i >= len(bullet_groups):
                print(f"  ⚠ More new bullets than original in '{section_name}', skipping extra")
                break
            
            old_spans = bullet_groups[i]
            old_text = _get_bullet_text(old_spans)
            
            # Skip if text hasn't changed
            if _normalize(old_text) == _normalize(new_text):
                continue
            
            # Get the bounding box encompassing all spans of this bullet
            x0 = min(s["x0"] for s in old_spans)
            y0 = min(s["y0"] for s in old_spans)
            x1 = max(s["x1"] for s in old_spans)
            y1 = max(s["y1"] for s in old_spans)
            
            # Use the font properties of the first body-text span
            body_span = old_spans[0]
            font_name = FONT_MAP.get(body_span["font"], "helv")
            font_size = body_span["size"]
            color = _int_to_rgb(body_span["color"])
            
            # Redact the old text area
            rect = fitz.Rect(x0, y0, x1, y1)
            page.add_redact_annot(rect, fill=(1, 1, 1))  # white fill
        
        # Apply all redactions at once for this section
        page.apply_redactions()
        
        # Now insert new text
        for i, new_text in enumerate(new_bullets):
            if i >= len(bullet_groups):
                break
            
            old_spans = bullet_groups[i]
            old_text = _get_bullet_text(old_spans)
            
            if _normalize(old_text) == _normalize(new_text):
                continue
            
            body_span = old_spans[0]
            font_name = FONT_MAP.get(body_span["font"], "helv")
            font_size = body_span["size"]
            color = _int_to_rgb(body_span["color"])
            
            x0 = min(s["x0"] for s in old_spans)
            y0 = min(s["y0"] for s in old_spans)
            x1 = max(s["x1"] for s in old_spans)
            y1 = max(s["y1"] for s in old_spans)
            
            # Sanitize the new text
            clean_text = _sanitize_text(new_text)
            
            # Ensure bullet prefix
            if not clean_text.startswith("•") and not clean_text.startswith("- "):
                clean_text = "• " + clean_text
            
            # Insert text at original position using text writer for wrapping
            text_rect = fitz.Rect(x0, y0, x1, y1)
            rc = page.insert_textbox(
                text_rect,
                clean_text,
                fontname=font_name,
                fontsize=font_size,
                color=color,
                align=fitz.TEXT_ALIGN_LEFT,
            )
            
            if rc < 0:
                # Text didn't fit — try with slightly smaller font
                page.insert_textbox(
                    text_rect,
                    clean_text,
                    fontname=font_name,
                    fontsize=font_size - 0.5,
                    color=color,
                    align=fitz.TEXT_ALIGN_LEFT,
                )
    
    doc.save(output_path)
    doc.close()
    
    print(f"✅ Updated resume saved to: {output_path}")
    return output_path


def _normalize(text: str) -> str:
    """Normalize text for comparison (strip whitespace, lower)."""
    return re.sub(r'\s+', ' ', text.strip().lower())


def _int_to_rgb(color_int: int) -> tuple:
    """Convert integer color to (r, g, b) tuple with 0-1 range."""
    r = ((color_int >> 16) & 0xFF) / 255.0
    g = ((color_int >> 8) & 0xFF) / 255.0
    b = (color_int & 0xFF) / 255.0
    return (r, g, b)
