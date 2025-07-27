# EPUB to Markdown Converter

This project extracts and converts EPUB files into Markdown format for use in Obsidian. It is designed for researchers (like myself) who need to annotate and reference book content for academic work, such as thesis writing.

## Project Goals

- Extract chapters and table of contents from `.epub` files
- Convert `.xhtml` files to `.md` using filenames and structure derived from `toc.xhtml`
- **Enhanced**: Extract book titles from copyright statements for better folder naming
- **Enhanced**: Apply proper Title Case formatting to all file names
- **Enhanced**: Robust subsection detection using comprehensive metadata extraction and anchor-based extraction
- Number files using logical patterns:
  - Front matter: `00a`, `00b`, `00c`, etc.
  - Chapters: `01.0`, `01.1`, `01.2`, ..., `06.0`, `06.1`, etc., where `.0` is the chapter heading and `.1+` are its subsections
  - Back matter: `90`, `91`, etc.
- Preserve images and ensure proper embedding in Markdown
- Update internal links and references for Obsidian-friendly navigation
- Automate this via a shell script (macOS Automator)
- Merge multipart chapters based on table of contents structure
- Display completion dialog on macOS with summary (files created, images copied, JSON log written, time elapsed)
- **Enhanced**: Comprehensive JSON logging with detailed metadata for troubleshooting

---

## 📦 EPUB Structure

An EPUB file is essentially a `.zip` archive containing:

```
/mimetype
/META-INF/container.xml
```

The content directory structure varies between EPUBs. Common variations include:

### **Structure A: OEBPS Root**
```
/OEBPS/
  ├── *.xhtml (chapters)
  ├── toc.ncx (navigation XML)
  ├── toc.xhtml (HTML-based TOC)
  ├── content.opf
  ├── images/
  ├── css/
  ├── fonts/
```

### **Structure B: OEBPS with HTML Subdirectory**
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

### **Structure C: EPUB Root**
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

The script automatically detects and handles all these variations by parsing `META-INF/container.xml` to locate the correct content root.

---

## 🛠️ Automation Workflow

### 1. Input

- Triggered on an `.epub` file using macOS “Run Shell Script” automation
- Output is always saved to a designated directory (e.g. `~/Documents/EpubNotes/`)

### 2. Process Outline

1. **Create Output Folder**  
   - **Enhanced**: Folder is named after the book title extracted from copyright statement (e.g., `Using Case Study in Education Research/`)
   - Falls back to EPUB filename if copyright title not found

2. **Extract EPUB**  
   - Use `unzip` or `bsdtar` to unpack the `.epub` to a temp directory

3. **Locate Content Directory**  
   - Parse `META-INF/container.xml` to locate `content.opf` root directory
   - **Enhanced**: Handles multiple EPUB structures (`OEBPS/`, `OEBPS/html/`, `EPUB/`)

4. **Copy Assets**  
   - If an `/images/` directory exists, it is copied to the output folder  
   - The final summary dialog will show ✅ if images were found, or ⛔ if no images were available

5. **Enhanced Metadata Extraction**  
   - **New**: Extract comprehensive metadata from each XHTML file
   - **Enhanced**: Search for IDs on ANY HTML tag (not just `<section>` or `<div>`)
   - **Enhanced**: Detect chapter numbers, level-based subsections, frontmatter, and backmatter
   - **Enhanced**: Apply Title Case formatting to all extracted titles
   - **Enhanced**: Extract subsections from anchor-based content within chapter files

6. **Convert XHTML to Markdown**  
   For each `.xhtml` chapter:  
   - Extract `<title>` from `<head>` section and apply Title Case
   - **Enhanced**: Use metadata-driven structure instead of TOC patterns alone
   - **Enhanced**: Create separate files for subsections found within chapter files
   - Rename output Markdown file based on metadata structure:
     - Front matter → `00a - Preface.md`, `00b - Introduction.md`, etc.
     - Chapters → `01.0 - Chapter Title.md` and `01.1 - Subsection Title.md`, `01.2`, etc.
     - **Enhanced**: Subsections are properly grouped with their parent chapters
     - This ensures proper numeric sorting in Finder and Obsidian
   - Convert XHTML body content to Markdown using `pandoc`  
   - A separate function applies post-processing cleanup rules

7. **Update Internal Links**  
   - Convert internal links to Obsidian-friendly `[[Note Name#Heading]]` format  
   - Strip `.md` extension and normalize anchor text

8. **Process TOC**  
   - **Enhanced**: Generate Obsidian-compatible TOC with proper file links
   - **Enhanced**: Prevent duplicate TOC files by excluding original `toc.xhtml` from content processing
   - TOC structure generated in Markdown follows Obsidian format with nesting and chapter/section hierarchy  
   - Filters out duplicate entries and multilingual fallbacks  
   - Convert nav links to Obsidian `[[Page Title]]` format

9. **Enhanced JSON Logging**  
   - **New**: Generate comprehensive JSON logs with timestamped filenames
   - **Enhanced**: Include detailed metadata about chapter grouping, file structure, and processing results
   - **Enhanced**: Log warnings, errors, and processing statistics for troubleshooting
   - **Enhanced**: Include book title, content root used, and EPUB structure type

10. **Clean Up**
    - Remove temporary extraction directory

11. **Post-Processing Cleanup**  
    - Clean up Markdown using custom Python rules:
      - Remove Pandoc-generated div blocks (`:::`)
      - Strip metadata spans like `{#id .class}`
      - Remove same-file anchor links (e.g. `#span_00123`)
      - Normalize heading levels (H1 for title, H2–H6 for internal sections)
      - Convert inline `<q>` tags to Obsidian-style block quotes (`>`)
      - Collapse bracketed reference clusters into single paragraphs
      - Clean up excessive line breaks
      - Normalize reference sections
      - Rewrite internal file links to Obsidian format

---

## 🔧 Requirements

- macOS (with Automator)
- Bash or zsh shell
- Python 3.x (for filename/title mapping and link logic)
- `pandoc` (called via CLI, no wrapper like pypandoc needed)

Install with:
```bash
brew install pandoc
```

Required (Python):
```bash
pip install beautifulsoup4 lxml
```

---

## 🧠 Notes

- **Enhanced**: The script now handles various EPUB structures and metadata patterns robustly
- **Enhanced**: Book titles are extracted from copyright statements for better folder naming
- **Enhanced**: All titles are converted to proper Title Case formatting
- **Enhanced**: Subsection detection works across different HTML tag types (h1, h2, p, div, section, etc.) and handles anchor-based subsections within chapter files
- The `<title>` tag is assumed to contain the correct chapter name
- Titles will be slugified for use in internal link resolution
- Chapters may span multiple .xhtml files (e.g., chapter7, chapter7a, chapter7b) — these will be merged based on metadata structure
- The cleanup stage uses a dedicated Python function that can be adjusted as needed for formatting edge cases.
- The script uses the full path to Pandoc (`/opt/homebrew/bin/pandoc`) to ensure compatibility with Automator workflows.
- Decimal-style filenames ensure correct Obsidian navigation and file sorting (e.g., `06.0`, `06.1`, `06.2`). Front matter uses alphabetic suffixes (e.g., `00a`) and back matter uses numeric IDs (`90`, `91`, ...).
- **Enhanced**: Comprehensive JSON logging provides detailed troubleshooting information

---

## 🚀 Recent Improvements ✅

- ✅ **Enhanced Metadata Extraction**: Robust detection of chapter numbers, subsections, and content types
- ✅ **Title Case Formatting**: Proper capitalization of all file names and titles
- ✅ **Book Title Extraction**: Automatic extraction from copyright statements for better folder naming
- ✅ **Comprehensive JSON Logging**: Detailed logs with timestamps for troubleshooting
- ✅ **Duplicate TOC Prevention**: Prevents creation of multiple TOC files
- ✅ **Multi-EPUB Structure Support**: Handles various internal folder structures
- ✅ **Robust Subsection Detection**: Works across different HTML tag types and metadata patterns, including anchor-based subsections within chapter files

## 🔮 Future Improvements

- Optional metadata frontmatter (e.g., `title`, `chapter`, `source`)
- YAML header for Obsidian compatibility (partially implemented)
- Extend post-processing rules for quotes, footnotes, and special formatting
- GUI wrapper for drag-and-drop usage

---

## ✅ Completion Dialog

After the script finishes processing, a macOS dialog box will appear with:

- ✅ Status of each major step (Pandoc conversion, Markdown output, Cleanup, JSON log)
- 📄 Total Markdown files created
- 🖼️ Images copied (✅ or ⛔)
- 🕒 Total execution time
- Dialog remains visible until dismissed by the user

## 📊 Enhanced Output

The script now generates:

- **📁 Properly Named Folders**: Based on book title from copyright statement
- **📄 Title Case Files**: All files use proper Title Case formatting (e.g., "Chapter 1" not "CHAPTER 1")
- **🔗 Single TOC File**: Only `00 - Table of Contents.md` (no duplicates)
- **📋 Comprehensive JSON Logs**: Timestamped logs with detailed metadata for troubleshooting
- **📚 Proper Subsection Grouping**: Subsections correctly numbered and grouped with parent chapters
- **🔧 Filename Length Management**: Automatic truncation of long titles to prevent filesystem errors

## 🔍 Subsection Extraction Capabilities

The script now handles complex EPUB structures where subsections are embedded as anchors within chapter files:

- **Anchor-Based Detection**: Identifies subsections using level IDs (e.g., `level1_000001`, `level2_000002`)
- **Dynamic File Creation**: Creates separate XHTML files for each subsection before conversion
- **Proper Numbering**: Assigns decimal numbering (01.1, 01.2, 01.3, etc.) to subsections
- **Content Preservation**: Extracts full subsection content while maintaining structure
- **Robust Metadata**: Handles various subsection ID patterns and content types

**Example Results**: A recent test EPUB with 13 chapters generated 136 total files (including 123 subsections), with proper decimal numbering and grouping.