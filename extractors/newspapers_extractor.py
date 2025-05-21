# Newspapers.com extractor (future)
import requests
from bs4 import BeautifulSoup
import re
import logging
import time
from utils.logger import setup_logging

# Setup logging
logger = setup_logging(__name__)

def extract_from_newspapers_com(url, session_cookies=None):
    """
    Extract article content from a Newspapers.com article URL
    
    Note: This function requires pre-authentication. The user must log in to 
    Newspapers.com first, and then pass the session cookies.
    
    Args:
        url (str): The URL of the Newspapers.com article to extract
        session_cookies (dict, optional): Cookies from an authenticated session
        
    Returns:
        dict: A dictionary containing the extracted article data or error information
    """
    logger.info(f"Starting extraction from Newspapers.com URL: {url}")
    
    if not session_cookies:
        logger.warning("No session cookies provided - authentication will likely fail")
    
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
        
        # Make the request with cookies if provided
        if session_cookies:
            response = requests.get(url, headers=headers, cookies=session_cookies, timeout=15)
        else:
            response = requests.get(url, headers=headers, timeout=15)
            
        request_time = time.time() - start_time
        logger.debug(f"Request completed in {request_time:.2f} seconds")
        
        # Check if we hit a paywall or login page
        if "Please log in to continue" in response.text or "Subscribe now" in response.text:
            logger.error("Hit a paywall or login page - authentication required")
            return {
                "success": False, 
                "error": "Authentication required - please log in to Newspapers.com first"
            }
        
        # Check for HTTP errors
        response.raise_for_status()
        logger.info(f"Request successful: HTTP {response.status_code}")
        
        # Parse the HTML content
        logger.debug("Parsing HTML content with BeautifulSoup")
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract headline
        logger.debug("Extracting headline")
        headline = None
        headline_selectors = [
            '.article-title', 
            '.clipping-title',
            'h1.title',
            'h1'
        ]
        
        for selector in headline_selectors:
            headline_elem = soup.select_one(selector)
            if headline_elem:
                headline = headline_elem.text.strip()
                logger.debug(f"Found headline using selector '{selector}': {headline}")
                break
                
        if not headline:
            logger.warning("Could not find headline with standard selectors")
            # Extract from page title as fallback
            title_tag = soup.find('title')
            if title_tag:
                # Clean up the title (often contains site name)
                page_title = title_tag.text.strip()
                headline = page_title.split('|')[0].strip() if '|' in page_title else page_title
                logger.debug(f"Using page title as headline: {headline}")
                
        headline_text = headline if headline else "Unknown Headline"
        logger.info(f"Extracted headline: {headline_text}")
        
        # Extract date
        logger.debug("Extracting publication date")
        date_text = "Unknown Date"
        date_selectors = [
            '.pub-date', 
            '.article-date',
            '.date',
            '.newspaper-date'
        ]
        
        for selector in date_selectors:
            date_element = soup.select_one(selector)
            if date_element:
                date_text = date_element.text.strip()
                logger.debug(f"Found date using selector '{selector}': {date_text}")
                break
                
        # Try to find date in URL or other metadata if not found
        if date_text == "Unknown Date":
            logger.debug("Attempting to extract date from URL or metadata")
            # Look for date patterns in the URL
            date_pattern = r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})'
            date_match = re.search(date_pattern, url)
            if date_match:
                date_text = date_match.group(1).replace('-', '/')
                logger.debug(f"Extracted date from URL: {date_text}")
                
        logger.info(f"Extracted date: {date_text}")
        
        # Extract newspaper name
        logger.debug("Extracting newspaper name")
        newspaper_name = "Unknown Newspaper"
        newspaper_selectors = [
            '.newspaper-title',
            '.publication-name',
            '.source-name'
        ]
        
        for selector in newspaper_selectors:
            newspaper_elem = soup.select_one(selector)
            if newspaper_elem:
                newspaper_name = newspaper_elem.text.strip()
                logger.debug(f"Found newspaper name using selector '{selector}': {newspaper_name}")
                break
                
        logger.info(f"Extracted newspaper name: {newspaper_name}")
        
        # Extract page number
        logger.debug("Extracting page number")
        page_number = "Unknown Page"
        page_selectors = [
            '.page-number',
            '.article-page',
            '.page'
        ]
        
        for selector in page_selectors:
            page_elem = soup.select_one(selector)
            if page_elem:
                page_text = page_elem.text.strip()
                # Extract just the number with regex
                page_match = re.search(r'Page\s+(\d+)', page_text, re.IGNORECASE)
                if page_match:
                    page_number = f"Page {page_match.group(1)}"
                else:
                    page_number = page_text
                logger.debug(f"Found page number using selector '{selector}': {page_number}")
                break
                
        logger.info(f"Extracted page number: {page_number}")
        
        # Extract the article content
        logger.debug("Extracting article content")
        
        # For Newspapers.com, the content is often in a clipping viewer or OCR text block
        content_text = ""
        content_selectors = [
            '.ocr-text',
            '.article-text',
            '.clipping-text',
            '#article-content'
        ]
        
        for selector in content_selectors:
            content_elem = soup.select_one(selector)
            if content_elem:
                content_text = content_elem.text.strip()
                logger.debug(f"Found content using selector '{selector}': {len(content_text)} chars")
                break
        
        # If no content found, try to get any paragraphs within main content area
        if not content_text:
            logger.warning("No article text found with primary selectors, trying fallback")
            # Try to find the main content area
            main_content = soup.select_one('.main-content') or soup.select_one('#main-content')
            if main_content:
                paragraphs = main_content.find_all('p')
                if paragraphs:
                    content_text = "\n\n".join([p.text.strip() for p in paragraphs])
                    logger.debug(f"Extracted {len(paragraphs)} paragraphs from main content area")
        
        # Check if we have meaningful content
        if len(content_text) < 50:
            logger.warning(f"Extracted content is suspiciously short: {len(content_text)} chars")
            content_text = "Article text could not be extracted automatically. This may be a scanned newspaper article requiring OCR."
        else:
            logger.info(f"Successfully extracted {len(content_text)} chars of content")
        
        # Extract the article image URL
        logger.debug("Extracting article image URL")
        image_url = None
        
        # Look for the main article image
        image_selectors = [
            '.article-image img', 
            '.clipping-image img',
            '.newspaper-page-image img',
            '.main-image img'
        ]
        
        for selector in image_selectors:
            image_elem = soup.select_one(selector)
            if image_elem and image_elem.get('src'):
                image_url = image_elem['src']
                # Fix relative URLs
                if image_url.startswith('/'):
                    image_url = 'https://www.newspapers.com' + image_url
                logger.debug(f"Found image URL using selector '{selector}': {image_url}")
                break
        
        if not image_url:
            # Try to find any large image that might be the article
            logger.debug("No main image found, looking for any large image")
            images = soup.find_all('img')
            for img in images:
                # Skip small icons, ads, etc.
                if img.get('width') and img.get('height'):
                    try:
                        width = int(img['width'])
                        height = int(img['height'])
                        if width > 300 and height > 300:  # Likely a meaningful image
                            image_url = img['src']
                            # Fix relative URLs
                            if image_url.startswith('/'):
                                image_url = 'https://www.newspapers.com' + image_url
                            logger.debug(f"Found large image: {image_url} ({width}x{height})")
                            break
                    except (ValueError, TypeError):
                        pass
        
        if image_url:
            logger.info(f"Extracted image URL: {image_url}")
        else:
            logger.info("No suitable image found")
            
        # This is just a placeholder implementation
        # In a real implementation, you would need to handle authentication
        # and properly extract data from the DOM based on the actual structure
        logger.info("Article extraction completed successfully")
        
        return {
            "success": True,
            "headline": headline_text,
            "date": date_text,
            "newspaper": newspaper_name,
            "page": page_number,
            "text": content_text,
            "source": "Newspapers.com",
            "url": url,
            "image_url": image_url,
        }
        
    except requests.HTTPError as e:
        status_code = e.response.status_code if hasattr(e, 'response') else "unknown"
        logger.error(f"HTTP error {status_code} during extraction: {str(e)}")
        return {"success": False, "error": f"HTTP error {status_code}: {str(e)}"}
        
    except requests.RequestException as e:
        # Handle network-related errors
        logger.error(f"Network error during extraction: {str(e)}")
        return {"success": False, "error": f"Network error: {str(e)}"}
        
    except Exception as e:
        # Handle all other errors
        logger.exception(f"Unexpected error during extraction: {str(e)}")
        return {"success": False, "error": f"Extraction error: {str(e)}"}