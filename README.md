# EPUB to Markdown Converter

This project extracts and converts EPUB files into Markdown format for use in Obsidian. It is designed for researchers (like myself) who need to annotate and reference book content for academic work, such as thesis writing.

## Project Goals

- Extract chapters and table of contents from `.epub` files
- Convert `.xhtml` files to `.md` using filenames and structure derived from `toc.xhtml`
- Number files using logical patterns for front matter (`00a`, `00b`, …), chapters (`01`, `01a`, `01b`, …), and back matter (`90`, `91`, …)
- Preserve images and ensure proper embedding in Markdown
- Update internal links and references for Obsidian-friendly navigation
- Automate this via a shell script (macOS Automator)
- Merge multipart chapters based on table of contents structure
- Display completion dialog on macOS with summary (files created, images copied, JSON log written, time elapsed)

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
   - If an `/images/` directory exists, it is copied to the output folder  
   - The final summary dialog will show ✅ if images were found, or ⛔ if no images were available

5. **Convert XHTML to Markdown**  
   For each `.xhtml` chapter:  
   - Extract `<title>` from `<head>` section  
   - Rename output markdown file based on TOC structure (e.g., `01a - Chapter Title.md`)  
   - Group and number multi-part chapters (e.g., `01a`, `01b`, `01c`) based on TOC mapping  
   - Use TOC to define chapter boundaries and file naming instead of relying on `content.opf` order alone  
   - Convert XHTML body content to Markdown using `pandoc`  
   - A separate function applies post-processing cleanup rules

6. **Update Internal Links**  
   - Convert internal links to Obsidian-friendly `[[Note Name#Heading]]` format  
   - Strip `.md` extension and normalize anchor text

7. **Process TOC**  
   - Convert `toc.xhtml` to Markdown  
   - TOC structure generated in Markdown follows Obsidian format with nesting and chapter/section hierarchy  
   - Filters out duplicate entries and multilingual fallbacks  
   - Convert nav links to Obsidian `[[Page Title]]` format

8. **Clean Up**
   - Remove temporary extraction directory

9. **Post-Processing Cleanup**  
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

---

## ✅ Completion Dialog

After the script finishes processing, a macOS dialog box will appear with:

- ✅ Status of each major step (Pandoc conversion, Markdown output, Cleanup, JSON log)
- 📄 Total Markdown files created
- 🖼️ Images copied (✅ or ⛔)
- 🕒 Total execution time
- Dialog remains visible until dismissed by the user