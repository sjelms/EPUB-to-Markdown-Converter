import re

# Helper function to sanitize titles for filenames
def safe_filename(title: str) -> str:
    """Sanitize title for use as a filename (prevent subfolders or illegal characters)."""
    return re.sub(r'[\\/:"*?<>|]', '-', title)
#!/usr/bin/env python3
def clean_markdown_text(md: str, chapter_map=None) -> str:
    """Apply post-processing cleanup rules to raw Markdown."""
    import re
    # Remove Pandoc fenced divs (e.g., ::: {.class})
    md = re.sub(r'::: ?\{[^}]*\}', '', md)
    # Remove closing fenced divs (:::)
    md = re.sub(r':::', '', md)
    # Remove same-file internal anchor links: [text](#anchor) → text
    md = re.sub(r'\[([^\]]+)\]\(#[^)]+\)', r'\1', md)

    # Preserve and optionally reformat cross-file links: [text](chapter3.xhtml#Section2)
    # These are assumed to be converted in a later step or kept as-is for Obsidian
    # No change needed unless formatting is required

    # Collapse multiple blank lines to a single blank line
    md = re.sub(r'\n{3,}', '\n\n', md)
    # Optionally: remove lines before first heading to clean leading content
    lines = md.strip().splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith('#'):
            md = '\n'.join(lines[i:])
            break
    # Remove square brackets around citation-style blocks (not links)
    # Only unwrap if content looks like a citation (e.g., Author (Year))
    md = re.sub(
        r'(?<!\!)\[(.{20,}?)\](?!\()',
        lambda m: m.group(1) if re.search(r'\w+\s+\(\d{4}', m.group(1)) else m.group(0),
        md
    )
    # Convert isolated quotes followed by attribution into block quotes
    # Matches paragraphs with quotes and attribution on separate lines
    quote_block_pattern = re.compile(r'(?<=\n\n)([^>\n]{30,}?)\n\(([^)]+)\)(?=\n\n)', re.DOTALL)
    md = quote_block_pattern.sub(lambda m: f'> {m.group(1).strip()}\n> — {m.group(2).strip()}', md)

    # Convert cross-chapter links to Obsidian-style [[filename#heading]]
    if chapter_map:
        def replace_cross_links(match):
            text, target = match.group(1), match.group(2)
            if "#" in target:
                file_part, anchor = target.split("#", 1)
            else:
                file_part, anchor = target, ""
            if file_part in chapter_map:
                md_target = chapter_map[file_part]
                return f"[[{md_target}#{anchor}]]" if anchor else f"[[{md_target}]]"
            else:
                return text  # Leave unchanged if file not found

        md = re.sub(r'\[([^\]]+)\]\(([^)]+\.xhtml#[^)]+)\)', replace_cross_links, md)

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
    with open(toc_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')  # Use strict XML parsing

    toc_entries = []

    def process_ol(ol_tag, depth=1):
        for li in ol_tag.find_all('li', recursive=False):
            a_tag = li.find('a', href=True)
            if a_tag:
                href = a_tag['href']
                label = a_tag.get_text(strip=True)
                if '.xhtml' in href:
                    if '#' in href:
                        file_part, anchor = href.split('#', 1)
                    else:
                        file_part, anchor = href, None
                    toc_entries.append((file_part, anchor, label, depth))
            nested_ol = li.find('ol', recursive=False)
            if nested_ol:
                process_ol(nested_ol, depth + 1)

    nav = soup.find('nav')
    if nav:
        ol = nav.find('ol')
        if ol:
            process_ol(ol)
    else:
        # fallback to flat structure
        for a in soup.find_all('a', href=True):
            href = a['href']
            label = a.get_text(strip=True)
            if '.xhtml' in href:
                if '#' in href:
                    file_part, anchor = href.split('#', 1)
                else:
                    file_part, anchor = href, None
                toc_entries.append((file_part, anchor, label, 1))
    return toc_entries

def extract_title_from_xhtml(xhtml_path: Path) -> str:
    """Extracts the <title> from an XHTML file."""
    with open(xhtml_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')  # Use strict XML parsing
    title_tag = soup.find('title')
    return title_tag.get_text(strip=True) if title_tag else "Untitled"

def extract_xhtml_metadata(xhtml_path: Path) -> dict:
    """
    Extract comprehensive metadata from XHTML file including:
    - title
    - body type (frontmatter, bodymatter, backmatter)
    - section id and type
    - chapter information
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
        'subsection_number': None
    }
    
    # Extract title
    title_tag = soup.find('title')
    if title_tag:
        metadata['title'] = title_tag.get_text(strip=True)
    
    # Extract body type
    body_tag = soup.find('body')
    if body_tag and isinstance(body_tag, Tag):
        metadata['body_type'] = body_tag.get('epub:type')
    
    # Extract section information
    section_tag = soup.find('section')
    if section_tag and isinstance(section_tag, Tag):
        metadata['section_id'] = section_tag.get('id')
        metadata['section_type'] = section_tag.get('epub:type')
    
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
        # Extract chapter number from various formats
        if section_id.startswith("ch"):
            try:
                metadata['chapter_number'] = int(section_id[2:])
            except ValueError:
                pass
        elif section_id.startswith("chapter"):
            try:
                metadata['chapter_number'] = int(section_id[7:])
            except ValueError:
                pass
        elif section_id.startswith("Sec"):
            try:
                metadata['chapter_number'] = int(section_id[3:])
            except ValueError:
                pass
        # Extract from title if section_id doesn't have number
        elif "CHAPTER" in title_upper:
            import re
            match = re.search(r'CHAPTER\s+(\d+)', title_upper)
            if match:
                try:
                    metadata['chapter_number'] = int(match.group(1))
                except ValueError:
                    pass
    
    # Level detection within chapters (comprehensive)
    elif section_id.startswith("level"):
        parts = section_id.split("_")
        if len(parts) >= 2:
            level_part = parts[0]
            if level_part.startswith("level"):
                try:
                    metadata['level'] = int(level_part[5:])
                    # Extract subsection number from the second part
                    if len(parts) >= 2:
                        try:
                            metadata['subsection_number'] = int(parts[1])
                        except ValueError:
                            pass
                except ValueError:
                    pass
    
    # Backmatter detection (comprehensive)
    elif (section_id in ["references", "index", "glossary", "bibliography"] or
          title_upper in ["REFERENCES", "INDEX", "GLOSSARY", "BIBLIOGRAPHY", "CONCLUSION"] or
          "references" in section_id.lower() or
          "index" in section_id.lower()):
        metadata['is_backmatter'] = True
    
    return metadata

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

def build_metadata_driven_structure(toc_entries, content_root: Path) -> tuple:
    """
    Build chapter structure based on XHTML metadata instead of TOC patterns.
    Returns (chapter_groups, front_matter, back_matter) with proper organization.
    """
    # Extract metadata for all files
    file_metadata = {}
    for file, _, _, _ in toc_entries:
        xhtml_path = content_root / file
        if xhtml_path.exists():
            file_metadata[file] = extract_xhtml_metadata(xhtml_path)
            print(f"[DEBUG] {file}: {file_metadata[file]}")
    
    # Separate files by type
    frontmatter_files = []
    chapter_files = {}
    backmatter_files = []
    other_files = []
    
    for file, metadata in file_metadata.items():
        if metadata['is_frontmatter']:
            frontmatter_files.append(file)
        elif metadata['is_chapter']:
            chapter_num = metadata['chapter_number'] or 0
            if chapter_num not in chapter_files:
                chapter_files[chapter_num] = []
            chapter_files[chapter_num].append(file)
        elif metadata['is_backmatter']:
            backmatter_files.append(file)
        else:
            other_files.append(file)
    
    # Build chapter groups with proper ordering
    chapter_groups = []
    sorted_chapters = sorted(chapter_files.keys())
    
    for chapter_num in sorted_chapters:
        files = chapter_files[chapter_num]
        if files:
            # Get the main chapter title (first file in chapter)
            main_file = files[0]
            main_metadata = file_metadata[main_file]
            chapter_title = main_metadata['title']
            
            # Sort files within chapter by level and subsection number
            def sort_key(f):
                meta = file_metadata[f]
                level = meta.get('level', 999)  # Default high level for sorting
                subsection = meta.get('subsection_number', 999)  # Default high subsection
                # Primary sort by level, secondary by subsection number
                return (level, subsection)
            
            sorted_files = sorted(files, key=sort_key)
            chapter_groups.append((chapter_num, chapter_title, sorted_files))
    
    # Handle files that couldn't be classified by metadata
    if other_files:
        print(f"[WARNING] {len(other_files)} files could not be classified by metadata:")
        for f in other_files:
            print(f"  → {f}: {file_metadata[f]}")
        
        # Try to classify based on TOC position and filename patterns
        for file in other_files:
            # Check if it looks like frontmatter based on filename
            if any(pattern in file.lower() for pattern in ['toc', 'contents', 'preface', 'introduction']):
                frontmatter_files.append(file)
            # Check if it looks like backmatter
            elif any(pattern in file.lower() for pattern in ['references', 'index', 'glossary']):
                backmatter_files.append(file)
            else:
                # Default to frontmatter for safety
                frontmatter_files.append(file)
    
    return chapter_groups, frontmatter_files, backmatter_files

# === CLI ===

def generate_obsidian_toc(toc_entries, chapter_map, output_dir: Path):
    """Create a Markdown-formatted TOC compatible with Obsidian."""
    from collections import defaultdict
    toc_lines = ["# Table of Contents", ""]
    def obsidian_anchor(text):
        text = re.sub(r'[^\w\s-]', '', text)  # Remove punctuation
        text = re.sub(r'\s+', '-', text.strip().lower())  # Replace spaces with hyphens
        return text
    skip_mode = False
    duplicate_anchors = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "pi", "pii", "piii", "piv"}
    for entry in toc_entries:
        # toc_entries: list of (file_part, anchor, label, depth) or older forms
        if len(entry) == 4:
            file, anchor, label, depth = entry
        elif len(entry) == 3:
            file, anchor, label = entry
            depth = 1
        elif len(entry) == 2:
            file, label = entry
            anchor = None
            depth = 1
        else:
            continue
        # Insert skip logic for Arabic/duplicate sections
        # If label has Arabic TOC or matches duplicate anchor, skip all subsequent entries
        if any(kw in (label or "") for kw in ["قائمة الصفحات", "قائمة", "Index"]) or (anchor and re.match(r'^p?i{1,3}v?$', anchor)):
            skip_mode = True
        if skip_mode:
            continue
        if file not in chapter_map:
            continue
        md_file = chapter_map[file]
        indent = "  " * (depth - 1)
        if anchor:
            clean_anchor = obsidian_anchor(label)
            toc_lines.append(f"{indent}- [[{md_file}#{clean_anchor}]]")
        else:
            toc_lines.append(f"{indent}- [[{md_file}]]")
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

def main():
    import re
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Convert EPUB to Markdown (Obsidian-ready)")
    parser.add_argument("epub_file", type=Path, nargs="?", help="Path to the .epub file")
    parser.add_argument("--test-xhtml", type=Path, help="Run cleanup on a single XHTML file")
    args = parser.parse_args()

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

    output_dir = OUTPUT_ROOT / epub_file.stem  # Create folder named after EPUB file
    output_dir.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    start_timestamp = datetime.utcnow().isoformat() + "Z"

    images_src = None  # will be set before use
    conversion_log = {
        "epub": epub_file.name,
        "epub_path": epub_abs_path,
        "output_dir": str(output_dir),
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

    # === CHAPTER GROUPING (METADATA-DRIVEN) ===
    # Use XHTML metadata (body type, section id, etc.) to determine proper structure
    # This is more reliable than TOC pattern matching
    print("\n=== BUILDING METADATA-DRIVEN STRUCTURE ===")
    chapter_groups, front_matter, back_matter = build_metadata_driven_structure(toc_main_entries, content_root)
    
    # Enhanced debug output
    print("\n=== METADATA-DRIVEN STRUCTURE RESULTS ===")
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
    for i, fname in enumerate(front_matter):
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
    xhtml_files_for_md = list(all_xhtml_files)
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
    generate_obsidian_toc(toc_entries, chapter_map, output_dir)

    # Add runtime metadata before writing log
    from datetime import datetime
    end_timestamp = datetime.utcnow().isoformat() + "Z"
    conversion_log["end_time_utc"] = end_timestamp
    conversion_log["total_output_files"] = len(conversion_log["chapters"])

    log_path = LOG_DIR / f"{epub_file.stem}.json"  # Path for structured log output
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


        