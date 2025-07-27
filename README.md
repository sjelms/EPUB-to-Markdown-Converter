# EPUB to Markdown Converter

This project extracts and converts EPUB files into Markdown format for use in Obsidian. It is designed for researchers (like myself) who need to annotate and reference book content for academic work, such as thesis writing.

## Project Goals

- Extract chapters and table of contents from `.epub` files
- Convert `.xhtml` files to `.md` using filenames and structure derived from `toc.xhtml`
- **Enhanced**: Extract book titles from copyright statements for better folder naming
- **Enhanced**: Apply proper Title Case formatting to all file names
- **Enhanced**: Robust subsection detection using comprehensive metadata extraction and anchor-based extraction
- **NEW**: Three-phase conversion approach using markdownify for superior HTML-to-Markdown conversion
- **NEW**: Comprehensive academic book compatibility with specialized link and formatting fixes
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

- Triggered on an `.epub` file using macOS "Run Shell Script" automation
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
   - **Enhanced**: Use table of contents as primary source of truth for file grouping
   - **Enhanced**: Prevents over-extraction by treating anchor-based subsections as part of their parent files
   - **Enhanced**: Extract comprehensive metadata from each XHTML file for validation
   - **Enhanced**: Apply Title Case formatting to all extracted titles
   - **Enhanced**: Sequential numbering for frontmatter (00a, 00b, 00c) and chapters (01.0, 01.1, 01.2)

6. **NEW: Three-Phase XHTML to Markdown Conversion**  
   **Phase 1: HTML Pre-processing**
   - Parse XHTML with BeautifulSoup for structural cleanup
   - Remove XML declarations and processing instructions
   - Unwrap `<span>` and `<div>` tags that cause unwanted line breaks
   - Remove EPUB-specific attributes and classes
   - Consolidate multiple `<br>` tags
   - Remove empty paragraphs
   
   **Phase 2: Markdownify Conversion**
   - Use `markdownify` library for superior HTML-to-Markdown conversion
   - Configure for academic book formatting (ATX headings, proper emphasis, bullet lists)
   - Strip script and style tags
   
   **Phase 3: Post-processing Cleanup**
   - Fix academic book specific patterns (table links, figure references, footnotes)
   - Repair malformed links and image paths
   - Remove unwanted line breaks within paragraphs (but preserve heading separation)
   - Convert asterisk italics to underscores for consistency
   - Fix em-dash spacing and other typographic issues
   - Clean up table formatting and remove artifacts
   - Restore images and links with proper Obsidian formatting

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
pip install beautifulsoup4 lxml markdownify
```

**Note**: The script now uses `markdownify` for superior HTML-to-Markdown conversion, replacing the previous Pandoc-only approach for content processing.

---

## 🧠 Notes

- **NEW**: Three-phase conversion approach provides superior results for academic books
- **NEW**: markdownify integration eliminates many Pandoc artifacts and provides cleaner output
- **NEW**: Specialized fixes for academic book patterns (table links, figure references, footnotes)
- **NEW**: Intelligent line break handling that preserves heading separation while fixing paragraph breaks
- **Enhanced**: The script now handles various EPUB structures and metadata patterns robustly
- **Enhanced**: Book titles are extracted from copyright statements for better folder naming
- **Enhanced**: All titles are converted to proper Title Case formatting
- **Enhanced**: TOC-driven grouping prevents over-extraction and ensures proper file organization
- **Enhanced**: Comprehensive Markdown cleanup rules for Obsidian compatibility
- The `<title>` tag is assumed to contain the correct chapter name
- Titles will be slugified for use in internal link resolution
- Chapters may span multiple .xhtml files (e.g., chapter7, chapter7a, chapter7b) — these will be grouped based on TOC structure
- The script uses the full path to Pandoc (`/opt/homebrew/bin/pandoc`) to ensure compatibility with Automator workflows.
- Decimal-style filenames ensure correct Obsidian navigation and file sorting (e.g., `06.0`, `06.1`, `06.2`). Front matter uses alphabetic suffixes (e.g., `00a`) and back matter uses numeric IDs (`90`, `91`, ...).
- **Enhanced**: Comprehensive JSON logging provides detailed troubleshooting information

---

## 🚀 Recent Improvements ✅

- ✅ **NEW: Three-Phase Conversion**: HTML pre-processing → markdownify → post-processing cleanup
- ✅ **NEW: markdownify Integration**: Superior HTML-to-Markdown conversion for academic books
- ✅ **NEW: Academic Book Compatibility**: Specialized fixes for table links, figure references, footnotes
- ✅ **NEW: Intelligent Line Break Handling**: Preserves heading separation while fixing paragraph breaks
- ✅ **NEW: Comprehensive Link Repair**: Fixes malformed academic book links and references
- ✅ **Enhanced Metadata Extraction**: Robust detection of chapter numbers, subsections, and content types
- ✅ **Title Case Formatting**: Proper capitalization of all file names and titles
- ✅ **Book Title Extraction**: Automatic extraction from copyright statements for better folder naming
- ✅ **Comprehensive JSON Logging**: Detailed logs with timestamps for troubleshooting
- ✅ **Duplicate TOC Prevention**: Prevents creation of multiple TOC files
- ✅ **Multi-EPUB Structure Support**: Handles various internal folder structures
- ✅ **TOC-Driven Grouping**: Uses table of contents as primary source of truth to prevent over-extraction
- ✅ **Enhanced Markdown Cleanup**: Comprehensive post-processing rules for Obsidian compatibility
- ✅ **Isolated Testing**: `--test-cleanup` and `--test-single` flags for testing individual files

## 🔮 Future Improvements

- Optional metadata frontmatter (e.g., `title`, `chapter`, `source`)
- YAML header for Obsidian compatibility (partially implemented)
- Extend post-processing rules for quotes, footnotes, and special formatting
- GUI wrapper for drag-and-drop usage

---

## ✅ Completion Dialog

After the script finishes processing, a macOS dialog box will appear with:

- ✅ Status of each major step (Three-phase conversion, Markdown output, Cleanup, JSON log)
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
- **📚 TOC-Driven File Organization**: Files properly numbered and organized based on table of contents
- **🔧 Filename Length Management**: Automatic truncation of long titles to prevent filesystem errors
- **🎯 Academic Book Ready**: Clean, properly formatted Markdown optimized for academic research

## 🔍 Three-Phase Conversion Approach

The script now uses a sophisticated three-phase approach for superior results:

**Phase 1: HTML Pre-processing**
- Structural cleanup using BeautifulSoup
- Removal of EPUB-specific artifacts and attributes
- Intelligent handling of `<span>` tags to prevent unwanted line breaks
- Consolidation of formatting elements

**Phase 2: markdownify Conversion**
- Superior HTML-to-Markdown conversion
- Academic book optimized settings
- Clean, semantic output without Pandoc artifacts

**Phase 3: Post-processing Cleanup**
- Academic book specific pattern fixes
- Link and image path repair
- Intelligent line break handling
- Obsidian compatibility optimization

**Example Results**: Academic books now convert with clean formatting, proper link structure, and no unwanted artifacts, making them immediately usable in Obsidian for research work.

## 🧪 Testing Features

The script includes several testing modes for development and troubleshooting:

- `--test-single <xhtml_file>`: Test three-phase conversion on a single XHTML file
- `--test-cleanup <markdown_file>`: Test post-processing cleanup on existing Markdown
- `--test-xhtml <xhtml_file>`: Test Pandoc + cleanup pipeline (legacy mode)

These features allow for iterative development and testing of conversion rules.