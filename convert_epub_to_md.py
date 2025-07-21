#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup
import zipfile
import shutil
import json

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
    container_xml = container_path / "META-INF" / "container.xml"
    with open(container_xml, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, "xml")
    return container_path / soup.find("rootfile")["full-path"]

def run_pandoc(input_file: Path, output_file: Path):
    """Converts a single XHTML file to Markdown using Pandoc."""
    subprocess.run([
        "pandoc",
        str(input_file),
        "-f", "html",
        "-t", "markdown",
        "-o", str(output_file)
    ], check=True)

def parse_toc_xhtml(toc_path: Path):
    """Parses toc.xhtml and returns a list of (filename, anchor, label) in TOC order."""
    from bs4 import BeautifulSoup
    with open(toc_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'lxml')

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

def group_chapter_files(ordered_files):
    """Groups files like chapter7.xhtml, chapter7a.xhtml, etc. by shared base name."""
    from collections import defaultdict
    import re

    # Normalize by stripping suffix like 'a', 'b', 'c' from base name
    chapter_groups = defaultdict(list)
    for fname in ordered_files:
        # Remove path and extension
        base = Path(fname).stem
        # Strip trailing letter suffixes (e.g., chapter7a -> chapter7)
        match = re.match(r"(.*?chapter\d+)", base)
        if match:
            group_key = match.group(1)
        else:
            group_key = base
        chapter_groups[group_key].append(fname)

    return list(chapter_groups.values())

def extract_title_from_xhtml(xhtml_path: Path) -> str:
    """Extracts the <title> from an XHTML file."""
    with open(xhtml_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'lxml')
    title_tag = soup.find('title')
    return title_tag.get_text(strip=True) if title_tag else "Untitled"

# === CLI ===

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Convert EPUB to Markdown (Obsidian-ready)")
    parser.add_argument("epub_file", type=Path, help="Path to the .epub file")
    args = parser.parse_args()

    epub_file = args.epub_file.resolve()
    if not epub_file.exists():
        print(f"File not found: {epub_file}")
        sys.exit(1)

    # Create output directory
    output_dir = OUTPUT_ROOT / epub_file.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    conversion_log = {
        "epub": epub_file.name,
        "output_dir": str(output_dir),
        "chapters": []
    }

    # Create temporary extraction directory
    temp_dir = Path("/tmp") / f"epub_extract_{epub_file.stem}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    # Extract EPUB contents
    extract_epub(epub_file, temp_dir)

    # Locate and parse TOC
    toc_file = temp_dir / "OEBPS" / "toc.xhtml"
    if not toc_file.exists():
        print("Error: toc.xhtml not found.")
        sys.exit(1)

    toc_entries = parse_toc_xhtml(toc_file)
    ordered_files = []
    seen = set()
    for file, _, _ in toc_entries:
        if file not in seen:
            seen.add(file)
            ordered_files.append(file)

    print("Ordered XHTML files from TOC:")
    for f in ordered_files:
        print(f"  - {f}")

    # Group chapters (including multipart ones)
    chapter_groups = group_chapter_files(ordered_files)

    print("Grouped chapter files:")
    for idx, group in enumerate(chapter_groups, start=1):
        print(f"  Chapter {idx:02d}: {group}")

    for idx, group in enumerate(chapter_groups, start=1):
        combined_md = []
        for fname in group:
            xhtml_path = temp_dir / "OEBPS" / fname
            title = extract_title_from_xhtml(xhtml_path)
            header = f"# {title}\n\n"
            md_temp = temp_dir / f"{xhtml_path.stem}.md"
            run_pandoc(xhtml_path, md_temp)
            with open(md_temp, "r", encoding="utf-8") as f:
                md_content = f.read()
            combined_md.append(header + md_content)
            md_temp.unlink()  # Remove temp .md file

        # Save the final combined file with padded chapter number
        output_filename = output_dir / f"{idx:02d} - {title}.md"
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write("\n\n".join(combined_md))
        print(f"Wrote {output_filename.name}")

        conversion_log["chapters"].append({
            "index": idx,
            "title": title,
            "source_files": group,
            "output_file": output_filename.name
        })

    print(f"EPUB extracted to: {temp_dir}")
    print(f"Markdown will be saved to: {output_dir}")

    log_path = LOG_DIR / f"{epub_file.stem}.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(conversion_log, f, indent=2)
    print(f"Log saved to: {log_path}")

if __name__ == "__main__":
    main()

    # Preview titles for each file in each chapter group
    print("Section titles in each chapter group:")
    for idx, group in enumerate(chapter_groups, start=1):
        print(f"  Chapter {idx:02d}:")
        for fname in group:
            fpath = temp_dir / "OEBPS" / fname
            title = extract_title_from_xhtml(fpath)
            print(f"    - {fname} → {title}")