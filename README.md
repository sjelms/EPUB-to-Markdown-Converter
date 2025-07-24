# EPUB to Markdown Converter

This project extracts and converts EPUB files into Markdown format for use in Obsidian. It is designed for researchers (like myself) who need to annotate and reference book content for academic work, such as thesis writing.

## Project Goals

- Extract chapters and table of contents from `.epub` files
- Convert `.xhtml` files to `.md` with filenames based on `<title>` tags
- Preserve images and ensure proper embedding in Markdown
- Update internal links and references for Obsidian-friendly navigation
- Automate this via a shell script (macOS Automator)
- Merge multipart chapters based on table of contents structure

---

## 📦 EPUB Structure

An EPUB file is essentially a `.zip` archive containing:

```
/mimetype
/META-INF/container.xml
/OEBPS/ (or other root directory)
  ├── *.xhtml (chapters)
  ├── toc.ncx (navigation XML)
  ├── toc.xhtml (HTML-based TOC)
  ├── images/
  ├── css/
  ├── fonts/
```

---

## 🛠️ Automation Workflow

### 1. Input

- Triggered on an `.epub` file using macOS “Run Shell Script” automation
- Output is always saved to a designated directory (e.g. `~/Documents/EpubNotes/`)

### 2. Process Outline

1. **Create Output Folder**  
   - Folder is named after the EPUB file (e.g., `Improving_Working_as_Learning/`)

2. **Extract EPUB**  
   - Use `unzip` or `bsdtar` to unpack the `.epub` to a temp directory

3. **Locate Content Directory**  
   - Parse `META-INF/container.xml` to locate `content.opf` root directory

4. **Copy Assets**  
   - Copy `/images/` folder into the new output directory

5. **Convert XHTML to Markdown**  
   For each `.xhtml` chapter:
   - Extract `<title>` from `<head>` section
   - Rename output markdown file to match title (e.g., `01 - Promoting Health.md`)
   - Merge multi-part chapters (e.g., chapter7.xhtml + chapter7a.xhtml) using TOC order
   - Convert XHTML body content to Markdown using `pandoc`
   - A separate function applies post-processing cleanup rules

6. **Update Internal Links**  
   - Parse `<a href="Chapter-2.xhtml#...">` and replace with  
     `[[Chapter 2 - Mapping the Working as Learning Framework#...]]`
   - A mapping dictionary may be needed to resolve target titles

7. **Process TOC**  
   - Convert `toc.xhtml` to Markdown
   - Convert nav links to Obsidian `[[Page Title]]` format

8. **Clean Up**
   - Remove temporary extraction directory

9. **Post-Processing Cleanup**  
   - Clean up Markdown using custom Python rules:
     - Remove Pandoc-generated div blocks (`:::`)
     - Remove same-file anchor links (e.g. `#span_00123`)
     - Normalize heading levels (only one H1 per file; internal sections use H2-H6)
     - Convert inline `<q>` tags to Obsidian-style block quotes
     - Flatten bracketed reference clusters and remove inline citations
     - Normalize paragraph and line spacing
     - Clean up and collapse multi-line reference sections
     - Rewrite internal cross-file links using `[[Note Name#Heading]]` syntax

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

- Some EPUBs may use different internal structures or IDs—test before batch-processing
- The `<title>` tag is assumed to contain the correct chapter name
- Titles will be slugified for use in internal link resolution
- Chapters may span multiple .xhtml files (e.g., chapter7, chapter7a, chapter7b) — these will be merged based on TOC structure
- The cleanup stage uses a dedicated Python function that can be adjusted as needed for formatting edge cases.
 - The script uses the full path to Pandoc (`/opt/homebrew/bin/pandoc`) to ensure compatibility with Automator workflows.

---

## 🚀 Future Improvements

- Optional metadata frontmatter (e.g., `title`, `chapter`, `source`)
- ✅ YAML header for Obsidian compatibility (partially implemented)
- Extend post-processing rules for quotes, footnotes, and special formatting
- GUI wrapper for drag-and-drop usage