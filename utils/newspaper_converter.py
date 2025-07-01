import os
import re
import tempfile
import requests
import zipfile
import io
import random
from urllib.parse import urlparse
from docx import Document
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import markdown
from bs4 import BeautifulSoup
import logging
from datetime import datetime
from utils.logger import setup_logging

logger = setup_logging(__name__, log_level=logging.INFO)

# Font matrix for different site types
FONT_MATRIX = {
    'newspaper_sites': {
        'serif_fonts': [
            'Times New Roman',
            'Georgia',
            'Playfair Display',
            'Minion Pro',
            'Adobe Garamond Pro',
            'Times',
            'Book Antiqua',
            'Century Schoolbook'
        ],
        'domains': [
            'nytimes.com',
            'washingtonpost.com',
            'wsj.com',
            'theguardian.com',
            'ft.com',
            'latimes.com',
            'chicagotribune.com',
            'usatoday.com',
            'boston.com',
            'sfgate.com'
        ]
    },
    'web_news_sites': {
        'sans_serif_fonts': [
            'Arial',
            'Helvetica',
            'Calibri',
            'Verdana',
            'Tahoma',
            'Franklin Gothic Medium',
            'Segoe UI',
            'Roboto'
        ],
        'domains': [
            'espn.com',
            'cnn.com',
            'bbc.com',
            'reuters.com',
            'buzzfeed.com',
            'techcrunch.com',
            'mashable.com',
            'theverge.com',
            'wired.com',
            'engadget.com'
        ]
    }
}

def get_font_for_site(url):
    """
    Determine the appropriate font based on the site URL
    
    Args:
        url (str): The source URL of the article
        
    Returns:
        str: Font name to use for the article
    """
    if not url:
        return random.choice(FONT_MATRIX['newspaper_sites']['serif_fonts'])
    
    domain = urlparse(url).netloc.replace('www.', '').lower()
    
    # Check if it's a newspaper site
    if any(news_domain in domain for news_domain in FONT_MATRIX['newspaper_sites']['domains']):
        return random.choice(FONT_MATRIX['newspaper_sites']['serif_fonts'])
    
    # Check if it's a web news site
    if any(web_domain in domain for web_domain in FONT_MATRIX['web_news_sites']['domains']):
        return random.choice(FONT_MATRIX['web_news_sites']['sans_serif_fonts'])
    
    # Default fallback - assume newspaper for unknown sites
    return random.choice(FONT_MATRIX['newspaper_sites']['serif_fonts'])

def calculate_word_count(text):
    """
    Calculate word count for article text
    
    Args:
        text (str): The text to count words in
        
    Returns:
        int: Number of words
    """
    if not text:
        return 0
    
    # Split by whitespace and filter out empty strings
    words = [word.strip() for word in text.split() if word.strip()]
    return len(words)

def create_directory_name(article_data, font_name, word_count):
    """
    Create directory name with word count, font, and article title
    
    Args:
        article_data (dict): Article data dictionary
        font_name (str): Font used for the article
        word_count (int): Word count of the article body
        
    Returns:
        str: Directory name
    """
    title = article_data.get('headline', 'Unknown Title')
    # Clean title for directory name
    clean_title = sanitize_filename(title)
    
    # Create directory name: WordCount_Font_Title
    font_clean = font_name.replace(' ', '-')
    directory_name = f"{word_count}words_{font_clean}_{clean_title}"
    
    # Ensure directory name isn't too long (limit to 100 chars)
    if len(directory_name) > 100:
        max_title_length = 100 - len(f"{word_count}words_{font_clean}_")
        clean_title = clean_title[:max_title_length]
        directory_name = f"{word_count}words_{font_clean}_{clean_title}"
    
    return directory_name

def sanitize_filename(title):
    """Convert article title to safe filename with hyphens"""
    if not title:
        return "untitled-article"
    
    # Remove or replace problematic characters
    title = title.strip()
    
    # Replace spaces and common punctuation with hyphens
    title = re.sub(r'[^\w\s-]', '', title)  # Remove special chars except word chars, spaces, hyphens
    title = re.sub(r'\s+', '-', title)      # Replace spaces with hyphens
    title = re.sub(r'-+', '-', title)       # Replace multiple hyphens with single hyphen
    title = title.strip('-')                # Remove leading/trailing hyphens
    
    # Convert to lowercase for consistency
    title = title.lower()
    
    # Limit length to avoid filesystem issues
    if len(title) > 50:
        # Find the last word boundary before 50 characters
        truncated = title[:50]
        if '-' in truncated:
            last_hyphen = truncated.rfind('-')
            title = truncated[:last_hyphen]
        else:
            title = truncated
    
    # Ensure we have something
    if not title:
        title = "untitled-article"
    
    return title

def extract_title_from_markdown(md_content):
    """Extract the first headline from markdown content"""
    lines = md_content.split('\n')
    
    for line in lines:
        line = line.strip()
        # Look for H1 or H2 headers
        if line.startswith('# '):
            return line[2:].strip()
        elif line.startswith('## '):
            return line[3:].strip()
    
    # Fallback: use first non-empty line
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            # Take first sentence or up to 50 chars
            if '.' in line:
                return line.split('.')[0].strip()
            else:
                return line[:50].strip()
    
    return "Untitled Article"

def extract_images_from_markdown(md_content):
    """Extract image URLs and alt text from markdown content."""
    image_pattern = r'!\[([^\]]*)\]\(([^)]+)\)'
    images = []
    
    logger.info(f"Searching for images in markdown content (length: {len(md_content)})")
    
    for match in re.finditer(image_pattern, md_content):
        alt_text = match.group(1)
        url = match.group(2)
        images.append({
            'alt_text': alt_text,
            'url': url,
            'markdown': match.group(0)
        })
        logger.info(f"Found image: {url} (alt: {alt_text})")
    
    logger.info(f"Total images found: {len(images)}")
    return images

def download_image(url, temp_dir):
    """Download image from URL and save to temporary directory."""
    logger.info(f"Attempting to download image from: {url}")
    
    try:
        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            logger.error(f"Invalid URL format: {url}")
            return None
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        logger.info(f"Making request to {url}")
        response = requests.get(url, headers=headers, timeout=15)  # Increased timeout
        response.raise_for_status()
        
        # Check if response contains image data
        content_type = response.headers.get('content-type', '').lower()
        if not content_type.startswith('image/'):
            logger.warning(f"URL does not return image content. Content-Type: {content_type}")
            return None
        
        # Get file extension from URL or content type
        parsed_url = urlparse(url)
        filename = os.path.basename(parsed_url.path)
        if not filename or '.' not in filename:            
            if 'jpeg' in content_type or 'jpg' in content_type:
                filename = 'image.jpg'
            elif 'png' in content_type:
                filename = 'image.png'
            elif 'gif' in content_type:
                filename = 'image.gif'
            elif 'webp' in content_type:
                filename = 'image.webp'
            else:
                filename = 'image.jpg'
        
        temp_path = os.path.join(temp_dir, filename)
        
        # Write image data
        with open(temp_path, 'wb') as f:
            f.write(response.content)
        
        logger.info(f"Successfully downloaded image to: {temp_path} ({len(response.content)} bytes)")
        return temp_path
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error downloading image from {url}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error downloading image from {url}: {str(e)}")
        return None

def determine_layout(content_length):
    """Determine column layout based on content length."""
    if content_length < 1500:
        return 'single'  # Short: single column with headline above image, body below
    else:
        return 'double'  # Long: two columns with image on left

def add_column_break(doc):
    """Add a column break to the document."""
    p = doc.add_paragraph()
    run = p.runs[0] if p.runs else p.add_run()
    fldChar = OxmlElement('w:br')
    fldChar.set(qn('w:type'), 'column')
    run._element.append(fldChar)

def set_column_layout(section, num_columns):
    """Set the number of columns for a section."""
    sectPr = section._sectPr
    cols = sectPr.find(qn('w:cols'))
    if cols is None:
        cols = OxmlElement('w:cols')
        sectPr.append(cols)
    cols.set(qn('w:num'), str(num_columns))
    if num_columns > 1:
        cols.set(qn('w:space'), '432')  # 0.3 inch spacing between columns

def apply_newspaper_styling(doc):
    """Apply newspaper-style formatting to the document."""
    # Set document margins (narrow margins for newspaper style)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.5)
        section.bottom_margin = Inches(0.5)
        section.left_margin = Inches(0.5)
        section.right_margin = Inches(0.5)

def create_headline_style(paragraph, text, font_name=None):
    """Apply headline styling to a paragraph."""
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(text)
    run.font.name = font_name or 'Times New Roman'
    run.font.size = Pt(38)  # Fixed headline size
    run.font.bold = True
    paragraph.space_after = Pt(6)

def create_body_style(paragraph, text, font_name=None, indented=False):
    """Apply body text styling to a paragraph."""
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    if indented:
        paragraph.paragraph_format.left_indent = Inches(0.5)
    run = paragraph.add_run(text)
    run.font.name = font_name or 'Times New Roman'
    run.font.size = Pt(14)  # Fixed body text size
    paragraph.space_after = Pt(3)

def create_blockquote_style(paragraph, text, font_name=None):
    """Apply blockquote styling to a paragraph."""
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.left_indent = Inches(0.5)
    paragraph.paragraph_format.right_indent = Inches(0.5)
    run = paragraph.add_run(text)
    run.font.name = font_name or 'Times New Roman'
    run.font.size = Pt(14)  # Fixed blockquote size to match body text
    run.font.italic = True
    paragraph.space_after = Pt(6)

def process_markdown_to_text(md_content):
    """Convert markdown to plain text and extract structure."""
    # Convert markdown to HTML first
    html = markdown.markdown(md_content)
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract headline (first h1 or h2)
    headline = None
    headline_tag = soup.find(['h1', 'h2'])
    if headline_tag:
        headline = headline_tag.get_text().strip()
        headline_tag.decompose()  # Remove from soup
    
    # Get remaining text as body
    body_text = soup.get_text().strip()
    
    return headline, body_text

def create_component_documents(article_data, temp_dir):
    """
    Create separate Word documents for each article component.
    
    Args:
        article_data: Dictionary containing article data with structured_content
        temp_dir: Temporary directory for file storage
        
    Returns:
        dict: Dictionary containing paths to component documents, images, and metadata
    """
    logger.info("Creating component documents from article data")
    
    # Get font for this article's source
    font_name = get_font_for_site(article_data.get('url', ''))
    logger.info(f"Selected font: {font_name} for source: {article_data.get('source', 'unknown')}")
    
    # Calculate word count for the article body
    article_text = article_data.get('text', '')
    word_count = calculate_word_count(article_text)
    logger.info(f"Article word count: {word_count}")
    
    # Create directory name with word count, font, and title
    directory_name = create_directory_name(article_data, font_name, word_count)
    logger.info(f"Directory name: {directory_name}")
    
    # Extract components
    headline = article_data.get('headline', '')
    structured_content = article_data.get('structured_content', [])
    images = extract_images_from_markdown(article_data.get('text', ''))
    
    components = {
        'heading': None,
        'blockquote': None,
        'body': None,
        'image': None,
        'metadata': {
            'font_name': font_name,
            'word_count': word_count,
            'directory_name': directory_name,
            'title': article_data.get('headline', 'Unknown Title')
        }
    }
    
    # Create heading document
    if headline:
        heading_doc = Document()
        apply_newspaper_styling(heading_doc)
        set_column_layout(heading_doc.sections[0], 1)  # Single column
        
        heading_para = heading_doc.add_paragraph()
        create_headline_style(heading_para, headline, font_name)
        
        heading_path = os.path.join(temp_dir, 'heading.docx')
        heading_doc.save(heading_path)
        components['heading'] = heading_path
        logger.info(f"Created heading document: {heading_path}")
    
    # Separate blockquotes and body content
    blockquote_texts = []
    body_texts = []
    
    if structured_content:
        for content_item in structured_content:
            if content_item['type'] == 'blockquote':
                blockquote_texts.append(content_item['text'])
            elif content_item['type'] == 'paragraph':
                body_texts.append({
                    'text': content_item['text'],
                    'indented': content_item.get('indented', False)
                })
    else:
        # Fallback: split regular content by paragraphs
        paragraphs = article_data.get('text', '').split('\n\n')
        for para in paragraphs:
            if para.strip():
                body_texts.append({'text': para.strip(), 'indented': False})
    
    # Create blockquote document
    if blockquote_texts:
        blockquote_doc = Document()
        apply_newspaper_styling(blockquote_doc)
        set_column_layout(blockquote_doc.sections[0], 1)  # Single column
        
        for quote_text in blockquote_texts:
            quote_para = blockquote_doc.add_paragraph()
            create_blockquote_style(quote_para, quote_text, font_name)
        
        blockquote_path = os.path.join(temp_dir, 'blockquote.docx')
        blockquote_doc.save(blockquote_path)
        components['blockquote'] = blockquote_path
        logger.info(f"Created blockquote document: {blockquote_path}")
    
    # Create body document
    if body_texts:
        body_doc = Document()
        apply_newspaper_styling(body_doc)
        set_column_layout(body_doc.sections[0], 1)  # Single column
        
        for body_item in body_texts:
            body_para = body_doc.add_paragraph()
            create_body_style(body_para, body_item['text'], font_name, body_item['indented'])
        
        body_path = os.path.join(temp_dir, 'body.docx')
        body_doc.save(body_path)
        components['body'] = body_path
        logger.info(f"Created body document: {body_path}")
    
    # Handle images
    downloaded_images = []
    if images:
        logger.info(f"Processing {len(images)} images")
        for i, image in enumerate(images):
            image_path = download_image(image['url'], temp_dir)
            if image_path:
                downloaded_images.append({
                    'path': image_path,
                    'alt_text': image['alt_text'],
                    'url': image['url']
                })
                logger.info(f"Downloaded image {i+1}: {image_path}")
    
    if downloaded_images:
        components['image'] = downloaded_images
    
    return components

def create_newspaper_document(md_content, temp_dir):
    """Create a Word document formatted like a newspaper clipping."""
    doc = Document()
    apply_newspaper_styling(doc)
    
    # Extract images from markdown
    images = extract_images_from_markdown(md_content)
    
    # Remove image markdown from content for text processing
    clean_content = md_content
    for image in images:
        clean_content = clean_content.replace(image['markdown'], '')
    
    # Process markdown to get headline and body
    headline, body_text = process_markdown_to_text(clean_content)
    
    # Get font for this content (try to extract URL from markdown if available)
    font_name = get_font_for_site(None)  # Default font since we don't have URL context here
    
    # Force single column layout as specified in requirements
    section = doc.sections[0]
    set_column_layout(section, 1)
    
    # Download images
    downloaded_images = []
    logger.info(f"Starting image download for {len(images)} images")
    
    for i, image in enumerate(images):
        logger.info(f"Processing image {i+1}/{len(images)}: {image['url']}")
        image_path = download_image(image['url'], temp_dir)
        if image_path:
            downloaded_images.append({
                'path': image_path,
                'alt_text': image['alt_text'],
                'url': image['url']  # Keep original URL for zip file processing
            })
            logger.info(f"Successfully processed image {i+1}")
        else:
            logger.warning(f"Failed to download image {i+1}: {image['url']}")
    
    logger.info(f"Downloaded {len(downloaded_images)} out of {len(images)} images")
    
    # Store downloaded images info for zip file processing
    doc._downloaded_images = downloaded_images
    
    # Single column layout with components in order: headline, image, body
    # Add headline
    if headline:
        headline_para = doc.add_paragraph()
        create_headline_style(headline_para, headline, font_name)
    
    # Add image
    if downloaded_images:
        img_para = doc.add_paragraph()
        img_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = img_para.add_run()
        run.add_picture(downloaded_images[0]['path'], width=Inches(3))
        img_para.space_after = Pt(6)
    
    # Add body text with paragraph breaks and indentation preserved
    body_paragraphs = body_text.split('\n\n')
    for para_text in body_paragraphs:
        if para_text.strip():
            body_para = doc.add_paragraph()
            create_body_style(body_para, para_text.strip(), font_name)
    
    return doc

def convert_markdown_to_newspaper(md_content, output_path=None):
    """Convert markdown content to a newspaper-style Word document."""
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create the document
        doc = create_newspaper_document(md_content, temp_dir)
        
        # Save the document
        if output_path is None:
            output_path = os.path.join(temp_dir, 'newspaper_clipping.docx')
        
        doc.save(output_path)
        logger.info(f"Newspaper document created: {output_path}")
        
        return output_path
    
    except Exception as e:
        logger.error(f"Error creating newspaper document: {str(e)}")
        raise
    
    finally:
        # Clean up downloaded images
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory: {str(e)}")

def convert_articles_to_component_zip(articles_data, output_zip_path=None):
    """
    Convert articles to separate component Word documents organized by word count, font, and title.
    
    Args:
        articles_data: List of article data dictionaries with structured content
        output_zip_path: Optional path to save zip file
        
    Returns:
        dict: Summary of created files
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        all_component_files = []
        all_images = []
        article_directories = {}  # Track directories by article
        
        for i, article_data in enumerate(articles_data):
            logger.info(f"Processing article {i+1}/{len(articles_data)}")
            
            # Create component documents for this article
            components = create_component_documents(article_data, temp_dir)
            
            # Get metadata for directory organization
            metadata = components.get('metadata', {})
            directory_name = metadata.get('directory_name', f"article_{i+1}")
            
            # Store directory info
            article_directories[directory_name] = {
                'metadata': metadata,
                'components': [],
                'images': []
            }
            
            # Process each component document
            for component_type, component_path in components.items():
                if component_path and component_type not in ['image', 'metadata']:
                    # Read the document data
                    with open(component_path, 'rb') as f:
                        doc_data = f.read()
                    
                    filename = f"{component_type}.docx"
                    
                    component_info = {
                        'filename': filename,
                        'data': doc_data,
                        'directory': directory_name,
                        'component': component_type,
                        'size': len(doc_data),
                        'metadata': metadata
                    }
                    
                    all_component_files.append(component_info)
                    article_directories[directory_name]['components'].append(component_info)
                    
                    logger.info(f"Created {component_type} document for directory: {directory_name}")
            
            # Handle images
            if components.get('image'):
                for img_idx, img in enumerate(components['image']):
                    img_filename = f"image_{img_idx + 1}_{os.path.basename(img['path'])}"
                    img_info = {
                        'source_path': img['path'],
                        'clip_filename': img_filename,
                        'directory': directory_name,
                        'url': img['url'],
                        'alt_text': img['alt_text']
                    }
                    all_images.append(img_info)
                    article_directories[directory_name]['images'].append(img_info)
        
        # Create zip file with organized directory structure
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add Word documents organized by article directory
            for doc_file in all_component_files:
                directory_path = doc_file['directory']
                zip_path = f"{directory_path}/{doc_file['filename']}"
                zip_file.writestr(zip_path, doc_file['data'])
                logger.info(f"Added to zip: {zip_path}")
            
            # Add images to their respective article directories
            logger.info(f"Adding {len(all_images)} images to article directories")
            for img in all_images:
                try:
                    with open(img['source_path'], 'rb') as f:
                        img_data = f.read()
                    
                    directory_path = img['directory']
                    zip_path = f"{directory_path}/images/{img['clip_filename']}"
                    zip_file.writestr(zip_path, img_data)
                    logger.info(f"Added image to zip: {zip_path}")
                    
                except Exception as e:
                    logger.warning(f"Failed to add image {img['clip_filename']} to zip: {str(e)}")
            
            # Add metadata file for each article directory
            for directory_name, dir_info in article_directories.items():
                metadata = dir_info['metadata']
                metadata_content = f"""Article Information:
Title: {metadata.get('title', 'Unknown')}
Word Count: {metadata.get('word_count', 0)} words
Font Used: {metadata.get('font_name', 'Unknown')}
Components: {len(dir_info['components'])} documents
Images: {len(dir_info['images'])} files
"""
                zip_path = f"{directory_name}/article_info.txt"
                zip_file.writestr(zip_path, metadata_content)
                logger.info(f"Added metadata file: {zip_path}")
        
        zip_data = zip_buffer.getvalue()
        
        # Save zip file if path provided
        if output_zip_path:
            with open(output_zip_path, 'wb') as f:
                f.write(zip_data)
            logger.info(f"Component zip file created: {output_zip_path}")
        
        # Generate summary
        total_size = sum(doc['size'] for doc in all_component_files)
        component_counts = {}
        for doc in all_component_files:
            component_type = doc['component']
            component_counts[component_type] = component_counts.get(component_type, 0) + 1
        
        summary = {
            'zip_data': zip_data,
            'document_count': len(all_component_files),
            'total_size': total_size,
            'image_count': len(all_images),
            'article_count': len(article_directories),
            'component_counts': component_counts,
            'directories': list(article_directories.keys()),
            'articles': [
                {
                    'directory': directory_name,
                    'title': dir_info['metadata'].get('title', 'Unknown'),
                    'word_count': dir_info['metadata'].get('word_count', 0),
                    'font': dir_info['metadata'].get('font_name', 'Unknown'),
                    'components': len(dir_info['components']),
                    'images': len(dir_info['images'])
                } for directory_name, dir_info in article_directories.items()
            ]
        }
        
        logger.info(f"Successfully created organized zip with {len(article_directories)} article directories")
        return summary
    
    except Exception as e:
        logger.error(f"Error creating component zip: {str(e)}")
        raise
    
    finally:
        # Clean up temporary directory
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory: {str(e)}")

def convert_multiple_markdown_to_newspaper_zip(markdown_contents, output_zip_path=None, processed_articles=None):
    """Convert multiple markdown contents to individual Word documents and package in a zip file.
    
    Args:
        markdown_contents: List of markdown strings
        output_zip_path: Optional path to save zip file
        processed_articles: Optional list of article objects with image_data from batch processing
    """
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create individual Word documents
        doc_files = []
        all_images = []  # Collect all images for the clippings directory
        
        for i, md_content in enumerate(markdown_contents):
            logger.info(f"Processing markdown file {i+1}/{len(markdown_contents)}")
            
            # Extract title for filename
            title = extract_title_from_markdown(md_content)
            safe_filename = sanitize_filename(title)
            
            # Ensure unique filenames
            docx_filename = f"{safe_filename}.docx"
            counter = 1
            original_filename = docx_filename
            while any(doc['filename'] == docx_filename for doc in doc_files):
                docx_filename = f"{safe_filename}-{counter}.docx"
                counter += 1
            
            # Handle processed articles with image_data (from batch processing)
            enhanced_md_content = md_content
            if processed_articles and i < len(processed_articles):
                article = processed_articles[i]
                if article.get('image_data'):
                    logger.info(f"Processing image_data for article: {title}")
                    try:
                        # Save the PIL Image to temp directory
                        image_filename = f"{safe_filename}_scraped_image.png"
                        image_path = os.path.join(temp_dir, image_filename)
                        
                        image_saved = False
                        
                        # Convert image_data to PIL Image if it's not already
                        if hasattr(article['image_data'], 'save'):
                            # It's already a PIL Image
                            article['image_data'].save(image_path, 'PNG')
                            image_saved = True
                        else:
                            # It might be base64 or other format - try to handle it
                            from PIL import Image
                            import base64
                            
                            if isinstance(article['image_data'], str):
                                # Assume base64
                                img_data = base64.b64decode(article['image_data'])
                                img = Image.open(io.BytesIO(img_data))
                                img.save(image_path, 'PNG')
                                image_saved = True
                            else:
                                logger.warning(f"Unknown image_data format for {title}: {type(article['image_data'])}")
                        
                        # Only proceed if image was saved successfully
                        if image_saved:
                            # Add image reference to markdown
                            enhanced_md_content = md_content + f"\n\n![Scraped Article Image]({image_path})\n\n"
                            
                            # Add to clippings collection
                            clip_filename = f"{safe_filename}_scraped_image.png"
                            all_images.append({
                                'source_path': image_path,
                                'clip_filename': clip_filename,
                                'url': 'scraped_from_newspapers.com',
                                'alt_text': f'Scraped image for {title}'
                            })
                            
                            logger.info(f"Successfully processed scraped image for {title}")
                        
                    except Exception as e:
                        logger.error(f"Failed to process image_data for {title}: {str(e)}")
            
            # Create the document
            doc = create_newspaper_document(enhanced_md_content, temp_dir)
            
            # Collect images from this document (from markdown URLs)
            if hasattr(doc, '_downloaded_images'):
                for img in doc._downloaded_images:
                    # Create unique filename for the clippings directory
                    img_filename = f"{safe_filename}_{os.path.basename(img['path'])}"
                    all_images.append({
                        'source_path': img['path'],
                        'clip_filename': img_filename,
                        'url': img['url'],
                        'alt_text': img['alt_text']
                    })
            
            # Save to temporary file
            temp_doc_path = os.path.join(temp_dir, docx_filename)
            doc.save(temp_doc_path)
            
            # Read the document data
            with open(temp_doc_path, 'rb') as f:
                doc_data = f.read()
            
            doc_files.append({
                'filename': docx_filename,
                'data': doc_data,
                'title': title,
                'size': len(doc_data)
            })
            
            logger.info(f"Created document: {docx_filename} ({len(doc_data):,} bytes)")
        
        # Create zip file
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add Word documents
            for doc_file in doc_files:
                zip_file.writestr(doc_file['filename'], doc_file['data'])
                logger.info(f"Added to zip: {doc_file['filename']}")
            
            # Add images to clippings directory
            logger.info(f"Adding {len(all_images)} images to clippings directory")
            for img in all_images:
                try:
                    # Read image data
                    with open(img['source_path'], 'rb') as f:
                        img_data = f.read()
                    
                    # Add to clippings directory in zip
                    zip_path = f"clippings/{img['clip_filename']}"
                    zip_file.writestr(zip_path, img_data)
                    logger.info(f"Added image to zip: {zip_path}")
                    
                except Exception as e:
                    logger.warning(f"Failed to add image {img['clip_filename']} to zip: {str(e)}")
        
        zip_data = zip_buffer.getvalue()
        
        # Save zip file if path provided
        if output_zip_path:
            with open(output_zip_path, 'wb') as f:
                f.write(zip_data)
            logger.info(f"Zip file created: {output_zip_path}")
        
        # Generate summary
        total_size = sum(doc['size'] for doc in doc_files)
        summary = {
            'zip_data': zip_data,
            'document_count': len(doc_files),
            'total_size': total_size,
            'image_count': len(all_images),
            'documents': [{'filename': doc['filename'], 'title': doc['title'], 'size': doc['size']} for doc in doc_files]
        }
        
        logger.info(f"Successfully created zip with {len(doc_files)} newspaper documents and {len(all_images)} images ({total_size:,} bytes total)")
        
        return summary
    
    except Exception as e:
        logger.error(f"Error creating newspaper zip: {str(e)}")
        raise
    
    finally:
        # Clean up temporary directory
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Failed to clean up temp directory: {str(e)}")

def convert_markdown_files_to_newspaper_zip(markdown_file_paths, output_zip_path=None):
    """Convert multiple markdown files to individual Word documents and package in a zip file."""
    markdown_contents = []
    
    for file_path in markdown_file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                markdown_contents.append(content)
                logger.info(f"Loaded markdown file: {file_path}")
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {str(e)}")
            raise
    
    if not markdown_contents:
        raise ValueError("No markdown content found in provided files")
    
    return convert_multiple_markdown_to_newspaper_zip(markdown_contents, output_zip_path)

def main():
    """Example usage of the newspaper converter."""
    sample_markdown = """
# Breaking News: AI Revolution Continues

![AI Robot](https://example.com/robot.jpg)

The artificial intelligence industry has seen unprecedented growth this year, with new developments emerging almost daily. Companies across the globe are investing heavily in AI research and development.

This technological revolution is transforming industries from healthcare to finance. Machine learning algorithms are becoming more sophisticated, enabling computers to perform tasks that were once thought to be exclusively human.

Experts predict that the next decade will bring even more dramatic changes as AI systems become more integrated into our daily lives. The implications for society are both exciting and challenging.

As we move forward, it will be crucial to balance innovation with ethical considerations and ensure that the benefits of AI are distributed fairly across all segments of society.
"""
    
    try:
        output_file = convert_markdown_to_newspaper(sample_markdown)
        print(f"Sample newspaper document created: {output_file}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()