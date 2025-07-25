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
    subprocess.run([
        "/opt/homebrew/bin/pandoc",  # Full path to Pandoc binary
        str(input_file),               # Input XHTML file
        "-f", "html",                  # From format: HTML (XHTML compatible)
        "-t", "markdown",              # To format: Markdown
        "--wrap=none",                 # Prevent forced line breaks (natural wrapping)
        "-o", str(output_file)         # Output Markdown file
    ], check=True)

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
        if file not in chapter_map:
            continue
        md_file = chapter_map[file]
        indent = "  " * (depth - 1)
        if anchor:
            toc_lines.append(f"{indent}- [[{md_file}#{label}]]")
        else:
            toc_lines.append(f"{indent}- [[{md_file}]]")
    toc_text = "\n".join(toc_lines)
    toc_path = output_dir / "00 - Table of Contents.md"
    with open(toc_path, "w", encoding="utf-8") as f:
        f.write(toc_text)
    print(f"TOC written to: {toc_path}")

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

    # Extract EPUB contents into temporary folder for processing
    extract_epub(epub_file, temp_dir)

    opf_path = find_opf_path(temp_dir)  # Locate OPF file via container.xml
    content_root = opf_path.parent      # Set root for content folder (usually OEBPS or EPUB)

    from functools import reduce
    import operator

    # Parse the Table of Contents (toc.xhtml) to obtain ordered chapter files
    toc_file = content_root / "toc.xhtml"  # Look for the navigation file
    if not toc_file.exists():
        print("Error: toc.xhtml not found.")
        sys.exit(1)

    toc_entries = parse_toc_xhtml(toc_file)  # Parse TOC to get file order
    ordered_files = []
    seen = set()
    for file, _, _ in toc_entries:  # De-duplicate and track order
        if file not in seen:
            seen.add(file)
            ordered_files.append(file)

    print("Ordered XHTML files from TOC:")
    for f in ordered_files:
        print(f"  - {f}")

    # Determine which files are part of chapters (from TOC) and which are not
    all_xhtml_files = {f.name for f in (content_root).glob("*.xhtml")}
    toc_xhtml_order = [file for file, _, _ in toc_entries]
    toc_used = set(toc_xhtml_order)

    front_matter = sorted(all_xhtml_files - toc_used)

    # --- Automatic back matter detection based on title keywords ---
    # Detect back matter files using title keywords to separate from main chapters
    back_keywords = ["references", "glossary", "index"]
    new_toc_xhtml_order = []
    back_matter = []

    for file in toc_xhtml_order:
        xhtml_path = content_root / file
        title = "Untitled"
        title = extract_title_from_xhtml(xhtml_path).lower()
        if any(keyword in title for keyword in back_keywords):
            back_matter.append(file)
        else:
            new_toc_xhtml_order.append(file)

    toc_xhtml_order = new_toc_xhtml_order
    toc_used = set(toc_xhtml_order)  # Update used set to exclude back matter
    # --------------------------------------------------------------

    # Build final ordered list with section labels for output filenames
    file_sections = []

    # Front matter: label as 00a, 00b, etc.
    for i, fname in enumerate(front_matter):
        label = f"00{chr(ord('a') + i)}"
        file_sections.append((label, [fname]))

    # Group XHTML files by chapter titles based on TOC structure
    title_to_files = {}
    for file, anchor, label in toc_entries:
        xhtml_path = content_root / file
        title = "Untitled"
        title = extract_title_from_xhtml(xhtml_path)
        title_to_files.setdefault(title, []).append(file)

    # Assign label numbers by title order
    title_list = list(title_to_files.keys())
    chapter_labels = []
    for idx, title in enumerate(title_list, start=1):
        label = f"{idx:02d}"
        file_sections.append((label, title_to_files[title]))

    # Back matter: label as 90, 91, 92, etc.
    for i, fname in enumerate(back_matter):
        label = f"{90 + i}"
        file_sections.append((label, [fname]))

    # Assign output filenames and write initial Markdown files without cross-link cleanup
    for label, group in file_sections:
        if not group:
            continue  # Skip empty groups to avoid unbound title error
        combined_md = []
        title = "Untitled"
        for fname in group:
            xhtml_path = content_root / fname
            title = extract_title_from_xhtml(xhtml_path)
            header = f"## {title}\n\n"
            md_temp = temp_dir / f"{xhtml_path.stem}.md"
            run_pandoc(xhtml_path, md_temp)
            with open(md_temp, "r", encoding="utf-8") as f:
                raw_md = f.read()
                md_content = clean_markdown_text(raw_md, chapter_map=None)  # Will update after chapter_map defined
            combined_md.append(header + md_content)
            md_temp.unlink()

        output_filename = output_dir / f"{label} - {title}.md"
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write("\n\n".join(combined_md))
        print(f"Wrote {output_filename.name}")

        conversion_log["chapters"].append({
            "index": label,
            "title": title,
            "source_files": group,
            "output_file": output_filename.name
        })

    print(f"EPUB extracted to: {temp_dir}")
    print(f"Markdown will be saved to: {output_dir}")

    # Build map from XHTML filename to final Markdown filename for cross-link conversion
    chapter_map = {src: entry["output_file"] for entry in conversion_log["chapters"] for src in entry["source_files"]}

    # Re-run cleanup with chapter_map to convert cross-file links properly and rewrite files
    for label, group in file_sections:
        if not group:
            continue  # Skip empty groups to avoid unbound title error
        combined_md = []
        title = "Untitled"
        for fname in group:
            xhtml_path = content_root / fname
            title = extract_title_from_xhtml(xhtml_path)
            header = f"## {title}\n\n"
            md_temp = temp_dir / f"{xhtml_path.stem}.md"
            run_pandoc(xhtml_path, md_temp)
            with open(md_temp, "r", encoding="utf-8") as f:
                raw_md = f.read()
                md_content = clean_markdown_text(raw_md, chapter_map)
            combined_md.append(header + md_content)
            md_temp.unlink()

        output_filename = output_dir / f"{label} - {title}.md"
        output_filename.parent.mkdir(parents=True, exist_ok=True)
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write("\n\n".join(combined_md))
        print(f"Wrote {output_filename.name}")

    # Generate Obsidian-compatible Table of Contents file
    generate_obsidian_toc(toc_entries, chapter_map, output_dir)

    log_path = LOG_DIR / f"{epub_file.stem}.json"  # Path for structured log output
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(conversion_log, f, indent=2)
    print(f"Log saved to: {log_path}")

    # Preview titles for each file in each chapter group for verification
    print("Section titles in each chapter group:")
    # We no longer have chapter groups, but can print by chapter number
    # Collect chapters by base chapter number
    chapters_dict = {}
    for label, group in file_sections:
        base_label = re.match(r"(\d+)", label)
        if base_label:
            chap_num = base_label.group(1)
        else:
            chap_num = label
        chapters_dict.setdefault(chap_num, []).extend(group)

    for chap_num in sorted(chapters_dict.keys()):
        print(f"  Chapter {chap_num}:")
        for fname in chapters_dict[chap_num]:
            fpath = content_root / fname
            title = extract_title_from_xhtml(fpath)
            print(f"    - {fname} → {title}")

if __name__ == "__main__":
    main()