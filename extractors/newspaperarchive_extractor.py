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
        # Check if we should use selenium-wire or fall back to regular selenium
        use_selenium_wire = SELENIUM_WIRE_AVAILABLE and not (self.is_render or self.is_replit_deployment)
        
        if not use_selenium_wire:
            if self.is_render or self.is_replit_deployment:
                logger.info("Using regular selenium for deployment environment due to compatibility constraints")
            else:
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
                seleniumwire_options = {
                    'verify_ssl': False,
                    'suppress_connection_errors': True,
                    'connection_timeout': 30,
                    'read_timeout': 30
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
                    time.sleep(3)  # Wait for download to initiate
                    
                    # Step 5: Monitor for downloads with polling loop (similar to newspapers_extractor)
                    if use_selenium_wire:
                        logger.info("Monitoring selenium-wire requests for downloads...")
                        
                        # Wait for downloads with polling loop
                        max_wait_time = 15  # Maximum 15 seconds to wait
                        wait_interval = 2   # Check every 2 seconds
                        waited_time = 0
                        
                        while waited_time < max_wait_time and not downloaded_files:
                            logger.info(f"Checking for downloads... ({waited_time}/{max_wait_time}s)")
                            
                            # Monitor network requests for downloads - look for content-disposition header
                            found_downloads = 0
                            for request in driver.requests:
                                # Log all requests for debugging (only on first check to avoid spam)
                                if waited_time == 0:
                                    logger.debug(f"Request: {request.url} - Response: {bool(request.response)} - Content-Type: {request.response.headers.get('content-type', 'N/A') if request.response else 'N/A'}")
                                
                                # Look for the content-disposition header which indicates a file download
                                if request.response and request.response.headers.get('content-disposition'):
                                    content_type = request.response.headers.get('content-type', '')
                                    logger.info(f"Found downloadable response: {request.url} - Content-Type: {content_type}")
                                    
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
                            
                            if found_downloads > 0:
                                logger.info(f"Found {found_downloads} downloads after {waited_time}s")
                                break
                            
                            # Wait before next check
                            time.sleep(wait_interval)
                            waited_time += wait_interval
                        
                        if waited_time >= max_wait_time and not downloaded_files:
                            logger.warning(f"No downloads found after waiting {max_wait_time}s")
                        
                        logger.info(f"Found {len(downloaded_files)} files through selenium-wire monitoring")
                    
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
            processed_files = []
            
            # Process all downloaded files (should now only be actual downloads with content-disposition)
            logger.info(f"Processing {len(downloaded_files)} downloaded files")
            
            # Pre-compute values used multiple times (like newspapers_extractor)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            for i, file_data in enumerate(downloaded_files):
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

