#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess
from pathlib import Path
from bs4 import BeautifulSoup
import zipfile
import shutil

# === Constants ===
OUTPUT_ROOT = Path("/Users/stephenelms/Documents/Epub to Md")

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

    # Create temporary extraction directory
    temp_dir = Path("/tmp") / f"epub_extract_{epub_file.stem}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    # Extract EPUB contents
    extract_epub(epub_file, temp_dir)

    # TODO: Parse OPF file and TOC to determine reading order and merge chapters

    # TODO: Convert extracted XHTML files to Markdown using run_pandoc()

    print(f"EPUB extracted to: {temp_dir}")
    print(f"Markdown will be saved to: {output_dir}")

if __name__ == "__main__":
    main()
