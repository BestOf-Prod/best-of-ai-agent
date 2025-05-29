# Newspapers.com extractor (future)
import requests
from bs4 import BeautifulSoup
import re
import logging
import time
from utils.logger import setup_logging
from urllib.parse import urljoin

# Setup logging
logger = setup_logging(__name__)

class NewspapersComExtractor:
    def __init__(self, session_cookies=None):
        logger.info("Initializing NewspapersComExtractor")
        self.session = requests.Session()
        if session_cookies:
            logger.debug("Updating session with provided cookies")
            self.session.cookies.update(session_cookies)
        else:
            logger.debug("No session cookies provided")
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        logger.debug("Headers configured for requests")
        
    def _check_authentication(self, response):
        """Check if the response indicates authentication is required."""
        logger.debug("Checking authentication status of response")
        auth_indicators = [
            "Please log in to continue",
            "Subscribe now",
            "Sign in to view",
            "Access denied"
        ]
        for indicator in auth_indicators:
            if indicator in response.text:
                logger.warning(f"Authentication required - found indicator: {indicator}")
                return True
        logger.debug("No authentication required")
        return False
    
    def _extract_metadata(self, soup, url):
        """Extract metadata from the article page."""
        logger.info("Starting metadata extraction")
        metadata = {
            "headline": "Unknown Headline",
            "date": "Unknown Date",
            "newspaper": "Unknown Newspaper",
            "page": "Unknown Page"
        }
        
        # Extract headline
        logger.debug("Attempting to extract headline")
        headline_selectors = ['.article-title', '.clipping-title', 'h1.title', 'h1']
        for selector in headline_selectors:
            if elem := soup.select_one(selector):
                metadata["headline"] = elem.text.strip()
                logger.info(f"Found headline: {metadata['headline']}")
                break
        else:
            logger.warning("No headline found using any selector")
        
        # Extract date
        logger.debug("Attempting to extract date")
        date_selectors = ['.pub-date', '.article-date', '.date', '.newspaper-date']
        for selector in date_selectors:
            if elem := soup.select_one(selector):
                metadata["date"] = elem.text.strip()
                logger.info(f"Found date: {metadata['date']}")
                break
        else:
            logger.warning("No date found using any selector")
        
        # Extract newspaper name
        logger.debug("Attempting to extract newspaper name")
        newspaper_selectors = ['.newspaper-title', '.publication-name', '.source-name']
        for selector in newspaper_selectors:
            if elem := soup.select_one(selector):
                metadata["newspaper"] = elem.text.strip()
                logger.info(f"Found newspaper: {metadata['newspaper']}")
                break
        else:
            logger.warning("No newspaper name found using any selector")
        
        # Extract page number
        logger.debug("Attempting to extract page number")
        page_selectors = ['.page-number', '.article-page', '.page']
        for selector in page_selectors:
            if elem := soup.select_one(selector):
                page_text = elem.text.strip()
                if match := re.search(r'Page\s+(\d+)', page_text, re.IGNORECASE):
                    metadata["page"] = f"Page {match.group(1)}"
                    logger.info(f"Found page number: {metadata['page']}")
                else:
                    metadata["page"] = page_text
                    logger.info(f"Found page text: {metadata['page']}")
                break
        else:
            logger.warning("No page number found using any selector")
        
        logger.info("Metadata extraction completed")
        return metadata
    
    def _extract_image_url(self, soup, base_url):
        """Extract the article image URL."""
        logger.debug("Starting image URL extraction")
        image_selectors = [
            '.article-image img', 
            '.clipping-image img',
            '.newspaper-page-image img',
            '.main-image img'
        ]
        
        for selector in image_selectors:
            logger.debug(f"Trying image selector: {selector}")
            if img := soup.select_one(selector):
                if src := img.get('src'):
                    image_url = urljoin(base_url, src)
                    logger.info(f"Found image URL: {image_url}")
                    return image_url
                else:
                    logger.debug(f"Found img element with selector {selector} but no src attribute")
        
        logger.warning("No image URL found using any selector")
        return None
    
    def extract_article(self, url):
        """
        Extract article content from a Newspapers.com article URL.
        
        Args:
            url (str): The URL of the Newspapers.com article to extract
            
        Returns:
            dict: A dictionary containing the extracted article data or error information
        """
        logger.info(f"Starting extraction from Newspapers.com URL: {url}")
        start_time = time.time()
        
        try:
            logger.debug("Sending HTTP request")
            response = self.session.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            logger.debug(f"Received response with status code: {response.status_code}")
            
            if self._check_authentication(response):
                logger.error("Authentication required - please log in to Newspapers.com first")
                return {
                    "success": False,
                    "error": "Authentication required - please log in to Newspapers.com first"
                }
            
            logger.debug("Parsing HTML content")
            soup = BeautifulSoup(response.content, 'html.parser')
            
            logger.debug("Extracting metadata")
            metadata = self._extract_metadata(soup, url)
            
            logger.debug("Extracting image URL")
            image_url = self._extract_image_url(soup, url)
            
            extraction_time = time.time() - start_time
            logger.info(f"Extraction completed successfully in {extraction_time:.2f} seconds")
            
            return {
                "success": True,
                **metadata,
                "source": "Newspapers.com",
                "url": url,
                "image_url": image_url,
            }
            
        except requests.HTTPError as e:
            status_code = e.response.status_code if hasattr(e, 'response') else "unknown"
            logger.error(f"HTTP error {status_code} during extraction: {str(e)}")
            return {"success": False, "error": f"HTTP error {status_code}: {str(e)}"}
            
        except requests.RequestException as e:
            logger.error(f"Network error during extraction: {str(e)}")
            return {"success": False, "error": f"Network error: {str(e)}"}
            
        except Exception as e:
            logger.exception(f"Unexpected error during extraction: {str(e)}")
            return {"success": False, "error": f"Extraction error: {str(e)}"}

# For backward compatibility
def extract_from_newspapers_com(url, session_cookies=None):
    logger.info("Using legacy extract_from_newspapers_com function")
    extractor = NewspapersComExtractor(session_cookies)
    return extractor.extract_article(url)