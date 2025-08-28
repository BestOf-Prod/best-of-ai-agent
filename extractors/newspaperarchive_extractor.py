# newspaperarchive_extractor.py
# NewspaperArchive.com Scraping Suite with Click-to-Download Logic

import streamlit as st
from utils.storage_manager import StorageManager
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support import expected_conditions as EC
try:
    import seleniumwire
    from seleniumwire import webdriver as wire_webdriver
    SELENIUM_WIRE_AVAILABLE = True
    print(f"DEBUG: selenium-wire imported successfully, version: {getattr(seleniumwire, '__version__', 'unknown')}")
except ImportError as e:
    SELENIUM_WIRE_AVAILABLE = False
    print(f"DEBUG: selenium-wire import failed: {e}")
except Exception as e:
    SELENIUM_WIRE_AVAILABLE = False
    print(f"DEBUG: selenium-wire import error (not ImportError): {e}")

import cv2
import pytesseract
from PIL import Image, ImageEnhance
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

import browser_cookie3
import json
import pickle
import os
import time
import io
import base64
from datetime import datetime, timedelta
import hashlib
import re
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import logging
from bs4 import BeautifulSoup
import signal
import threading
import queue
import tempfile
import shutil
from pathlib import Path

# Import paragraph formatter for text processing
from utils.paragraph_formatter import format_article_paragraphs

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
logger = logging.getLogger(__name__)

# Log selenium-wire availability after logger is configured
if not SELENIUM_WIRE_AVAILABLE:
    logger.warning("selenium-wire not available. Download capture features will be disabled.")

@dataclass
class ArticleMetadata:
    title: str
    date: str
    url: str
    newspaper: str
    sentiment_score: float
    text_preview: str
    player_mentions: List[str]
    
@dataclass
class ClippingResult:
    image: Image.Image
    metadata: ArticleMetadata
    filename: str
    bounding_box: Tuple[int, int, int, int]
    stitched_images: Optional[List[Image.Image]] = None
    article_boundaries: Optional[List[Tuple[int, int, int, int]]] = None

class NewspaperArchiveExtractor:
    """Main scraper class for NewspaperArchive.com with click-to-download functionality"""
    
    def __init__(self, auto_auth: bool = True, project_name: str = "default"):
        self.session = requests.Session()
        
        # Set realistic headers to get high-quality images (matching manual browser downloads)
        realistic_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'same-origin'
        }
        self.session.headers.update(realistic_headers)
        logger.info("Initialized session with realistic browser headers for high-quality image downloads")
        
        self.cookies = {}
        self.results = []
        self.auto_auth = auto_auth
        self.storage_manager = StorageManager(project_name=project_name)
        self.project_name = project_name
        self.is_render = 'RENDER' in os.environ or 'RENDER_SERVICE_ID' in os.environ
        self.is_replit_deployment = 'REPLIT_DEPLOYMENT' in os.environ or 'REPL_ID' in os.environ
        
        # CSS selectors for NewspaperArchive.com based on actual site structure
        self.css_selectors = {
            # Download flow selectors (3-click process)
            'download_button': '.btn-flsave',  # The save button that shows the options
            'download_menu': '#save_option',   # The div that appears with format options
            'jpg_option': 'a[onclick="OpenJPGImagePopup()"]',  # JPG option link
            'pdf_option': 'a[onclick="OpenPDfImagePopup()"]',  # PDF option link
            'save_button': '#SaveImagebtn',    # Final save button to complete download
            
            # Alternative selectors for direct download links
            'download_link': 'a[href*="download"], a[href*=".jpg"], a[href*=".pdf"]',
            'image_download': 'a[href*="image"], a[href*="view_image"]',
            
            # Metadata selectors
            'article_title': '.article-title, .headline, h1.title, .entry-title',
            'article_date': '.publication-date, .pub-date, .date, .article-date',
            'newspaper_name': '.newspaper-title, .publication, .source-name, .newspaper',
            'article_content': '.article-text, .content, .article-body, .entry-content',
            
            # Page loading indicators
            'page_loaded': '.article-viewer, .newspaper-viewer, .content-area',
            'loading_spinner': '.loading, .spinner, .loading-indicator'
        }
        
    def initialize(self, cookies_dict: Dict = None) -> bool:
        """Initialize with LAPL cookies for NewspaperArchive access"""
        st.info("🔍 Setting up NewspaperArchive.com authentication...")
        
        if cookies_dict:
            self.cookies = cookies_dict
            for name, value in cookies_dict.items():
                self.session.cookies.set(name, value)
            
            if self._test_authentication():
                st.success("✅ Authentication successful using LAPL cookies!")
                return True
            else:
                st.error("❌ Cookie authentication failed")
                return False
        else:
            st.error("❌ No LAPL cookies provided for NewspaperArchive access")
            return False
    
    def _test_authentication(self) -> bool:
        """Test if current cookies provide valid access"""
        try:
            test_url = "https://access-newspaperarchive-com.lapl.idm.oclc.org"
            response = self.session.get(test_url, timeout=10)
            return response.status_code == 200 and "login" not in response.url.lower()
        except Exception as e:
            logger.error(f"Authentication test failed: {e}")
            return False
    
    def get_authentication_status(self) -> Dict:
        """Get current authentication status"""
        return {
            'initialized': bool(self.cookies),
            'authenticated': self._test_authentication(),
            'cookies_count': len(self.cookies),
            'last_extraction': None
        }
    
    def extract_from_url(self, url: str, player_name: Optional[str] = None, project_name: str = "default") -> Dict:
        """Extract article using click-to-download method"""
        logger.info(f"Extracting article from NewspaperArchive URL: {url}")
        return self.extract_via_download_clicks(url, player_name, project_name)

    def extract_via_download_clicks(self, url: str, player_name: Optional[str] = None, project_name: str = "default") -> Dict:
        """
        Extract article using click-to-download approach.
        This method clicks download buttons and captures the downloaded files.
        
        Args:
            url: The NewspaperArchive URL to extract from
            player_name: Optional player name for filtering
            project_name: Project name for storage organization
            
        Returns:
            Dict with extraction results including downloaded files
        """
        # Use selenium-wire if available (same as newspapers_extractor which works on Render)
        use_selenium_wire = SELENIUM_WIRE_AVAILABLE
        
        if not use_selenium_wire:
            logger.warning("selenium-wire not available, falling back to regular selenium")
        
        try:
            # Setup Chrome options optimized for Render deployment
            chrome_options = Options()
            chrome_options.add_argument("--headless")  # Must be headless on Render
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--window-size=1366,768")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Add realistic User-Agent to get high-quality images like manual browser downloads
            realistic_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            chrome_options.add_argument(f"--user-agent={realistic_user_agent}")
            
            # Render-specific options to fix user-data-dir issues
            chrome_options.add_argument("--disable-background-timer-throttling")
            chrome_options.add_argument("--disable-backgrounding-occluded-windows")
            chrome_options.add_argument("--disable-renderer-backgrounding")
            chrome_options.add_argument("--disable-features=TranslateUI")
            chrome_options.add_argument("--disable-ipc-flooding-protection")
            chrome_options.add_argument("--single-process")  # Helps prevent user-data-dir conflicts
            chrome_options.add_argument("--no-zygote")  # Prevents zygote process issues
            
            # Set a unique user data directory to avoid conflicts
            import tempfile
            import uuid
            unique_user_data_dir = tempfile.gettempdir() + f"/chrome_user_data_{uuid.uuid4().hex[:8]}"
            chrome_options.add_argument(f"--user-data-dir={unique_user_data_dir}")
            
            # Add user agent to avoid detection
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Configure download behavior
            download_dir = tempfile.gettempdir()
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Initialize appropriate webdriver
            if use_selenium_wire:
                # Use the same selenium-wire options as newspapers_extractor (which works on Render)
                seleniumwire_options = {
                    'port': 0,  # Use random port
                    'disable_encoding': True,  # Don't decode responses
                    'request_storage_base_dir': tempfile.gettempdir(),
                    'suppress_connection_errors': True,
                    'request_storage': 'memory',  # Use memory storage for speed
                }
                driver = wire_webdriver.Chrome(
                    options=chrome_options,
                    seleniumwire_options=seleniumwire_options
                )
                logger.info("Using selenium-wire webdriver for NewspaperArchive extraction")
            else:
                driver = webdriver.Chrome(options=chrome_options)
                logger.info("Using regular selenium webdriver for NewspaperArchive extraction")
            
            try:
                # Apply cookies to multiple domains that might be needed
                domains_to_set_cookies = [
                    "https://access-newspaperarchive-com.lapl.idm.oclc.org",
                    "https://login.lapl.idm.oclc.org",
                    "https://lapl.idm.oclc.org"
                ]
                
                for domain_url in domains_to_set_cookies:
                    try:
                        logger.info(f"Setting cookies for domain: {domain_url}")
                        driver.get(domain_url)
                        time.sleep(1)  # Brief pause
                        
                        for name, value in self.cookies.items():
                            try:
                                # Set cookie with proper domain
                                cookie_dict = {
                                    'name': name, 
                                    'value': value,
                                    'domain': '.lapl.idm.oclc.org',  # Use wildcard domain
                                    'path': '/'
                                }
                                driver.add_cookie(cookie_dict)
                            except Exception as e:
                                logger.warning(f"Failed to add cookie {name} to {domain_url}: {e}")
                    except Exception as e:
                        logger.warning(f"Failed to access domain {domain_url}: {e}")
                
                # Navigate to the target URL
                logger.info(f"Navigating to: {url}")
                driver.get(url)
                time.sleep(3)  # Give more time for potential redirects to complete
                
                # Wait for page to load
                wait = WebDriverWait(driver, 15)
                wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
                
                # Check if we're still on the login page after cookie setup
                current_url = driver.current_url
                if "login.lapl.idm.oclc.org" in current_url:
                    logger.error(f"Still on login page after cookie setup. Current URL: {current_url}")
                    return {
                        'success': False,
                        'error': 'Authentication failed - still redirected to login page',
                        'debug_info': {
                            'final_url': current_url,
                            'cookies_applied': len(self.cookies)
                        }
                    }
                
                logger.info(f"Successfully navigated to NewspaperArchive page: {current_url}")
                downloaded_files = []
                
                try:
                    # Step 1: Click the .btn-flsave button
                    logger.info("Looking for save button (.btn-flsave)...")
                    save_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, self.css_selectors['download_button'])))
                    save_button.click()
                    logger.info("Clicked save button (.btn-flsave)")
                    
                    # Step 2: Wait for the #save_option div to appear with options
                    logger.info("Waiting for save options menu to appear...")
                    save_options = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, self.css_selectors['download_menu'])))
                    
                    # Wait for the menu to be visible and options to be clickable
                    wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, self.css_selectors['download_menu'])))
                    logger.info("Save options menu appeared")
                    time.sleep(2)  # Give time for dynamic content to fully load
                    
                    # Step 3: Click the JPG option
                    logger.info("Looking for JPG option...")
                    jpg_option = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, self.css_selectors['jpg_option'])))
                    jpg_option.click()
                    logger.info("Clicked JPG option")
                    time.sleep(2)  # Wait for any popup or dialog to appear
                    
                    # Step 4: Click the final Save button
                    logger.info("Looking for final Save button...")
                    final_save_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, self.css_selectors['save_button'])))
                    final_save_button.click()
                    logger.info("Clicked final Save button (#SaveImagebtn)")
                    time.sleep(5)  # Wait longer for high-resolution image processing and download to initiate
                    
                    # Step 5: Monitor for downloads with enhanced debugging
                    logger.info(f"Using selenium-wire: {use_selenium_wire}")
                    logger.info(f"Driver has requests attribute: {hasattr(driver, 'requests')}")
                    
                    if use_selenium_wire and hasattr(driver, 'requests'):
                        logger.info("Monitoring selenium-wire requests for downloads...")
                        
                        # Wait for downloads with polling loop (longer for high-res images)
                        max_wait_time = 25  # Maximum 25 seconds to wait for high-resolution processing
                        wait_interval = 2   # Check every 2 seconds
                        waited_time = 0
                        
                        while waited_time < max_wait_time and not downloaded_files:
                            logger.info(f"Checking for downloads... ({waited_time}/{max_wait_time}s)")
                            logger.info(f"Total requests so far: {len(driver.requests)}")
                            
                            # Monitor network requests for downloads - look for content-disposition header
                            found_downloads = 0
                            image_requests = 0
                            
                            for request in driver.requests:
                                # Log all requests for debugging (only on first check to avoid spam)
                                if waited_time == 0:
                                    logger.debug(f"Request: {request.url} - Response: {bool(request.response)} - Content-Type: {request.response.headers.get('content-type', 'N/A') if request.response else 'N/A'}")
                                
                                # Count image requests
                                if request.response:
                                    content_type = request.response.headers.get('content-type', '').lower()
                                    if 'image/' in content_type:
                                        image_requests += 1
                                        
                                # Look for the content-disposition header which indicates a file download
                                if request.response and request.response.headers.get('content-disposition'):
                                    content_type = request.response.headers.get('content-type', '')
                                    content_length = len(request.response.body)
                                    logger.info(f"Found downloadable response: {request.url[:150]} - Content-Type: {content_type} - Size: {content_length} bytes ({content_length/1024:.1f} KB)")
                                    
                                    # Save both JPG and PDF files
                                    if any(img_type in content_type.lower() for img_type in ['jpeg', 'jpg', 'png', 'pdf']):
                                        try:
                                            file_extension = 'jpg'
                                            if 'pdf' in content_type.lower():
                                                file_extension = 'pdf'
                                            elif 'png' in content_type.lower():
                                                file_extension = 'png'
                                            
                                            downloaded_files.append({
                                                'url': request.url,
                                                'content': request.response.body,
                                                'content_type': content_type,
                                                'headers': dict(request.response.headers),
                                                'filename': f"newspaperarchive_{int(time.time())}.{file_extension}"
                                            })
                                            found_downloads += 1
                                            logger.info(f"Captured download via content-disposition: {content_type}")
                                        except Exception as e:
                                            logger.warning(f"Failed to capture download {request.url}: {e}")
                            
                            logger.info(f"Found {image_requests} image requests, {found_downloads} downloads after {waited_time}s")
                            
                            if found_downloads > 0:
                                logger.info(f"Found {found_downloads} downloads after {waited_time}s")
                                break
                            
                            # Wait before next check
                            time.sleep(wait_interval)
                            waited_time += wait_interval
                        
                        if waited_time >= max_wait_time and not downloaded_files:
                            logger.warning(f"No downloads found after waiting {max_wait_time}s - trying fallback approach")
                            
                            # Fallback: try to capture any large image responses
                            logger.info("Trying fallback: capturing large image responses...")
                            for request in driver.requests:
                                if request.response and request.response.status_code == 200:
                                    content_type = request.response.headers.get('content-type', '').lower()
                                    if 'image/' in content_type:
                                        try:
                                            content_length = len(request.response.body)
                                            logger.info(f"Found image request: {request.url[:100]} - Size: {content_length} bytes - Type: {content_type}")
                                            
                                            # Look for clues in the URL about image quality
                                            url_lower = request.url.lower()
                                            is_likely_full_size = any(keyword in url_lower for keyword in [
                                                'download', 'full', 'original', 'hi-res', 'high', 'large'
                                            ])
                                            is_likely_thumbnail = any(keyword in url_lower for keyword in [
                                                'thumb', 'preview', 'small', 'mini', 'icon'
                                            ])
                                            
                                            logger.info(f"URL analysis - Full-size indicators: {is_likely_full_size}, Thumbnail indicators: {is_likely_thumbnail}")
                                            
                                            # Prioritize images that are likely full-size and larger than 100KB for higher quality
                                            size_threshold = 100000 if is_likely_full_size else 50000  # 100KB for likely full-size, 50KB otherwise
                                            if content_length > size_threshold and not is_likely_thumbnail:
                                                file_extension = 'jpg'
                                                if 'png' in content_type:
                                                    file_extension = 'png'
                                                
                                                downloaded_files.append({
                                                    'url': request.url,
                                                    'content': request.response.body,
                                                    'content_type': content_type,
                                                    'headers': dict(request.response.headers),
                                                    'filename': f"newspaperarchive_fallback_{int(time.time())}.{file_extension}"
                                                })
                                                logger.info(f"Captured large image as fallback: {content_length} bytes")
                                                # Add size metadata for sorting later
                                                downloaded_files[-1]['size'] = content_length
                                        except Exception as e:
                                            logger.warning(f"Failed to capture fallback image {request.url}: {e}")
                        
                        logger.info(f"Found {len(downloaded_files)} files through selenium-wire monitoring")
                    else:
                        logger.warning("Selenium-wire not available or driver doesn't have requests attribute")
                        
                        # Alternative approach: Use JavaScript to capture download URLs
                        logger.info("Trying JavaScript-based download capture...")
                        try:
                            # Wait a bit more for download to process
                            time.sleep(5)
                            
                            # Use JavaScript to find any download-related elements or recently created blob URLs
                            js_script = """
                            var downloadLinks = [];
                            var images = [];
                            
                            // Look for any download links that might have been created
                            var links = document.querySelectorAll('a[href]');
                            for (var i = 0; i < links.length; i++) {
                                var href = links[i].href;
                                if (href.includes('download') || href.includes('blob:') || 
                                    href.includes('.jpg') || href.includes('.png') || href.includes('.pdf')) {
                                    downloadLinks.push(href);
                                }
                            }
                            
                            // Look for images that might be the newspaper page
                            var imgs = document.querySelectorAll('img');
                            for (var j = 0; j < imgs.length; j++) {
                                var src = imgs[j].src;
                                if (src && !src.includes('icon') && !src.includes('logo') && 
                                    (imgs[j].width > 200 || imgs[j].height > 200)) {
                                    images.push({
                                        src: src,
                                        width: imgs[j].width,
                                        height: imgs[j].height,
                                        naturalWidth: imgs[j].naturalWidth,
                                        naturalHeight: imgs[j].naturalHeight
                                    });
                                }
                            }
                            
                            return {
                                downloadLinks: downloadLinks,
                                images: images
                            };
                            """
                            
                            result = driver.execute_script(js_script)
                            logger.info(f"JavaScript found {len(result.get('downloadLinks', []))} download links and {len(result.get('images', []))} images")
                            
                            # Try to download from any found links
                            for link in result.get('downloadLinks', []):
                                try:
                                    logger.info(f"Attempting to download from JS-found link: {link[:100]}")
                                    # Session already has realistic headers set
                                    response = self.session.get(link, timeout=30)
                                    
                                    if response.status_code == 200 and len(response.content) > 10000:  # At least 10KB
                                        content_type = response.headers.get('content-type', 'image/jpeg')
                                        file_extension = 'jpg'
                                        if 'png' in content_type.lower():
                                            file_extension = 'png'
                                        elif 'pdf' in content_type.lower():
                                            file_extension = 'pdf'
                                        
                                        downloaded_files.append({
                                            'url': link,
                                            'content': response.content,
                                            'content_type': content_type,
                                            'headers': dict(response.headers),
                                            'filename': f"newspaperarchive_js_{int(time.time())}.{file_extension}"
                                        })
                                        logger.info(f"Successfully downloaded via JavaScript method: {len(response.content)} bytes")
                                        break  # Stop after first successful download
                                        
                                except Exception as e:
                                    logger.warning(f"Failed to download JS link {link}: {e}")
                            
                            # If no download links worked, try the images
                            if not downloaded_files:
                                logger.info("No download links worked, trying to capture large images...")
                                for img in result.get('images', []):
                                    try:
                                        # Focus on large images (likely newspaper pages)
                                        if (img.get('naturalWidth', 0) > 500 and img.get('naturalHeight', 0) > 500) or \
                                           (img.get('width', 0) > 500 and img.get('height', 0) > 500):
                                            
                                            src = img['src']
                                            logger.info(f"Attempting to download large image: {src[:100]} ({img.get('width')}x{img.get('height')})")
                                            
                                            # Session already has realistic headers set
                                            response = self.session.get(src, timeout=30)
                                            
                                            if response.status_code == 200 and len(response.content) > 50000:  # At least 50KB for newspaper image
                                                content_type = response.headers.get('content-type', 'image/jpeg')
                                                file_extension = 'jpg'
                                                if 'png' in content_type.lower():
                                                    file_extension = 'png'
                                                
                                                downloaded_files.append({
                                                    'url': src,
                                                    'content': response.content,
                                                    'content_type': content_type,
                                                    'headers': dict(response.headers),
                                                    'filename': f"newspaperarchive_img_{int(time.time())}.{file_extension}"
                                                })
                                                logger.info(f"Successfully captured newspaper image: {len(response.content)} bytes")
                                                break  # Stop after first successful image
                                                
                                    except Exception as e:
                                        logger.warning(f"Failed to download image {img['src']}: {e}")
                                        
                        except Exception as e:
                            logger.error(f"JavaScript-based capture failed: {e}")
                    
                    # Also check for files downloaded to the temp directory
                    logger.info("Checking for files downloaded to filesystem...")
                    try:
                        import os
                        import glob
                        
                        # Check the download directory for new files
                        download_patterns = [
                            os.path.join(download_dir, "*.jpg"),
                            os.path.join(download_dir, "*.jpeg"), 
                            os.path.join(download_dir, "*.png"),
                            os.path.join(download_dir, "*.pdf")
                        ]
                        
                        for pattern in download_patterns:
                            for filepath in glob.glob(pattern):
                                try:
                                    # Check if file was created recently (last 30 seconds)
                                    file_age = time.time() - os.path.getmtime(filepath)
                                    if file_age < 30:
                                        with open(filepath, 'rb') as f:
                                            file_content = f.read()
                                        
                                        filename = os.path.basename(filepath)
                                        downloaded_files.append({
                                            'url': f'file://{filepath}',
                                            'content': file_content,
                                            'content_type': 'application/octet-stream',
                                            'filename': f"newspaperarchive_{filename}"
                                        })
                                        logger.info(f"Found downloaded file: {filepath}")
                                        
                                        # Clean up the temp file
                                        os.remove(filepath)
                                except Exception as e:
                                    logger.warning(f"Error processing downloaded file {filepath}: {e}")
                    except Exception as e:
                        logger.warning(f"Error checking download directory: {e}")
                    
                    if not use_selenium_wire:
                        # Fallback: look for direct download links and try to capture them
                        logger.info("Trying fallback download link detection...")
                        download_links = driver.find_elements(By.CSS_SELECTOR, self.css_selectors['download_link'])
                        for link in download_links:
                            try:
                                download_url = link.get_attribute('href')
                                if download_url:
                                    # Try to download directly
                                    response = self.session.get(download_url, timeout=30)
                                    if response.status_code == 200:
                                        downloaded_files.append({
                                            'url': download_url,
                                            'content': response.content,
                                            'content_type': response.headers.get('content-type', 'image/jpeg'),
                                            'filename': f"newspaperarchive_{int(time.time())}.jpg"
                                        })
                                        logger.info(f"Downloaded file from: {download_url}")
                            except Exception as e:
                                logger.warning(f"Failed to download from link: {e}")
                    
                    logger.info(f"Total files found: {len(downloaded_files)}")
                    
                    # Extract metadata (placeholder selectors)
                    metadata = self._extract_metadata(driver, url, player_name)
                    
                    # Process downloaded files
                    if downloaded_files:
                        return self._process_downloaded_files(downloaded_files, url, player_name, project_name)
                    else:
                        logger.warning("No files were downloaded")
                        return {
                            'success': False,
                            'error': 'No files were downloaded',
                            'metadata': metadata
                        }
                
                except TimeoutException as e:
                    logger.error(f"Timeout waiting for page elements: {e}")
                    return {
                        'success': False,
                        'error': f'Timeout waiting for page elements: {str(e)}',
                        'debug_info': {
                            'page_title': driver.title,
                            'current_url': driver.current_url
                        }
                    }
                
            finally:
                try:
                    driver.quit()
                except Exception as e:
                    logger.warning(f"Error closing driver: {e}")
                
        except WebDriverException as e:
            logger.error(f"WebDriver error during NewspaperArchive extraction: {e}")
            return {'success': False, 'error': f'WebDriver error: {str(e)}'}
        except Exception as e:
            logger.error(f"Unexpected error during NewspaperArchive extraction: {e}")
            return {'success': False, 'error': f'Unexpected error: {str(e)}'}

    def _extract_metadata(self, driver, url: str, player_name: Optional[str]) -> Dict:
        """Extract article metadata using placeholder selectors"""
        metadata = {
            'title': 'Unknown Title',
            'date': 'Unknown Date', 
            'newspaper': 'Unknown Newspaper',
            'url': url,
            'player_name': player_name,
            'content_preview': ''
        }
        
        try:
            # Extract title (placeholder selector)
            try:
                title_elem = driver.find_element(By.CSS_SELECTOR, self.css_selectors['article_title'])
                metadata['title'] = title_elem.text.strip()
            except:
                logger.warning("Could not extract article title")
            
            # Extract date (placeholder selector)
            try:
                date_elem = driver.find_element(By.CSS_SELECTOR, self.css_selectors['article_date'])
                metadata['date'] = date_elem.text.strip()
            except:
                logger.warning("Could not extract article date")
            
            # Extract newspaper name (placeholder selector)
            try:
                newspaper_elem = driver.find_element(By.CSS_SELECTOR, self.css_selectors['newspaper_name'])
                metadata['newspaper'] = newspaper_elem.text.strip()
            except:
                logger.warning("Could not extract newspaper name")
            
            # Extract content preview (placeholder selector)
            try:
                content_elem = driver.find_element(By.CSS_SELECTOR, self.css_selectors['article_content'])
                content_text = content_elem.text.strip()
                metadata['content_preview'] = content_text[:500] + "..." if len(content_text) > 500 else content_text
            except:
                logger.warning("Could not extract article content")
                
        except Exception as e:
            logger.warning(f"Error extracting metadata: {e}")
        
        return metadata

    def _process_downloaded_files(self, downloaded_files: List[Dict], url: str, player_name: Optional[str], project_name: str) -> Dict:
        """Process and save downloaded files"""
        try:
            # Sort downloaded files by size (largest first) to prioritize highest quality
            sorted_files = sorted(downloaded_files, key=lambda x: len(x.get('content', b'')), reverse=True)
            
            if len(sorted_files) != len(downloaded_files):
                logger.info(f"Sorted {len(downloaded_files)} files by size for quality prioritization")
            
            # Log file sizes for debugging
            for i, file_data in enumerate(sorted_files[:3]):  # Log first 3 files
                size = len(file_data.get('content', b''))
                logger.info(f"File {i+1} size: {size} bytes ({size/1024:.1f} KB)")
                if size > 500000:  # 500KB+
                    logger.info(f"High-quality file detected: {size} bytes - likely full resolution")
                elif size < 100000:  # <100KB
                    logger.warning(f"Potentially low-quality file: {size} bytes - might be thumbnail/preview")
            
            processed_files = []
            
            # Pre-compute values used multiple times (like newspapers_extractor)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            logger.info(f"Processing {len(sorted_files)} downloaded files (sorted by size)")
            
            # Process files in size-sorted order (largest/highest quality first)
            for i, file_data in enumerate(sorted_files):
                try:
                    content_type = file_data['content_type']
                    content = file_data['content']
                    
                    # Optimized filename generation (like newspapers_extractor)
                    filename = (file_data.get('filename') or 
                              f"newspaperarchive_download_{timestamp}_{i+1}.jpg")
                    
                    # Handle storage using StorageManager (for Render deployment)
                    result = self.storage_manager.store_file(filename=filename, content=content)
                    file_path = result.get('path', filename) if result.get('success') else filename
                    
                    # Extract image metadata if it's an image
                    metadata = None
                    content = file_data['content']
                    if 'image' in file_data.get('content_type', '').lower():
                        try:
                            with Image.open(io.BytesIO(content)) as image:
                                metadata = {
                                    'size': image.size,
                                    'format': image.format,
                                    'mode': image.mode
                                }
                        except Exception:
                            pass  # Silently skip metadata extraction failures
                    
                    processed_files.append({
                        'filename': filename,
                        'path': file_path,
                        'content_type': file_data.get('content_type', 'image/jpeg'),
                        'size': len(content),
                        'metadata': metadata,
                        'url': file_data.get('url', url),
                        'content': content  # Include content for UI/Word doc processing
                    })
                    
                    logger.info(f"Saved downloaded file: {file_path}")
                    
                except Exception as e:
                    logger.error(f"Error processing downloaded file {i}: {e}")
                    continue
            
            # Get image data for UI preview (same as newspapers_extractor)
            image_data = (processed_files[0]['content'] 
                         if processed_files and 'image' in processed_files[0].get('content_type', '').lower() 
                         else None)
            
            if processed_files:
                now = datetime.now()
                return {
                    'success': True,
                    'method': 'newspaperarchive_download',
                    'url': url,
                    'files': processed_files,
                    'player_name': player_name,
                    'project_name': project_name,
                    'timestamp': now.isoformat(),
                    'image_data': image_data,  # Key for UI display
                    'headline': f"Downloaded from NewspaperArchive: {url}",
                    'source': 'newspaperarchive.com',
                    'date': now.strftime('%Y-%m-%d'),
                    'total_files': len(processed_files)
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to process any downloaded files',
                    'attempted_files': len(downloaded_files)
                }
                
        except Exception as e:
            logger.error(f"Error in _process_downloaded_files: {e}")
            return {
                'success': False,
                'error': f'Error processing files: {str(e)}'
            }

