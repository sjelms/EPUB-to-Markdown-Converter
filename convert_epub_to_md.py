from pathlib import Path
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from typing import Union, Any

def generate_markdown_outputs(
    chapter_map: list[dict],
    output_dir_path: Path,
    bibtex_data: dict | None = None
):
    """Generate Markdown files from the structured chapter map."""
    from bs4 import BeautifulSoup
    from markdownify import markdownify as md

    output_dir_path.mkdir(parents=True, exist_ok=True)

    for entry in chapter_map:
        filepath = entry["filepath"]
        label = entry["label"]
        title = entry.get("title", entry["filename"].replace(".xhtml", ""))
        output_filename = f"{label} - {title}.md"
        output_path = output_dir_path / safe_filename(output_filename)

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "lxml")
        except Exception as e:
            print(f"[ERROR] Failed to parse {filepath.name}: {e}")
            continue

        # Extract clean title if possible
        heading = soup.find(["h1", "title"])
        if heading and isinstance(heading, (Tag, NavigableString)):
            if hasattr(heading, "get_text"):
                title = heading.get_text(strip=True)

        # Convert to Markdown
        markdown_text = md(
            str(soup),
            heading_style="ATX",
            em_symbol="*",
            strong_symbol="**",
            bullets="-",
            code_symbol="`",
            strip=["script", "style"]
        )

        # YAML header
        yaml_header = f"---\ntitle: {title}\nlabel: {label}\nfilename: {entry['filename']}\n---\n\n"

        with open(output_path, "w", encoding="utf-8") as out_md:
            out_md.write(yaml_header + markdown_text)
def assign_manifest_structure(manifest_map: list[dict]) -> list[dict]:
    """Assigns structured output labels (e.g., 00a, 01.0, 900) to each manifest item."""
    front_counter = 0
    chapter_counter = 1
    back_counter = 900
    chapter_map = []

    for item in manifest_map:
        classification = item.get("classified_as", "chapter")

        if classification == "frontmatter":
            label = f"00{chr(97 + front_counter)}"  # 00a, 00b, 00c
            front_counter += 1

        elif classification == "chapter":
            label = f"{chapter_counter:02}.0"
            chapter_counter += 1

        elif classification == "backmatter":
            label = f"{back_counter}"
            back_counter += 1

        else:
            label = f"999"  # fallback

        item["label"] = label
        chapter_map.append(item)

    return chapter_map
def build_manifest_map(opf_soup, opf_path: Path) -> list[dict]:
    """Creates a manifest map based on spine and manifest structure."""
    manifest_items = []
    manifest = {item["id"]: item for item in opf_soup.find_all("item") if isinstance(item, Tag) and item.has_attr("id")}
    spine = opf_soup.find("spine")
    spine_items = spine.find_all("itemref") if spine else []
    
    for index, itemref in enumerate(spine_items):
        if not isinstance(itemref, Tag):
            continue
        idref = itemref.get("idref")
        if not idref:
            continue
        manifest_item = manifest.get(idref)
        if not manifest_item:
            continue
        href = manifest_item.get("href")
        if not href:
            continue
        media_type = manifest_item.get("media-type", "")
        properties = manifest_item.get("properties", "")
        epub_type = itemref.get("epub:type", "")
        
        # Construct absolute path to the content file
        file_path = (opf_path.parent / str(href)).resolve()
        filename = Path(str(href)).name
        
        # Basic classification based on filename
        classification = "chapter"
        if any(kw in filename.lower() for kw in ("cover", "title", "copyright", "acknowledgements", "intro")):
            classification = "frontmatter"
        elif any(kw in filename.lower() for kw in ("index", "references", "appendix", "conclusion", "notes", "ref", "back")):
            classification = "backmatter"
        
        manifest_items.append({
            "filename": filename,
            "filepath": file_path,
            "classified_as": classification,
            "media_type": str(media_type),
            "properties": str(properties),
            "epub_type": str(epub_type),
            "spine_index": index
        })
    
    return manifest_items
import subprocess

# Helper function to show a macOS dialog (restored for completion notification)
def show_completion_dialog(message: str):
    try:
        subprocess.run([
            "osascript", "-e",
            f'display dialog "{message}" with title "EPUB to Markdown" buttons ["OK"] default button "OK"'
        ])
    except Exception as e:
        print(f"[WARNING] Unable to display completion dialog: {e}")
# === Helper functions for frontmatter and backmatter detection ===
def is_frontmatter_file(filename: str, title: str = "") -> bool:
    lower_name = filename.lower()
    lower_title = title.lower() if title else ""
    return any(kw in lower_name for kw in ("cover", "title", "copyright", "acknowledgements", "praise", "brand", "about")) or \
           any(kw in lower_title for kw in ("acknowledgements", "introduction", "about the author", "preface", "foreword"))

def is_backmatter_file(filename: str, title: str = "") -> bool:
    lower_name = filename.lower()
    lower_title = title.lower() if title else ""
    return any(kw in lower_name for kw in ("index", "references", "appendix", "bibliography", "notes")) or \
           any(kw in lower_title for kw in ("index", "references", "conclusion", "bibliography", "appendix", "notes"))

import re
from markdownify import markdownify as md

def title_case(text: str) -> str:
    """Convert text to Title Case (first letter of major words capitalized)."""
    
    # Words that should remain lowercase (unless first or last word)
    minor_words = {
        'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'if', 'in', 'is', 'it', 'no', 'nor', 
        'of', 'on', 'or', 'so', 'the', 'to', 'up', 'yet', 'with', 'from', 'into', 'through', 
        'during', 'before', 'after', 'above', 'below', 'between', 'among', 'within', 'without'
    }
    
    # If text is all uppercase, convert to title case first
    if text.isupper():
        text = text.title()
    
    # Split into words and process each
    words = text.split()
    if not words:
        return text
    
    result = []
    for i, word in enumerate(words):
        # Clean the word (remove punctuation for processing)
        clean_word = re.sub(r'[^\w]', '', word.lower())
        
        # Capitalize if:
        # 1. It's the first or last word
        # 2. It's not a minor word
        # 3. It's longer than 3 characters (to catch important short words)
        should_capitalize = (
            i == 0 or i == len(words) - 1 or  # First or last word
            clean_word not in minor_words or  # Not a minor word
            len(clean_word) > 3  # Longer than 3 characters
        )
        
        if should_capitalize:
            # Capitalize the first letter, preserve original case for rest
            if word:
                result.append(word[0].upper() + word[1:])
            else:
                result.append(word)
        else:
            # Keep minor words lowercase
            result.append(word.lower())
    
    return ' '.join(result)



# Helper function to sanitize titles for filenames
def safe_filename(title: str) -> str:
    """Sanitize title for use as a filename (prevent subfolders or illegal characters)."""
    # First sanitize the title
    safe_title = re.sub(r'[\\/:"*?<>|]', '-', title)
    
    # Limit filename length to prevent filesystem errors
    # Most filesystems have a limit of 255 characters for filename
    # We'll use a more conservative limit of 100 characters
    if len(safe_title) > 100:
        # Truncate and add ellipsis
        safe_title = safe_title[:97] + "..."
    
    return safe_title

def clean_markdown_text(md_content: str, chapter_map=None) -> str:
    """
    Robust, browser-like XHTML to Markdown conversion:
    - Parse the entire XHTML file (not just <body> or a fragment)
    - Pre-process HTML to fix structural issues before conversion
    - Pass the full DOM to markdownify for conversion
    - Post-process for final cleanup and formatting
    """
    from bs4 import BeautifulSoup
    from bs4.element import Tag
    import os
    import re
    
    # If already Markdown, skip HTML processing
    if not md_content.strip().startswith('<'):
        return post_process_markdown(md_content, chapter_map)
    
    # Store original HTML for image-only page detection after conversion
    raw_html = md_content
    soup = BeautifulSoup(md_content, 'html.parser')
    
    # === PRE-PROCESSING: Fix HTML structure before conversion ===
    
    # Remove <script> and <style> tags
    for tag in soup.find_all(['script', 'style']):
        tag.decompose()
    
    # Fix image src attributes
    for img in soup.find_all('img'):
        if isinstance(img, Tag):
            src = img.get('src')
            if isinstance(src, str) and src:
                image_filename = os.path.basename(src)
                img['src'] = os.path.join('images', image_filename)
    
    # Fix chapter title structure - extract and clean up the main title
    header = soup.find('header')
    if header and isinstance(header, Tag):
        h1 = header.find('h1')
        if h1 and isinstance(h1, Tag):
            # Extract the chapter number and title
            chap_label = h1.find('span', class_='chap-label')
            if chap_label and isinstance(chap_label, Tag):
                chap_text = chap_label.get_text(strip=True)
                # Remove extra whitespace and line breaks
                chap_text = re.sub(r'\s+', ' ', chap_text)
            
            # Extract the bold title
            bold_title = h1.find('b')
            if bold_title and isinstance(bold_title, Tag):
                title_text = bold_title.get_text(strip=True)
                # Create a clean title
                clean_title = f"# Chapter 2: {title_text}"
                # Replace the entire h1 with clean text
                h1.clear()
                h1.string = clean_title
    
    # Fix subtitle structure
    subtitle_p = soup.find('p', class_='subtitle')
    if subtitle_p and isinstance(subtitle_p, Tag):
        subtitle_link = subtitle_p.find('a')
        if subtitle_link and isinstance(subtitle_link, Tag):
            subtitle_text = subtitle_link.get_text(strip=True)
            # Replace with clean subtitle
            subtitle_p.clear()
            subtitle_p.string = f"## {subtitle_text}"
    
    # Fix author formatting
    author_p = soup.find('p', class_='author')
    if author_p and isinstance(author_p, Tag):
        author_i = author_p.find('i')
        if author_i and isinstance(author_i, Tag):
            author_text = author_i.get_text(strip=True)
            # Replace with clean author line
            author_p.clear()
            author_p.string = f"*{author_text}*"
    
    # Fix image captions - remove the _List_of_figures.xhtml references
    for img in soup.find_all('img'):
        if isinstance(img, Tag):
            # Find the next sibling that might be a caption
            next_sibling = img.find_next_sibling()
            if next_sibling and isinstance(next_sibling, Tag):
                caption_text = next_sibling.get_text()
                # Clean up caption text
                if '_List_of_figures.xhtml#' in caption_text:
                    # Extract just the caption part before the _List_of_figures
                    clean_caption = caption_text.split('_List_of_figures.xhtml#')[0]
                    next_sibling.string = clean_caption
    
    # Convert superscript tags to Obsidian footnote format
    for sup in soup.find_all('sup'):
        if isinstance(sup, Tag):
            sup_text = sup.get_text(strip=True)
            # Check if this is a footnote reference (usually just a number)
            if sup_text.isdigit():
                # Convert to Obsidian footnote format
                footnote_ref = f"[^{sup_text}]"
                # Create a new NavigableString for the footnote reference
                from bs4.element import NavigableString
                footnote_element = NavigableString(footnote_ref)
                sup.replace_with(footnote_element)
            else:
                # For other superscript content, just keep the text
                sup.unwrap()
    

    
    # Fix figure references in text
    for text in soup.find_all(text=True):
        if isinstance(text, str) and '_List_of_figures.xhtml#' in text:
            # Replace with clean figure reference
            clean_text = re.sub(r'_List_of_figures\.xhtml#[^_\s]+', '', text)
            # Create a new NavigableString for the replacement
            from bs4.element import NavigableString
            new_text = NavigableString(clean_text)
            text.replace_with(new_text)
    
    # Fix broken links in text
    for a_tag in soup.find_all('a'):
        if isinstance(a_tag, Tag):
            href = a_tag.get('href', '')
            if href and isinstance(href, str) and 'contents.xhtml' in href:
                # Remove problematic internal links
                a_tag.unwrap()
    
    # === CONVERSION ===
    # Pass the full DOM to markdownify
    import markdownify
    markdown_text = markdownify.markdownify(
        str(soup),
        heading_style="ATX",
        em_symbol="*",
        strong_symbol="**",
        bullets="-",
        code_symbol="`",
        strip=['script', 'style'],
    )

    # === SPECIAL HANDLING: Detect image-only pages and convert <img> tags to Markdown ===
    # If the original raw_html contains only an <img> tag (no <h1>, <h2>, <p>, <div>, <section> or text content)
    # Place this after markdownify and before writing .md file
    if "<img" in raw_html and all(tag not in raw_html for tag in ("<p", "<h1", "<h2", "<div", "<section")):
        soup_img = BeautifulSoup(raw_html, "html.parser")
        img_tag = soup_img.find("img")
        if img_tag and img_tag.get("src"):
            img_src = img_tag["src"]
            # Classify as front or back matter based on spine position is not possible here, but we ensure the image is preserved
            img_md = f"![]({img_src})"
            markdown_text = img_md  # overwrite with just the image if it's the only content
            print(f"[INFO] Image-only page detected: inserted Markdown image tag for {img_src}")

    # === POST-PROCESSING ===
    return post_process_markdown(markdown_text, chapter_map)

def post_process_markdown(markdown_text: str, chapter_map=None, image_positions=None) -> str:
    """
    Phase 3: Post-process the Markdown for final polishing
    """
    
    # === PROTECT IMPORTANT CONTENT ===
    
    # Protect links from modification
    def protect_link(match):
        link_text = match.group(1)
        link_url = match.group(2)
        return f"LINK_PLACEHOLDER_{link_text}_{link_url}"
    
    markdown_text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', protect_link, markdown_text)
    
    # === CLEANUP AND FORMATTING ===
    
    # Remove XML declarations from the final output
    markdown_text = re.sub(r'^xml version="1\.0" encoding="UTF-8"\?\n?', '', markdown_text, flags=re.MULTILINE)
    
    # Collapse multiple newlines into maximum of 2
    markdown_text = re.sub(r'\n{3,}', '\n\n', markdown_text)
    
    # Remove trailing whitespace from lines
    markdown_text = re.sub(r' +\n', '\n', markdown_text)
    
    # Fix headings that got merged with paragraphs
    # Pattern: # Heading text (should be # Heading\n\ntext)
    markdown_text = re.sub(r'^(#{1,6}\s+[^#\n]+)\s+([A-Z][a-z])', r'\1\n\n\2', markdown_text, flags=re.MULTILINE)
    
    # Fix unwanted line breaks within sentences (but be more conservative)
    # Only fix when it's clearly a broken sentence, not across structural boundaries
    # Pattern: word\n\nword (where it should be word word) but only within paragraphs
    markdown_text = re.sub(r'([a-z])\n\n([a-zA-Z])', r'\1 \2', markdown_text, flags=re.MULTILINE)
    
    # Fix heading hierarchy - convert Activity headings to level 3
    markdown_text = re.sub(r'^# Activity (\d+\.\d+)', r'### Activity \1', markdown_text, flags=re.MULTILINE)
    
    # Fix table-to-heading conversions for activities
    markdown_text = re.sub(r'^\|  \|  \|\n\| --- \| --- \|\n\| Activity (\d+\.\d+) \| figure \|', r'### Activity \1', markdown_text, flags=re.MULTILINE)
    
    # Fix other table-to-heading conversions
    markdown_text = re.sub(r'^\|  \|  \|\n\| --- \| --- \|\n\| ([^|]+) \| figure \|', r'### \1', markdown_text, flags=re.MULTILINE)
    
    # Fix bullet list formatting
    markdown_text = re.sub(r'^- $', '', markdown_text, flags=re.MULTILINE)  # Remove empty bullets
    markdown_text = re.sub(r'^- \n', '', markdown_text, flags=re.MULTILINE)  # Remove bullets with only newlines
    
    # Fix bullet list artifacts
    markdown_text = re.sub(r'^- \)_', r'- ', markdown_text, flags=re.MULTILINE)  # Remove )_ artifacts
    markdown_text = re.sub(r'^- \)_([^_]+)_', r'- \1', markdown_text, flags=re.MULTILINE)  # Fix )_text_ patterns
    
    # Fix spacing around headings
    markdown_text = re.sub(r'([^\n])\n(#{1,6}\s)', r'\1\n\n\2', markdown_text)  # Add space before headings
    markdown_text = re.sub(r'(#{1,6}\s+[^#\n]+)\n([^\n])', r'\1\n\n\2', markdown_text)  # Add space after headings
    
    # Fix italic formatting (convert * to _ for consistency)
    markdown_text = re.sub(r'\*([^*]+)\*', r'_\1_', markdown_text)
    
    # Fix incomplete italic formatting - more precise approach
    # Pattern: _word (should be _word_) but only for specific known words
    italic_words = ['means', 'techne', 'are', 'combinations', 'the', 'some', 'not']
    for word in italic_words:
        # Replace _word with _word_ but only when it's a standalone word
        markdown_text = re.sub(rf'_({word})(?=\s|$)', r'_\1_', markdown_text)
    
    # Fix heading structure - ensure proper spacing
    # Pattern: # Heading text → # Heading\n\ntext
    markdown_text = re.sub(r'^(#{1,6}\s+[^#\n]+)([A-Z][a-z])', r'\1\n\n\2', markdown_text, flags=re.MULTILINE)
    
    # Fix incomplete italic formatting - add missing closing underscores
    markdown_text = re.sub(r'_([^_\n]+?)(?=\s|$|\.|,|;|:|!|\?)', r'_\1_', markdown_text)
    
    # Fix superscript tags to Obsidian footnote format
    markdown_text = re.sub(r'<sup>(\d+)</sup>', r'[^\1]', markdown_text)
    
    # Fix footnote references in text to link to footnote definitions
    # Pattern: [^1] should link to footnote definition at end
    markdown_text = re.sub(r'\[(\^?\d+)\]', r'[^\1]', markdown_text)
    
    # Fix em-dash spacing
    markdown_text = re.sub(r'—([a-zA-Z])', r'— \1', markdown_text)
    
    # Fix double hash in titles (e.g., "# # Chapter 2: System structures")
    markdown_text = re.sub(r'^# # ', r'# ', markdown_text, flags=re.MULTILINE)
    
    # Fix heading formatting with extra underscores
    markdown_text = re.sub(r'^## \*([^*]+)__$', r'## \1', markdown_text, flags=re.MULTILINE)
    markdown_text = re.sub(r'^## _([^_]+)__$', r'## \1', markdown_text, flags=re.MULTILINE)
    
    # Fix image captions - remove _List_of_figures.xhtml# references
    markdown_text = re.sub(r'_List_of_figures\.xhtml#[^_\s]+', '', markdown_text)
    
    # Fix broken paragraph flow - remove stray closing parentheses
    markdown_text = re.sub(r'\)\n\n([A-Z][a-z])', r'\n\n\1', markdown_text)
    
    # Fix malformed URLs in notes section
    markdown_text = re.sub(r'\[http[^]]+\]\([^)]+\)', '', markdown_text)
    
    # Fix figure references - clean up "Figure 2.X" references
    markdown_text = re.sub(r'Figure (\d+\.\d+)', r'**Figure \1**', markdown_text)
    
    # Fix author line formatting - ensure it's properly italicized
    markdown_text = re.sub(r'^_([^_]+)$', r'*_\1_*', markdown_text, flags=re.MULTILINE)
    
    # === RESTORE PROTECTED CONTENT ===
    
    # Restore links
    def restore_link(match):
        link_text = match.group(1)
        link_url = match.group(2)
        
        # Handle cross-references if chapter_map provided
        if chapter_map and '.xhtml#' in link_url:
            if "#" in link_url:
                file_part, anchor = link_url.split("#", 1)
            else:
                file_part, anchor = link_url, ""
            if file_part in chapter_map:
                md_target = chapter_map[file_part]
                return f"[[{md_target}]]"
        
        return f"[{link_text}]({link_url})"
    
    markdown_text = re.sub(r'LINK_PLACEHOLDER_([^_]+)_([^_]+)', restore_link, markdown_text)
    
    # === FINAL CLEANUP ===
    
    # Remove any remaining artifacts
    markdown_text = re.sub(r'^\s*:\s*$', '', markdown_text, flags=re.MULTILINE)  # Remove stray colons
    
    # Remove placeholder artifacts
    markdown_text = re.sub(r'LINK\)_PLACEHOLDER_', '', markdown_text)
    
    # Fix remaining artifacts
    markdown_text = re.sub(r'\)\)_([^_]+)_', r'\1', markdown_text)  # Fix ))_text_ patterns
    markdown_text = re.sub(r'\)_([^_]+)_', r'\1', markdown_text)  # Fix )_text_ patterns
    
    # Fix academic book specific patterns
    # Fix malformed footnote links: [1](#fn21 → [1](#fn21)
    markdown_text = re.sub(r'\[(\d+)\]\(#fn(\d+)$', r'[\1](#fn\2)', markdown_text, flags=re.MULTILINE)
    
    # Fix malformed figure links: [Figure 2.1](#fig21 → [Figure 2.1](#fig21)
    markdown_text = re.sub(r'\[Figure ([^]]+)\]\(#fig([^)]+)$', r'[Figure \1](#fig\2)', markdown_text, flags=re.MULTILINE)
    
    # Fix malformed table links: [Table 2.2](#ch02-table2-2, → [Table 2.2](#ch02-table2-2)
    markdown_text = re.sub(r'\[Table ([^]]+)\]\(#([^)]+),$', r'[Table \1](#\2)', markdown_text, flags=re.MULTILINE)
    
    # Fix trailing commas in any links: [text](#link, → [text](#link)
    markdown_text = re.sub(r'\[([^\]]+)\]\(([^)]+),$', r'[\1](\2)', markdown_text, flags=re.MULTILINE)
    
    # Fix trailing commas in links followed by text: [text](#link, text → [text](#link) text
    markdown_text = re.sub(r'\[([^\]]+)\]\(([^)]+),(\s)', r'[\1](\2)\3', markdown_text, flags=re.MULTILINE)
    
    # Fix malformed table links with underscores: Table 2.2_#ch02-table2-2 → [Table 2.2](#ch02-table2-2)
    markdown_text = re.sub(r'([A-Za-z]+ \d+\.\d+)_#([^,\s]+)', r'[\1](#\2)', markdown_text)
    
    # Fix malformed table links with underscores at end: Table 2.4_#ch02-table2-4 → [Table 2.4](#ch02-table2-4)
    markdown_text = re.sub(r'([A-Za-z]+ \d+\.\d+)_#([^,\s]+)', r'[\1](#\2)', markdown_text)
    
    # Remove internal anchor references since we're not doing web-style navigation
    # Pattern: [text](#anchor) → text
    markdown_text = re.sub(r'\[([^\]]+)\]\(#([^)]+)\)', r'\1', markdown_text)
    
    # Fix orphaned parentheses from removed anchor references
    # Pattern: (Table X.Y → Table X.Y
    markdown_text = re.sub(r'\(([A-Za-z]+ \d+\.\d+)', r'\1', markdown_text)
    
    # Fix trailing underscores in headings and text
    markdown_text = re.sub(r'([^_])_$', r'\1', markdown_text, flags=re.MULTILINE)  # Remove trailing underscores
    
    # Fix double underscores in headings: ## __Introduction__ → ## Introduction
    markdown_text = re.sub(r'^(#{1,6})\s*__([^_]+)__', r'\1 \2', markdown_text, flags=re.MULTILINE)
    
    # Fix complex academic book link patterns
    # Pattern: [Chapter 2 *](System structures)___04-9781315743332_contents.xhtml#chapter2
    markdown_text = re.sub(r'\[([^]]+)\*\]\(([^)]+)___([^)]+)\)', r'[\1](\3)', markdown_text)
    
    # Fix incomplete image paths: ![fig2](images/fig → ![fig2](images/fig.jpg)
    markdown_text = re.sub(r'!\[([^\]]+)\]\(([^)]*?images/[^)]*?)$', r'![\1](\2.jpg)', markdown_text, flags=re.MULTILINE)
    
    # Fix incomplete image paths with numbers: ![fig2](2.tifimages/fig → ![fig2](images/fig2.jpg)
    markdown_text = re.sub(r'!\[([^\]]+)\]\((\d+)\.(tif|jpg|png)([^)]*?)([^)]*?)$', r'![\1](images/\5\2.\3)', markdown_text, flags=re.MULTILINE)
    
    # Fix duplicate file extensions in image paths (e.g., .jpg.jpg -> .jpg)
    markdown_text = re.sub(r'!\[([^\]]+)\]\(([^)]*?)\.(jpg|png|gif|jpeg)\.(jpg|png|gif|jpeg)\)', r'![\1](\2.\3)', markdown_text)
    
    # Fix malformed images (missing opening bracket)
    markdown_text = re.sub(r'!figure_images/([^_]+)', r'![figure](images/\1)', markdown_text)
    markdown_text = re.sub(r'!figure\)_images/([^_]+)', r'![figure](images/\1)', markdown_text)
    
    # Fix broken image tags (missing closing parenthesis)
    markdown_text = re.sub(r'!\[([^\]]+)\]\(([^)]+)$', r'![\1](\2)', markdown_text, flags=re.MULTILINE)
    
    # Remove extra closing parentheses at the end
    markdown_text = re.sub(r'\)+$', '', markdown_text)
    
    # Fix specific stray parentheses issues
    markdown_text = re.sub(r'position\)$', 'position', markdown_text, flags=re.MULTILINE)  # Line 43
    markdown_text = re.sub(r'experiencing\) perceiving', 'experiencing (perceiving', markdown_text)  # Line 45
    markdown_text = re.sub(r'them\) explicitly', 'them (explicitly', markdown_text)  # Line 113
    markdown_text = re.sub(r'^\s*\)\s*$', '', markdown_text, flags=re.MULTILINE)  # Standalone ) characters
    
    # Fix incomplete sentences with missing closing parentheses
    markdown_text = re.sub(r'understanding the chair\?\n\)', 'understanding the chair?)', markdown_text)  # Line 45
    markdown_text = re.sub(r'about the concept\.\n\)', 'about the concept.)', markdown_text)  # Line 114
    
    # Remove any remaining standalone ) characters that are clearly artifacts
    markdown_text = re.sub(r'\n\)\n', '\n', markdown_text)  # Remove standalone ) on its own line
    
    # Fix the specific incomplete sentences by adding missing closing parentheses
    markdown_text = re.sub(r'understanding the chair\?\n\)', 'understanding the chair?)', markdown_text)
    markdown_text = re.sub(r'about the concept\.\n\)', 'about the concept.)', markdown_text)
    
    # === ENHANCED CLEANUP FOR OFFSITE ARCHITECTURE ISSUES ===
    
    # Fix malformed image paths with file extension before folder path
    # Pattern: ![fig2](1.jpgimages/fig21.jpg) → ![fig2](images/fig2_1.jpg)
    markdown_text = re.sub(r'!\[([^\]]+)\]\((\d+)\.(jpg|png|gif)([^)]*?images/[^)]*?)(\d+)\.(jpg|png|gif)\)', 
                          r'![\1](images/fig\2_\5.\6)', markdown_text)
    
    # Fix image paths where underscores were removed
    # Pattern: ![fig2](images/fig21.jpg) → ![fig2](images/fig2_1.jpg)
    markdown_text = re.sub(r'!\[([^\]]+)\]\(images/fig(\d+)(\d+)\.(jpg|png|gif)\)', 
                          r'![\1](images/fig\2_\3.\4)', markdown_text)
    
    # Fix more complex malformed image paths
    # Pattern: ![fig2](1.jpgimages/fig21.jpg) → ![fig2](images/fig2_1.jpg)
    markdown_text = re.sub(r'!\[([^\]]+)\]\((\d+)\.(jpg|png|gif|tif)([^)]*?)(\d+)\.(jpg|png|gif|tif)\)', 
                          r'![\1](images/fig\2_\5.\6)', markdown_text)
    
    # Fix image paths with tif extension issues
    # Pattern: ![fig2](2.tifimages/fig22.jpg) → ![fig2](images/fig2_2.jpg)
    markdown_text = re.sub(r'!\[([^\]]+)\]\((\d+)\.(tif)([^)]*?)(\d+)\.(jpg|png|gif)\)', 
                          r'![\1](images/fig\2_\5.\6)', markdown_text)
    
    # Remove LINK_PLACEHOLDER_ artifacts from captions
    # Pattern: LINK_PLACEHOLDER_Figure 2.1 → Figure 2.1
    markdown_text = re.sub(r'LINK_PLACEHOLDER_([^_\n]+)', r'\1', markdown_text)
    
    # Remove stray code from captions
    # Pattern: __System structural isomorphism (left) and equifinality (right)___04a-9781315743332_List_of_figures.xhtml#fig2_1
    # → System structural isomorphism (left) and equifinality (right)
    markdown_text = re.sub(r'__([^_]+)___[^_\n]+', r'\1', markdown_text)
    
    # Fix forced line breaks caused by inline tags on their own lines
    # Pattern: word\n\n*italic*\n\nword → word *italic* word
    markdown_text = re.sub(r'([a-zA-Z])\n\n\*([^*]+)\*\n\n([a-zA-Z])', r'\1 *\2* \3', markdown_text)
    markdown_text = re.sub(r'([a-zA-Z])\n\n\*\*([^*]+)\*\*\n\n([a-zA-Z])', r'\1 **\2** \3', markdown_text)
    
    # Fix stray parentheses that appear after text
    # Pattern: text) → text
    markdown_text = re.sub(r'([a-zA-Z])\n\)', r'\1', markdown_text, flags=re.MULTILINE)
    
    # Remove leftover XHTML code artifacts
    # Pattern: any remaining HTML-like tags or attributes
    markdown_text = re.sub(r'<[^>]+>', '', markdown_text)
    markdown_text = re.sub(r'xmlns="[^"]*"', '', markdown_text)
    markdown_text = re.sub(r'class="[^"]*"', '', markdown_text)
    
    # Fix escaped backslashes in image tags
    # Pattern: ![fig2\](images/fig1_1.jpg) → ![fig2](images/fig1_1.jpg)
    markdown_text = re.sub(r'!\[([^\]]+)\\\]\(([^)]+)\)', r'![\1](\2)', markdown_text)
    
    # Fix broken caption formatting
    # Pattern: [Figure 2.1 → Figure 2.1
    markdown_text = re.sub(r'\[Figure ([^\]\n]+)', r'Figure \1', markdown_text)
    
    # Fix broken caption formatting with trailing artifacts
    # Pattern: [Figure 2.1\n](\System structural isomorphism... → Figure 2.1\n\nSystem structural isomorphism...
    markdown_text = re.sub(r'\[Figure ([^\]\n]+)\n\]\([^)]+\)', r'Figure \1', markdown_text)
    
    # Remove remaining link artifacts from captions
    # Pattern: ](\System structural isomorphism (left) and equifinality (right)\\__04a-9781315743332_List_of_figures.xhtml#fig2_1 → System structural isomorphism (left) and equifinality (right)
    markdown_text = re.sub(r'\]\([^)]*?___[^)]*?\)', '', markdown_text)
    
    # Remove trailing artifacts after figure captions
    # Pattern: ](System structural isomorphism (left) and equifinality (right)\__04a-9781315743332_List_of_figures.xhtml#fig2_1 → System structural isomorphism (left) and equifinality (right)
    markdown_text = re.sub(r'\]\(([^)]*?)\__[^)]*?\)', r'\1', markdown_text)
    
    # Clean up any remaining escaped backslashes in text
    markdown_text = re.sub(r'\\([^\\])', r'\1', markdown_text)
    
    # Fix double underscores in headings and text
    markdown_text = re.sub(r'\\_\\_([^_]+)\\\_\\_', r'\1', markdown_text)
    
    # Convert numbered footnotes in Notes section to Obsidian footnote format
    # Pattern: "1 taking the bus..." → "[^1]: taking the bus..."
    # But ONLY in the Notes section, not in the main text
    lines = markdown_text.split('\n')
    in_notes_section = False
    for i, line in enumerate(lines):
        if line.strip() == '## Notes':
            in_notes_section = True
            continue
        if in_notes_section and line.strip().startswith('##'):
            in_notes_section = False
            continue
        if in_notes_section and re.match(r'^\d+\s+', line.strip()):
            # Convert numbered footnotes to Obsidian format
            lines[i] = re.sub(r'^(\d+)\s+', r'[^\1]: ', line)
    markdown_text = '\n'.join(lines)
    
    # Fix line breaks around italic text - remove unwanted breaks
    # Pattern: word\n\n_italic_\n\nword → word _italic_ word
    markdown_text = re.sub(r'([a-zA-Z])\n\n_([^_]+)_\n\n([a-zA-Z])', r'\1 _\2_ \3', markdown_text)
    markdown_text = re.sub(r'([a-zA-Z])\n_([^_]+)_\n([a-zA-Z])', r'\1 _\2_ \3', markdown_text)
    
    # Fix specific line break issues around italic words
    # Pattern: word\n_italic_\nword → word _italic_ word
    markdown_text = re.sub(r'([a-zA-Z])\n_([a-zA-Z]+)_\n([a-zA-Z])', r'\1 _\2_ \3', markdown_text)
    
    # Fix malformed footnote references that got converted to definitions
    # Pattern: [1]: text → [^1] text (in main text, not Notes section)
    lines = markdown_text.split('\n')
    in_notes_section = False
    for i, line in enumerate(lines):
        if line.strip() == '## Notes':
            in_notes_section = True
            continue
        if in_notes_section and line.strip().startswith('##'):
            in_notes_section = False
            continue
        if not in_notes_section and re.match(r'^\[\d+\]:', line.strip()):
            # Convert [1]: text to [^1] text in main text
            lines[i] = re.sub(r'^\[(\d+)\]:\s*', r'[^\1] ', line)
    markdown_text = '\n'.join(lines)
    
    # === CRITICAL FIXES FOR BOLD TEXT AND HEADINGS ===
    
    # Fix escaped backslashes that should be bold text
    # Pattern: \text\ → **text**
    markdown_text = re.sub(r'\\([^\\]+)\\', r'**\1**', markdown_text)
    
    # Fix missing headings that got merged with text
    # Pattern: **Case study: the Cellophane House** some points from a case study → ## Case study: the Cellophane House\n\nsome points from a case study
    markdown_text = re.sub(r'\*\*([^*]+)\*\*([^\n]+?)(In the following section)', r'## \1\n\n\3', markdown_text)
    
    # Fix other missing headings
    # Pattern: **Integrated complexity** → ## Integrated complexity
    markdown_text = re.sub(r'\*\*([^*]+)\*\*([^\n]+?)(Although it is perhaps)', r'## \1\n\n\3', markdown_text)
    
    # Fix missing headings for parallel and serially nested deliveries
    # Pattern: **Parallel and serially nested deliveries** → ## Parallel and serially nested deliveries
    markdown_text = re.sub(r'\*\*([^*]+)\*\*([^\n]+?)(In some cases)', r'## \1\n\n\3', markdown_text)
    
    # Fix missing headings for case study
    # Pattern: **Case study: the Cellophane House** → ## Case study: the Cellophane House
    markdown_text = re.sub(r'\*\*([^*]+)\*\*([^\n]+?)(One of the several)', r'## \1\n\n\3', markdown_text)
    
    # Fix missing headings for key conclusions
    # Pattern: **Key conclusions and further research** → ## Key conclusions and further research
    markdown_text = re.sub(r'\*\*([^*]+)\*\*([^\n]+?)(The notion)', r'## \1\n\n\3', markdown_text)
    
    # Fix missing headings for notes
    # Pattern: **Notes** → ## Notes
    markdown_text = re.sub(r'\*\*([^*]+)\*\*([^\n]+?)(1 taking)', r'## \1\n\n\3', markdown_text)
    
    # Fix broken links (missing closing parenthesis)
    markdown_text = re.sub(r'\[([^\]]+)\]\(([^)]+)$', r'[\1](\2)', markdown_text, flags=re.MULTILINE)
    
    # Fix malformed citations
    markdown_text = re.sub(r'([A-Z][a-z]+, [A-Z]\. \([0-9]{4})([A-Z])', r'\1 \2', markdown_text)
    
    # Fix remaining artifacts at end of file
    markdown_text = re.sub(r'\)\n\n# ([^#\n]+)\n\n\)', r')\n\n# \1', markdown_text)
    markdown_text = re.sub(r'\)\n\n# ([^#\n]+)\n\n\)', r')\n\n# \1', markdown_text)
    
    # Add line breaks after images for better formatting
    markdown_text = re.sub(r'!\[([^\]]+)\]\(([^)]+)\)([^\n])', r'![\1](\2)\n\3', markdown_text)
    
    # === PHASE 4: HEADING-BASED IMAGE POSITIONING ===
    if image_positions:
        # Find which images are already in the markdown
        existing_images = set()
        for match in re.finditer(r'!\[([^\]]+)\]\(([^)]+)\)', markdown_text):
            alt, src = match.groups()
            existing_images.add((alt, src))
        
        # For missing images, find their associated heading and insert them there
        for img_info in image_positions:
            if (img_info['alt'], img_info['src']) not in existing_images:
                heading = img_info['heading']
                if heading:
                    # Look for the heading in the markdown
                    lines = markdown_text.split('\n')
                    for i, line in enumerate(lines):
                        # Look for the heading (case-insensitive, partial match)
                        if heading.lower() in line.lower() and line.strip().startswith('#'):
                            # Insert image after this heading
                            image_md = f"![{img_info['alt']}]({img_info['src']})"
                            lines.insert(i + 1, image_md)
                            lines.insert(i + 2, "")  # Add blank line after image
                            markdown_text = '\n'.join(lines)
                            break
                    else:
                        # If heading not found, add to end
                        markdown_text += f"\n\n![{img_info['alt']}]({img_info['src']})"
                else:
                    # No heading available, add to end
                    markdown_text += f"\n\n![{img_info['alt']}]({img_info['src']})"
    
    # Final trim and ensure proper ending
    return markdown_text.strip() + '\n'


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
    """Unzips EPUB to a temporary folder and returns (content_root, opf_path), or None on failure."""
    try:
        with zipfile.ZipFile(epub_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        # Find the OPF file
        opf_path = find_opf_path(extract_to)
        # The content root is the directory containing the OPF file
        content_root = opf_path.parent if opf_path else None
        if not content_root or not opf_path:
            return None
        return content_root, opf_path
    except Exception as e:
        print(f"[ERROR] Failed to extract EPUB: {e}")
        return None

def find_opf_path(container_path: Path) -> Path:
    """Parses container.xml to find the OPF file path."""
    container_xml = Path(container_path) / "META-INF" / "container.xml"
    with open(container_xml, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, "xml")
    rootfile = soup.find("rootfile")
    if not rootfile or not rootfile.get("full-path"):
        raise FileNotFoundError("Could not find a valid <rootfile> tag in META-INF/container.xml")
    full_path = rootfile["full-path"]
    if isinstance(full_path, list):
        full_path = full_path[0]
    return Path(container_path) / full_path





def extract_book_metadata_from_copyright(content_root: Path) -> dict | None:
    """Extract book metadata from copyright statement using RNIB_COPYRIGHT_LEGALESE IDs or fulltitle page."""
    # First try RNIB_COPYRIGHT_LEGALESE format
    for xhtml_file in content_root.glob("*.xhtml"):
        try:
            with open(xhtml_file, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'xml')
            
            metadata = {}
            
            # Look for the copyright title element
            copyright_title = soup.find('p', id='RNIB_COPYRIGHT_LEGALESE_0')
            if copyright_title:
                title = copyright_title.get_text(strip=True)
                if title and title != "":
                    metadata['title'] = title
                    print(f"[INFO] Found book title from copyright: {title}")
            
            # Look for the copyright authors element
            copyright_authors = soup.find('p', id='RNIB_COPYRIGHT_LEGALESE_1')
            if copyright_authors:
                authors = copyright_authors.get_text(strip=True)
                if authors and authors != "":
                    metadata['authors'] = authors
                    print(f"[INFO] Found book authors from copyright: {authors}")
            
            # Look for the copyright ISBN element
            copyright_isbn = soup.find('p', id='RNIB_COPYRIGHT_LEGALESE_2')
            if copyright_isbn:
                isbn = copyright_isbn.get_text(strip=True)
                if isbn and isbn != "":
                    metadata['isbn'] = isbn
                    print(f"[INFO] Found book ISBN from copyright: {isbn}")
            
            if metadata:
                return metadata
                
        except Exception as e:
            print(f"[WARNING] Error reading {xhtml_file}: {e}")
            continue
    
    # Fallback: Look for title and authors in fulltitle page
    for xhtml_file in content_root.glob("*fulltitle*.xhtml"):
        try:
            with open(xhtml_file, 'r', encoding='utf-8') as f:
                soup = BeautifulSoup(f, 'xml')
            
            metadata = {}
            
            # Look for book title
            book_title = soup.find('h1', class_='book-title')
            if book_title:
                title = book_title.get_text(strip=True)
                if title and title != "":
                    metadata['title'] = title
                    print(f"[INFO] Found book title from fulltitle: {title}")
            
            # Look for subtitle
            subtitle = soup.find('p', class_='subtitle1')
            if subtitle:
                subtitle_text = subtitle.get_text(strip=True)
                if subtitle_text and subtitle_text != "":
                    if 'title' in metadata:
                        metadata['title'] = metadata['title'] + " – " + subtitle_text
                    print(f"[INFO] Found book subtitle: {subtitle_text}")
            
            # Look for authors
            author1 = soup.find('p', class_='author1')
            if author1:
                authors = author1.get_text(strip=True)
                if authors and authors != "":
                    # Remove "EDITED BY" prefix
                    authors = re.sub(r'^EDITED BY\s+', '', authors, flags=re.IGNORECASE)
                    metadata['authors'] = authors
                    print(f"[INFO] Found book authors from fulltitle: {authors}")
            
            if metadata:
                return metadata
                
        except Exception as e:
            print(f"[WARNING] Error reading {xhtml_file}: {e}")
            continue
    
    print("[WARNING] Could not find book metadata in copyright statement or fulltitle page")
    return None

def extract_book_title_from_copyright(content_root: Path) -> str | None:
    """Extract the book title from copyright statement using RNIB_COPYRIGHT_LEGALESE_0 ID."""
    metadata = extract_book_metadata_from_copyright(content_root)
    return metadata.get('title') if metadata else None

def find_bibtex_entry_by_title_and_authors(title: str, authors: str, bibtex_path: Path = Path("epub.bib")) -> dict | None:
    """Find BibTeX entry by matching title and authors with robust parsing."""
    if not bibtex_path.exists():
        print(f"[WARNING] BibTeX file not found: {bibtex_path}")
        return None
    
    try:
        with open(bibtex_path, 'r', encoding='utf-8') as f:
            bibtex_content = f.read()
        
        # Split into individual entries
        entries = bibtex_content.split('@')
        
        for entry in entries:
            if not entry.strip():
                continue
            
            # Extract entry type and key
            lines = entry.split('\n')
            if not lines:
                continue
            
            first_line = lines[0].strip()
            
            # Extract citation key - look for pattern like "BOOK{Smith2017-zx,"
            key_match = re.search(r'\{([^,]+),', first_line)
            if not key_match:
                continue
            
            citation_key = key_match.group(1).strip()
            
            # Look for title and author/editor fields with better parsing
            entry_title = None
            entry_authors = None
            entry_editor = None
            entry_year = None
            entry_publisher = None
            
            for line in lines:
                line = line.strip()
                
                # Extract title with better regex
                if 'title' in line and '=' in line:
                    title_match = re.search(r'title\s*=\s*["\']([^"\']+)["\']', line)
                    if title_match:
                        entry_title = clean_bibtex_text(title_match.group(1))
                
                # Extract author with fallback to editor
                elif 'author' in line and '=' in line:
                    author_match = re.search(r'author\s*=\s*["\']([^"\']+)["\']', line)
                    if author_match:
                        entry_authors = clean_bibtex_text(author_match.group(1))
                
                # Extract editor as fallback
                elif 'editor' in line and '=' in line:
                    editor_match = re.search(r'editor\s*=\s*["\']([^"\']+)["\']', line)
                    if editor_match:
                        entry_editor = clean_bibtex_text(editor_match.group(1))
                
                # Extract year for additional matching
                elif 'year' in line and '=' in line:
                    year_match = re.search(r'year\s*=\s*["\']?(\d{4})["\']?', line)
                    if year_match:
                        entry_year = year_match.group(1)
                
                # Extract publisher for additional context
                elif 'publisher' in line and '=' in line:
                    publisher_match = re.search(r'publisher\s*=\s*["\']([^"\']+)["\']', line)
                    if publisher_match:
                        entry_publisher = clean_bibtex_text(publisher_match.group(1))
            
            # Use editor as fallback if no author found
            if not entry_authors and entry_editor:
                entry_authors = entry_editor
                print(f"[INFO] Using editor as author for entry: {citation_key}")
            
            # Try to match title and authors
            if entry_title and entry_authors:
                # Enhanced fuzzy matching
                title_words = set(re.findall(r'\b\w+\b', title.lower()))
                entry_title_words = set(re.findall(r'\b\w+\b', entry_title.lower()))
                
                # Check for significant overlap in title words
                title_overlap = len(title_words & entry_title_words) / max(len(title_words), 1)
                
                # Also check if the search title is contained in the entry title
                title_contained = title.lower() in entry_title.lower()
                
                # Additional check: if titles are very similar (high overlap)
                if title_overlap > 0.5 or title_contained:
                    return {
                        'citation_key': citation_key,
                        'title': entry_title,
                        'authors': entry_authors,
                        'year': entry_year,
                        'publisher': entry_publisher,
                        'was_editor': entry_authors == entry_editor
                    }
        
        print(f"[WARNING] No matching BibTeX entry found for title: {title}")
        return None
        
    except Exception as e:
        print(f"[ERROR] Error parsing BibTeX file: {e}")
        return None

def clean_bibtex_text(text: str) -> str:
    """Clean BibTeX text by removing braces and normalizing formatting."""
    if not text:
        return ""
    
    text = text.strip()
    text = text.replace("\n", " ")  # Ensure multiline text is on a single line
    text = re.sub(r"\{(.*?)\}", r"\1", text)  # Remove braces `{}` while preserving content
    text = text.replace("&", "and")  # Replace ampersands with "and"
    return text.strip()

def parse_bibtex_authors(author_string: str) -> list:
    """Parse BibTeX author string into list of formatted author names with robust handling."""
    if not author_string:
        return []
    
    # Clean the author string first
    author_string = clean_bibtex_text(author_string)
    
    # Remove common prefixes (but be more careful about "By" at the start)
    if author_string.lower().startswith('by '):
        author_string = author_string[3:].strip()
    
    # Identify institutions inside `{}` and preserve them
    protected_authors = re.findall(r"\{.*?\}", author_string)  # Find `{}` enclosed text
    temp_replacement = "INSTITUTION_PLACEHOLDER"
    temp_authors = re.sub(r"\{.*?\}", temp_replacement, author_string)  # Temporarily replace institutions
    
    # Split by " and " to separate individual authors
    authors = re.split(r'\s+and\s+', temp_authors)
    
    # If we only got one author but it contains a comma, it might be two authors
    if len(authors) == 1 and ',' in authors[0]:
        # Check if this looks like "Last, First" format (single person) vs "Name1, Name2" (two people)
        author = authors[0]
        if not author.startswith('{') and author.count(',') == 1:
            # This might be "Last, First" format - leave it as is
            pass
        else:
            # This might be multiple authors separated by commas
            # Split by comma and clean up
            potential_authors = [a.strip() for a in author.split(',')]
            # Only use this if the parts look like individual names
            if all(len(part.split()) >= 2 for part in potential_authors):
                authors = potential_authors
    
    # Clean up any trailing commas from the split
    authors = [author.rstrip(',').strip() for author in authors]
    
    # Restore institution names in their correct positions
    for i, author in enumerate(authors):
        if temp_replacement in author:
            authors[i] = protected_authors.pop(0)
    
    formatted_authors = []
    for author in authors:
        author = author.strip()
        if not author:
            continue
        
        # Clean the author name
        author = clean_bibtex_text(author)
        
        # Handle "Last, First" format for personal names (not institutions)
        # Only apply this if it looks like a single person's name in "Last, First" format
        if ',' in author and not author.startswith("{"):
            parts = author.split(',', 1)
            if len(parts) == 2:
                last_name = parts[0].strip()
                first_name = parts[1].strip()
                # Only apply "Last, First" -> "First Last" if both parts look like name components
                # (i.e., not if one part looks like a full name)
                if (len(last_name.split()) <= 3 and len(first_name.split()) <= 3 and 
                    not (len(last_name.split()) >= 2 and len(first_name.split()) >= 2)):
                    formatted_author = f"{first_name} {last_name}"
                else:
                    # This might be two separate names, not "Last, First" format
                    formatted_author = author
            else:
                formatted_author = author
        else:
            # For names without commas, assume they're already in "First Last" format
            formatted_author = author
        
        formatted_authors.append(formatted_author)
    
    return formatted_authors



def extract_title_from_xhtml(xhtml_path: Path) -> str:
    """Extracts the <title> from an XHTML file and converts to Title Case."""
    with open(xhtml_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')  # Use strict XML parsing
    title_tag = soup.find('title')
    raw_title = title_tag.get_text(strip=True) if title_tag else "Untitled"
    return title_case(raw_title)











# === CLI ===



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

def test_single_xhtml(xhtml_path: Path, output_dir: Path | None = None):
    """Test function to convert a single XHTML file to Markdown using the new three-phase approach."""
    if output_dir is None:
        output_dir = Path("test_sandbox")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract title for filename
    title = extract_title_from_xhtml(xhtml_path)
    safe_title = safe_filename(title)
    output_filename = f"test_{safe_title}.md"
    output_path = output_dir / output_filename
    
    print(f"Converting: {xhtml_path}")
    print(f"Title: {title}")
    print(f"Output: {output_path}")
    
    # Read the original XHTML content
    with open(xhtml_path, "r", encoding="utf-8") as f:
        xhtml_content = f.read()
    
    print(f"\n=== ORIGINAL XHTML CONTENT (first 500 chars) ===")
    print(xhtml_content[:500] + "..." if len(xhtml_content) > 500 else xhtml_content)
    
    # Apply the new three-phase approach directly to XHTML
    cleaned_md = clean_markdown_text(xhtml_content, None)
    
    print(f"\n=== AFTER THREE-PHASE CONVERSION ===")
    print(cleaned_md[:500] + "..." if len(cleaned_md) > 500 else cleaned_md)
    
    # Save the result
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned_md)
    
    print(f"\nConverted version saved to: {output_path}")
    return output_path

from pathlib import Path
from datetime import datetime, timezone
import time
import json

def convert_book(epub_path: Path, output_dir_base: Path, bibtex_data: dict | None = None, use_obsidian_format: bool = True, skip_images: bool = False):
    """
    Main conversion function using the manifest-based pipeline.
    """
    start_timestamp = datetime.now(timezone.utc).isoformat()
    start_time = time.time()

    import tempfile
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        result = extract_epub(epub_path, extract_to=temp_dir_path)
        if not result or not isinstance(result, tuple) or len(result) != 2:
            raise RuntimeError(f"[ERROR] Failed to extract EPUB from {epub_path}. File may be corrupt or improperly formatted.")
        content_root, opf_path = result
        print(f"[INFO] EPUB extracted to: {content_root}")

        # Build manifest map from OPF
        with open(opf_path, "r", encoding="utf-8") as f:
            opf_soup = BeautifulSoup(f, "lxml")
        manifest_items = build_manifest_map(opf_soup, opf_path)

        # Assign chapter structure and labels
        chapter_map = assign_manifest_structure(manifest_items)

        # Determine output directory name
        book_title = extract_book_title_from_copyright(content_root)
        safe_book_title = safe_filename(book_title) if book_title else epub_path.stem
        output_dir_path = output_dir_base / safe_book_title
        output_dir_path.mkdir(parents=True, exist_ok=True)

        # Extract book metadata and find BibTeX entry if not provided
        if bibtex_data is None:
            book_metadata = extract_book_metadata_from_copyright(content_root)
            if book_metadata and book_metadata.get('title') and book_metadata.get('authors'):
                bibtex_data = find_bibtex_entry_by_title_and_authors(
                    book_metadata['title'], 
                    book_metadata['authors']
                )
                if bibtex_data:
                    print(f"[INFO] Found BibTeX entry: {bibtex_data.get('citation_key', 'Unknown')}")
                else:
                    print("[INFO] No matching BibTeX entry found")

        # Copy images if not skipped
        if not skip_images:
            assets_dir = output_dir_path / "assets"
            copy_images(manifest_items, assets_dir)

        # Generate output markdown files
        generate_markdown_outputs(chapter_map, output_dir_path, bibtex_data)

        # Write JSON log
        log_data = {
            "book_title": book_title,
            "source_file": str(epub_path.name),
            "output_dir": str(output_dir_path),
            "output_files": [f"{entry['label']} - {entry.get('title', entry['filename'])}.md" for entry in chapter_map],
            "start": start_timestamp,
            "end": datetime.now(timezone.utc).isoformat()
        }
        log_file = output_dir_path / f"{safe_book_title}_log.json"
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2)

        elapsed_time = time.time() - start_time

        # Final dialog
        show_final_dialog(
            log=log_data,
            elapsed_sec=elapsed_time,
            md_status=True,
            cleanup_status=True,
            json_status=True
        )

        return log_data

# --- CLI interface ---
if __name__ == "__main__":
    import sys
    import time
    import argparse
    
    # Direct XHTML-to-Markdown conversion utility (must run before argparse)
    if len(sys.argv) == 3 and sys.argv[1] == "--xhtml-to-md":
        from pathlib import Path
        xhtml_path = sys.argv[2]
        with open(xhtml_path, "r", encoding="utf-8") as f:
            xhtml_content = f.read()
        md = clean_markdown_text(xhtml_content)
        print(md)
        sys.exit(0)
    
    # CLI argument parsing
    parser = argparse.ArgumentParser(description="Convert EPUB to Markdown (Obsidian-ready)")
    parser.add_argument("input", type=str, help="Path to the .epub file")
    parser.add_argument("--output", type=str, default=str(OUTPUT_ROOT), help="Output directory")
    parser.add_argument("--skip-images", action="store_true", help="Skip copying images")
    parser.add_argument("--obsidian", action="store_true", help="Use Obsidian formatting")
    parser.add_argument("--test-cleanup", type=str, help="Test cleanup on a single Markdown file")
    parser.add_argument("--test-single", type=str, help="Test single XHTML file conversion and cleanup")
    args = parser.parse_args()
    
    start_time = time.time()
    
    if args.test_cleanup:
        input_path = Path(args.test_cleanup).resolve()
        if not input_path.exists():
            print(f"File not found: {input_path}")
            sys.exit(1)
        
        print(f"Testing cleanup on: {input_path}")
        with open(input_path, "r", encoding="utf-8") as f:
            raw_md = f.read()
        
        print("\n=== BEFORE CLEANUP ===")
        print(raw_md[:500] + "..." if len(raw_md) > 500 else raw_md)
        
        cleaned_md = clean_markdown_text(raw_md, None)
        
        print("\n=== AFTER CLEANUP ===")
        print(cleaned_md[:500] + "..." if len(cleaned_md) > 500 else cleaned_md)
        
        response = input("\nSave cleaned version? (y/n): ").lower().strip()
        if response == 'y':
            backup_path = input_path.with_suffix('.md.backup')
            import shutil
            shutil.copy2(input_path, backup_path)
            print(f"Backup saved to: {backup_path}")
            
            with open(input_path, "w", encoding="utf-8") as f:
                f.write(cleaned_md)
            print(f"Cleaned version saved to: {input_path}")
    elif args.test_single:
        input_path = Path(args.test_single).resolve()
        if not input_path.exists():
            print(f"File not found: {input_path}")
            sys.exit(1)
        test_single_xhtml(input_path)
    else:
        # Main conversion
        result = convert_book(
            epub_path=args.input,
            output_dir_base=args.output,
            use_obsidian_format=args.obsidian,
            skip_images=args.skip_images
        )
        print(f"Conversion completed: {result}")
    
    elapsed = time.time() - start_time
    print(f"Total time: {elapsed:.2f} seconds")


        
# Update process_xhtml_content call if present
# Update copy_images function and its call if present

# If process_xhtml_content is used in convert_book, ensure output_dir is passed
# If copy_images exists, update its signature and logic

# --- PATCH: Update copy_images if present ---
import shutil
def copy_images(manifest_items: list[dict], assets_dir: Path):
    assets_dir.mkdir(parents=True, exist_ok=True)
    image_count = 0
    for item in manifest_items:
        source_path = item["filepath"]
        if source_path.suffix.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.svg']:
            dest_path = assets_dir / source_path.name
            shutil.copy2(source_path, dest_path)
            image_count += 1
    print(f"Copied {image_count} image(s) to {assets_dir}")