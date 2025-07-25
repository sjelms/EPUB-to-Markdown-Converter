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
    """Parses toc.xhtml and returns a list of (filename, anchor, label) in TOC order."""
    from bs4 import BeautifulSoup
    with open(toc_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')  # Use strict XML parsing

    toc_entries = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        label = a.get_text(strip=True)
        if '.xhtml' in href:
            if '#' in href:
                file_part, anchor = href.split('#', 1)
            else:
                file_part, anchor = href, None
            toc_entries.append((file_part, anchor, label))
    return toc_entries

def extract_title_from_xhtml(xhtml_path: Path) -> str:
    """Extracts the <title> from an XHTML file."""
    with open(xhtml_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')  # Use strict XML parsing
    title_tag = soup.find('title')
    return title_tag.get_text(strip=True) if title_tag else "Untitled"

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
        # toc_entries: list of (file_part, anchor, label)
        if len(entry) == 3:
            file, anchor, label = entry
            # Try to find depth from nesting of TOC (not available here, so default to 1)
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

    output_dir = OUTPUT_ROOT / epub_file.stem  # Create folder named after EPUB file
    output_dir.mkdir(parents=True, exist_ok=True)

    conversion_log = {
        "epub": epub_file.name,
        "output_dir": str(output_dir),
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

    # Copy images directory if present
    images_src = content_root / "images"
    images_dst = output_dir / "images"
    if images_src.exists() and images_src.is_dir():
        shutil.copytree(images_src, images_dst, dirs_exist_ok=True)
        print(f"Copied images to: {images_dst}")

    # Parse the Table of Contents (toc.xhtml) to obtain ordered chapter files
    toc_file = content_root / "toc.xhtml"  # Look for the navigation file
    if not toc_file.exists():
        print("Error: toc.xhtml not found.")
        sys.exit(1)

    toc_entries = parse_toc_xhtml(toc_file)  # Parse TOC to get file order

    # List all xhtml files in content_root
    all_xhtml_files = {f.name for f in (content_root).glob("*.xhtml")}
    toc_xhtml_files = [file for file, _, _ in toc_entries]
    toc_used = set(toc_xhtml_files)

    # Front matter: files not referenced in TOC
    front_matter = sorted(all_xhtml_files - toc_used)

    # --- Automatic back matter detection based on title keywords ---
    back_keywords = ["references", "glossary", "index"]
    # Remove toc.xhtml from TOC-driven structure (already handled separately as front matter)
    toc_main_entries = [(f, a, l) for f, a, l in toc_entries if "toc.xhtml" not in f]
    back_matter = []
    filtered_toc_main_entries = []
    for file, anchor, label in toc_main_entries:
        xhtml_path = content_root / file
        title = extract_title_from_xhtml(xhtml_path).lower()
        if any(keyword in title for keyword in back_keywords):
            back_matter.append(file)
        else:
            filtered_toc_main_entries.append((file, anchor, label))
    toc_main_entries = filtered_toc_main_entries
    # --------------------------------------------------------------

    # Group contiguous files in TOC with the same label as a chapter group.
    # Each chapter can have multiple files (e.g. 01a, 01b, ...)
    chapter_index_map = {}  # file -> (chapter_label, chapter_title)
    chapter_groups = []  # [(chapter_index, chapter_title, [file1, file2, ...])]
    prev_label = None
    prev_title = None
    group_files = []
    chapter_num = 1
    for idx, (file, anchor, label) in enumerate(toc_main_entries):
        xhtml_path = content_root / file
        title = extract_title_from_xhtml(xhtml_path)
        # If label/title is the same as previous, it's a subfile; else, new chapter group
        if prev_title is not None and title == prev_title:
            group_files.append(file)
        else:
            if prev_title is not None:
                chapter_groups.append((chapter_num, prev_title, group_files))
                chapter_num += 1
            group_files = [file]
            prev_title = title
    # Don't forget the last group
    if prev_title is not None and group_files:
        chapter_groups.append((chapter_num, prev_title, group_files))

    # Assign chapter_index_map for all TOC files
    for group in chapter_groups:
        chap_num, chap_title, files = group
        for i, file in enumerate(files):
            suffix = chr(ord('a') + i)
            label = f"{chap_num:02d}{suffix}"
            chapter_index_map[file] = (label, chap_title)

    # Build file_sections for output
    file_sections = []
    # Front matter: 00a, 00b, ...
    for i, fname in enumerate(front_matter):
        label = f"00{chr(ord('a') + i)}"
        file_sections.append((label, [fname], "Front Matter"))
    # Chapters from TOC: 01a, 01b, ... 02a, ...
    for group in chapter_groups:
        chap_num, chap_title, files = group
        for i, fname in enumerate(files):
            label = f"{chap_num:02d}{chr(ord('a') + i)}"
            file_sections.append((label, [fname], chap_title))
    # Back matter: 90, 91, ...
    for i, fname in enumerate(back_matter):
        label = f"{90 + i}"
        file_sections.append((label, [fname], "Back Matter"))

    # --- PHASE 1: Pandoc Conversion Phase ---
    # Convert all .xhtml files to temp .md files in a dedicated temp_md_dir
    temp_md_dir = temp_dir / "md"
    temp_md_dir.mkdir(parents=True, exist_ok=True)
    xhtml_files_for_md = list(all_xhtml_files)
    # Validation step: Check XHTML files exist before Pandoc conversion
    for xhtml_file in xhtml_files_for_md:
        xhtml_path = content_root / xhtml_file
        if not xhtml_path.exists():
            print(f"Warning: XHTML file missing: {xhtml_path}")
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
                print(f"Warning: Expected file not found: {md_temp_path}")
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


        