# ESPN extractor
import requests
from bs4 import BeautifulSoup
import re
import logging
from utils.logger import setup_logging
import time

# Setup logging
logger = setup_logging(__name__)

def extract_from_espn(url):
    """
    Extract article content from an ESPN article URL
    
    Args:
        url (str): The URL of the ESPN article to extract
        
    Returns:
        dict: A dictionary containing the extracted article data or error information
    """
    logger.info(f"Starting extraction from ESPN URL: {url}")
    
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
        headline_selectors = ['h1', '.article-header h1', '.article-headline']
        
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
            'time'
        ]
        
        for selector in date_selectors:
            date_element = soup.select_one(selector)
            if date_element:
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
            '.article-meta .name'
        ]
        
        for selector in author_selectors:
            author_element = soup.select_one(selector)
            if author_element:
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
            '.article__content'
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
                if len(text) > 20 and not any(skip in text.lower() for skip in ['advertisement', 'subscribe', 'privacy policy']):
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
            '.article img'
        ]
        
        for selector in image_selectors:
            image_tags = soup.select(selector)
            for img in image_tags:
                if img.get('src') and not any(skip in img.get('src', '').lower() for skip in ['spacer', 'pixel', 'advertisement']):
                    # Filter out small icons or tracking pixels
                    if img.get('width') and img.get('height'):
                        try:
                            width = int(img['width'])
                            height = int(img['height'])
                            if width < 100 or height < 100:
                                continue  # Skip small images
                        except (ValueError, TypeError):
                            pass  # Can't determine size, continue

                    image_url = img['src']
                    # Fix relative URLs
                    if image_url.startswith('/'):
                        image_url = 'https://www.espn.com' + image_url
                    logger.debug(f"Found image URL: {image_url}")
                    break
            
            if image_url:
                break
                
        if image_url:
            logger.info(f"Extracted image URL: {image_url}")
        else:
            logger.info("No suitable image found")
        
        logger.info("Article extraction completed successfully")
        return {
            "success": True,
            "headline": headline_text,
            "date": date_text,
            "author": author,
            "text": content,
            "source": "ESPN",
            "url": url,
            "image_url": image_url,
        }
        
    except requests.RequestException as e:
        # Handle network-related errors
        logger.error(f"Network error during extraction: {str(e)}")
        return {"success": False, "error": f"Network error: {str(e)}"}
        
    except Exception as e:
        # Handle all other errors
        logger.exception(f"Unexpected error during extraction: {str(e)}")
        return {"success": False, "error": f"Extraction error: {str(e)}"}