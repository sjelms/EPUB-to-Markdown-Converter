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
    markdown_text = md(
        str(soup),
        heading_style="ATX",
        em_symbol="*",
        strong_symbol="**",
        bullets="-",
        code_symbol="`",
        strip=['script', 'style'],
    )
    
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
    """Parses toc.xhtml and returns a list of (filename, anchor, label, depth) in TOC order."""
    from bs4 import BeautifulSoup
    from bs4.element import Tag
    with open(toc_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')  # Use strict XML parsing

    toc_entries = []

    def process_ol(ol_tag, depth=1):
        for li in ol_tag.find_all('li', recursive=False):
            a_tag = li.find('a', href=True)
            if a_tag and isinstance(a_tag, Tag):
                href = a_tag.get('href', '')
                if isinstance(href, list):
                    href = href[0] if href else ''
                label = a_tag.get_text(strip=True)
                if href and '.xhtml' in href:
                    if '#' in href:
                        file_part, anchor = href.split('#', 1)
                    else:
                        file_part, anchor = href, None
                    toc_entries.append((file_part, anchor, label, depth))
            nested_ol = li.find('ol', recursive=False)
            if nested_ol and isinstance(nested_ol, Tag):
                process_ol(nested_ol, depth + 1)

    nav = soup.find('nav')
    if nav and isinstance(nav, Tag):
        ol = nav.find('ol')
        if ol and isinstance(ol, Tag):
            process_ol(ol)
    else:
        # fallback to flat structure
        for a in soup.find_all('a', href=True):
            if isinstance(a, Tag):
                href = a.get('href', '')
                if isinstance(href, list):
                    href = href[0] if href else ''
                label = a.get_text(strip=True)
                if href and '.xhtml' in href:
                    if '#' in href:
                        file_part, anchor = href.split('#', 1)
                    else:
                        file_part, anchor = href, None
                    toc_entries.append((file_part, anchor, label, 1))
    return toc_entries

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

def generate_yaml_header(title: str, chapter: str, authors: list, citation_key: str, toc_filename: str) -> str:
    """Generate YAML header for Obsidian Markdown files."""
    yaml_lines = ["---"]
    
    # Convert colons to hyphens in title to prevent YAML formatting issues
    safe_title = title.replace(":", " - ")
    yaml_lines.append(f"title: {safe_title}")
    
    # Remove .md extension from chapter
    chapter_without_ext = chapter.replace(".md", "")
    yaml_lines.append(f"chapter: {chapter_without_ext}")
    
    yaml_lines.append(f'toc: "[[{toc_filename.replace(".md", "")}]]"')
    
    # Add authors
    for i, author in enumerate(authors, 1):
        yaml_lines.append(f'author-{i}: "[[{author}]]"')
    
    # Add citation key
    yaml_lines.append(f'citation-key: "[[@{citation_key}]]"')
    yaml_lines.append("---")
    
    return "\n".join(yaml_lines)

def extract_title_from_xhtml(xhtml_path: Path) -> str:
    """Extracts the <title> from an XHTML file and converts to Title Case."""
    with open(xhtml_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')  # Use strict XML parsing
    title_tag = soup.find('title')
    raw_title = title_tag.get_text(strip=True) if title_tag else "Untitled"
    return title_case(raw_title)

def extract_xhtml_metadata(xhtml_path: Path) -> dict:
    """
    Extract comprehensive metadata from XHTML file including:
    - title
    - body type (frontmatter, bodymatter, backmatter)
    - section id and type
    - chapter information
    
    ENHANCED: Now searches for IDs on ANY tag within the body, not just section/div tags.
    This fixes the subsection detection issue where level IDs are placed on h1, h2, p tags, etc.
    """
    with open(xhtml_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')
    
    metadata = {
        'title': "Untitled",
        'body_type': None,
        'section_id': None,
        'section_type': None,
        'is_frontmatter': False,
        'is_chapter': False,
        'is_backmatter': False,
        'chapter_number': None,
        'level': None,
        'subsection_number': None,
        'all_ids': []  # NEW: Track all IDs in the file
    }
    
    # Extract title
    title_tag = soup.find('title')
    if title_tag:
        raw_title = title_tag.get_text(strip=True)
        metadata['title'] = title_case(raw_title)
    
    # Extract body type from body tag
    body_tag = soup.find('body')
    if body_tag and isinstance(body_tag, Tag):
        metadata['body_type'] = body_tag.get('epub:type')
    
    # --- ENHANCED SECTION ID DETECTION ---
    # Find ALL tags in the body that have ID attributes, not just the first one
    # This is crucial for detecting subsections that are anchors within the same file
    if body_tag and isinstance(body_tag, Tag):
        all_id_tags = body_tag.find_all(id=True)
        for tag in all_id_tags:
            if isinstance(tag, Tag) and tag.get('id'):
                metadata['all_ids'].append(tag.get('id'))
    
    # Use the first ID for primary classification (usually the main section/chapter ID)
    if metadata['all_ids']:
        primary_id = metadata['all_ids'][0]
        metadata['section_id'] = primary_id
        
        # Get the type from the first tag with an ID
        first_id_tag = None
        if body_tag and isinstance(body_tag, Tag):
            first_id_tag = body_tag.find(id=primary_id)
        if first_id_tag and isinstance(first_id_tag, Tag):
            metadata['section_type'] = first_id_tag.get('epub:type')
    # --- END ENHANCED SECTION ---
    
    # Determine content type based on metadata
    section_id = str(metadata['section_id'] or "")
    body_type = str(metadata['body_type'] or "")
    section_type = str(metadata['section_type'] or "")
    title_upper = metadata['title'].upper()
    
    # Frontmatter detection (comprehensive)
    if (body_type == "frontmatter" or 
        section_id.startswith("frontmatter_") or
        section_id.startswith("page_") or  # Roman numeral pages
        "titlepage" in section_type or
        "toc" in section_type or
        "preface" in section_id.lower() or
        "acknowledgements" in section_id.lower() or
        "abouttheauthors" in section_id.lower() or
        "introduction" in section_id.lower() or
        title_upper in ["CONTENTS", "ACKNOWLEDGEMENTS", "ABOUT THE AUTHORS", "INTRODUCTION"]):
        metadata['is_frontmatter'] = True
    
    # Chapter detection (comprehensive)
    elif (section_id.startswith("ch") or
          section_id.startswith("chapter") or
          section_id.startswith("Sec") or  # Springer format
          section_type == "chapter" or
          (title_upper and "CHAPTER" in title_upper)):
        metadata['is_chapter'] = True
        # Extract chapter number from various formats using regex for better reliability
        if section_id.startswith("ch"):
            try:
                match = re.search(r'\d+', section_id)
                if match:
                    metadata['chapter_number'] = int(match.group())
            except (ValueError, AttributeError):
                pass
        elif section_id.startswith("chapter"):
            try:
                match = re.search(r'\d+', section_id)
                if match:
                    metadata['chapter_number'] = int(match.group())
            except (ValueError, AttributeError):
                pass
        elif section_id.startswith("Sec"):
            try:
                match = re.search(r'\d+', section_id)
                if match:
                    metadata['chapter_number'] = int(match.group())
            except (ValueError, AttributeError):
                pass
        # Extract from title if section_id doesn't have number
        elif "CHAPTER" in title_upper:
            match = re.search(r'CHAPTER\s+(\d+)', title_upper)
            if match:
                try:
                    metadata['chapter_number'] = int(match.group(1))
                except ValueError:
                    pass
    
    # Level detection within chapters (comprehensive)
    # ENHANCED: More robust regex parsing to handle variations in level ID formats
    elif section_id.startswith("level"):
        parts = section_id.split("_")
        if len(parts) >= 2:
            level_part = parts[0]
            if level_part.startswith("level"):
                try:
                    metadata['level'] = int(level_part[5:])
                    # Extract subsection number from the second part using regex
                    if len(parts) >= 2:
                        try:
                            # Use regex to find number in case of extra chars
                            match = re.search(r'\d+', parts[1])
                            if match:
                                metadata['subsection_number'] = int(match.group())
                        except (ValueError, AttributeError):
                            pass
                except (ValueError, AttributeError):
                    pass
    
    # Backmatter detection (comprehensive)
    elif (section_id in ["references", "index", "glossary", "bibliography", "conclusion"] or
          title_upper in ["REFERENCES", "INDEX", "GLOSSARY", "BIBLIOGRAPHY", "CONCLUSION"] or
          "references" in section_id.lower() or
          "index" in section_id.lower()):
        metadata['is_backmatter'] = True
    
    return metadata

def extract_subsections_from_xhtml(xhtml_path: Path) -> list:
    """
    Extract all subsections from an XHTML file based on level IDs.
    Returns a list of subsection metadata for files that contain multiple subsections.
    This handles the case where subsections are anchors within the same XHTML file as the chapter.
    """
    with open(xhtml_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'xml')
    
    subsections = []
    body_tag = soup.find('body')
    
    if not body_tag or not isinstance(body_tag, Tag):
        return subsections
    
    # Find all tags with level IDs (level1_000001, level2_000002, etc.)
    level_tags = body_tag.find_all(id=True)
    level_tags = []
    for tag in body_tag.find_all(id=True):
        if isinstance(tag, Tag):
            tag_id = tag.get('id')
            if tag_id and isinstance(tag_id, str) and re.match(r'^level\d+_', tag_id):
                level_tags.append(tag)
    
    for tag in level_tags:
        if isinstance(tag, Tag):
            section_id = tag.get('id', '')
            if not section_id or not isinstance(section_id, str):
                continue
            
            # Parse level and subsection number
            parts = section_id.split('_')
            if len(parts) >= 2:
                level_part = parts[0]
                if level_part.startswith('level'):
                    try:
                        level = int(level_part[5:])
                        # Extract subsection number
                        match = re.search(r'\d+', parts[1])
                        subsection_num = int(match.group()) if match else 0
                        
                        # Extract title from the tag content
                        title = tag.get_text(strip=True)
                        if not title:
                            # Try to find a heading within this tag
                            heading = tag.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
                            if heading and isinstance(heading, Tag):
                                title = heading.get_text(strip=True)
                        
                        if title:
                            subsections.append({
                                'section_id': section_id,
                                'level': level,
                                'subsection_number': subsection_num,
                                'title': title_case(title),
                                'tag_name': tag.name
                            })
                    except (ValueError, AttributeError):
                        continue
    
    # Sort subsections by level and subsection number
    subsections.sort(key=lambda x: (x['level'], x['subsection_number']))
    return subsections

def is_chapter_boundary(title: str, label: str) -> bool:
    """
    Determine if a TOC entry represents a new chapter boundary.
    Returns True if this should start a new chapter group.
    """
    import re
    title_upper = title.upper()
    label_upper = label.upper()
    
    # Primary patterns for chapter detection
    chapter_patterns = [
        r'^CHAPTER\s+\d+',           # "CHAPTER 1", "CHAPTER 2"
        r'^SECTION\s+\d+',           # "SECTION 1", "SECTION 2" 
        r'^PART\s+\d+',              # "PART 1", "PART 2"
        r'^\d+\.\s+[A-Z]',           # "1. INTRODUCTION", "2. METHODS"
        r'^[A-Z][A-Z\s]{10,}$',      # Long all-caps titles (likely chapters)
        r'^INTRODUCTION$',            # Common chapter title
        r'^CONCLUSION$',              # Common chapter title
        r'^\d+\s*[-–]\s*[A-Z]',      # "1 - TITLE" format
        r'^APPENDIX\s*[A-Z]?$',      # "APPENDIX A", "APPENDIX"
        r'^BIBLIOGRAPHY$',           # Common back matter
        r'^REFERENCES$',              # Common back matter
        r'^GLOSSARY$',                # Common back matter
        r'^INDEX$'                    # Common back matter
    ]
    
    # Check title patterns
    for pattern in chapter_patterns:
        if re.match(pattern, title_upper):
            return True
        if re.match(pattern, label_upper):
            return True
    
    # Additional heuristics
    if len(title_upper) > 50 and title_upper.isupper():
        return True  # Very long uppercase titles are likely chapters
        
    return False

def validate_chapter_groups(chapter_groups, max_expected_chapters=20):
    """
    Validate chapter grouping results and apply fallbacks if needed.
    If we detect too many single-file chapters, apply alternative grouping.
    """
    single_file_chapters = sum(1 for _, _, files in chapter_groups if len(files) == 1)
    total_chapters = len(chapter_groups)
    
    # Check for over-grouping (chapters with too many files)
    oversized_chapters = sum(1 for _, _, files in chapter_groups if len(files) > 10)
    
    # If more than 70% are single-file chapters and we have many chapters, 
    # this suggests our detection failed
    if total_chapters > max_expected_chapters or (single_file_chapters / total_chapters) > 0.7:
        print(f"[WARNING] Detected {total_chapters} chapters with {single_file_chapters} single-file chapters")
        print("[WARNING] This suggests chapter detection may have failed")
        return False
    
    # If we have oversized chapters, that's also concerning
    if oversized_chapters > 0:
        print(f"[WARNING] Detected {oversized_chapters} chapters with more than 10 files")
        print("[WARNING] This suggests over-grouping may have occurred")
        return False
    
    return True

def build_spine_driven_structure(opf_soup, content_root: Path) -> tuple:
    """
    NEW FUNCTION: Build chapter structure based on the spine in content.opf.
    This method uses the spine (reading order) and heading structure from XHTML files
    instead of relying on a nav.xhtml or toc.xhtml which may not be present.
    """
    print("\n=== BUILDING SPINE-DRIVEN STRUCTURE ===")

    # Parse manifest and spine
    manifest = {item["id"]: item for item in [
        {"id": item.get("id"), "href": item.get("href"), "media-type": item.get("media-type")}
        for item in opf_soup.find_all("item")
    ]}
    spine_ids = [item.get("idref") for item in opf_soup.find_all("itemref") if item.get("idref")]

    # Resolve hrefs for spine items
    spine_files = [manifest[item_id]["href"] for item_id in spine_ids if item_id in manifest]

    # Extract metadata for each spine file
    chapter_groups = []
    frontmatter_files = []
    backmatter_files = []

    chapter_index = 1
    current_chapter_files = []
    current_chapter_title = None

    for file in spine_files:
        xhtml_path = content_root / file
        if not xhtml_path.exists():
            print(f"[WARNING] Missing file in spine: {file}")
            continue

        metadata = extract_xhtml_metadata(xhtml_path)
        title = metadata.get("title") or file

        # Determine section type
        if metadata.get("is_frontmatter"):
            frontmatter_files.append(file)
        elif metadata.get("is_backmatter"):
            if current_chapter_files:
                chapter_groups.append((chapter_index, current_chapter_title or "Untitled", current_chapter_files))
                chapter_index += 1
                current_chapter_files = []
            backmatter_files.append(file)
        elif metadata.get("is_chapter"):
            if current_chapter_files:
                chapter_groups.append((chapter_index, current_chapter_title or "Untitled", current_chapter_files))
                chapter_index += 1
            current_chapter_files = [file]
            current_chapter_title = title
        else:
            current_chapter_files.append(file)

    # Add the final chapter if one is open
    if current_chapter_files:
        chapter_groups.append((chapter_index, current_chapter_title or "Untitled", current_chapter_files))

    # Print summary
    print(f"Frontmatter files: {len(frontmatter_files)}")
    print(f"Chapters: {len(chapter_groups)}")
    for num, title, files in chapter_groups:
        print(f"  Chapter {num:02d}: {title} ({len(files)} files)")
    print(f"Backmatter files: {len(backmatter_files)}")

    return chapter_groups, frontmatter_files, backmatter_files

# === CLI ===

def generate_obsidian_toc(conversion_log, output_dir: Path, book_title: str | None = None):
    """Create a Markdown-formatted TOC compatible with Obsidian based on actual output files."""
    book_title = book_title or ""
    toc_lines = ["# Table of Contents", ""]
    # Sort chapters by their index to maintain proper order
    sorted_chapters = sorted(conversion_log["chapters"], key=lambda x: x["index"])
    for chapter in sorted_chapters:
        index = chapter["index"]
        title = chapter["title"]
        output_file = chapter["output_file"]
        if "." in index:
            parts = index.split(".")
            if len(parts) >= 2 and parts[1] == "0":
                indent = ""
            else:
                indent = "  "
        else:
            indent = ""
        toc_link = output_file.replace('.md', '')
        toc_lines.append(f"{indent}- [[{toc_link}]]")
    toc_text = "\n".join(toc_lines)
    # Create unique TOC filename based on book title
    safe_book_title = safe_filename(book_title)
    if safe_book_title:
        toc_filename = f"00 - TOC for {safe_book_title}.md"
    else:
        toc_filename = "00 - Table of Contents.md"
    
    toc_path = output_dir / toc_filename
    with open(toc_path, "w", encoding="utf-8") as f:
        f.write(toc_text)
    print(f"TOC written to: {toc_path}")
    
    return toc_filename

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

def convert_book(
    epub_path: str,
    output_dir: str,
    skip_images: bool = False,
    use_obsidian_format: bool = False
) -> dict:
    """
    Core function to convert an EPUB file.
    This function is self-contained and does not use argparse.
    Returns a log dict or result object.
    """
    import sys
    import shutil
    import json
    from pathlib import Path
    from datetime import datetime
    import time

    # Start timer for elapsed time
    start = time.time()
    
    # Convert string paths to Path objects
    epub_file = Path(epub_path).resolve()
    output_dir_base = Path(output_dir)
    
    if not epub_file.exists():
        print(f"File not found: {epub_file}")
        return {"status": "error", "message": f"File not found: {epub_file}"}
    
    epub_abs_path = str(epub_file.resolve())
    SCRIPT_VERSION = "v0.9.0-beta"
    
    start_timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Initialize conversion_log
    conversion_log = {
        "epub": epub_file.name,
        "epub_path": epub_abs_path,
        "output_dir": "",
        "start_time_utc": start_timestamp,
        "images_moved": False,
        "script_version": SCRIPT_VERSION,
        "xhtml_files_in_epub": [],
        "unlinked_files": [],
        "toc_entries": [],
        "chapter_groups": [],
        "warnings": [],
        "chapters": []
    }
    
    temp_dir = Path("/tmp") / f"epub_extract_{epub_file.stem}"
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)
    
    # Extract EPUB contents
    extract_epub(epub_file, temp_dir)
    print(f"EPUB extracted to: {temp_dir}")
    
    opf_path = find_opf_path(temp_dir)
    content_root = opf_path.parent

    # Handle different EPUB folder structures
    potential_content_roots = [
        content_root,
        content_root / "html",
        content_root / "EPUB",
    ]

    actual_content_root = None
    for root in potential_content_roots:
        if root.exists() and any(root.glob("*.xhtml")):
            actual_content_root = root
            break

    if actual_content_root is None:
        actual_content_root = content_root
        print(f"[WARNING] Could not find XHTML files in expected locations, using: {content_root}")

    content_root = actual_content_root
    print(f"[INFO] Using content root: {content_root}")
    
    # Extract book title from copyright statement
    book_title = extract_book_title_from_copyright(content_root)
    if book_title:
        safe_book_title = safe_filename(str(book_title))
        output_dir_path = Path(output_dir_base) / safe_book_title
        print(f"[INFO] Using book title for folder: {safe_book_title}")
    else:
        output_dir_path = Path(output_dir_base) / epub_file.stem
        print(f"[INFO] Using EPUB filename for folder: {epub_file.stem}")

    output_dir_path.mkdir(parents=True, exist_ok=True)
    
    # Update conversion_log
    conversion_log["output_dir"] = str(output_dir_path)
    conversion_log["book_title"] = book_title if book_title else epub_file.stem
    
    # Copy images directory if present
    if not skip_images:
        images_src = content_root / "images"
        images_dst = output_dir_path / "images"
        if images_src.exists() and images_src.is_dir():
            shutil.copytree(images_src, images_dst, dirs_exist_ok=True)
            print(f"Copied images to: {images_dst}")
        conversion_log["images_moved"] = images_src.exists() and images_src.is_dir() and any(images_src.iterdir())
    
    # === SPINE-DRIVEN STRUCTURE ===
    with open(opf_path, "r", encoding="utf-8") as f:
        opf_soup = BeautifulSoup(f, "xml")

    # Use the new spine-driven structure instead of TOC-driven.
    chapter_groups, front_matter, back_matter = build_spine_driven_structure(opf_soup, content_root)

    # Debug output
    print("\n=== SPINE-DRIVEN STRUCTURE RESULTS ===")
    print(f"Total chapters: {len(chapter_groups)}")
    for i, (num, title, files) in enumerate(chapter_groups, 1):
        print(f"Chapter {i}: {title} ({len(files)} files)")
        for j, file in enumerate(files, 1):
            print(f"  {j}. {file}")

    print(f"\nFront matter: {len(front_matter)} files")
    for file in front_matter:
        print(f"  - {file}")

    print(f"\nBack matter: {len(back_matter)} files")
    for file in back_matter:
        print(f"  - {file}")

    print("[INFO] Subsections that are anchors within the same XHTML file will remain as part of that file")

    conversion_log["chapter_groups"] = [
        {"chapter_num": f"{num:02d}", "title": title, "files": group}
        for num, title, group in chapter_groups
    ]

    # Add chapter grouping metadata
    conversion_log["chapter_grouping_metadata"] = {
        "total_chapters": len(chapter_groups),
        "single_file_chapters": sum(1 for _, _, files in chapter_groups if len(files) == 1),
        "multi_file_chapters": sum(1 for _, _, files in chapter_groups if len(files) > 1),
        "max_files_per_chapter": max(len(files) for _, _, files in chapter_groups) if chapter_groups else 0,
        "avg_files_per_chapter": sum(len(files) for _, _, files in chapter_groups) / len(chapter_groups) if chapter_groups else 0,
        "content_root_used": str(content_root),
        "epub_structure_type": "OEBPS/html" if "html" in str(content_root) else "OEBPS" if "OEBPS" in str(content_root) else "EPUB" if "EPUB" in str(content_root) else "Unknown"
    }

    # Assign labels to chapters
    chapter_map = {}
    for num, title, group in chapter_groups:
        label = f"{num:02d}.0"
        for fname in group:
            chapter_map[fname] = label
    
    # Phase 1: Pandoc Conversion
    temp_md_dir = temp_dir / "md"
    temp_md_dir.mkdir(parents=True, exist_ok=True)
    
    # Get all files that need to be converted, including front and back matter
    xhtml_files_for_md = list(front_matter)
    for _, _, group in chapter_groups:
        xhtml_files_for_md.extend(group)
    xhtml_files_for_md.extend(back_matter)
    
    # Validation step
    for xhtml_file in xhtml_files_for_md:
        xhtml_path = content_root / xhtml_file
        if not xhtml_path.exists():
            warning = f"Missing XHTML file: {xhtml_path.name}"
            print(f"Warning: {warning}")
            conversion_log["warnings"].append(warning)
    
    # Convert XHTML to Markdown
    for xhtml_file in xhtml_files_for_md:
        xhtml_path = content_root / xhtml_file
        md_temp_path = temp_md_dir / f"{Path(xhtml_file).stem}.md"
        run_pandoc(xhtml_path, md_temp_path)
    print(f"[Phase 1] Converted {len(xhtml_files_for_md)} XHTML files to Markdown in temp folder: {temp_md_dir}")
    
    # === PHASE 2: FILE ORGANIZATION ===
    print("\n=== PHASE 2: FILE ORGANIZATION ===")

    # Assign labels and process front matter
    from string import ascii_lowercase
    for i, fname in enumerate(front_matter):
        label = f"00{ascii_lowercase[i]}"
        xhtml_path = content_root / fname
        title = extract_title_from_xhtml(xhtml_path)
        safe_title = safe_filename(title)
        # TOC file: assign label 100 to move to end if it's the raw XHTML-based TOC export
        if (
            "table of contents" in safe_title.lower()
            or safe_title.strip().lower() in {"toc", "contents"}
        ):
            label = "100"
        output_filename = f"{label} - {safe_title}.md"

        md_temp_path = temp_md_dir / f"{Path(fname).stem}.md"
        output_path = output_dir_path / output_filename

        if md_temp_path.exists():
            shutil.move(str(md_temp_path), str(output_path))
            chapter_map[fname] = output_filename
            conversion_log["chapters"].append({
                "index": label,
                "title": title,
                "source_files": [fname],
                "output_file": output_filename,
                "output_path": str(output_path)
            })
            print(f"  [FRONT] {fname} -> {output_filename}")

    # Assign labels and process chapters
    for num, title, group in chapter_groups:
        print(f"\nProcessing Chapter {num:02d}: {title}")
        for idx, fname in enumerate(group):
            label = f"{num:02d}.{idx}"
            xhtml_path = content_root / fname
            title = extract_title_from_xhtml(xhtml_path)
            safe_title = safe_filename(title)
            # TOC file: assign label 100 to move to end if it's the raw XHTML-based TOC export
            if (
                "table of contents" in safe_title.lower()
                or safe_title.strip().lower() in {"toc", "contents"}
            ):
                label = "100"
            output_filename = f"{label} - {safe_title}.md"

            md_temp_path = temp_md_dir / f"{Path(fname).stem}.md"
            output_path = output_dir_path / output_filename

            if md_temp_path.exists():
                shutil.move(str(md_temp_path), str(output_path))
                chapter_map[fname] = output_filename
                conversion_log["chapters"].append({
                    "index": label,
                    "title": title,
                    "source_files": [fname],
                    "output_file": output_filename,
                    "output_path": str(output_path)
                })
                print(f"  {fname} -> {output_filename}")

    # Assign labels and process back matter
    for i, fname in enumerate(back_matter):
        label = f"{90 + i}"
        xhtml_path = content_root / fname
        title = extract_title_from_xhtml(xhtml_path)
        safe_title = safe_filename(title)
        # TOC file: assign label 100 to move to end if it's the raw XHTML-based TOC export
        if (
            "table of contents" in safe_title.lower()
            or safe_title.strip().lower() in {"toc", "contents"}
        ):
            label = "100"
        output_filename = f"{label} - {safe_title}.md"

        md_temp_path = temp_md_dir / f"{Path(fname).stem}.md"
        output_path = output_dir_path / output_filename

        if md_temp_path.exists():
            shutil.move(str(md_temp_path), str(output_path))
            chapter_map[fname] = output_filename
            conversion_log["chapters"].append({
                "index": label,
                "title": title,
                "source_files": [fname],
                "output_file": output_filename,
                "output_path": str(output_path)
            })
            print(f"  [BACK] {fname} -> {output_filename}")
    
    # Phase 3: Markdown Cleanup
    print("\n=== PHASE 3: MARKDOWN CLEANUP ===")
    for entry in conversion_log["chapters"]:
        md_path = output_dir_path / entry["output_file"]
        if not md_path.exists():
            continue
        
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        cleaned_content = clean_markdown_text(content, chapter_map)
        
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(cleaned_content)
        
        print(f"Cleaned: {entry['output_file']}")
    
    # Phase 4: Cross-Link Rewriting
    if use_obsidian_format:
        print("\n=== PHASE 4: CROSS-LINK REWRITING ===")
        for entry in conversion_log["chapters"]:
            md_path = output_dir_path / entry["output_file"]
            if not md_path.exists():
                continue
            
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Apply cross-link rewriting
            content = post_process_markdown(content, chapter_map)
            
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            print(f"Rewrote links: {entry['output_file']}")
    
    # Generate Obsidian TOC
    toc_filename = generate_obsidian_toc(conversion_log, output_dir_path, str(book_title) if book_title is not None else "")
    toc_path = output_dir_path / toc_filename
    print(f"[INFO] Generated Obsidian-compatible TOC: {toc_path}")
    
    # Phase 5: YAML Header Injection
    book_metadata = extract_book_metadata_from_copyright(content_root)
    
    if book_metadata:
        title = book_metadata.get('title', '')
        authors_string = book_metadata.get('authors', '')
        
        # Find matching BibTeX entry
        bibtex_entry = find_bibtex_entry_by_title_and_authors(title, authors_string)
        
        if bibtex_entry:
            citation_key = bibtex_entry['citation_key']
            bibtex_authors = parse_bibtex_authors(bibtex_entry['authors'])
            
            # Generate YAML headers for all chapters
            for entry in conversion_log["chapters"]:
                md_path = output_dir_path / entry["output_file"]
                if not md_path.exists():
                    continue
                
                # Read current content
                with open(md_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Generate YAML header using the full title from BibTeX entry
                yaml_header = generate_yaml_header(
                    title=bibtex_entry['title'],
                    chapter=entry["output_file"],
                    authors=bibtex_authors,
                    citation_key=citation_key,
                    toc_filename=toc_filename
                )
                
                # Prepend YAML header to content
                new_content = yaml_header + "\n\n" + content
                
                # Write back to file
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                
                print(f"[Phase 5] Added YAML header to: {entry['output_file']}")
        else:
            print(f"[WARNING] No matching BibTeX entry found for book: {title}")
    else:
        print(f"[WARNING] No book metadata found for YAML header generation")
    
    # Add runtime metadata
    end_timestamp = datetime.utcnow().isoformat() + "Z"
    conversion_log["end_time_utc"] = end_timestamp
    conversion_log["total_output_files"] = len(conversion_log["chapters"])
    
    # Create timestamped log filename
    timestamp = datetime.now().strftime("%Y-%m-%d_%H.%M")
    if book_title:
        safe_log_title = safe_filename(book_title)
        log_path = LOG_DIR / f"{safe_log_title}_{timestamp}.json"
    else:
        log_path = LOG_DIR / f"{epub_file.stem}_{timestamp}.json"
    
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(conversion_log, f, indent=2)
    print(f"Log saved to: {log_path}")
    
    # Show macOS summary dialog (uncommented for macOS)
    show_final_dialog(conversion_log, time.time() - start, md_status=True, cleanup_status=True, json_status=True)
    return conversion_log

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
            output_dir=args.output,
            skip_images=args.skip_images,
            use_obsidian_format=args.obsidian
        )
        print(f"Conversion completed: {result}")
    
    elapsed = time.time() - start_time
    print(f"Total time: {elapsed:.2f} seconds")


        