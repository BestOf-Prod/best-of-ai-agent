# Generic article extractor
import requests
from bs4 import BeautifulSoup
import re
import logging
from utils.logger import setup_logging
import time
from urllib.parse import urlparse
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
import os
from datetime import datetime

# Setup logging
logger = setup_logging(__name__)

def wrap_text(text, font, max_width, draw):
    """
    Wrap text for a given pixel width using the provided font.
    """
    lines = []
    if not text:
        return lines
    words = text.split()
    line = ''
    for word in words:
        test_line = f"{line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            line = test_line
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines

def create_newspaper_clipping(article_data):
    """
    Create a newspaper clipping style image from the article data
    
    Args:
        article_data (dict): The extracted article data
        
    Returns:
        bytes: The image data in bytes format
    """
    logger.info("Starting newspaper clipping creation")
    try:
        # Create a new image with a white background
        width = 1200
        height = 1600
        margin = 100
        section_padding = 30
        logger.info(f"Creating new image with dimensions {width}x{height}")
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)
        
        # Load fonts (using default fonts for now)
        logger.info("Loading fonts")
        try:
            headline_font = ImageFont.truetype("Arial Bold", 48)
            date_font = ImageFont.truetype("Arial", 24)
            content_font = ImageFont.truetype("Arial", 28)
            logger.info("Successfully loaded Arial fonts")
        except:
            # Fallback to default font if Arial is not available
            logger.warning("Arial fonts not available, falling back to default font")
            headline_font = ImageFont.load_default()
            date_font = ImageFont.load_default()
            content_font = ImageFont.load_default()
        
        # Add a light gray background for the clipping effect
        logger.info("Adding background and border effects")
        draw.rectangle([(50, 50), (width-50, height-50)], fill='#f5f5f5')
        
        # Add the headline
        headline = article_data.get('headline', 'Unknown Headline')
        max_text_width = width - 2 * margin
        headline_lines = wrap_text(headline, headline_font, max_text_width, draw)
        headline_text = '\n'.join(headline_lines)
        logger.info(f"Adding headline: {headline[:50]}...")
        y = margin
        draw.multiline_text((margin, y), headline_text, fill='black', font=headline_font, spacing=6)
        # Calculate height of headline block
        bbox = draw.multiline_textbbox((margin, y), headline_text, font=headline_font, spacing=6)
        y = bbox[3] + section_padding
        
        # Add the date and source
        date_text = f"{article_data.get('date', 'Unknown Date')} - {article_data.get('source', 'Unknown Source')}"
        date_lines = wrap_text(date_text, date_font, max_text_width, draw)
        date_text_wrapped = '\n'.join(date_lines)
        logger.info(f"Adding date and source: {date_text}")
        draw.multiline_text((margin, y), date_text_wrapped, fill='#666666', font=date_font, spacing=4)
        bbox = draw.multiline_textbbox((margin, y), date_text_wrapped, font=date_font, spacing=4)
        y = bbox[3] + section_padding
        
        # Add the content
        content = article_data.get('text', '')
        content_lines = wrap_text(content, content_font, max_text_width, draw)
        content_text = '\n'.join(content_lines)
        logger.info(f"Adding content (first 50 chars): {content[:50]}...")
        draw.multiline_text((margin, y), content_text, fill='black', font=content_font, spacing=6)
        # No need to update y further unless you want to add more sections
        
        # Add a decorative border
        draw.rectangle([(40, 40), (width-40, height-40)], outline='#333333', width=2)
        
        # Save the image to disk in the images directory
        logger.info("Saving image to disk")
        os.makedirs('images', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        image_path = os.path.join('images', f'newspaper_clipping_{timestamp}.png')
        image.save(image_path, format='PNG')
        
        # Convert the saved image to bytes
        logger.info("Reading image bytes from disk")
        with open(image_path, 'rb') as f:
            img_byte_arr = f.read()
        
        logger.info("Successfully created newspaper clipping in memory")
        return img_byte_arr
    except Exception as e:
        logger.error(f"Error creating newspaper clipping: {str(e)}")
        return None

def extract_from_url(url):
    """
    Extract article content from a given URL
    
    Args:
        url (str): The URL of the article to extract
        
    Returns:
        dict: A dictionary containing the extracted article data or error information
    """
    logger.info(f"Starting extraction from URL: {url}")
    
    try:
        # Configure request headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        logger.debug(f"Sending HTTP request to: {url}")
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=10)
        request_time = time.time() - start_time
        logger.debug(f"Request completed in {request_time:.2f} seconds")
        
        # Check for HTTP errors
        response.raise_for_status()
        logger.info(f"Request successful: HTTP {response.status_code}")
        
        # Parse the HTML content
        logger.debug("Parsing HTML content with BeautifulSoup")
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract headline - try multiple selectors
        logger.debug("Extracting headline")
        headline = None
        headline_selectors = [
            'h1', 
            'article h1',
            '.article-header h1', 
            '.article-headline',
            '.headline',
            '.story-headline',
            'header h1'
        ]
        
        for selector in headline_selectors:
            headline_elem = soup.select_one(selector)
            if headline_elem:
                headline = headline_elem.text.strip()
                logger.debug(f"Found headline using selector '{selector}': {headline}")
                break
                
        if not headline:
            logger.warning("Could not find headline with standard selectors")
            # Fallback: Try to find any large text that might be a headline
            h_tags = soup.find_all(['h1', 'h2'])
            for h in h_tags:
                if len(h.text.strip()) > 10:  # Likely a headline, not a section title
                    headline = h.text.strip()
                    logger.debug(f"Using fallback headline: {headline}")
                    break
                    
        headline_text = headline if headline else "Unknown Headline"
        logger.info(f"Extracted headline: {headline_text}")
        
        # Extract date - Multiple formats possible
        logger.debug("Extracting date")
        date_text = "Unknown Date"
        date_selectors = [
            'span.timestamp', 
            '.article-meta', 
            '.pub-date',
            '.article-date',
            'time',
            '.date',
            '.published-date',
            'meta[property="article:published_time"]'
        ]
        
        for selector in date_selectors:
            date_element = soup.select_one(selector)
            if date_element:
                # Handle both content and meta tags
                if date_element.name == 'meta':
                    date_text = date_element.get('content', '').strip()
                else:
                    date_text = date_element.text.strip()
                
                logger.debug(f"Found date using selector '{selector}': {date_text}")
                
                # Try to extract just the date part with regex
                date_match = re.search(r'\w+\s+\d+,\s+\d{4}', date_text)
                if date_match:
                    date_text = date_match.group(0)
                    logger.debug(f"Extracted date format: {date_text}")
                break
                
        logger.info(f"Extracted date: {date_text}")
        
        # Extract author
        logger.debug("Extracting author")
        author = "Unknown Author"
        author_selectors = [
            '.author', 
            '.byline',
            '.author-name',
            '.article-meta .name',
            '.writer',
            'meta[name="author"]',
            '.contributor'
        ]
        
        for selector in author_selectors:
            author_element = soup.select_one(selector)
            if author_element:
                # Handle both content and meta tags
                if author_element.name == 'meta':
                    author = author_element.get('content', '').strip()
                else:
                    author = author_element.text.strip()
                
                # Clean up common prefixes
                author = re.sub(r'^By\s+', '', author, flags=re.IGNORECASE)
                logger.debug(f"Found author using selector '{selector}': {author}")
                break
                
        logger.info(f"Extracted author: {author}")
        
        # Extract article content
        logger.debug("Extracting article content")
        content = ""
        
        # Try multiple selectors for article body
        content_selectors = [
            '.article-body',
            '#story-body',
            '.story-content',
            '[data-article-id]',
            '.article__content',
            'article',
            '.post-content',
            '.entry-content',
            '.content'
        ]
        
        article_body = None
        for selector in content_selectors:
            article_body = soup.select_one(selector)
            if article_body:
                logger.debug(f"Found article body using selector '{selector}'")
                break
        
        if article_body:
            # Extract all paragraphs
            paragraphs = article_body.find_all('p')
            logger.debug(f"Found {len(paragraphs)} paragraphs in article body")
            
            # Join paragraphs, removing any that seem like non-content
            filtered_paragraphs = []
            for p in paragraphs:
                text = p.text.strip()
                # Skip very short paragraphs or known ad/promo text
                if len(text) > 20 and not any(skip in text.lower() for skip in ['advertisement', 'subscribe', 'privacy policy', 'cookie policy', 'terms of use']):
                    filtered_paragraphs.append(text)
            
            content = "\n\n".join(filtered_paragraphs)
            logger.debug(f"Extracted content length: {len(content)} characters")
        else:
            # Last resort - try to get any paragraphs that seem to be content
            logger.warning("No article body container found, trying fallback extraction")
            all_paragraphs = soup.find_all('p')
            
            # Filter out very short paragraphs that are likely not main content
            content_paragraphs = [p.text.strip() for p in all_paragraphs if len(p.text.strip()) > 40]
            content = "\n\n".join(content_paragraphs)
            logger.debug(f"Fallback extraction found {len(content_paragraphs)} paragraphs")
        
        # Verify we have meaningful content
        if len(content) < 100:
            logger.warning(f"Extracted content is suspiciously short: {len(content)} chars")
        else:
            logger.info(f"Successfully extracted {len(content)} chars of content")
        
        # Extract main image if available
        logger.debug("Extracting featured image")
        image_url = None
        image_selectors = [
            'picture img',
            '.article-featured-image img',
            '.main-image img',
            'article img',
            '.article img',
            '.featured-image img',
            'meta[property="og:image"]',
            'meta[name="twitter:image"]'
        ]
        
        for selector in image_selectors:
            image_tags = soup.select(selector)
            for img in image_tags:
                # Handle both img tags and meta tags
                if img.name == 'meta':
                    image_url = img.get('content')
                else:
                    image_url = img.get('src')
                
                if image_url and not any(skip in image_url.lower() for skip in ['spacer', 'pixel', 'advertisement']):
                    # Filter out small icons or tracking pixels
                    if img.get('width') and img.get('height'):
                        try:
                            width = int(img['width'])
                            height = int(img['height'])
                            if width < 100 or height < 100:
                                continue  # Skip small images
                        except (ValueError, TypeError):
                            pass  # Can't determine size, continue

                    # Fix relative URLs
                    if image_url.startswith('/'):
                        parsed_url = urlparse(url)
                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        image_url = base_url + image_url
                    logger.debug(f"Found image URL: {image_url}")
                    break
            
            if image_url:
                break
                
        if image_url:
            logger.info(f"Extracted image URL: {image_url}")
        else:
            logger.info("No suitable image found")
        
        # Get the source domain
        parsed_url = urlparse(url)
        source = parsed_url.netloc.replace('www.', '')
        
        logger.info("Article extraction completed successfully")
        
        # After successful extraction, create the newspaper clipping
        article_data = {
            "success": True,
            "headline": headline_text,
            "date": date_text,
            "author": author,
            "text": content,
            "source": source,
            "url": url,
            "image_url": image_url,
        }
        
        # Generate the newspaper clipping
        clipping_image = create_newspaper_clipping(article_data)
        if clipping_image:
            article_data["clipping_image"] = clipping_image
            
        return article_data
        
    except requests.RequestException as e:
        # Handle network-related errors
        logger.error(f"Network error during extraction: {str(e)}")
        return {"success": False, "error": f"Network error: {str(e)}"}
        
    except Exception as e:
        # Handle all other errors
        logger.exception(f"Unexpected error during extraction: {str(e)}")
        return {"success": False, "error": f"Extraction error: {str(e)}"}