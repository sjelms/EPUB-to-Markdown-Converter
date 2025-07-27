import re

def title_case(text: str) -> str:
    """Convert text to Title Case (first letter of major words capitalized)."""
    
    # Words that should remain lowercase (unless first or last word)
    minor_words = {
        'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'if', 'in', 'is', 'it', 'no', 'nor', 
        'of', 'on', 'or', 'so', 'the', 'to', 'up', 'yet', 'with', 'from', 'into', 'through', 
        'during', 'before', 'after', 'above', 'below', 'between', 'among', 'within', 'without'
    }
    
    # If text is all uppercase, convert to title case first
    if text.isupper():
        text = text.title()
    
    # Split into words and process each
    words = text.split()
    if not words:
        return text
    
    result = []
    for i, word in enumerate(words):
        # Clean the word (remove punctuation for processing)
        clean_word = re.sub(r'[^\w]', '', word.lower())
        
        # Capitalize if:
        # 1. It's the first or last word
        # 2. It's not a minor word
        # 3. It's longer than 3 characters (to catch important short words)
        should_capitalize = (
            i == 0 or i == len(words) - 1 or  # First or last word
            clean_word not in minor_words or  # Not a minor word
            len(clean_word) > 3  # Longer than 3 characters
        )
        
        if should_capitalize:
            # Capitalize the first letter, preserve original case for rest
            if word:
                result.append(word[0].upper() + word[1:])
            else:
                result.append(word)
        else:
            # Keep minor words lowercase
            result.append(word.lower())
    
    return ' '.join(result)

# Helper function to sanitize titles for filenames
def safe_filename(title: str) -> str:
    """Sanitize title for use as a filename (prevent subfolders or illegal characters)."""
    # First sanitize the title
    safe_title = re.sub(r'[\\/:"*?<>|]', '-', title)
    
    # Limit filename length to prevent filesystem errors
    # Most filesystems have a limit of 255 characters for filename
    # We'll use a more conservative limit of 100 characters
    if len(safe_title) > 100:
        # Truncate and add ellipsis
        safe_title = safe_title[:97] + "..."
    
    return safe_title

def clean_markdown_text(md: str, chapter_map=None) -> str:
    """Apply post-processing cleanup rules to raw Markdown using systematic approach."""
    
    # === PHASE 1: PROTECT WHAT WE WANT TO KEEP ===
    
    # Replace images with placeholders to protect them during cleanup
    def protect_image(match):
        alt_text = match.group(1)
        img_path = match.group(2)
        return f"IMAGE_PLACEHOLDER_{alt_text}_{img_path}"
    
    md = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', protect_image, md)
    
    # Replace external links with placeholders
    def protect_external_link(match):
        link_text = match.group(1)
        link_url = match.group(2)
        return f"EXTERNAL_LINK_PLACEHOLDER_{link_text}_{link_url}"
    
    md = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', protect_external_link, md)
    
    # Replace internal Obsidian links with placeholders
    def protect_internal_link(match):
        link_text = match.group(1)
        return f"INTERNAL_LINK_PLACEHOLDER_{link_text}"
    
    md = re.sub(r'\[\[([^\]]+)\]\]', protect_internal_link, md)
    
    # Replace cross-references with placeholders
    def protect_cross_ref(match):
        link_text = match.group(1)
        target = match.group(2)
        return f"CROSS_REF_PLACEHOLDER_{link_text}_{target}"
    
    md = re.sub(r'\[([^\]]+)\]\(([^)]+\.xhtml#[^)]+)\)', protect_cross_ref, md)
    
    # Also protect any remaining external links that might have been missed
    def protect_remaining_links(match):
        link_text = match.group(1)
        link_url = match.group(2)
        return f"EXTERNAL_LINK_PLACEHOLDER_{link_text}_{link_url}"
    
    # This will catch any remaining [text](url) patterns that weren't caught above
    md = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', protect_remaining_links, md)
    
    # === PHASE 2: AGGRESSIVE ARTIFACT REMOVAL ===
    
    # Remove all table artifacts
    md = re.sub(r'\|-{20,}\+', '', md)  # Remove table separators with excessive dashes
    md = re.sub(r'\+-{20,}\+', '', md)  # Remove table cell boundaries with dashes
    md = re.sub(r'\|-{20,}\|', '', md)  # Remove table separators
    md = re.sub(r' -{20,} ', ' ', md)   # Remove dash lines
    md = re.sub(r'-{20,}\+', '', md)    # Remove trailing dashes with +
    md = re.sub(r'-{20,}', '', md)      # Remove any remaining long dash sequences
    
    # Remove all stray pipes (except those in placeholders)
    md = re.sub(r'(?<!PLACEHOLDER_)\|(?!PLACEHOLDER_)', '', md)
    
    # Remove all stray brackets (except those in placeholders)
    # More robust protection: don't remove brackets that are part of placeholder patterns
    md = re.sub(r'(?<!PLACEHOLDER_)\[(?!.*PLACEHOLDER_)', '', md)
    md = re.sub(r'(?<!PLACEHOLDER_)\](?!.*PLACEHOLDER_)', '', md)
    
    # Remove EPUB/Pandoc artifacts
    md = re.sub(r'\[\]{#[^}]*\.pagebreak[^}]*}', '', md)  # Page break elements
    md = re.sub(r'<span[^>]*epub:type="pagebreak"[^>]*/>', '', md)  # Page break spans
    md = re.sub(r'::: ?\{[^}]*\}', '', md)  # Pandoc fenced divs
    md = re.sub(r':::', '', md)  # Pandoc fenced divs
    md = re.sub(r'\{#[^}]*\.h[0-9][a-z]?\}', '', md)  # EPUB heading attributes
    md = re.sub(r'\s+xml:space="[^"]*"', '', md)  # XML space attributes
    md = re.sub(r'\s+epub:type="[^"]*"', '', md)  # EPUB type attributes
    md = re.sub(r'\s*\{#[^}]*\}\s*', ' ', md)  # Remaining heading attributes
    md = re.sub(r'^::\s*$', '', md, flags=re.MULTILINE)  # Stray colons
    
    # Remove Pandoc text artifacts
    md = re.sub(r'\[([^\]]*?)\]\{#span_[^}]*\.text\}', r'\1', md)  # Pandoc span wrappers
    md = re.sub(r'\[([^\]]*?)\]\{#li_[^}]*\}', r'\1', md)  # Pandoc list item attributes
    md = re.sub(r'\{#img_[^}]*\}', '', md)  # Pandoc image attributes
    
    # Remove empty brackets
    md = re.sub(r'\[\]', '', md)
    
    # === PHASE 3: CONVERT TABLE-LIKE STRUCTURES TO BULLET LISTS ===
    
    # Convert activity table format to proper heading with inline image
    def fix_activity_format(match):
        activity_text = match.group(1).strip()
        img_path = match.group(2)
        activity_num = activity_text.replace('# ', '').replace('Activity ', '')
        return f"### Activity {activity_num} IMAGE_PLACEHOLDER_Activity {activity_num}_{img_path}"
    
    # Handle various activity formats
    md = re.sub(r'^(# Activity \d+\.\d+)\s*IMAGE_PLACEHOLDER_([^_]+)_([^_]+)$', fix_activity_format, md, flags=re.MULTILINE)
    
    # Also handle activity format that wasn't caught by placeholder protection
    md = re.sub(r'^(# Activity \d+\.\d+)\s*!\[figure\]\(([^)]+)\)', fix_activity_format, md, flags=re.MULTILINE)
    
    # Fix activity headings that weren't converted (final fallback)
    md = re.sub(r'^# Activity (\d+\.\d+)', r'### Activity \1', md, flags=re.MULTILINE)
    
    # Handle other table format headings
    def fix_other_table_heading(match):
        heading_text = match.group(1).strip()
        img_path = match.group(2)
        return f"### {heading_text} IMAGE_PLACEHOLDER_figure_{img_path}"
    
    md = re.sub(r'^(# [^_]+)\s*IMAGE_PLACEHOLDER_([^_]+)_([^_]+)$', fix_other_table_heading, md, flags=re.MULTILINE)
    
    # Convert remaining table-like structures to bullet lists
    def convert_table_to_bullets(match):
        table_content = match.group(0)
        
        # Look for patterns that look like tables and convert them
        lines = table_content.split('\n')
        if len(lines) < 2:
            return table_content
        
        # Skip if this contains images or headings (not a real table)
        if 'IMAGE_PLACEHOLDER_' in table_content or any(line.strip().startswith('#') for line in lines):
            return table_content
        
        # Simple conversion: split by spaces and create bullet lists
        result = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('-') and not line.startswith('#'):
                # Split by multiple spaces (likely table columns)
                parts = re.split(r'\s{3,}', line)
                if len(parts) > 1:
                    for part in parts:
                        if part.strip():
                            result.append(f"- {part.strip()}")
                else:
                    result.append(f"- {line}")
        
        return '\n'.join(result) if result else table_content
    
    # Apply table conversion to multi-line structures that look like tables
    md = re.sub(r'(?:[^\n]+\s{3,}[^\n]+\n)+', convert_table_to_bullets, md, flags=re.MULTILINE)
    
    # === PHASE 4: CLEAN UP BULLET LISTS ===
    
    # Remove bullets from standalone images (images are not list items)
    md = re.sub(r'^- !\[([^\]]+)\]\(([^)]+)\)', r'![\1](\2)', md, flags=re.MULTILINE)
    
    # Fix bullet list breaks after headings
    md = re.sub(r'^(#{1,6}\s+[^#\n]+)\n- $', r'\1\n', md, flags=re.MULTILINE)  # Remove stray bullets
    md = re.sub(r'^(#{1,6}\s+[^#\n]+)\n\n- ([^-])', r'\1\n\n- \2', md, flags=re.MULTILINE)  # Fix spacing
    
    # Remove empty bullet points
    md = re.sub(r'^- $\n', '', md, flags=re.MULTILINE)
    
    # === PHASE 5: RESTORE PROTECTED CONTENT ===
    
    # Restore images
    def restore_image(match):
        alt_text = match.group(1)
        img_path = match.group(2)
        
        # Clean up malformed image paths
        img_path = img_path.rstrip(' -_')  # Remove trailing dashes, spaces, underscores
        
        # Fix common path issues
        if img_path.endswith('_1.jpg'):
            img_path = img_path.replace('_1.jpg', '.jpg')
        if img_path.endswith('_1.png'):
            img_path = img_path.replace('_1.png', '.png')
        
        # Ensure proper image syntax
        if not img_path.endswith(')'):
            img_path = img_path + ')'
        
        return f"![{alt_text}]({img_path})"
    
    md = re.sub(r'IMAGE_PLACEHOLDER_([^_]+)_([^_]+)', restore_image, md)
    
    # Restore external links
    def restore_external_link(match):
        link_text = match.group(1)
        link_url = match.group(2)
        return f"[{link_text}]({link_url})"
    
    md = re.sub(r'EXTERNAL_LINK_PLACEHOLDER_([^_]+)_([^_]+)', restore_external_link, md)
    
    # Restore internal links
    def restore_internal_link(match):
        link_text = match.group(1)
        return f"[[{link_text}]]"
    
    md = re.sub(r'INTERNAL_LINK_PLACEHOLDER_([^_]+)', restore_internal_link, md)
    
    # Restore cross-references (convert to Obsidian format if chapter_map provided)
    def restore_cross_ref(match):
        link_text = match.group(1)
        target = match.group(2)
        
        if chapter_map:
            if "#" in target:
                file_part, anchor = target.split("#", 1)
            else:
                file_part, anchor = target, ""
            if file_part in chapter_map:
                md_target = chapter_map[file_part]
                return f"[[{md_target}]]"
        
        return f"[{link_text}]({target})"  # Keep original if no chapter_map
    
    md = re.sub(r'CROSS_REF_PLACEHOLDER_([^_]+)_([^_]+)', restore_cross_ref, md)
    
    # === PHASE 5: FINAL FORMATTING POLISH ===
    
    # Fix heading hierarchy (only for actual # headings, not already-formatted ones)
    def fix_heading_level(match):
        heading_level = match.group(1)
        content = match.group(2)
        
        # Don't modify if content already has heading markers
        if content.strip().startswith('#'):
            return match.group(0)
        
        if heading_level == '1' and len(content.strip()) < 80:
            return f"### {content.strip()}"
        
        return match.group(0)
    
    md = re.sub(r'^(#{1,6})\s+(.+)$', fix_heading_level, md, flags=re.MULTILINE)
    
    # Fix spacing issues
    md = re.sub(r'\n{3,}', '\n\n', md)  # Collapse multiple blank lines
    md = re.sub(r'\n{3,}(#{1,6}\s)', r'\n\n\1', md)  # Fix excessive line breaks before headings
    
    # Fix headings merged with content
    md = re.sub(r'(#{1,6}\s+[^#\n]+?)([A-Z][a-z])', r'\1\n\n\2', md)
    md = re.sub(r'([^\n])\s+(#{1,6}\s)', r'\1\n\n\2', md)
    
    # Fix bullet lists
    md = re.sub(r' - ([^-])', r'\n- \1', md)
    
    # Fix formatting
    md = re.sub(r'--', '—', md)  # Convert double hyphens to em dash
    md = re.sub(r'\*([^*]+)\*', r'_\1_', md)  # Convert asterisk italics to underscore
    
    # Fix italic artifacts
    md = re.sub(r'__([^_]+)__', r'_\1_', md)
    md = re.sub(r'-_([^_]+)_-', r'_\1_', md)
    md = re.sub(r'_-([^-]+)-_', r'_\1_', md)
    md = re.sub(r'—([a-zA-Z])', r'— \1', md)
    
    # Remove final artifacts
    md = re.sub(r'^\s*:\s*$', '', md, flags=re.MULTILINE)
    
    # Remove any remaining placeholder artifacts
    md = re.sub(r'EXTERNAL\)_LINK_PLACEHOLDER_', '', md)  # Fix malformed placeholders
    md = re.sub(r'EXTERNAL\)_LINK_PLACEHOLDER_', '', md)  # Fix malformed placeholders
    md = re.sub(r'CROSS_REF_PLACEHOLDER_([^_]+)_([^_]+)', r'[\1](\2)', md)  # Convert to simple links
    
    # Fix any remaining malformed placeholders
    md = re.sub(r'EXTERNAL\)\)_LINK_PLACEHOLDER_', '', md)
    md = re.sub(r'EXTERNAL\)\)_LINK_PLACEHOLDER_', '', md)
    
    # Add line breaks after images
    md = re.sub(r'!\[([^\]]+)\]\(([^)]+)\)([^\n])', r'![\1](\2)\n\3', md)
    
    # Fix malformed image paths
    md = re.sub(r'!\[([^\]]+)\]\(([^)]+)\)_1\.(jpg|png)\)', r'![\1](\2.\3)', md)
    md = re.sub(r'!\[([^\]]+)\]\(([^)]+)\)_1\.(jpg|png)', r'![\1](\2.\3)', md)
    
    return md.strip() + '\n'


import os
import sys
import argparse
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup
from bs4.element import Tag
import zipfile
import shutil
import json
# Suppress XML parser warnings from BeautifulSoup
from bs4 import XMLParsedAsHTMLWarning
import warnings
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# === Constants ===
OUTPUT_ROOT = Path("/Users/stephenelms/Documents/Epub to Md")
LOG_DIR = OUTPUT_ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# === Functions ===

def extract_epub(epub_path: Path, extract_to: Path):
    """Unzips EPUB to a temporary folder."""
    with zipfile.ZipFile(epub_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

def find_opf_path(container_path: Path) -> Path:
    """Parses container.xml to find the OPF file path."""
    container_xml = Path(container_path) / "META-INF" / "container.xml"
    with open(container_xml, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, "xml")
    rootfile = soup.find("rootfile")
    # Extract the path to the OPF file from the container XML.
    # Handle edge case where 'full-path' might be returned as a list.
    if isinstance(rootfile, Tag) and rootfile.has_attr("full-path"):
        full_path = rootfile["full-path"]
        if isinstance(full_path, list):
            full_path = full_path[0]
        return Path(container_path) / full_path
    else:
        raise ValueError("Could not locate rootfile path in container.xml")

def run_pandoc(input_file: Path, output_file: Path):
    """Converts a single XHTML file to Markdown using Pandoc.

    This function is responsible for structural conversion only.
    It does not perform post-processing cleanup (e.g., line merging, YAML injection).
    """
    try:
        subprocess.run([
            "/opt/homebrew/bin/pandoc",  # Full path to Pandoc binary
            str(input_file),               # Input XHTML file
            "-f", "html",                  # From format: HTML (XHTML compatible)
            "-t", "markdown",              # To format: Markdown
            "--wrap=none",                 # Prevent forced line breaks (natural wrapping)
            "-o", str(output_file)         # Output Markdown file
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: Pandoc failed for file {input_file}")
        raise e

def parse_toc_xhtml(toc_path: Path):
    """Parses toc.xhtml and returns a list of (filename, anchor, label, depth) in TOC order."""
    from bs4 import BeautifulSoup
    from bs4.element import Tag
    with open(toc_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')  # Use strict XML parsing

    toc_entries = []

    def process_ol(ol_tag, depth=1):
        for li in ol_tag.find_all('li', recursive=False):
            a_tag = li.find('a', href=True)
            if a_tag and isinstance(a_tag, Tag):
                href = a_tag.get('href', '')
                if isinstance(href, list):
                    href = href[0] if href else ''
                label = a_tag.get_text(strip=True)
                if href and '.xhtml' in href:
                    if '#' in href:
                        file_part, anchor = href.split('#', 1)
                    else:
                        file_part, anchor = href, None
                    toc_entries.append((file_part, anchor, label, depth))
            nested_ol = li.find('ol', recursive=False)
            if nested_ol and isinstance(nested_ol, Tag):
                process_ol(nested_ol, depth + 1)

    nav = soup.find('nav')
    if nav and isinstance(nav, Tag):
        ol = nav.find('ol')
        if ol and isinstance(ol, Tag):
            process_ol(ol)
    else:
        # fallback to flat structure
        for a in soup.find_all('a', href=True):
            if isinstance(a, Tag):
                href = a.get('href', '')
                if isinstance(href, list):
                    href = href[0] if href else ''
                label = a.get_text(strip=True)
                if href and '.xhtml' in href:
                    if '#' in href:
                        file_part, anchor = href.split('#', 1)
                    else:
                        file_part, anchor = href, None
                    toc_entries.append((file_part, anchor, label, 1))
    return toc_entries

def extract_book_title_from_copyright(content_root: Path) -> str | None:
    """Extract the book title from copyright statement using RNIB_COPYRIGHT_LEGALESE_0 ID."""
    # Look for copyright statement in all XHTML files
    for xhtml_file in content_root.glob("*.xhtml"):
        try:
            with open(xhtml_file, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'xml')
            
            # Look for the copyright title element
            copyright_title = soup.find('p', id='RNIB_COPYRIGHT_LEGALESE_0')
            if copyright_title:
                title = copyright_title.get_text(strip=True)
                if title and title != "":
                    print(f"[INFO] Found book title from copyright: {title}")
                    return title
        except Exception as e:
            print(f"[WARNING] Error reading {xhtml_file}: {e}")
            continue
    
    print("[WARNING] Could not find book title in copyright statement")
    return None

def extract_title_from_xhtml(xhtml_path: Path) -> str:
    """Extracts the <title> from an XHTML file and converts to Title Case."""
    with open(xhtml_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')  # Use strict XML parsing
    title_tag = soup.find('title')
    raw_title = title_tag.get_text(strip=True) if title_tag else "Untitled"
    return title_case(raw_title)

def extract_xhtml_metadata(xhtml_path: Path) -> dict:
    """
    Extract comprehensive metadata from XHTML file including:
    - title
    - body type (frontmatter, bodymatter, backmatter)
    - section id and type
    - chapter information
    
    ENHANCED: Now searches for IDs on ANY tag within the body, not just section/div tags.
    This fixes the subsection detection issue where level IDs are placed on h1, h2, p tags, etc.
    """
    with open(xhtml_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')
    
    metadata = {
        'title': "Untitled",
        'body_type': None,
        'section_id': None,
        'section_type': None,
        'is_frontmatter': False,
        'is_chapter': False,
        'is_backmatter': False,
        'chapter_number': None,
        'level': None,
        'subsection_number': None,
        'all_ids': []  # NEW: Track all IDs in the file
    }
    
    # Extract title
    title_tag = soup.find('title')
    if title_tag:
        raw_title = title_tag.get_text(strip=True)
        metadata['title'] = title_case(raw_title)
    
    # Extract body type from body tag
    body_tag = soup.find('body')
    if body_tag and isinstance(body_tag, Tag):
        metadata['body_type'] = body_tag.get('epub:type')
    
    # --- ENHANCED SECTION ID DETECTION ---
    # Find ALL tags in the body that have ID attributes, not just the first one
    # This is crucial for detecting subsections that are anchors within the same file
    if body_tag and isinstance(body_tag, Tag):
        all_id_tags = body_tag.find_all(id=True)
        for tag in all_id_tags:
            if isinstance(tag, Tag) and tag.get('id'):
                metadata['all_ids'].append(tag.get('id'))
    
    # Use the first ID for primary classification (usually the main section/chapter ID)
    if metadata['all_ids']:
        primary_id = metadata['all_ids'][0]
        metadata['section_id'] = primary_id
        
        # Get the type from the first tag with an ID
        first_id_tag = None
        if body_tag and isinstance(body_tag, Tag):
            first_id_tag = body_tag.find(id=primary_id)
        if first_id_tag and isinstance(first_id_tag, Tag):
            metadata['section_type'] = first_id_tag.get('epub:type')
    # --- END ENHANCED SECTION ---
    
    # Determine content type based on metadata
    section_id = str(metadata['section_id'] or "")
    body_type = str(metadata['body_type'] or "")
    section_type = str(metadata['section_type'] or "")
    title_upper = metadata['title'].upper()
    
    # Frontmatter detection (comprehensive)
    if (body_type == "frontmatter" or 
        section_id.startswith("frontmatter_") or
        section_id.startswith("page_") or  # Roman numeral pages
        "titlepage" in section_type or
        "toc" in section_type or
        "preface" in section_id.lower() or
        "acknowledgements" in section_id.lower() or
        "abouttheauthors" in section_id.lower() or
        "introduction" in section_id.lower() or
        title_upper in ["CONTENTS", "ACKNOWLEDGEMENTS", "ABOUT THE AUTHORS", "INTRODUCTION"]):
        metadata['is_frontmatter'] = True
    
    # Chapter detection (comprehensive)
    elif (section_id.startswith("ch") or
          section_id.startswith("chapter") or
          section_id.startswith("Sec") or  # Springer format
          section_type == "chapter" or
          (title_upper and "CHAPTER" in title_upper)):
        metadata['is_chapter'] = True
        # Extract chapter number from various formats using regex for better reliability
        if section_id.startswith("ch"):
            try:
                match = re.search(r'\d+', section_id)
                if match:
                    metadata['chapter_number'] = int(match.group())
            except (ValueError, AttributeError):
                pass
        elif section_id.startswith("chapter"):
            try:
                match = re.search(r'\d+', section_id)
                if match:
                    metadata['chapter_number'] = int(match.group())
            except (ValueError, AttributeError):
                pass
        elif section_id.startswith("Sec"):
            try:
                match = re.search(r'\d+', section_id)
                if match:
                    metadata['chapter_number'] = int(match.group())
            except (ValueError, AttributeError):
                pass
        # Extract from title if section_id doesn't have number
        elif "CHAPTER" in title_upper:
            match = re.search(r'CHAPTER\s+(\d+)', title_upper)
            if match:
                try:
                    metadata['chapter_number'] = int(match.group(1))
                except ValueError:
                    pass
    
    # Level detection within chapters (comprehensive)
    # ENHANCED: More robust regex parsing to handle variations in level ID formats
    elif section_id.startswith("level"):
        parts = section_id.split("_")
        if len(parts) >= 2:
            level_part = parts[0]
            if level_part.startswith("level"):
                try:
                    metadata['level'] = int(level_part[5:])
                    # Extract subsection number from the second part using regex
                    if len(parts) >= 2:
                        try:
                            # Use regex to find number in case of extra chars
                            match = re.search(r'\d+', parts[1])
                            if match:
                                metadata['subsection_number'] = int(match.group())
                        except (ValueError, AttributeError):
                            pass
                except (ValueError, AttributeError):
                    pass
    
    # Backmatter detection (comprehensive)
    elif (section_id in ["references", "index", "glossary", "bibliography", "conclusion"] or
          title_upper in ["REFERENCES", "INDEX", "GLOSSARY", "BIBLIOGRAPHY", "CONCLUSION"] or
          "references" in section_id.lower() or
          "index" in section_id.lower()):
        metadata['is_backmatter'] = True
    
    return metadata

def extract_subsections_from_xhtml(xhtml_path: Path) -> list:
    """
    Extract all subsections from an XHTML file based on level IDs.
    Returns a list of subsection metadata for files that contain multiple subsections.
    This handles the case where subsections are anchors within the same XHTML file as the chapter.
    """
    with open(xhtml_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')
    
    subsections = []
    body_tag = soup.find('body')
    
    if not body_tag or not isinstance(body_tag, Tag):
        return subsections
    
    # Find all tags with level IDs (level1_000001, level2_000002, etc.)
    level_tags = body_tag.find_all(id=True)
    level_tags = []
    for tag in body_tag.find_all(id=True):
        if isinstance(tag, Tag):
            tag_id = tag.get('id')
            if tag_id and isinstance(tag_id, str) and re.match(r'^level\d+_', tag_id):
                level_tags.append(tag)
    
    for tag in level_tags:
        if isinstance(tag, Tag):
            section_id = tag.get('id', '')
            if not section_id or not isinstance(section_id, str):
                continue
            
            # Parse level and subsection number
            parts = section_id.split('_')
            if len(parts) >= 2:
                level_part = parts[0]
                if level_part.startswith('level'):
                    try:
                        level = int(level_part[5:])
                        # Extract subsection number
                        match = re.search(r'\d+', parts[1])
                        subsection_num = int(match.group()) if match else 0
                        
                        # Extract title from the tag content
                        title = tag.get_text(strip=True)
                        if not title:
                            # Try to find a heading within this tag
                            heading = tag.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                            if heading and isinstance(heading, Tag):
                                title = heading.get_text(strip=True)
                        
                        if title:
                            subsections.append({
                                'section_id': section_id,
                                'level': level,
                                'subsection_number': subsection_num,
                                'title': title_case(title),
                                'tag_name': tag.name
                            })
                    except (ValueError, AttributeError):
                        continue
    
    # Sort subsections by level and subsection number
    subsections.sort(key=lambda x: (x['level'], x['subsection_number']))
    return subsections

def is_chapter_boundary(title: str, label: str) -> bool:
    """
    Determine if a TOC entry represents a new chapter boundary.
    Returns True if this should start a new chapter group.
    """
    import re
    title_upper = title.upper()
    label_upper = label.upper()
    
    # Primary patterns for chapter detection
    chapter_patterns = [
        r'^CHAPTER\s+\d+',           # "CHAPTER 1", "CHAPTER 2"
        r'^SECTION\s+\d+',           # "SECTION 1", "SECTION 2" 
        r'^PART\s+\d+',              # "PART 1", "PART 2"
        r'^\d+\.\s+[A-Z]',           # "1. INTRODUCTION", "2. METHODS"
        r'^[A-Z][A-Z\s]{10,}$',      # Long all-caps titles (likely chapters)
        r'^INTRODUCTION$',            # Common chapter title
        r'^CONCLUSION$',              # Common chapter title
        r'^\d+\s*[-–]\s*[A-Z]',      # "1 - TITLE" format
        r'^APPENDIX\s*[A-Z]?$',      # "APPENDIX A", "APPENDIX"
        r'^BIBLIOGRAPHY$',           # Common back matter
        r'^REFERENCES$',              # Common back matter
        r'^GLOSSARY$',                # Common back matter
        r'^INDEX$'                    # Common back matter
    ]
    
    # Check title patterns
    for pattern in chapter_patterns:
        if re.match(pattern, title_upper):
            return True
        if re.match(pattern, label_upper):
            return True
    
    # Additional heuristics
    if len(title_upper) > 50 and title_upper.isupper():
        return True  # Very long uppercase titles are likely chapters
        
    return False

def validate_chapter_groups(chapter_groups, max_expected_chapters=20):
    """
    Validate chapter grouping results and apply fallbacks if needed.
    If we detect too many single-file chapters, apply alternative grouping.
    """
    single_file_chapters = sum(1 for _, _, files in chapter_groups if len(files) == 1)
    total_chapters = len(chapter_groups)
    
    # Check for over-grouping (chapters with too many files)
    oversized_chapters = sum(1 for _, _, files in chapter_groups if len(files) > 10)
    
    # If more than 70% are single-file chapters and we have many chapters, 
    # this suggests our detection failed
    if total_chapters > max_expected_chapters or (single_file_chapters / total_chapters) > 0.7:
        print(f"[WARNING] Detected {total_chapters} chapters with {single_file_chapters} single-file chapters")
        print("[WARNING] This suggests chapter detection may have failed")
        return False
    
    # If we have oversized chapters, that's also concerning
    if oversized_chapters > 0:
        print(f"[WARNING] Detected {oversized_chapters} chapters with more than 10 files")
        print("[WARNING] This suggests over-grouping may have occurred")
        return False
    
    return True

def build_toc_driven_structure(toc_entries, content_root: Path) -> tuple:
    """
    Build chapter structure based on TOC hierarchy first, then validate with metadata.
    This prevents over-extraction of subsections that are just anchors within chapters.
    
    NEW APPROACH: Use TOC as primary source of truth, only create separate files when
    TOC indicates different XHTML files, not just different anchors within the same file.
    """
    print("\n=== BUILDING TOC-DRIVEN STRUCTURE ===")
    
    # Extract metadata for all files for validation
    file_metadata = {}
    for file, _, _, _ in toc_entries:
        xhtml_path = content_root / file
        if xhtml_path.exists():
            file_metadata[file] = extract_xhtml_metadata(xhtml_path)
        else:
            print(f"[WARNING] XHTML file not found: {xhtml_path}")
    
    # Also check all XHTML files in content_root
    all_xhtml_files = list(content_root.glob("*.xhtml"))
    for xhtml_file in all_xhtml_files:
        if xhtml_file.name not in file_metadata:
            file_metadata[xhtml_file.name] = extract_xhtml_metadata(xhtml_file)
    
    # TOC-DRIVEN GROUPING LOGIC
    chapter_groups = []
    frontmatter_files = []
    backmatter_files = []
    
    current_chapter = None
    current_chapter_files = []
    current_chapter_title = ""
    
    # First pass: identify chapter boundaries more carefully
    chapter_boundaries = []
    for i, (file, anchor, label, depth) in enumerate(toc_entries):
        if file == "toc.xhtml":
            continue
            
        metadata = file_metadata.get(file, {})
        title = metadata.get('title', label)
        
        # Only start a new chapter if it's explicitly a "CHAPTER" entry
        if depth == 1 and "CHAPTER" in title.upper():
            chapter_boundaries.append(i)
    
    # Second pass: group files based on chapter boundaries
    for i, (file, anchor, label, depth) in enumerate(toc_entries):
        if file == "toc.xhtml":
            continue
            
        metadata = file_metadata.get(file, {})
        title = metadata.get('title', label)
        
        # Check if this is a chapter boundary
        if i in chapter_boundaries:
            # Save previous chapter if exists
            if current_chapter is not None and current_chapter_files:
                chapter_groups.append((current_chapter, current_chapter_title, current_chapter_files))
            
            # Start new chapter
            current_chapter = len(chapter_groups) + 1
            current_chapter_files = [file]
            current_chapter_title = title
            continue
        
        # Check if this is back matter
        if any(keyword in title.lower() for keyword in ["references", "glossary", "index", "conclusion", "discussion"]):
            # Save current chapter if exists
            if current_chapter is not None and current_chapter_files:
                chapter_groups.append((current_chapter, current_chapter_title, current_chapter_files))
            
            # Add to back matter
            backmatter_files.append(file)
            current_chapter = None
            current_chapter_files = []
            continue
        
        # Check if this is front matter (before any chapter starts)
        if current_chapter is None:
            frontmatter_files.append(file)
            continue
        
        # If we're in a chapter, add this file to the current chapter
        if current_chapter is not None:
            # Only add if it's a different XHTML file (not just a different anchor)
            if file not in current_chapter_files:
                current_chapter_files.append(file)
    
    # Save the last chapter
    if current_chapter is not None and current_chapter_files:
        chapter_groups.append((current_chapter, current_chapter_title, current_chapter_files))
    
    # Debug output
    print(f"\n=== TOC-DRIVEN STRUCTURE RESULTS ===")
    print(f"Front matter files: {len(frontmatter_files)}")
    for f in frontmatter_files:
        print(f"  → {f}")
    
    print(f"\nChapters: {len(chapter_groups)}")
    for chapter_num, title, files in chapter_groups:
        print(f"Chapter {chapter_num:02d}: {title}")
        for j, file in enumerate(files):
            label = f"{chapter_num:02d}.{j}" if j > 0 else f"{chapter_num:02d}.0"
            print(f"  → {label} - {file}")
    
    print(f"\nBack matter files: {len(backmatter_files)}")
    for f in backmatter_files:
        print(f"  → {f}")
    
    print("=" * 50)
    
    return chapter_groups, frontmatter_files, backmatter_files

# === CLI ===

def generate_obsidian_toc(conversion_log, output_dir: Path):
    """Create a Markdown-formatted TOC compatible with Obsidian based on actual output files."""
    toc_lines = ["# Table of Contents", ""]
    
    # Sort chapters by their index to maintain proper order
    sorted_chapters = sorted(conversion_log["chapters"], key=lambda x: x["index"])
    
    for chapter in sorted_chapters:
        index = chapter["index"]
        title = chapter["title"]
        output_file = chapter["output_file"]
        
        # Determine indentation based on the index structure
        # Main chapters (e.g., "01.0", "02.0") get no indentation
        # Subsections (e.g., "01.1", "01.2") get one level of indentation
        # Sub-subsections (e.g., "01.1.1") would get two levels, etc.
        if "." in index:
            parts = index.split(".")
            if len(parts) >= 2 and parts[1] == "0":
                # Main chapter - no indentation
                indent = ""
            else:
                # Subsection - one level of indentation
                indent = "  "
        else:
            # Front matter (00a, 00b) or back matter (90, 91) - no indentation
            indent = ""
        
        # Create the TOC entry with proper Obsidian file link (without .md extension)
        # Obsidian automatically hides .md extensions in links
        toc_link = output_file.replace('.md', '')
        toc_lines.append(f"{indent}- [[{toc_link}]]")
    
    toc_text = "\n".join(toc_lines)
    toc_path = output_dir / "00 - Table of Contents.md"
    with open(toc_path, "w", encoding="utf-8") as f:
        f.write(toc_text)
    print(f"TOC written to: {toc_path}")

def show_final_dialog(log: dict, elapsed_sec: float, md_status=True, cleanup_status=True, json_status=True):
    """Displays a summary dialog on macOS using AppleScript."""
    import subprocess
    from pathlib import Path

    def icon(flag): return "✅" if flag else "❌"

    from pathlib import Path
    md_files = list(Path(log.get("output_dir", ".")).glob("*.md"))
    count = len(md_files)
    time_min = int(elapsed_sec // 60)
    time_sec = int(elapsed_sec % 60)
    time_str = f"{time_min}m {time_sec}s" if time_min else f"{time_sec}s"

    # Determine images folder status
    images_dst = Path(log.get("output_dir", ".")) / "images"
    img_icon = "✅" if (images_dst.exists() and any(images_dst.iterdir())) else "⛔"

    summary = f"""📘 EPUB Conversion Summary

📄 Markdown output: {icon(md_status)}

🧹 Markdown cleanup: {icon(cleanup_status)}

🧾 JSON log written: {icon(json_status)}

🖼️ Images transferred: {img_icon}

📚 Total .md files: {count}

🕒 Time elapsed: {time_str}
"""

    subprocess.run([
        "osascript", "-e",
        f'display dialog "{summary}" buttons ["OK"] default button "OK" with title "EPUB to Markdown Converter Summary"'
    ])

def test_single_xhtml(xhtml_path: Path, output_dir: Path | None = None):
    """Test function to convert a single XHTML file to Markdown and apply cleanup."""
    if output_dir is None:
        output_dir = Path("test_sandbox")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract title for filename
    title = extract_title_from_xhtml(xhtml_path)
    safe_title = safe_filename(title)
    output_filename = f"test_{safe_title}.md"
    output_path = output_dir / output_filename
    
    print(f"Converting: {xhtml_path}")
    print(f"Title: {title}")
    print(f"Output: {output_path}")
    
    # Convert XHTML to Markdown using Pandoc
    run_pandoc(xhtml_path, output_path)
    
    # Read the raw Markdown
    with open(output_path, "r", encoding="utf-8") as f:
        raw_md = f.read()
    
    print(f"\n=== RAW PANDOC OUTPUT ===")
    print(raw_md[:500] + "..." if len(raw_md) > 500 else raw_md)
    
    # Apply cleanup
    cleaned_md = clean_markdown_text(raw_md, None)
    
    print(f"\n=== AFTER CLEANUP ===")
    print(cleaned_md[:500] + "..." if len(cleaned_md) > 500 else cleaned_md)
    
    # Save cleaned version
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned_md)
    
    print(f"\nCleaned version saved to: {output_path}")
    return output_path

def main():
    import re
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Convert EPUB to Markdown (Obsidian-ready)")
    parser.add_argument("epub_file", type=Path, nargs="?", help="Path to the .epub file")
    parser.add_argument("--test-xhtml", type=Path, help="Run cleanup on a single XHTML file")
    parser.add_argument("--test-cleanup", type=Path, help="Test cleanup on a single Markdown file")
    parser.add_argument("--test-single", type=Path, help="Test single XHTML file conversion and cleanup")
    args = parser.parse_args()

    if args.test_cleanup:
        input_path = args.test_cleanup.resolve()
        if not input_path.exists():
            print(f"File not found: {input_path}")
            sys.exit(1)
        
        print(f"Testing cleanup on: {input_path}")
        with open(input_path, "r", encoding="utf-8") as f:
            raw_md = f.read()
        
        print("\n=== BEFORE CLEANUP ===")
        print(raw_md[:500] + "..." if len(raw_md) > 500 else raw_md)
        
        cleaned_md = clean_markdown_text(raw_md, None)
        
        print("\n=== AFTER CLEANUP ===")
        print(cleaned_md[:500] + "..." if len(cleaned_md) > 500 else cleaned_md)
        
        # Ask if user wants to save the cleaned version
        response = input("\nSave cleaned version? (y/n): ").lower().strip()
        if response == 'y':
            backup_path = input_path.with_suffix('.md.backup')
            shutil.copy2(input_path, backup_path)
            print(f"Backup saved to: {backup_path}")
            
            with open(input_path, "w", encoding="utf-8") as f:
                f.write(cleaned_md)
            print(f"Cleaned version saved to: {input_path}")
        return

    if args.test_single:
        input_path = args.test_single.resolve()
        if not input_path.exists():
            print(f"File not found: {input_path}")
            sys.exit(1)
        
        test_single_xhtml(input_path)
        return

    if args.test_xhtml:
        input_path = args.test_xhtml.resolve()
        if not input_path.exists():
            print(f"File not found: {input_path}")
            sys.exit(1)

        from tempfile import NamedTemporaryFile
        with NamedTemporaryFile(suffix=".md", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            run_pandoc(input_path, tmp_path)
            with open(tmp_path, "r", encoding="utf-8") as f:
                raw_md = f.read()
                md_content = clean_markdown_text(raw_md, None)
            print("=== Cleaned Markdown Output ===\n")
            print(md_content)
            tmp_path.unlink()
        return

    epub_file = args.epub_file.resolve()  # Resolve full path to EPUB
    if not epub_file.exists():
        print(f"File not found: {epub_file}")
        sys.exit(1)

    epub_abs_path = str(epub_file.resolve())
    SCRIPT_VERSION = "v0.9.0-beta"

    from datetime import datetime
    start_timestamp = datetime.utcnow().isoformat() + "Z"

    images_src = None  # will be set before use
    # Initialize conversion_log without output_dir (will be updated later)
    conversion_log = {
        "epub": epub_file.name,
        "epub_path": epub_abs_path,
        "output_dir": "",  # Will be updated after output_dir is determined
        "start_time_utc": start_timestamp,
        "images_moved": False,
        "script_version": SCRIPT_VERSION,
        "xhtml_files_in_epub": [],
        "unlinked_files": [],
        "toc_entries": [],
        "chapter_groups": [],
        "warnings": [],
        "chapters": []
    }

    temp_dir = Path("/tmp") / f"epub_extract_{epub_file.stem}"  # Temporary extraction folder
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    # === PHASE 1: Pandoc Conversion Phase ===
    # Extract EPUB contents into temporary folder for processing
    extract_epub(epub_file, temp_dir)
    print(f"EPUB extracted to: {temp_dir}")

    opf_path = find_opf_path(temp_dir)  # Locate OPF file via container.xml
    content_root = opf_path.parent      # Set root for content folder (usually OEBPS or EPUB)
    
    # Handle different EPUB folder structures
    # Some EPUBs have XHTML files directly in OEBPS/, others in OEBPS/html/
    potential_content_roots = [
        content_root,  # OEBPS/ or EPUB/
        content_root / "html",  # OEBPS/html/
        content_root / "EPUB",  # OEBPS/EPUB/
    ]
    
    # Find the folder that contains XHTML files
    actual_content_root = None
    for root in potential_content_roots:
        if root.exists() and any(root.glob("*.xhtml")):
            actual_content_root = root
            break
    
    if actual_content_root is None:
        # Fallback: use the original content_root
        actual_content_root = content_root
        print(f"[WARNING] Could not find XHTML files in expected locations, using: {content_root}")
    
    content_root = actual_content_root
    print(f"[INFO] Using content root: {content_root}")

    # Extract book title from copyright statement
    book_title = extract_book_title_from_copyright(content_root)
    if book_title:
        # Use book title for folder name, sanitize it
        safe_book_title = safe_filename(book_title)
        output_dir = OUTPUT_ROOT / safe_book_title
        print(f"[INFO] Using book title for folder: {safe_book_title}")
    else:
        # Fallback to EPUB filename
        output_dir = OUTPUT_ROOT / epub_file.stem
        print(f"[INFO] Using EPUB filename for folder: {epub_file.stem}")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Update conversion_log with the correct output_dir and book title
    conversion_log["output_dir"] = str(output_dir)
    conversion_log["book_title"] = book_title if book_title else epub_file.stem

    # Copy images directory if present
    images_src = content_root / "images"
    images_dst = output_dir / "images"
    if images_src.exists() and images_src.is_dir():
        shutil.copytree(images_src, images_dst, dirs_exist_ok=True)
        print(f"Copied images to: {images_dst}")
    # Update images_moved status in conversion_log
    conversion_log["images_moved"] = images_src.exists() and images_src.is_dir() and any(images_src.iterdir())

    # Parse the Table of Contents (toc.xhtml) to obtain ordered chapter files
    toc_file = content_root / "toc.xhtml"  # Look for the navigation file
    if not toc_file.exists():
        print("Error: toc.xhtml not found.")
        sys.exit(1)

    toc_entries = parse_toc_xhtml(toc_file)  # Parse TOC to get file order
    conversion_log["toc_entries"] = [
        {"file": f, "anchor": a, "label": l, "depth": d}
        for f, a, l, d in toc_entries
    ]

    # List all xhtml files in content_root
    all_xhtml_files = {f.name for f in (content_root).glob("*.xhtml")}
    
    # --- FIX: Explicitly remove toc.xhtml so it is not processed as content ---
    # This prevents the duplicate TOC file issue where toc.xhtml gets converted to Markdown
    # and creates a second TOC file alongside our generated one.
    all_xhtml_files.discard("toc.xhtml")
    print(f"[INFO] Excluded toc.xhtml from content processing to prevent duplicate TOC files")
    # --- END FIX ---
    
    conversion_log["xhtml_files_in_epub"] = sorted(list(all_xhtml_files))
    toc_xhtml_files = [file for file, _, _, _ in toc_entries]
    toc_used = set(toc_xhtml_files)

    # Front matter: files not referenced in TOC (will be overridden by metadata-driven structure)
    old_front_matter = sorted(all_xhtml_files - toc_used)
    conversion_log["unlinked_files"] = sorted(list(old_front_matter))

    # --- Automatic back matter detection based on title keywords ---
    back_keywords = ["references", "glossary", "index"]
    # Remove toc.xhtml from TOC-driven structure (already handled separately as front matter)
    toc_main_entries = [(f, a, l, d) for f, a, l, d in toc_entries if "toc.xhtml" not in f]
    back_matter = []
    filtered_toc_main_entries = []
    for file, anchor, label, depth in toc_main_entries:
        xhtml_path = content_root / file
        title = extract_title_from_xhtml(xhtml_path).lower()
        if any(keyword in title for keyword in back_keywords):
            back_matter.append(file)
        else:
            filtered_toc_main_entries.append((file, anchor, label, depth))
    toc_main_entries = filtered_toc_main_entries
    # --------------------------------------------------------------

    # === CHAPTER GROUPING (TOC-DRIVEN) ===
    # Use TOC hierarchy as primary source of truth, validate with metadata
    # This prevents over-extraction of subsections that are just anchors within chapters
    print("\n=== BUILDING TOC-DRIVEN STRUCTURE ===")
    chapter_groups, front_matter, back_matter = build_toc_driven_structure(toc_main_entries, content_root)
    
    # Debug output for TOC-driven structure
    print("\n=== TOC-DRIVEN STRUCTURE RESULTS ===")
    print(f"Front matter files: {len(front_matter)}")
    for f in front_matter:
        print(f"  → {f}")
    
    print(f"\nChapters: {len(chapter_groups)}")
    for chapter_num, title, files in chapter_groups:
        print(f"Chapter {chapter_num:02d}: {title}")
        for j, file in enumerate(files):
            label = f"{chapter_num:02d}.{j}" if j > 0 else f"{chapter_num:02d}.0"
            print(f"  → {label} - {file}")
    
    print(f"\nBack matter files: {len(back_matter)}")
    for f in back_matter:
        print(f"  → {f}")
    
    print("=" * 50)
    
    # TOC-DRIVEN APPROACH: No subsection extraction needed
    # We now use the TOC structure to determine file grouping
    # Subsections that are anchors within the same XHTML file stay as part of that file
    print("\n=== TOC-DRIVEN APPROACH: No subsection extraction ===")
    print("[INFO] Using TOC structure to determine file grouping")
    print("[INFO] Subsections that are anchors within the same XHTML file will remain as part of that file")

    conversion_log["chapter_groups"] = [
        {"chapter_num": f"{num:02d}", "title": title, "files": group}
        for num, title, group in chapter_groups
    ]
    
    # Add chapter grouping metadata for debugging
    conversion_log["chapter_grouping_metadata"] = {
        "total_chapters": len(chapter_groups),
        "single_file_chapters": sum(1 for _, _, files in chapter_groups if len(files) == 1),
        "multi_file_chapters": sum(1 for _, _, files in chapter_groups if len(files) > 1),
        "max_files_per_chapter": max(len(files) for _, _, files in chapter_groups) if chapter_groups else 0,
        "avg_files_per_chapter": sum(len(files) for _, _, files in chapter_groups) / len(chapter_groups) if chapter_groups else 0,
        "content_root_used": str(content_root),
        "epub_structure_type": "OEBPS/html" if "html" in str(content_root) else "OEBPS" if "OEBPS" in str(content_root) else "EPUB" if "EPUB" in str(content_root) else "Unknown"
    }

    # === ASSIGN LABELS ===
    # chapter_index_map maps each file to its decimal chapter/subsection label (e.g., 01.0, 01.1, ...)
    chapter_index_map = {}  # Maps original file to label (e.g., 01.0, 01.1, etc.)
    file_sections = []

    # --- Front Matter ---
    # Files not referenced in TOC are considered front matter and labeled as 00a, 00b, ...
    # Sort frontmatter files by their order in the TOC to ensure sequential lettering
    frontmatter_with_order = []
    for i, (file, anchor, label, depth) in enumerate(toc_entries):
        if file in front_matter:
            frontmatter_with_order.append((i, file))  # (toc_index, filename)
    
    # Sort by TOC order and assign sequential letters
    frontmatter_with_order.sort(key=lambda x: x[0])
    for i, (toc_index, fname) in enumerate(frontmatter_with_order):
        label = f"00{chr(ord('a') + i)}"
        chapter_index_map[fname] = label
        file_sections.append((label, [fname], "Front Matter"))

    # --- Chapters + Subsections ---
    # Each chapter group: first file is the chapter header (e.g., 01.0), subsequent files are subsections (e.g., 01.1, 01.2, ...)
    for chap_num, chap_title, files in chapter_groups:
        for i, file in enumerate(files):
            if i == 0:
                label = f"{chap_num:02d}.0"  # Chapter header
            else:
                label = f"{chap_num:02d}.{i}"  # Chapter subsections
            chapter_index_map[file] = label
            file_sections.append((label, [file], chap_title))

    # --- Back Matter ---
    # Files detected as back matter (e.g., references, glossary, index) are labeled as 90, 91, ...
    for i, fname in enumerate(back_matter):
        label = f"{90 + i}"
        chapter_index_map[fname] = label
        file_sections.append((label, [fname], "Back Matter"))

    # Debug output of chapter_index_map
    print("\n--- DEBUG: Chapter Index Map ---")
    for k, v in chapter_index_map.items():
        print(f"{k}: {v}")

    # --- PHASE 1: Pandoc Conversion Phase ---
    # Convert all .xhtml files to temp .md files in a dedicated temp_md_dir
    temp_md_dir = temp_dir / "md"
    temp_md_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all files that need to be converted (including subsections)
    all_files_to_convert = set()
    all_files_to_convert.update(all_xhtml_files)  # All XHTML files
    
    # Also include any files from chapter groups that might not be in all_xhtml_files
    for chap_num, chap_title, files in chapter_groups:
        all_files_to_convert.update(files)
    
    # Also include frontmatter and backmatter files
    all_files_to_convert.update(front_matter)
    all_files_to_convert.update(back_matter)
    
    xhtml_files_for_md = list(all_files_to_convert)
    print(f"[DEBUG] Files to convert: {len(xhtml_files_for_md)}")
    for f in sorted(xhtml_files_for_md):
        print(f"  → {f}")
    
    # Validation step: Check XHTML files exist before Pandoc conversion
    for xhtml_file in xhtml_files_for_md:
        xhtml_path = content_root / xhtml_file
        if not xhtml_path.exists():
            warning = f"Missing XHTML file: {xhtml_path.name}"
            print(f"Warning: {warning}")
            conversion_log["warnings"].append(warning)
    
    for xhtml_file in xhtml_files_for_md:
        xhtml_path = content_root / xhtml_file
        md_temp_path = temp_md_dir / f"{Path(xhtml_file).stem}.md"
        run_pandoc(xhtml_path, md_temp_path)
    print(f"[Phase 1] Converted {len(xhtml_files_for_md)} XHTML files to Markdown in temp folder: {temp_md_dir}")

    # --- PHASE 2: File Naming & Renaming Phase ---
    # Assign logical filenames (00a, 01a, etc.) based on TOC and extracted titles.
    # Move .md files from temp_md_dir to final output directory.
    chapter_map = {}  # XHTML file -> final .md filename
    for label, group, chap_title in file_sections:
        if not group:
            continue
        for fname in group:
            xhtml_path = content_root / fname
            title = extract_title_from_xhtml(xhtml_path)
            safe_title = safe_filename(title)
            output_filename = f"{label} - {safe_title}.md"
            stem = Path(fname).stem
            md_temp_path = temp_md_dir / (Path(fname).stem + ".md")
            output_path = output_dir / output_filename
            # Check if the expected file exists before moving
            if not md_temp_path.exists():
                warning = f"Expected markdown not found: {md_temp_path.name}"
                print(f"Warning: {warning}")
                conversion_log["warnings"].append(warning)
                continue
            # Move/rename the file
            shutil.move(str(md_temp_path), str(output_path))
            chapter_map[fname] = output_filename
            # Log for JSON
            conversion_log["chapters"].append({
                "index": label,
                "title": title,
                "source_files": [fname],
                "output_file": output_filename
            })
            print(f"[Phase 2] Moved {md_temp_path.name} to {output_filename}")

    # Remove any leftover temp .md files (should be none, but for safety)
    for f in temp_md_dir.glob("*.md"):
        f.unlink()
    # Only remove temp_md_dir if it is empty
    if not any(temp_md_dir.iterdir()):
        temp_md_dir.rmdir()
    print(f"[Phase 2] Temp Markdown files cleaned up.")

    # --- PHASE 3: Markdown Cleanup Phase ---
    # Read each .md file in the output directory, apply clean_markdown_text() (excluding link conversion)
    for entry in conversion_log["chapters"]:
        md_path = output_dir / entry["output_file"]
        if not md_path.exists():
            continue
        with open(md_path, "r", encoding="utf-8") as f:
            raw_md = f.read()
        cleaned_md = clean_markdown_text(raw_md, chapter_map=None)  # Exclude link conversion
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(cleaned_md)
        print(f"[Phase 3] Cleaned markdown: {entry['output_file']}")

    # --- PHASE 4: Cross-Link Rewriting Phase ---
    # Replace internal [text](chapter.xhtml#anchor) with Obsidian [[filename#anchor]]
    for entry in conversion_log["chapters"]:
        md_path = output_dir / entry["output_file"]
        if not md_path.exists():
            continue
        with open(md_path, "r", encoding="utf-8") as f:
            raw_md = f.read()
        cleaned_md = clean_markdown_text(raw_md, chapter_map=chapter_map)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(cleaned_md)
        print(f"[Phase 4] Rewrote cross-links in: {entry['output_file']}")

    # Generate Obsidian-compatible Table of Contents file
    # This creates the main TOC file with proper Obsidian links
    # The toc.xhtml file has been excluded from content processing above to prevent duplicates
    toc_path = output_dir / "00 - Table of Contents.md"
    if not toc_path.exists():
        generate_obsidian_toc(conversion_log, output_dir)
        print(f"[INFO] Generated Obsidian-compatible TOC: {toc_path}")
    else:
        print(f"[INFO] TOC file already exists, skipping generation")

    # Add runtime metadata before writing log
    from datetime import datetime
    end_timestamp = datetime.utcnow().isoformat() + "Z"
    conversion_log["end_time_utc"] = end_timestamp
    conversion_log["total_output_files"] = len(conversion_log["chapters"])

    # Create timestamped log filename
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d_%H.%M")
    # Use book title for log filename if available, otherwise use EPUB filename
    if book_title:
        safe_log_title = safe_filename(book_title)
        log_path = LOG_DIR / f"{safe_log_title}_{timestamp}.json"
    else:
        log_path = LOG_DIR / f"{epub_file.stem}_{timestamp}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(conversion_log, f, indent=2)
    print(f"Log saved to: {log_path}")

    return conversion_log

import time
if __name__ == "__main__":
    start_time = time.time()
    # Run main() and capture conversion log
    log = main()
    if log is None:
        log = {}
    elapsed = time.time() - start_time
    # Show summary dialog with accurate counts
    show_final_dialog(log, elapsed, md_status=True, cleanup_status=True, json_status=True)


        