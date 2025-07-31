# EPUB to Markdown Converter - Technical Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Quick Start](#quick-start)
3. [Architecture Evolution](#architecture-evolution)
4. [Current Architecture](#current-architecture)
5. [Usage Guide](#usage-guide)
6. [Development Roadmap](#development-roadmap)
7. [Testing Strategy](#testing-strategy)
8. [Quality Assurance](#quality-assurance)
9. [Performance Considerations](#performance-considerations)
10. [Troubleshooting](#troubleshooting)
11. [API Reference](#api-reference)
12. [Deployment and Distribution](#deployment-and-distribution)

## Project Overview

The EPUB to Markdown Converter is a sophisticated Python-based tool designed for academic researchers who need to convert EPUB books into Obsidian-compatible Markdown format. The project has evolved through multiple architectural phases to handle complex academic book structures and provide superior conversion quality.

##### Github Repository
[https://github.com/sjelms/EPUB-to-Markdown-Converter](https://github.com/sjelms/EPUB-to-Markdown-Converter)

### **Dependencies and Environment Setup**

To run or develop this script, the following external Python libraries must be installed:

```bash
pip install beautifulsoup4 lxml markdownify
```

- **BeautifulSoup4**: For parsing XML and XHTML documents
- **lxml**: A high-performance parser backend for BeautifulSoup
- **markdownify**: For robust conversion of HTML to Markdown

### **System Requirements**
- Python 3.8+
- macOS (primary target), Linux, Windows
- Pandoc (optional, for fallback conversion)
- 4GB+ RAM recommended for large EPUBs

## Quick Start

### **Basic Usage**
```bash
python convert_epub_to_md.py input.epub --output /path/to/output
```

### **Advanced Usage** ✅ **FULLY INTEGRATED**
```bash
python convert_epub_to_md.py input.epub \
  --output /path/to/output \
  --obsidian \
  --skip-images
```

**All CLI flags are now fully functional:**
- `--obsidian`: Enables Obsidian-specific formatting
- `--skip-images`: Skips image copying to assets folder
- `--output`: Specifies custom output directory

### **Testing Features**
```bash
# Test single XHTML file
python convert_epub_to_md.py --test-single chapter1.xhtml

# Test cleanup on existing Markdown
python convert_epub_to_md.py --test-cleanup output.md
```

## Architecture Evolution

### Phase 1: Heuristic-Based TOC Parsing (Legacy)

The first version relied on filename patterns and parsing of `toc.xhtml` to infer book structure. No OPF or spine parsing was performed.

**Limitations:**
- Failed on books without a valid `toc.xhtml`
- Could not resolve spine order for non-linear books
- Incorrect image and link handling due to path assumptions

### Phase 2: TOC-Driven Structured Parsing (Interim)

This version improved structural inference by more rigorously parsing `toc.xhtml`, including nested sections and anchor references.

**Limitations:**
- Still failed on malformed or missing TOCs
- Did not use OPF or manifest spine for true reading order
- Relied heavily on XHTML filename order rather than package metadata

### Phase 3: Manifest & Spine-Based Pipeline (Current) ✅ **UPDATED**

The current architecture uses the EPUB standard's `package.opf` as the canonical source of content structure. This approach is fully standards-compliant and works for both simple and complex EPUBs.

**Recent Improvements:**
- **Fixed data structure consistency** - resolved manifest map vs list structure mismatch
- **Removed dead code** - eliminated 451 lines of unused complex functions
- **Integrated missing features** - image copying, BibTeX lookup, CLI argument handling
- **Enhanced type safety** - improved function signatures and parameter handling

**Benefits:**
- Works on malformed TOCs or missing `toc.xhtml`
- Maintains correct reading order as intended by publisher
- Robust path resolution supports nested content folders and assets
- Clean, maintainable codebase with no architectural conflicts

## Current Architecture

### Core Components

#### 1. **EPUB Extraction Layer**
```python
def extract_epub(epub_path: Path, extract_to: Path) -> tuple[Path, Path] | None
```
- Handles ZIP extraction with error handling
- Returns content root and OPF path
- Supports multiple EPUB structures (OEBPS, OEBPS/html, EPUB)

#### 2. **Structure Detection** ✅ **UPDATED**
```python
def build_manifest_map(opf_soup, opf_path: Path) -> list[dict]
def assign_manifest_structure(manifest_map: list[dict]) -> list[dict]
```
- Parses OPF manifest and spine
- Returns structured list of manifest items with classification
- Assigns sequential labels (00a, 01.0, 900, etc.)
- Handles frontmatter, chapters, and backmatter classification

#### 3. **Three-Phase Conversion Pipeline**
```python
def clean_markdown_text(md_content: str, chapter_map=None) -> str
```

**Phase 1: HTML Pre-processing**
- BeautifulSoup structural cleanup
- EPUB-specific artifact removal
- Image path normalization
- Chapter title structure fixes

**Phase 2: Markdownify Conversion**
- Superior HTML-to-Markdown conversion
- Academic book optimized settings
- Clean semantic output

**Phase 3: Post-processing Cleanup**
- Academic book pattern fixes
- Link and image repair
- Obsidian compatibility optimization
- Typographic improvements

#### 4. **Metadata Extraction**
```python
def extract_book_metadata_from_copyright(content_root: Path) -> dict | None
def extract_book_title_from_copyright(content_root: Path) -> str | None
```
- Copyright statement parsing
- RNIB_COPYRIGHT_LEGALESE format support
- Fallback to fulltitle page extraction
- Title and author extraction

#### 5. **BibTeX Integration** ✅ **INTEGRATED**
```python
def find_bibtex_entry_by_title_and_authors(title: str, authors: str, bibtex_path: Path) -> dict | None
def parse_bibtex_authors(author_string: str) -> list
```
- **Automatic lookup** - integrated into main conversion pipeline
- Fuzzy title matching with enhanced accuracy
- Author name parsing and normalization
- Citation key extraction for YAML headers
- **Fallback handling** - graceful degradation when no match found

### File Organization System

#### Naming Convention
- **Frontmatter**: `00a`, `00b`, `00c` (alphabetic)
- **Chapters**: `01.0`, `01.1`, `01.2` (decimal with subsections)
- **Backmatter**: `900`, `901`, `902` (numeric, scalable for large books)

#### Output Directory Structure (Example)
```
📚 /output/Example Book Title/
├── 00 - TOC for Example Book Title.md
├── 00a - Title Page.md
├── 00b - Copyright.md
├── 00c - Preface.md
├── 01.0 - Chapter 1 Introduction.md
├── 01.1 - Background Concepts.md
├── 01.2 - Related Work.md
├── 02.0 - Chapter 2 Methods.md
├── 02.1 - Data Collection.md
├── 02.2 - Analysis Techniques.md
├── 03.0 - Chapter 3 Results.md
├── 03.1 - Case Study A.md
├── 03.2 - Case Study B.md
├── 900 - References.md
├── 901 - Index.md
├── assets/
│   ├── image1.jpg
│   └── diagram.svg
├── Example Book Title_log.json
```

**Note:** Image copying is now automatically integrated and can be controlled via `--skip-images` CLI flag.
```

### EPUB Structure Variations

The content directory structure varies between EPUBs. Common variations include:

**Structure A: OEBPS Root**
```
/OEBPS/
├── *.xhtml (chapters)
├── toc.ncx (navigation XML)
├── toc.xhtml (HTML-based TOC)
├── content.opf
├── images/
├── css/
└── fonts/
```

**Structure B: OEBPS with HTML Subdirectory**
```
/OEBPS/
├── html/
│   ├── *.xhtml (chapters)
│   └── toc.xhtml (HTML-based TOC)
├── toc.ncx (navigation XML)
├── content.opf
├── images/
├── css/
└── fonts/
```

**Structure C: EPUB Root**
```
/EPUB/
├── *.xhtml (chapters)
├── toc.ncx (navigation XML)
├── toc.xhtml (HTML-based TOC)
├── content.opf
├── images/
├── css/
└── fonts/
```

## Usage Guide

### Command-Line Interface

The script accepts the following arguments:

- **`input`** (Required): Path to the source `.epub` file
- **`--output`** (Optional): Output directory (default: `~/Documents/Epub to Md`)
- **`--skip-images`** (Optional): Skip copying image files
- **`--obsidian`** (Optional): Enable Obsidian-specific formatting
- **`--test-single`** (Optional): Test single XHTML file conversion
- **`--test-cleanup`** (Optional): Test post-processing on existing Markdown

### Core Orchestration Logic

The main `convert_book` function orchestrates the entire pipeline:

1. **Setup**: Create temporary directory for EPUB extraction
2. **Map Creation**: Locate OPF file and build manifest map
3. **Asset Handling**: Copy images to assets subfolder
4. **Content Conversion Loop**: Process each spine file through three-phase conversion
5. **Reporting**: Generate JSON log and display summary dialog
6. **Cleanup**: Remove temporary directory

### YAML Header Generation

The script generates Obsidian-compatible YAML headers:

```yaml
---
title: {Title}
chapter: {01 - Chapter Name}
toc: "[[00 - TOC for {Title}]]"
author-1: "[[Name]]"
author-2: "[[Name]]"
citation-key: "[[@Key]]"
---
```

### **Markdown Post-Processing and Cleanup Rules**

This section details the automated cleanup rules applied to the raw Markdown generated from XHTML content. The primary goal is to remove EPUB-specific artifacts, normalize formatting, and optimize the output for use in Obsidian. The implementation relies on a series of regular expression substitutions performed by the `post_process_markdown` function.

---

#### **Structural and Whitespace Cleanup**

These rules address spacing, empty elements, and general structural integrity.

- **Normalize Newlines:** Collapses three or more consecutive newlines into a maximum of two. This ensures consistent spacing between paragraphs without excessive empty space.
- **Remove Empty Headings:** Deletes any heading lines (e.g., `### `) that are not followed by any text.
- **Remove Leading/Trailing Whitespace:** Strips all whitespace from the beginning and end of the entire document.

---

#### **EPUB Artifact Removal**

This category focuses on removing elements that are specific to the EPUB format and are not semantically useful in Markdown.

- **Remove Page Number Anchors:** Eliminates empty anchor tags often used to mark page breaks in the source EPUB (e.g., `<a id="page_31"></a>`).
- **Remove `<span>` Tags:** Strips `<span>` and `</span>` tags, which are often used for stylistic formatting in EPUBs but typically serve no purpose in Markdown.
- **Remove XML Declarations:** Deletes any residual XML declaration headers (e.g., `<?xml ... ?>`) that may have been inadvertently included in the Markdown output.

---

#### **Link and Footnote Formatting for Obsidian**

These rules are designed to convert standard HTML links and footnote structures into formats that are either more readable in Markdown or optimized for Obsidian's features.

- **Simplify Internal Links:** Converts internal XHTML links (e.g., `[Chapter 1](chapter1.xhtml#section1)`) into simplified text (e.g., `Chapter 1`). This removes dead links that point to files that no longer exist in the same way.
- **Format Footnotes for Obsidian:**
  - Identifies footnote reference links, which often appear as bracketed superscripts (e.g., `[1]`, `[a]`) pointing to a footnote definition.
  - Reformats these into Obsidian-compatible inline footnotes using the `[^...]:` syntax. For example, `[1]` becomes `[^1]`, and the corresponding footnote definition `1. Some note text.` is converted to `[^1]: Some note text.`.
- **Convert Image Links to Obsidian Embeds:**
  - Targets standard Markdown image links like `![alt-text](path/to/image.jpg)`.
  - Converts them into the Obsidian wikilink embed format, `![[path/to/image.jpg]]`, for seamless rendering within Obsidian vaults.

---

#### **Content and Table Formatting**

- **Standardize Table Formatting:** Finds and replaces the HTML `<table>`, `<tr>`, `<th>`, and `<td>` tags with their Markdown pipe-table equivalents. It includes logic to correctly construct the header row and the separator line (`|---|`).
- **Clean Up Bold/Italic Markers:** Ensures there is no extraneous whitespace immediately following opening bold (`**`) or italic (`*`) markers. For example, `** text**` becomes `**text**`.

## Development Roadmap

### ✅ **COMPLETED**

#### 1. Data Structure Consistency ✅
- [x] Fixed manifest map vs list structure mismatch
- [x] Updated function signatures for consistency
- [x] Resolved runtime errors from structural conflicts

#### 2. Dead Code Removal ✅
- [x] Removed 451 lines of unused complex functions
- [x] Eliminated architectural confusion (TOC vs Manifest)
- [x] Cleaned up abandoned approaches and legacy code
- [x] Reduced file size by 26% (1741 → 1290 lines)

#### 3. Missing Integration Points ✅
- [x] Integrated image copying logic into main pipeline
- [x] Added automatic BibTeX lookup and integration
- [x] Connected all CLI arguments to conversion function
- [x] Ensured all defined features are actually used

### Immediate Fixes (Priority 1)

#### 1. Type Safety Improvements
- [ ] Fix BeautifulSoup import issues
- [ ] Add proper type annotations for all functions
- [ ] Implement consistent error handling
- [ ] Add type checking for critical operations

#### 2. Code Cleanup
- [x] Consolidate duplicate functionality
- [x] Standardize function signatures
- [x] Organize imports consistently
- [x] Remove legacy code paths

#### 3. Architecture Unification
- [x] Choose single approach (TOC vs Manifest)
- [x] Refactor to consistent architecture
- [x] Implement proper abstraction layers
- [ ] Add comprehensive testing

### Medium-term Improvements (Priority 2)

#### 1. Enhanced Error Handling
- [ ] Implement structured error reporting
- [ ] Add validation for all input parameters
- [ ] Create error recovery mechanisms
- [ ] Add detailed logging throughout pipeline

#### 2. Performance Optimization
- [ ] Implement parallel processing for large books
- [ ] Add caching for repeated operations
- [ ] Optimize memory usage for large files
- [ ] Add progress reporting

#### 3. Configuration System
- [ ] Add configuration file support
- [ ] Implement customizable conversion rules
- [ ] Add plugin system for custom processors
- [ ] Create preset configurations for different book types

### Long-term Enhancements (Priority 3)

#### 1. Advanced Features
- [ ] Support for complex academic formatting
- [ ] Enhanced footnote handling
- [ ] Bibliography integration
- [ ] Cross-reference resolution

#### 2. User Interface
- [ ] GUI wrapper for non-technical users
- [ ] Drag-and-drop interface
- [ ] Real-time preview
- [ ] Batch processing interface

#### 3. Integration Features
- [ ] Direct Obsidian vault integration
- [ ] Zotero bibliography sync
- [ ] Academic database integration
- [ ] Export to other formats (LaTeX, Word)

### Large EPUB Conversion Enhancements (Priority 4)

For EPUBs > 50 MB, the following optimizations are planned:

**Key Risk Factors:**
- Large XHTML files (100K+ lines)
- RAM load during parse (full DOM trees)
- Image density (hundreds of high-resolution figures)
- Temp file bloat (500+ assets)
- Markdown cleanup post-processing

**Technical Strategy:**
- Stream-based parsing using `lxml.iterparse()`
- Process elements as stream (one tag at a time)
- Clear tags after processing to free memory
- Implement chunked processing for large files

## Testing Strategy

### Current Testing Capabilities
- `--test-single`: Single XHTML file conversion
- `--test-cleanup`: Post-processing validation
- `--xhtml-to-md`: Direct conversion utility

### Planned Testing Improvements
- [ ] Unit tests for all core functions
- [ ] Integration tests for full pipeline
- [ ] Performance benchmarking
- [ ] Regression testing for academic books
- [ ] Automated quality assessment

## Quality Assurance

### Code Quality Standards
- [ ] Type annotations for all functions
- [ ] Comprehensive docstrings
- [ ] Error handling for all operations
- [ ] Consistent naming conventions
- [ ] Modular design principles

### Output Quality Standards
- [ ] Clean, readable Markdown
- [ ] Proper heading hierarchy
- [ ] Functional internal links
- [ ] Correct image references
- [ ] Obsidian compatibility

## Performance Considerations

### Current Performance Characteristics
- Single-threaded processing
- Memory usage scales with file size
- No caching of intermediate results
- Sequential file processing

### Optimization Opportunities
- Parallel processing for independent files
- Streaming processing for large files
- Caching of parsed OPF data
- Incremental processing for updates

## Troubleshooting

### Common Issues

#### 1. **"File not found" errors**
- Ensure EPUB file is not corrupted
- Check file permissions
- Verify path contains no special characters

#### 2. **Memory errors with large EPUBs**
- Close other applications to free RAM
- Consider using `--skip-images` flag
- Process smaller EPUBs first

#### 3. **Malformed output**
- Check if EPUB has valid OPF structure
- Try `--test-single` on problematic files
- Review JSON log for specific errors

#### 4. **Missing images**
- Verify EPUB contains image files
- Check assets folder permissions
- Review image path resolution in log

### Debug Mode
```bash
# Enable verbose logging
python convert_epub_to_md.py input.epub --output /path/to/output --verbose
```

### **Post-Conversion Reporting: JSON Log and Summary Dialog**

To provide a comprehensive and user-friendly summary of each conversion task, the script incorporates a two-part reporting system that executes only after all processing is complete. This system generates a detailed, machine-readable JSON log and displays a human-readable summary dialog box.

---

#### **JSON Log File**

The primary goal of the JSON log is to create a persistent, structured record of the entire conversion process. This is invaluable for debugging, tracking changes across conversion runs, or programmatic analysis of batch operations.

- **Process**
    Throughout its execution, the script collects key metrics and metadata in a Python dictionary. This includes timestamps, file paths, counts of processed files, and a list of any warnings generated. Upon completion of all other tasks, this dictionary is serialized into a JSON file and saved in the root of the main output directory.
- **Data Schema**
    The JSON log contains a detailed set of key-value pairs, including:
    - `book_title`: The title of the processed EPUB.
    - `start_time_utc` / `end_time_utc`: ISO 8601 timestamps marking the beginning and end of the operation.
    - `epub_path` / `output_dir`: The source and destination paths for the conversion.
    - `xhtml_files_in_epub`: A list of all XHTML files found in the source EPUB.
    - `total_output_files`: The total number of Markdown files generated.
    - `images_moved`: A boolean flag indicating if image files were copied.
    - `warnings`: A list of any non-critical issues encountered during the process.

---

#### **Summary Dialog Box**

To provide immediate feedback to the user, the script displays a graphical summary dialog box upon completion.

- **Process**
    This feature uses Python's built-in **`tkinter`** library to create a simple, cross-platform message window. After the main conversion logic is finished and the JSON log has been saved, the script formats the key statistics from the report data into a summary string. This string is then presented in the dialog box, and the script's execution pauses until the user manually closes the window.

---

#### **Execution Trigger**

The entire reporting process is designed as the final step of the conversion pipeline.

- **Implementation**
    The function calls to generate the JSON log and display the summary dialog are placed at the end of the main `convert_book` function, typically within a `finally` block. This ensures that a report is generated even if an unexpected error occurs during the conversion. This placement guarantees that all metrics, such as the `end_time_utc` and the final file counts, are accurate and reflect the completed state of the operation.

### Log Analysis
The JSON log file contains detailed information about:
- Processing timestamps
- File counts and paths
- Warning messages
- Error details
- Performance metrics

## API Reference

### Core Functions

#### `convert_book(epub_path: Path, output_dir_base: Path, bibtex_data: dict | None = None, use_obsidian_format: bool = True, skip_images: bool = False)` ✅ **UPDATED**
Main conversion function using the manifest-based pipeline.

**Parameters:**
- `epub_path`: Path to EPUB file
- `output_dir_base`: Base output directory
- `bibtex_data`: Optional BibTeX metadata (auto-lookup if None)
- `use_obsidian_format`: Enable Obsidian formatting
- `skip_images`: Skip image copying to assets folder

**Returns:** Dictionary with conversion results

**Features:**
- Automatic BibTeX lookup when metadata not provided
- Integrated image copying with skip option
- Complete CLI argument integration

#### `extract_epub(epub_path: Path, extract_to: Path) -> tuple[Path, Path] | None`
Extract EPUB contents and return content root and OPF path.

#### `build_manifest_map(opf_soup, opf_path: Path) -> list[dict]` ✅ **UPDATED**
Build manifest map from OPF spine and manifest structure.

#### `assign_manifest_structure(manifest_map: list[dict]) -> list[dict]` ✅ **UPDATED**
Assign structured output labels to manifest items.

#### `clean_markdown_text(md_content: str, chapter_map=None) -> str`
Three-phase conversion pipeline for XHTML to Markdown.

### Utility Functions

#### `extract_book_metadata_from_copyright(content_root: Path) -> dict | None`
Extract book metadata from copyright statements.

#### `copy_images(manifest_items: list[dict], assets_dir: Path)` ✅ **INTEGRATED**
Copy image files from EPUB to assets directory.

#### `extract_book_metadata_from_copyright(content_root: Path) -> dict | None`
Extract book metadata from copyright statements.

#### `safe_filename(title: str) -> str`
Sanitize title for use as filename.

## Deployment and Distribution

### Current Distribution
- Single Python script
- Manual dependency installation
- macOS-focused automation

### Future Distribution Options
- [ ] PyPI package
- [ ] Standalone executable
- [ ] Docker container
- [ ] Homebrew formula

## Monitoring and Logging

### Current Logging ✅ **ENHANCED**
- Basic print statements with informative progress messages
- JSON log files with comprehensive conversion metadata
- Error reporting with graceful fallbacks
- BibTeX lookup status reporting
- Image copying progress indicators

### Enhanced Logging Plan
- [ ] Structured logging with levels
- [ ] Performance metrics
- [ ] Error tracking
- [ ] Usage analytics

## Security Considerations

### Input Validation
- [ ] Validate EPUB file integrity
- [ ] Sanitize file paths
- [ ] Check for malicious content
- [ ] Validate XML structure

### Output Safety
- [ ] Safe filename generation
- [ ] Path traversal prevention
- [ ] Content sanitization
- [ ] Resource usage limits

## Documentation Standards

### Code Documentation
- [ ] Function-level docstrings
- [ ] Type annotations
- [ ] Example usage
- [ ] Error conditions

### User Documentation
- [ ] Installation instructions
- [ ] Usage examples
- [ ] Troubleshooting guide
- [ ] Configuration reference

## Conclusion

The EPUB to Markdown Converter has evolved from a simple extraction tool to a sophisticated academic book processing pipeline. The current focus should be on:

1. **Immediate**: Fixing type safety and code structure issues
2. **Short-term**: Unifying the architecture and improving error handling
3. **Long-term**: Adding advanced features and user interface improvements

The project demonstrates the complexity of handling real-world academic book formats and the importance of robust, well-tested conversion pipelines for research workflows.
