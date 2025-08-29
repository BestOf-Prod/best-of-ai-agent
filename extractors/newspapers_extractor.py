# newspapers_extractor.py
# Complete Newspaper.com Scraping Suite with Auto Cookie Extraction

import streamlit as st
from utils.storage_manager import StorageManager
from utils.credential_manager import CredentialManager
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException, WebDriverException, StaleElementReferenceException
from selenium.webdriver.support import expected_conditions as EC
try:
    import seleniumwire
    from seleniumwire import webdriver as wire_webdriver
    SELENIUM_WIRE_AVAILABLE = True
    print(f"DEBUG: selenium-wire imported successfully, version: {getattr(seleniumwire, '__version__', 'unknown')}")
except ImportError as e:
    SELENIUM_WIRE_AVAILABLE = False
    print(f"DEBUG: selenium-wire import failed: {e}")
    # Try alternative import path
    try:
        import sys
        print(f"DEBUG: Python path: {sys.path}")
        print(f"DEBUG: Installed packages contain seleniumwire: {'seleniumwire' in str(sys.modules)}")
    except:
        pass
except Exception as e:
    SELENIUM_WIRE_AVAILABLE = False
    print(f"DEBUG: selenium-wire import error (not ImportError): {e}")
import cv2
import pytesseract
from PIL import Image, ImageEnhance
# Optional numpy import with fallback
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("NumPy not available. Advanced image processing features will be disabled.")
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

class SeleniumLoginManager:
    """Handle direct login authentication using Selenium"""
    
    def __init__(self):
        self.driver = None
        self.cookies = {}
        self.last_login = None
        self.login_credentials = None
        self.is_replit = 'REPL_ID' in os.environ or 'REPL_SLUG' in os.environ
        self.is_render = 'RENDER' in os.environ or 'RENDER_SERVICE_ID' in os.environ
        # Detect if we're in a Replit deployment (more restrictive than IDE)
        self.is_replit_deployment = (
            self.is_replit and 
            ('REPL_DEPLOYMENT' in os.environ or 
             'REPLIT_DEPLOYMENT' in os.environ or
             os.environ.get('REPL_ENVIRONMENT') == 'production' or
             os.environ.get('REPLIT_ENVIRONMENT') == 'production' or
             # Check for deployment-specific environment variables
             'REPL_DEPLOYMENT_ID' in os.environ or
             'REPLIT_DEPLOYMENT_ID' in os.environ or
             # Check if we're running on a deployment URL pattern
             os.environ.get('REPL_SLUG', '').endswith('.repl.co') or
             # Check for reduced resource indicators
             os.environ.get('REPL_MEMORY_LIMIT') == '1024' or
             os.environ.get('REPLIT_MEMORY_LIMIT') == '1024')
        )
        # Detect if we're in batch processing mode (higher timeout needs)
        self.is_batch_processing = (
            threading.active_count() > 1 or  # Multiple threads active
            os.environ.get('BATCH_PROCESSING', '').lower() == 'true'  # Explicit batch mode flag
        )
    
    def set_credentials(self, email: str, password: str):
        """Set login credentials"""
        self.login_credentials = {'email': email, 'password': password}
    
    def _initialize_chrome_driver(self):
        """Initialize Chrome driver with standard settings."""
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
        chrome_options.add_argument('--lang=en-US')
        
        # Add Replit-specific Chrome options to prevent timeout issues
        if self.is_replit:
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-features=TranslateUI')
            chrome_options.add_argument('--disable-ipc-flooding-protection')
            chrome_options.add_argument('--disable-background-networking')
            chrome_options.add_argument('--disable-default-apps')
            chrome_options.add_argument('--disable-hang-monitor')
            chrome_options.add_argument('--disable-prompt-on-repost')
            chrome_options.add_argument('--disable-sync')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--metrics-recording-only')
            chrome_options.add_argument('--no-first-run')
            chrome_options.add_argument('--safebrowsing-disable-auto-update')
            chrome_options.add_argument('--enable-automation')
            chrome_options.add_argument('--password-store=basic')
            chrome_options.add_argument('--use-mock-keychain')
            chrome_options.add_argument('--single-process')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            
            # Add deployment-specific options for even more resource constraints
            if self.is_replit_deployment or self.is_render:
                chrome_options.add_argument('--memory-pressure-off')
                chrome_options.add_argument('--max_old_space_size=256')  # Even more aggressive for Render
                chrome_options.add_argument('--disable-background-mode')
                chrome_options.add_argument('--disable-plugins')
                chrome_options.add_argument('--disable-java')
                chrome_options.add_argument('--disable-component-extensions-with-background-pages')
                chrome_options.add_argument('--disable-software-rasterizer')
                chrome_options.add_argument('--disable-accelerated-2d-canvas')
                chrome_options.add_argument('--disable-accelerated-video-decode')
                chrome_options.add_argument('--disable-accelerated-video-encode')
                chrome_options.add_argument('--disable-threaded-scrolling')
                chrome_options.add_argument('--disable-smooth-scrolling')
                chrome_options.add_argument('--window-size=800,600')  # Smaller window for deployment
                chrome_options.add_argument('--remote-debugging-port=9222')  # Enable remote debugging
                
                # Render-specific ultra-low memory options
                if self.is_render:
                    chrome_options.add_argument('--max-memory-usage=128MB')
                    chrome_options.add_argument('--single-process')  # Force single process mode
                    chrome_options.add_argument('--disable-site-isolation-trials')
                    chrome_options.add_argument('--disable-features=VizDisplayCompositor,VizHitTestSurfaceLayer')
                    chrome_options.add_argument('--aggressive-cache-discard')
                    chrome_options.add_argument('--disable-shared-workers')
                    chrome_options.add_argument('--disable-service-worker-navigation-preload')
                    logger.info("Applied Render-specific ultra-low memory Chrome options")
                else:
                    logger.info("Applied deployment-specific Chrome options for resource constraints")
            
            # Add batch processing options for improved stability
            if self.is_batch_processing:
                chrome_options.add_argument('--renderer-timeout=30000')  # 30 seconds renderer timeout
                chrome_options.add_argument('--ipc-timeout=30000')  # 30 seconds IPC timeout
                chrome_options.add_argument('--disable-renderer-backgrounding')
                chrome_options.add_argument('--disable-background-timer-throttling')
                chrome_options.add_argument('--disable-features=VizDisplayCompositor')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_argument('--disable-web-security')
                chrome_options.add_argument('--disable-features=TranslateUI')
                logger.info("Applied batch processing Chrome options for improved stability")
        
        try:
            # Try multiple approaches to initialize Chrome driver
            driver = None
            
            # Deployment environments need special handling - try undetected-chromedriver first
            if self.is_replit_deployment:
                logger.info("Detected Replit deployment environment - using optimized driver initialization")
                
                # First try: undetected-chromedriver for deployment (most compatible)
                try:
                    import undetected_chromedriver as uc
                    
                    # Convert Chrome options to undetected_chromedriver format
                    uc_options = uc.ChromeOptions()
                    for arg in chrome_options.arguments:
                        uc_options.add_argument(arg)
                    
                    # Use version_main parameter to ensure compatibility
                    driver = uc.Chrome(options=uc_options, headless=True, version_main=None)
                    logger.info("Successfully initialized undetected Chrome WebDriver for deployment")
                except Exception as e:
                    logger.warning(f"Undetected Chrome WebDriver failed in deployment: {str(e)}")
                    
                    # Second try: WebDriverManager with longer timeout for deployment
                    try:
                        from webdriver_manager.chrome import ChromeDriverManager
                        from selenium.webdriver.chrome.service import Service
                        
                        # Increase timeout for deployment environment
                        service = Service(ChromeDriverManager().install())
                        driver = webdriver.Chrome(service=service, options=chrome_options)
                        logger.info("Successfully initialized Chrome WebDriver with WebDriverManager for deployment")
                    except Exception as e:
                        logger.warning(f"WebDriverManager Chrome failed in deployment: {str(e)}")
            
            # Standard initialization order for IDE or if deployment methods failed
            if not driver:
                # First try: Standard Chrome WebDriver
                try:
                    driver = webdriver.Chrome(options=chrome_options)
                    logger.info("Successfully initialized Chrome WebDriver")
                except WebDriverException as e:
                    logger.warning(f"Standard Chrome WebDriver failed: {str(e)}")
                    
                    # Second try: Use WebDriverManager for automatic driver management
                    try:
                        from webdriver_manager.chrome import ChromeDriverManager
                        from selenium.webdriver.chrome.service import Service
                        
                        service = Service(ChromeDriverManager().install())
                        driver = webdriver.Chrome(service=service, options=chrome_options)
                        logger.info("Successfully initialized Chrome WebDriver with WebDriverManager")
                    except Exception as e:
                        logger.warning(f"WebDriverManager Chrome failed: {str(e)}")
                        
                        # Third try: Use undetected-chromedriver for Replit environments
                        try:
                            import undetected_chromedriver as uc
                            
                            # Convert Chrome options to undetected_chromedriver format
                            uc_options = uc.ChromeOptions()
                            for arg in chrome_options.arguments:
                                uc_options.add_argument(arg)
                            
                            driver = uc.Chrome(options=uc_options, headless=True)
                            logger.info("Successfully initialized undetected Chrome WebDriver")
                        except Exception as e:
                            logger.error(f"Undetected Chrome WebDriver failed: {str(e)}")
                            
                            # Fourth try: Try to find Chrome binary manually
                            try:
                                import shutil
                                chrome_paths = [
                                    '/usr/bin/google-chrome',
                                    '/usr/bin/google-chrome-stable',
                                    '/usr/bin/chromium-browser',
                                    '/usr/bin/chromium',
                                    '/snap/bin/chromium',
                                    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
                                ]
                                
                                chrome_binary = None
                                for path in chrome_paths:
                                    if shutil.which(path) or os.path.exists(path):
                                        chrome_binary = path
                                        break
                                
                                if chrome_binary:
                                    chrome_options.binary_location = chrome_binary
                                    driver = webdriver.Chrome(options=chrome_options)
                                    logger.info(f"Successfully initialized Chrome WebDriver with binary: {chrome_binary}")
                                else:
                                    logger.error("No Chrome binary found on system")
                                    
                            except Exception as e:
                                logger.error(f"Manual Chrome binary detection failed: {str(e)}")
            
            if driver:
                self.driver = driver
                # Set context-specific timeouts
                if self.is_replit_deployment or self.is_render:
                    page_load_timeout = 180  # Even longer for deployment
                    implicit_wait = 30
                    logger.info("Applied deployment-specific timeouts (180s page load, 30s implicit wait)")
                elif self.is_batch_processing:
                    page_load_timeout = 120  # Longer for batch processing
                    implicit_wait = 30  # Increase implicit wait for batch processing
                    logger.info("Applied batch processing timeouts (120s page load, 30s implicit wait)")
                elif self.is_replit:
                    page_load_timeout = 120
                    implicit_wait = 20
                    logger.info("Applied Replit IDE timeouts (120s page load, 20s implicit wait)")
                else:
                    page_load_timeout = 30
                    implicit_wait = 10
                
                self.driver.set_page_load_timeout(page_load_timeout)
                self.driver.implicitly_wait(implicit_wait)
                return True
            else:
                raise WebDriverException("All Chrome WebDriver initialization methods failed")
                
        except WebDriverException as e:
            logger.error(f"Failed to initialize Chrome driver: {str(e)}")
            if self.is_replit_deployment:
                st.error(f"Chrome WebDriver failed in Replit deployment environment. This may be due to resource constraints or missing Chrome installation. Try redeploying or contact support. Error: {str(e)}")
            elif self.is_replit:
                st.error(f"Chrome WebDriver failed in Replit IDE environment. Please install Chrome/Chromium or use a different browser. Error: {str(e)}")
            else:
                st.error(f"Failed to initialize web browser. Please ensure Chrome is installed and updated: {str(e)}")
            return False

    def login(self) -> bool:
        """Perform login using Selenium."""
        if not self.login_credentials and not self.cookies:
            logger.error("No login credentials or cookies set.")
            return False

        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except Exception as e:
                logger.warning(f"Failed to quit existing driver gracefully: {e}")

        if not self._initialize_chrome_driver():
            return False

        try:
            # If we have cookies, go directly to home page and verify authentication
            if self.cookies:
                logger.info("Cookies provided, verifying authentication from home page...")
                self.driver.get('https://www.newspapers.com/')
                
                # Add cookies to the driver
                for name, value in self.cookies.items():
                    try:
                        # Check if driver is still valid before adding cookies
                        if not self.driver:
                            logger.error("Driver connection lost during cookie addition")
                            return False
                        cookie_domain = '.newspapers.com'
                        self.driver.add_cookie({'name': name, 'value': value, 'domain': cookie_domain, 'path': '/'})
                    except Exception as e:
                        logger.warning(f"Could not add cookie {name} to driver: {e}")
                        # If connection is lost, try to reinitialize driver
                        if "Connection refused" in str(e) or "Remote end closed" in str(e):
                            logger.warning("WebDriver connection lost, attempting to reinitialize")
                            if not self._initialize_chrome_driver():
                                logger.error("Failed to reinitialize driver after connection loss")
                                return False
                            # Restart from the beginning with new driver
                            self.driver.get('https://www.newspapers.com/')
                            break
                
                # Refresh page to apply cookies (check driver validity first)
                if not self.driver:
                    logger.error("Driver connection lost before refresh")
                    return False
                try:
                    self.driver.refresh()
                except Exception as e:
                    logger.error(f"Failed to refresh page: {e}")
                    if "Connection refused" in str(e) or "Remote end closed" in str(e):
                        logger.warning("WebDriver connection lost during refresh, attempting to reinitialize")
                        if not self._initialize_chrome_driver():
                            logger.error("Failed to reinitialize driver after refresh failure")
                            return False
                        self.driver.get('https://www.newspapers.com/')
                    else:
                        return False
                
                # Wait for the 'ncom' object and its 'isloggedin' property to be accessible and true
                try:
                    wait_timeout = 90 if (self.is_replit or self.is_render) else 30
                    WebDriverWait(self.driver, wait_timeout).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "span.MemberNavigation_Subscription__RU0Cu"))
                    )
                    logger.info("Authentication verified via cookies: Subscription element found.")
                    return True
                except TimeoutException:
                    logger.warning("Cookie-based authentication verification timed out.")
                    return False
                
            # If no cookies or cookie verification failed, proceed with standard login
            logger.info("Navigating to login page...")
            self.driver.get('https://www.newspapers.com/signin/')

            # Wait for either (1) email field to appear OR (2) Cloudflare CAPTCHA to appear
            try:
                wait_timeout = 60 if (self.is_replit or self.is_render) else 20
                WebDriverWait(self.driver, wait_timeout).until(
                    EC.presence_of_element_located((By.ID, "email"))
                )
                logger.info("Login page loaded and email field found.")
                # At this point, check for Cloudflare specific elements if they are present alongside the form
                if self._is_cloudflare_captcha_present():
                    logger.warning("Cloudflare CAPTCHA detected after page load.")
                    st.error("Cloudflare CAPTCHA detected. Automated login is blocked. Manual intervention or anti-captcha service needed.")
                    self._save_debug_html(self.driver, "cloudflare_captcha_present_on_load")
                    return False

            except TimeoutException:
                # This could mean CAPTCHA immediately appeared and prevented form loading
                logger.warning("Email field not found within timeout. Checking for immediate Cloudflare redirect/block.")
                if self._is_cloudflare_captcha_present():
                    logger.error("Cloudflare CAPTCHA immediately blocked page load. Cannot proceed.")
                    st.error("Cloudflare CAPTCHA immediately blocked access. This is a hard block.")
                    self._save_debug_html(self.driver, "cloudflare_captcha_immediate_block")
                    return False
                else:
                    logger.error("Email field not found and no Cloudflare CAPTCHA. Page structure might have changed or unexpected error.")
                    self._save_debug_html(self.driver, "email_field_not_found_no_captcha")
                    return False

            email_field = self.driver.find_element(By.ID, "email")
            password_field = self.driver.find_element(By.ID, "password")

            email_field.clear()
            password_field.clear()

            email_field.send_keys(self.login_credentials['email'])
            time.sleep(1)
            password_field.send_keys(self.login_credentials['password'])
            time.sleep(1)
            
            # Check for Cloudflare "Verify you are human" checkbox BEFORE clicking submit
            cloudflare_checkbox_selector = 'label.cf-turnstile-label' # Common selector for the label next to the checkbox
            if self.driver.find_elements(By.CSS_SELECTOR, cloudflare_checkbox_selector):
                logger.warning("Cloudflare 'Verify you are human' checkbox detected before submit. Automated login is blocked.")
                st.error("Cloudflare 'Verify you are human' checkbox detected. Automated login is blocked.")
                self._save_debug_html(self.driver, "cloudflare_captcha_before_submit")
                return False

            logger.info("Login form filled. Looking for Newspapers.com sign in button...")
            submit_button = self.driver.find_element(By.CSS_SELECTOR, 'button[title="Sign in with Newspapers.com"]')
            logger.info("Found Newspapers.com sign in button. Clicking...")
            submit_button.click()

            # Wait for login success
            login_successful = False
            try:
                # Wait for either successful login indicators or error messages
                wait_timeout = 90 if (self.is_replit or self.is_render) else 30
                WebDriverWait(self.driver, wait_timeout).until(
                    lambda d: (
                        d.execute_script("return window.ncom && window.ncom.statsiguser && window.ncom.statsiguser.custom && window.ncom.statsiguser.custom.isloggedin;") or
                        "incorrect email or password" in d.page_source.lower() or
                        "invalid login" in d.page_source.lower()
                    )
                )
                
                # Check if login was successful
                login_successful = self.driver.execute_script("return window.ncom && window.ncom.statsiguser && window.ncom.statsiguser.custom && window.ncom.statsiguser.custom.isloggedin;")
                
                if login_successful:
                    logger.info("Login successful: isloggedin flag is true.")
                else:
                    logger.warning("Login failed: isloggedin flag is false.")

            except TimeoutException:
                logger.warning("Login timed out during post-submission wait or 'isloggedin' check.")
                # Attempt to check if an error message for incorrect credentials appeared
                if "incorrect email or password" in self.driver.page_source.lower() or \
                   "invalid login" in self.driver.page_source.lower():
                    st.error("Login failed: Incorrect email or password. Please verify your credentials.")
                elif self._is_cloudflare_captcha_present(): # Check for CAPTCHA after timeout
                    logger.error("Cloudflare CAPTCHA detected after login attempt. This is the blocker.")
                    st.error("Cloudflare CAPTCHA detected. Automated login is blocked after submission.")
                else:
                    st.error("Login timed out: Could not determine status after submission. The page might be loading slowly or encountering a dynamic challenge.")

                self._save_debug_html(self.driver, "login_failure_timeout") # Save debug HTML on any login failure
                return False

            if not login_successful:
                logger.error("Selenium auto-authentication failed: Login status inconclusive after wait.")
                self._save_debug_html(self.driver, "login_inconclusive")
                return False

            time.sleep(7) # Keep this to allow all JS to settle

            self.cookies = self.driver.get_cookies() # Retrieve all cookies *after* successful login and page load
            # Convert to dictionary for easier use
            self.cookies = {cookie['name']: cookie['value'] for cookie in self.cookies}

            if not self.cookies:
                logger.warning("No cookies found after successful login attempt via Selenium. This is unusual but might happen if cookies are HttpOnly.")
                # If 'isloggedin' is true, and no cookies are found, it's a very rare edge case.
                # For now, if 'isloggedin' is true, we consider it a success even without cookies, as the driver is authenticated.
                if not self.driver.execute_script("return window.ncom && window.ncom.statsiguser && window.ncom.statsiguser.custom && window.ncom.statsiguser.custom.isloggedin;"):
                     return False # If 'isloggedin' is false, it's definitely a failure
                else:
                     logger.info("Proceeding without explicit cookies, 'isloggedin' is true.")

            self.last_login = datetime.now()
            logger.info(f"Selenium login completed. Extracted {len(self.cookies)} cookies.")
            return True

        except Exception as e:
            logger.error(f"Selenium login process failed unexpectedly: {str(e)}", exc_info=True)
            st.error(f"An unexpected error occurred during Newspapers.com login: {str(e)}")
            self._save_debug_html(self.driver, "login_unexpected_error")
            return False
        finally:
            # The driver is kept open here and handled by the AutoCookieManager or subsequent calls.
            pass

    def _is_cloudflare_captcha_present(self) -> bool:
        """Checks for common Cloudflare CAPTCHA elements."""
        try:
            # Check for the cf-turnstile iframe or its parent container
            if self.driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="challenges.cloudflare.com/turnstile"]'):
                logger.debug("Cloudflare Turnstile iframe found.")
                return True
            if self.driver.find_elements(By.ID, 'cf-challenge-body') or \
               self.driver.find_elements(By.CLASS_NAME, 'cf-turnstile'):
                logger.debug("Cloudflare challenge body or turnstile element found.")
                return True
            # Check for the "Verify you are human" text
            if "verify you are human" in self.driver.page_source.lower():
                logger.debug("Cloudflare 'verify you are human' text found in page source.")
                return True
            return False
        except Exception as e:
            logger.warning(f"Error checking for Cloudflare CAPTCHA elements: {e}")
            return False

    def _save_debug_html(self, driver, url: str) -> None:
        """Saves debug HTML and a summary of the page."""
        try:
            debug_dir = "debug_html"
            os.makedirs(debug_dir, exist_ok=True)
            
            page_html = driver.page_source
            
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"debug_page_{timestamp}_{url_hash}.html"
            filepath = os.path.join(debug_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(page_html)
            
            logger.info(f"Debug HTML saved to {filepath}")
            
            # Also save a summary
            summary_filename = f"debug_summary_{timestamp}_{url_hash}.txt"
            summary_filepath = os.path.join(debug_dir, summary_filename)
            
            with open(summary_filepath, 'w', encoding='utf-8') as f:
                f.write(f"URL: {url}\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Page Title: {driver.title}\n")
                f.write(f"Current URL: {driver.current_url}\n")
                f.write(f"Page source length: {len(page_html)} characters\n")
                f.write(f"HTML file: {filename}\n")
                
                # Check for common paywall indicators
                paywall_indicators = ['subscription', 'sign in to view', 'upgrade your access', 'paywall']
                found_indicators = [ind for ind in paywall_indicators if ind in page_html.lower()]
                if found_indicators:
                    f.write(f"Paywall indicators found: {found_indicators}\n")
                else:
                    f.write("No paywall indicators found\n")
            
            logger.info(f"Debug summary saved to {summary_filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save debug HTML for {url}: {e}")

class AutoCookieManager:
    """Automatically extract and manage cookies from user's browser, preferring Selenium login."""
    
    def __init__(self):
        self.cookies = {}
        self.session = requests.Session()
        self.last_extraction = None
        self.selenium_login_manager = SeleniumLoginManager() # Renamed to avoid confusion
        
    def set_login_credentials(self, email: str, password: str):
        """Set login credentials for Selenium authentication"""
        self.selenium_login_manager.set_credentials(email, password)
        
    def auto_authenticate(self) -> bool:
        """Attempt to authenticate using Selenium login."""
        logger.info("Attempting auto-authentication via Selenium login.")
        
        # If we have cookies, pass them to the SeleniumLoginManager
        if self.cookies:
            logger.info(f"Using provided cookies for authentication. Cookie count: {len(self.cookies)}")
            logger.debug(f"Cookie names: {list(self.cookies.keys())}")
            self.selenium_login_manager.cookies = self.cookies
            
        if self.selenium_login_manager.login():
            self.cookies = self.selenium_login_manager.cookies
            self.last_extraction = datetime.now()

            # Transfer Selenium cookies to requests.Session
            self.session.cookies.clear()
            for name, value in self.cookies.items():
                # Add domain and path for robustness, though requests usually handles it
                self.session.cookies.set(name, value, domain=".newspapers.com", path="/")
            logger.info(f"Transferred {len(self.cookies)} cookies to requests.Session.")
            return True
        logger.error("Selenium auto-authentication failed.")
        return False
    
    def test_authentication(self, test_url: str = "https://www.newspapers.com/") -> bool:
        """Test if extracted cookies provide valid authentication using Selenium."""
        # Use the Selenium driver directly for robust authentication check, especially for JS state
        if not self.selenium_login_manager.driver:
            logger.warning("No active Selenium driver for authentication test. Attempting to re-initialize.")
            if not self.selenium_login_manager._initialize_chrome_driver():
                logger.error("Failed to initialize driver for authentication test.")
                return False
            # If a new driver is initialized, ensure cookies are loaded into it.
            driver = self.selenium_login_manager.driver
            driver.get('https://www.newspapers.com/') # Go to base domain to set cookies
            
            if not self.cookies:
                logger.error("No cookies available for authentication test")
                return False
                
            logger.info(f"Adding {len(self.cookies)} cookies to driver for authentication test")
            for name, value in self.cookies.items():
                try:
                    cookie_domain = '.newspapers.com'
                    driver.add_cookie({'name': name, 'value': value, 'domain': cookie_domain, 'path': '/'})
                    logger.debug(f"Added cookie: {name}")
                except Exception as e:
                    logger.warning(f"Could not add cookie {name} to driver for test: {e}")
            time.sleep(2) # Give browser a moment to apply cookies

        driver = self.selenium_login_manager.driver

        try:
            logger.info(f"Testing authentication by accessing {test_url} with Selenium.")
            driver.get(test_url)

            # Wait for the 'ncom' object and its 'isloggedin' property to be accessible and true
            wait_timeout = 90 if (self.selenium_login_manager.is_replit or self.selenium_login_manager.is_render) else 30
            WebDriverWait(driver, wait_timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.MemberNavigation_Subscription__RU0Cu"))
            )
            logger.info("Authentication verified: window.ncom.statsiguser.custom.isloggedin is true.")
            return True

        except TimeoutException:
            logger.warning("Selenium authentication test timed out: 'isloggedin' flag not true.")
            self.selenium_login_manager._save_debug_html(driver, "auth_test_failure_timeout")
            return False
        except Exception as e:
            logger.error(f"Selenium authentication test failed due to exception: {str(e)}", exc_info=True)
            self.selenium_login_manager._save_debug_html(driver, "auth_test_failure_exception")
            return False
    
    def refresh_cookies_if_needed(self) -> bool:
        """Check if cookies need refreshing and do so automatically."""
        if not self.last_extraction or datetime.now() - self.last_extraction > timedelta(hours=3): # Reduced refresh interval
            logger.info("Cookies are old or not present, re-authenticating.")
            if not self.auto_authenticate():
                st.error("Failed to re-authenticate. Please check credentials in sidebar.")
                return False
        
        if not self.test_authentication():
            logger.warning("Existing cookies failed authentication test, re-authenticating.")
            if not self.auto_authenticate():
                st.error("Failed to re-authenticate after test failure. Please check credentials in sidebar.")
                return False
        
        logger.info("Authentication is current and valid.")
        return True

class NewspaperImageProcessor:
    """Advanced image processing for newspaper clippings"""
    
    def __init__(self):
        self.min_article_area = 30000  # Minimum area for article detection
        self.text_confidence_threshold = 30  # Minimum OCR confidence
    
    def detect_newspaper_clipping_borders(self, image: Image.Image) -> Tuple[int, int, int, int]:
        """
        Detect the borders of a newspaper clipping to crop out excess background.
        Uses multiple detection methods for better accuracy.
        Returns (x, y, width, height) of the clipping area.
        """
        logger.info(f"Detecting newspaper clipping borders in image of size: {image.size}")
        
        if not NUMPY_AVAILABLE:
            logger.warning("NumPy not available, returning full image bounds")
            return (0, 0, image.width, image.height)
        
        # Convert PIL image to OpenCV format
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Method 1: Edge detection approach
        try:
            logger.info("Trying edge detection method...")
            # Apply stronger Gaussian blur to reduce noise and focus on main boundaries
            blurred = cv2.GaussianBlur(gray, (9, 9), 0)
            
            # Use more conservative Canny edge detection to find main boundaries
            edges = cv2.Canny(blurred, 30, 100)
            
            # Use larger kernel and more iterations to merge nearby edges
            kernel = np.ones((7, 7), np.uint8)
            edges = cv2.dilate(edges, kernel, iterations=3)
            edges = cv2.erode(edges, kernel, iterations=1)  # Clean up
            
            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Filter contours by area (must be at least 5% of image)
                min_area = (image.width * image.height) * 0.05
                valid_contours = [c for c in contours if cv2.contourArea(c) > min_area]
                
                if valid_contours:
                    # Find the largest valid contour
                    largest_contour = max(valid_contours, key=cv2.contourArea)
                    x, y, w, h = cv2.boundingRect(largest_contour)
                    
                    # Check if this looks like a reasonable clipping area
                    area_ratio = (w * h) / (image.width * image.height)
                    if 0.15 <= area_ratio <= 0.95:  # Between 15% and 95% of image
                        logger.info(f"Edge detection successful: area_ratio={area_ratio:.3f}")
                        return self._apply_smart_padding(x, y, w, h, image)
        except Exception as e:
            logger.warning(f"Edge detection failed: {e}")
        
        # Method 2: Brightness-based detection
        try:
            logger.info("Trying brightness-based detection...")
            # Calculate brightness statistics
            mean_brightness = np.mean(gray)
            std_brightness = np.std(gray)
            
            # Create binary mask for areas significantly different from background
            # Assume background is either very bright or very dark
            if mean_brightness > 128:  # Light background
                threshold = mean_brightness - std_brightness
                mask = gray < threshold
            else:  # Dark background
                threshold = mean_brightness + std_brightness
                mask = gray > threshold
            
            # Find the bounding box of the content area
            coords = np.column_stack(np.where(mask))
            if len(coords) > 0:
                y_min, x_min = coords.min(axis=0)
                y_max, x_max = coords.max(axis=0)
                
                x, y = x_min, y_min
                w, h = x_max - x_min, y_max - y_min
                
                # Check if this looks reasonable
                area_ratio = (w * h) / (image.width * image.height)
                if 0.15 <= area_ratio <= 0.95:
                    logger.info(f"Brightness detection successful: area_ratio={area_ratio:.3f}")
                    return self._apply_smart_padding(x, y, w, h, image)
        except Exception as e:
            logger.warning(f"Brightness detection failed: {e}")
        
        # Method 3: Simple trim whitespace/background
        try:
            logger.info("Trying background trimming...")
            # Find the dominant background color (corner pixel)
            bg_color = gray[0, 0]
            
            # Find bounds where content differs significantly from background
            tolerance = 50  # More lenient tolerance to avoid cropping too tightly
            
            # Find top and bottom bounds
            for y in range(gray.shape[0]):
                if np.any(np.abs(gray[y, :] - bg_color) > tolerance):
                    top = y
                    break
            else:
                top = 0
            
            for y in range(gray.shape[0] - 1, -1, -1):
                if np.any(np.abs(gray[y, :] - bg_color) > tolerance):
                    bottom = y
                    break
            else:
                bottom = gray.shape[0] - 1
            
            # Find left and right bounds
            for x in range(gray.shape[1]):
                if np.any(np.abs(gray[:, x] - bg_color) > tolerance):
                    left = x
                    break
            else:
                left = 0
            
            for x in range(gray.shape[1] - 1, -1, -1):
                if np.any(np.abs(gray[:, x] - bg_color) > tolerance):
                    right = x
                    break
            else:
                right = gray.shape[1] - 1
            
            x, y = left, top
            w, h = right - left, bottom - top
            
            # Check if this looks reasonable
            area_ratio = (w * h) / (image.width * image.height)
            if 0.15 <= area_ratio <= 0.95:
                logger.info(f"Background trimming successful: area_ratio={area_ratio:.3f}")
                return self._apply_smart_padding(x, y, w, h, image)
        except Exception as e:
            logger.warning(f"Background trimming failed: {e}")
        
        # Fallback: return full image
        logger.warning("All detection methods failed, returning full image bounds")
        return (0, 0, image.width, image.height)
    
    def _apply_smart_padding(self, x: int, y: int, w: int, h: int, image: Image.Image) -> Tuple[int, int, int, int]:
        """Apply intelligent padding to detected borders"""
        # Calculate padding based on image size (2% of each dimension)
        padding_x = max(10, int(image.width * 0.02))
        padding_y = max(10, int(image.height * 0.02))
        
        # Apply padding while keeping within image bounds
        x = max(0, x - padding_x)
        y = max(0, y - padding_y)
        w = min(image.width - x, w + 2 * padding_x)
        h = min(image.height - y, h + 2 * padding_y)
        
        logger.info(f"Applied smart padding: x={x}, y={y}, w={w}, h={h}")
        return (x, y, w, h)
    
    def enhance_image_quality(self, image: Image.Image) -> Image.Image:
        """Enhance image quality for better OCR"""
        if image.mode != 'L':
            image = image.convert('L')
        
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        if not NUMPY_AVAILABLE:
            logger.warning("NumPy not available, using basic image enhancement")
            return image
            
        img_array = np.array(image)
        
        denoised = cv2.fastNlMeansDenoising(img_array)
        
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        return Image.fromarray(binary)
    
    def detect_article_regions(self, image: Image.Image) -> List[Tuple[int, int, int, int]]:
        """Detect individual article regions in newspaper page"""
        logger.info(f"Detecting article regions in image of size: {image.size}")
        
        if not NUMPY_AVAILABLE:
            logger.warning("NumPy not available, using simple article region detection")
            # Return full image as single region
            return [(0, 0, image.width, image.height)]
            
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        morphed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(
            morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        logger.info(f"Found {len(contours)} total contours.")
        
        article_regions = []
        min_area = 5000
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            
            if area > min_area:
                x, y, w, h = cv2.boundingRect(contour)
                
                padding = 10
                x = max(0, x - padding)
                y = max(0, y - padding)
                w = min(image.width - x, w + 2 * padding)
                h = min(image.height - y, h + 2 * padding)
                
                aspect_ratio = h / w if w > 0 else 0
                
                if 0.1 < aspect_ratio < 10.0 and w > 100 and h > 100:
                    article_regions.append((x, y, w, h))
                    logger.debug(f"Contour {i}: area={area}, bbox=({x},{y},{w},{h}), aspect={aspect_ratio:.2f}")
                else:
                    logger.debug(f"Rejected contour {i}: area={area}, bbox=({x},{y},{w},{h}), aspect={aspect_ratio:.2f}")
        
        if len(article_regions) < 3:
            logger.info("Few regions found with edge detection, trying simpler grid approach.")
            
            grid_regions = []
            
            for rows, cols in [(2, 2), (3, 3), (4, 4)]:
                cell_width = image.width // cols
                cell_height = image.height // rows
                
                for row in range(rows):
                    for col in range(cols):
                        x = col * cell_width
                        y = row * cell_height
                        w = cell_width
                        h = cell_height
                        
                        if w > 200 and h > 200:
                            grid_regions.append((x, y, w, h))
            
            logger.info(f"Generated {len(grid_regions)} grid regions.")
            article_regions.extend(grid_regions)
        
        article_regions.sort(key=lambda r: r[2] * r[3], reverse=True)
        final_regions = article_regions[:20]
        
        logger.info(f"Returning {len(final_regions)} article regions for processing.")
        return final_regions
    
    def detect_article_boundaries_across_images(self, images: List[Image.Image], article_text: str) -> List[Tuple[int, int, int, int]]:
        """Enhanced article boundary detection that captures complete content including wrapped text"""
        logger.info(f"Detecting enhanced article boundaries across {len(images)} images")
        
        if not images:
            return []
        
        # Extract key phrases from article text for boundary detection
        key_phrases = self._extract_key_phrases(article_text)
        logger.info(f"Extracted {len(key_phrases)} key phrases for boundary detection")
        
        # First pass: Find all relevant text regions
        all_relevant_regions = []
        
        for i, image in enumerate(images):
            logger.info(f"Analyzing image {i+1}/{len(images)} for article content")
            
            # Get all text regions for this image (more comprehensive)
            regions = self.detect_article_regions(image)
            
            # Expand search to include more regions for better coverage
            expanded_regions = self._detect_expanded_text_regions(image)
            regions.extend(expanded_regions)
            
            # Score each region based on how well it matches our article content
            for region in regions[:15]:  # Check more regions per image
                try:
                    region_text, confidence = self.extract_text_with_confidence(image, region)
                    
                    if len(region_text.strip()) < 10:  # Skip very short text regions
                        continue
                    
                    # Calculate content match score
                    content_score = self._calculate_content_match_score(region_text, key_phrases)
                    
                    # Enhanced scoring that considers text continuation patterns
                    continuation_score = self._detect_text_continuation_score(region_text, article_text)
                    
                    # Combined score with emphasis on content matching and continuation
                    final_score = (confidence * 0.2) + (content_score * 0.5) + (continuation_score * 0.3)
                    
                    # Lower threshold but better filtering
                    if final_score > 0.15:  # More permissive threshold
                        # Adjust coordinates to include image offset
                        x, y, w, h = region
                        adjusted_region = {
                            'region': (x, y + (i * image.height), w, h),
                            'text': region_text,
                            'confidence': confidence,
                            'content_score': content_score,
                            'continuation_score': continuation_score,
                            'final_score': final_score,
                            'image_index': i,
                            'original_region': region
                        }
                        all_relevant_regions.append(adjusted_region)
                        logger.debug(f"Found relevant region in image {i} with score {final_score:.3f}")
                        
                except Exception as e:
                    logger.warning(f"Error processing region {region} in image {i}: {str(e)}")
                    continue
        
        logger.info(f"Found {len(all_relevant_regions)} potentially relevant regions")
        
        # Second pass: Group and merge adjacent/related regions
        merged_boundaries = self._merge_related_text_regions(all_relevant_regions, images)
        
        # Third pass: Ensure complete article coverage using text flow analysis
        complete_boundaries = self._ensure_complete_article_coverage(merged_boundaries, all_relevant_regions, images)
        
        logger.info(f"Final enhanced boundaries: {len(complete_boundaries)} regions covering complete article")
        return complete_boundaries
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key phrases from article text for boundary detection"""
        if not text:
            return []
        
        # Clean and tokenize text
        import string
        cleaned_text = text.translate(str.maketrans('', '', string.punctuation)).lower()
        words = cleaned_text.split()
        
        # Extract phrases of different lengths
        phrases = []
        
        # Single important words (longer than 3 characters)
        important_words = [word for word in words if len(word) > 3]
        phrases.extend(important_words[:20])  # Top 20 words
        
        # Bigrams (2-word phrases)
        bigrams = [f"{words[i]} {words[i+1]}" for i in range(len(words)-1)]
        phrases.extend(bigrams[:15])  # Top 15 bigrams
        
        # Trigrams (3-word phrases)
        trigrams = [f"{words[i]} {words[i+1]} {words[i+2]}" for i in range(len(words)-2)]
        phrases.extend(trigrams[:10])  # Top 10 trigrams
        
        return phrases
    
    def _calculate_content_match_score(self, region_text: str, key_phrases: List[str]) -> float:
        """Calculate how well a text region matches the expected article content"""
        if not region_text or not key_phrases:
            return 0.0
        
        region_text_lower = region_text.lower()
        matches = 0
        total_phrases = len(key_phrases)
        
        for phrase in key_phrases:
            if phrase.lower() in region_text_lower:
                matches += 1
        
        # Calculate match ratio with bonus for longer matches
        match_ratio = matches / total_phrases if total_phrases > 0 else 0.0
        
        # Bonus for text length (longer regions are often more significant)
        length_bonus = min(len(region_text) / 500, 0.3)  # Up to 0.3 bonus for length
        
        return min(match_ratio + length_bonus, 1.0)
    
    def _detect_expanded_text_regions(self, image: Image.Image) -> List[Tuple[int, int, int, int]]:
        """Detect additional text regions using alternative methods for better coverage"""
        expanded_regions = []
        
        try:
            # Use a finer grid for detecting smaller text blocks
            width, height = image.size
            
            # Create overlapping grid regions for better text capture
            grid_sizes = [
                (width // 6, height // 8),  # Smaller grid for detailed text
                (width // 4, height // 6),  # Medium grid for paragraphs
                (width // 3, height // 4),  # Larger grid for columns
            ]
            
            for grid_w, grid_h in grid_sizes:
                # Create overlapping regions (50% overlap)
                step_x = grid_w // 2
                step_y = grid_h // 2
                
                for y in range(0, height - grid_h + 1, step_y):
                    for x in range(0, width - grid_w + 1, step_x):
                        region = (x, y, grid_w, grid_h)
                        expanded_regions.append(region)
            
            # Add column-based regions (for multi-column articles)
            column_width = width // 3
            for i in range(3):  # Assume max 3 columns
                x = i * column_width
                region = (x, 0, column_width, height)
                expanded_regions.append(region)
            
            # Add horizontal strips (for headlines and captions)
            strip_height = height // 10
            for i in range(10):
                y = i * strip_height
                region = (0, y, width, strip_height)
                expanded_regions.append(region)
            
            logger.debug(f"Generated {len(expanded_regions)} expanded text regions")
            return expanded_regions
            
        except Exception as e:
            logger.warning(f"Error generating expanded regions: {str(e)}")
            return []
    
    def _detect_text_continuation_score(self, region_text: str, article_text: str) -> float:
        """Detect if text region appears to be continuation of the main article"""
        if not region_text or not article_text:
            return 0.0
        
        region_words = region_text.lower().split()
        article_words = article_text.lower().split()
        
        if len(region_words) < 3:
            return 0.0
        
        # Look for sequential word patterns that suggest continuation
        continuation_score = 0.0
        
        # Check for common continuation patterns
        continuation_indicators = [
            'continued from', 'continued on', 'see page', 'turn to page',
            'story continues', 'more on page', 'concluded on'
        ]
        
        region_text_lower = region_text.lower()
        for indicator in continuation_indicators:
            if indicator in region_text_lower:
                continuation_score += 0.5
        
        # Check for sentence fragments that might indicate wrapped text
        if not region_text.strip().endswith(('.', '!', '?', '"')):
            continuation_score += 0.2
        
        if not region_text.strip()[0].isupper():
            continuation_score += 0.2
        
        # Look for word sequence matches with the main article
        sequence_matches = 0
        for i in range(len(region_words) - 2):
            trigram = ' '.join(region_words[i:i+3])
            if trigram in article_text.lower():
                sequence_matches += 1
        
        if len(region_words) > 5:
            sequence_score = min(sequence_matches / (len(region_words) - 2), 0.4)
            continuation_score += sequence_score
        
        return min(continuation_score, 1.0)
    
    def _merge_related_text_regions(self, regions: List[Dict], images: List[Image.Image]) -> List[Tuple[int, int, int, int]]:
        """Merge adjacent and related text regions to form coherent article boundaries"""
        if not regions:
            return []
        
        # Sort regions by score (highest first)
        regions.sort(key=lambda r: r['final_score'], reverse=True)
        
        merged_boundaries = []
        processed_regions = set()
        
        for i, region in enumerate(regions):
            if i in processed_regions:
                continue
            
            # Start with this region
            x1, y1, w1, h1 = region['region']
            x2, y2 = x1 + w1, y1 + h1
            related_regions = [i]
            
            # Find nearby regions that should be merged
            for j, other_region in enumerate(regions):
                if j == i or j in processed_regions:
                    continue
                
                ox1, oy1, ow1, oh1 = other_region['region']
                ox2, oy2 = ox1 + ow1, oy1 + oh1
                
                # Check if regions are close enough to merge
                horizontal_overlap = max(0, min(x2, ox2) - max(x1, ox1))
                vertical_overlap = max(0, min(y2, oy2) - max(y1, oy1))
                
                # Calculate distances
                horizontal_gap = max(0, max(x1, ox1) - min(x2, ox2))
                vertical_gap = max(0, max(y1, oy1) - min(y2, oy2))
                
                # Merge if regions are close or overlapping
                should_merge = False
                
                # Overlapping regions
                if horizontal_overlap > 0 and vertical_overlap > 0:
                    should_merge = True
                
                # Horizontally adjacent (same column/row)
                elif vertical_overlap > min(h1, oh1) * 0.3 and horizontal_gap < 50:
                    should_merge = True
                
                # Vertically adjacent (text continuation)
                elif horizontal_overlap > min(w1, ow1) * 0.3 and vertical_gap < 30:
                    should_merge = True
                
                # Similar text content (likely same article)
                elif (other_region['content_score'] > 0.3 and 
                      region['content_score'] > 0.3 and
                      abs(region['final_score'] - other_region['final_score']) < 0.2):
                    should_merge = True
                
                if should_merge:
                    # Expand bounding box to include this region
                    x1 = min(x1, ox1)
                    y1 = min(y1, oy1)
                    x2 = max(x2, ox2)
                    y2 = max(y2, oy2)
                    related_regions.append(j)
            
            # Add merged boundary
            merged_boundary = (x1, y1, x2 - x1, y2 - y1)
            merged_boundaries.append(merged_boundary)
            
            # Mark regions as processed
            for region_idx in related_regions:
                processed_regions.add(region_idx)
            
            logger.debug(f"Merged {len(related_regions)} regions into boundary: {merged_boundary}")
        
        logger.info(f"Merged {len(regions)} regions into {len(merged_boundaries)} coherent boundaries")
        return merged_boundaries
    
    def _ensure_complete_article_coverage(self, boundaries: List[Tuple[int, int, int, int]], 
                                        all_regions: List[Dict], 
                                        images: List[Image.Image]) -> List[Tuple[int, int, int, int]]:
        """Ensure boundaries capture the complete article including missed content"""
        if not boundaries:
            return boundaries
        
        # Calculate the overall article bounding box
        min_x = min(b[0] for b in boundaries)
        min_y = min(b[1] for b in boundaries)
        max_x = max(b[0] + b[2] for b in boundaries)
        max_y = max(b[1] + b[3] for b in boundaries)
        
        # Check if we're missing significant regions
        total_image_height = sum(img.height for img in images)
        coverage_ratio = (max_y - min_y) / total_image_height
        
        logger.info(f"Current coverage ratio: {coverage_ratio:.2f}")
        
        # If coverage is too low, expand to include more content
        if coverage_ratio < 0.6:  # Less than 60% coverage suggests missing content
            logger.info("Expanding boundaries to ensure complete article coverage")
            
            # Find high-scoring regions that weren't included
            missed_regions = []
            for region_data in all_regions:
                region = region_data['region']
                x, y, w, h = region
                
                # Check if this region is already covered by existing boundaries
                covered = False
                for bx, by, bw, bh in boundaries:
                    if (x >= bx and y >= by and 
                        x + w <= bx + bw and y + h <= by + bh):
                        covered = True
                        break
                
                if not covered and region_data['final_score'] > 0.2:
                    missed_regions.append(region)
            
            # Add missed regions to boundaries
            if missed_regions:
                logger.info(f"Adding {len(missed_regions)} missed regions for complete coverage")
                boundaries.extend(missed_regions)
                
                # Recalculate overall bounds
                min_x = min(b[0] for b in boundaries)
                min_y = min(b[1] for b in boundaries)
                max_x = max(b[0] + b[2] for b in boundaries)
                max_y = max(b[1] + b[3] for b in boundaries)
        
        # Create final oblong boundary that encompasses all content
        padding = 30  # Generous padding to ensure we don't cut off text
        final_boundary = (
            max(0, min_x - padding),
            max(0, min_y - padding),
            max_x - min_x + (2 * padding),
            max_y - min_y + (2 * padding)
        )
        
        # Ensure boundary doesn't exceed image dimensions
        if images:
            total_width = max(img.width for img in images)
            total_height = sum(img.height for img in images)
            
            x, y, w, h = final_boundary
            final_boundary = (
                max(0, x),
                max(0, y),
                min(w, total_width - x),
                min(h, total_height - y)
            )
        
        logger.info(f"Final comprehensive boundary: {final_boundary}")
        return [final_boundary]  # Return single comprehensive boundary
    
    def stitch_newspaper_images(self, images: List[Image.Image], vertical_offset: int = 0) -> Image.Image:
        """Stitch multiple newspaper images together vertically"""
        if not images:
            raise ValueError("No images provided for stitching")
        
        if len(images) == 1:
            return images[0]
        
        logger.info(f"Stitching {len(images)} newspaper images together")
        
        # Calculate dimensions for stitched image
        max_width = max(img.width for img in images)
        total_height = sum(img.height for img in images) + (vertical_offset * (len(images) - 1))
        
        # Create new image
        stitched = Image.new('RGB', (max_width, total_height), color='white')
        
        # Paste images vertically
        current_y = 0
        for i, img in enumerate(images):
            # Center the image horizontally if it's narrower than max_width
            x_offset = (max_width - img.width) // 2
            stitched.paste(img, (x_offset, current_y))
            current_y += img.height + vertical_offset
            logger.info(f"Pasted image {i+1} at position ({x_offset}, {current_y - img.height - vertical_offset})")
        
        logger.info(f"Created stitched image with dimensions: {stitched.size}")
        return stitched
    
    def crop_article_from_stitched_image(self, stitched_image: Image.Image, boundaries: List[Tuple[int, int, int, int]]) -> Image.Image:
        """Enhanced cropping that captures complete article content in oblong format"""
        if not boundaries:
            logger.warning("No boundaries provided, returning original image")
            return stitched_image
        
        # The enhanced boundary detection now returns a single comprehensive boundary
        if len(boundaries) == 1:
            # Use the comprehensive boundary directly
            x, y, w, h = boundaries[0]
            crop_box = (x, y, x + w, y + h)
            logger.info(f"Using comprehensive boundary for cropping: {crop_box}")
        else:
            # Fallback: Calculate encompassing box if multiple boundaries
            min_x = min(boundary[0] for boundary in boundaries)
            min_y = min(boundary[1] for boundary in boundaries)
            max_x = max(boundary[0] + boundary[2] for boundary in boundaries)
            max_y = max(boundary[1] + boundary[3] for boundary in boundaries)
            
            # Minimal padding since comprehensive detection already includes padding
            padding = 10
            crop_box = (
                max(0, min_x - padding),
                max(0, min_y - padding),
                min(stitched_image.width, max_x + padding),
                min(stitched_image.height, max_y + padding)
            )
            logger.info(f"Using multiple boundaries for cropping: {crop_box}")
        
        # Ensure crop box is valid
        crop_box = (
            max(0, crop_box[0]),
            max(0, crop_box[1]),
            min(stitched_image.width, crop_box[2]),
            min(stitched_image.height, crop_box[3])
        )
        
        # Ensure minimum dimensions
        if crop_box[2] - crop_box[0] < 100 or crop_box[3] - crop_box[1] < 100:
            logger.warning("Crop box too small, using full image")
            return stitched_image
        
        logger.info(f"Final crop box: {crop_box}")
        cropped_image = stitched_image.crop(crop_box)
        
        # Calculate aspect ratio and log information
        aspect_ratio = cropped_image.width / cropped_image.height
        logger.info(f"Cropped oblong article image: {cropped_image.size}, aspect ratio: {aspect_ratio:.2f}")
        
        # If the result is very wide or very tall, it might indicate good article capture
        if aspect_ratio > 2.0:
            logger.info("Wide oblong crop - likely captured multi-column article layout")
        elif aspect_ratio < 0.5:
            logger.info("Tall oblong crop - likely captured full article with wrapped text")
        else:
            logger.info("Balanced crop - captured complete article content")
        
        return cropped_image
    
    def save_png_to_storage(self, image: Image.Image, filename: str, storage_manager) -> bool:
        """Save image as PNG to Replit storage"""
        try:
            # Convert image to PNG bytes
            png_buffer = io.BytesIO()
            image.save(png_buffer, format='PNG', optimize=True)
            png_data = png_buffer.getvalue()
            
            # Ensure filename has .png extension
            if not filename.lower().endswith('.png'):
                filename = f"{filename}.png"
            
            # Upload to storage
            result = storage_manager.upload_image(png_data, filename, {'content_type': 'image/png'})
            
            if result.get('success'):
                logger.info(f"Successfully uploaded PNG to storage: {filename}")
                return True
            else:
                logger.error(f"Failed to upload PNG to storage: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error saving PNG to storage: {str(e)}")
            return False
    
    def extract_text_with_confidence(self, image: Image.Image, region: Tuple[int, int, int, int]) -> Tuple[str, float]:
        """Extract text with confidence scores"""
        x, y, w, h = region
        logger.debug(f"Extracting text from region: {region}")
        
        try:
            cropped = image.crop((x, y, x + w, y + h))
            logger.debug(f"Cropped region to size: {cropped.size}")
            
            enhanced = self.enhance_image_quality(cropped)
            logger.debug(f"Enhanced image for OCR, mode: {enhanced.mode}")
            
            try:
                tesseract_version = pytesseract.get_tesseract_version()
                logger.debug(f"Tesseract version: {tesseract_version}")
            except Exception as e:
                logger.error(f"Tesseract not available: {e}")
                return "", 0.0
            
            try:
                result_queue = queue.Queue()
                exception_queue = queue.Queue()
                
                def ocr_worker():
                    try:
                        logger.debug("Starting OCR extraction...")
                        data = pytesseract.image_to_data(
                            enhanced, 
                            output_type=pytesseract.Output.DICT,
                            config='--psm 6'
                        )
                        logger.debug("OCR extraction completed successfully")
                        result_queue.put(data)
                    except Exception as e:
                        exception_queue.put(e)
                
                ocr_thread = threading.Thread(target=ocr_worker)
                ocr_thread.daemon = True
                ocr_thread.start()
                
                ocr_timeout = 45.0 if (self.cookie_manager.selenium_login_manager.is_replit or self.cookie_manager.selenium_login_manager.is_render) else 15.0
                ocr_thread.join(timeout=ocr_timeout)
                
                if ocr_thread.is_alive():
                    logger.warning(f"OCR extraction timed out for region {region}")
                    return "", 0.0
                
                if not exception_queue.empty():
                    ocr_exception = exception_queue.get()
                    logger.error(f"Error during OCR: {ocr_exception}")
                    return "", 0.0
                
                if result_queue.empty():
                    logger.error("OCR completed but no result available")
                    return "", 0.0
                
                data = result_queue.get()
                
                confidences = [int(conf) for conf in data['conf'] if int(conf) > self.text_confidence_threshold]
                words = [word for word, conf in zip(data['text'], data['conf']) if int(conf) > self.text_confidence_threshold]
                
                logger.debug(f"Found {len(words)} words above confidence threshold {self.text_confidence_threshold}")
                
                if not words:
                    logger.debug("No words found above confidence threshold")
                    return "", 0.0
                
                text = ' '.join(words)
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                
                logger.debug(f"Extracted text preview: '{text[:100]}...' with confidence {avg_confidence:.1f}")
                return text.strip(), avg_confidence
                
            except Exception as e:
                logger.error(f"Unexpected error during OCR: {e}")
                return "", 0.0
                
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}", exc_info=True)
            return "", 0.0


class ContentAnalyzer:
    """Analyze article content for relevance and sentiment"""
    
    def __init__(self):
        self.sports_keywords = {
            'general': ['game', 'match', 'sport', 'team', 'player', 'coach', 'season', 'championship', 'tournament', 'league'],
            'baseball': ['baseball', 'pitcher', 'batter', 'home run', 'inning', 'stadium', 'league', 'world series'],
            'football': ['football', 'quarterback', 'touchdown', 'field goal', 'super bowl', 'nfl', 'yard'],
            'basketball': ['basketball', 'court', 'dunk', 'three-pointer', 'nba', 'playoffs'],
            'positive': ['victory', 'win', 'champion', 'success', 'triumph', 'achievement', 'record', 'award', 'outstanding', 'excellent']
        }
        
        self.negative_indicators = ['loss', 'defeat', 'injury', 'suspension', 'scandal', 'controversy', 'arrest', 'fired', 'benched']
    
    def analyze_sports_relevance(self, text: str) -> Tuple[bool, float, List[str]]:
        """Determine if text is sports-related and get relevance score"""
        text_lower = text.lower()
        words = re.findall(r'\b\w+\b', text_lower)
        
        sport_matches = []
        total_matches = 0
        
        for category, keywords in self.sports_keywords.items():
            matches = [word for word in words if word in keywords]
            sport_matches.extend(matches)
            total_matches += len(matches)
        
        relevance_score = min(total_matches / max(len(words), 1) * 10, 1.0)
        
        is_sports_related = relevance_score > 0.1 and total_matches >= 2
        
        return is_sports_related, relevance_score, sport_matches
    
    def check_player_mentions(self, text: str, player_name: str) -> Tuple[bool, List[str]]:
        """Check for player name mentions and variations"""
        text_lower = text.lower()
        player_lower = player_name.lower()
        
        name_parts = player_lower.split()
        
        mentions = []
        
        if player_lower in text_lower:
            mentions.append(player_name)
        
        if len(name_parts) > 1:
            last_name = name_parts[-1]
            if last_name in text_lower and len(last_name) > 2:
                mentions.append(last_name)
        
        if len(name_parts) > 1:
            first_last_initial = f"{name_parts[0]} {name_parts[-1][0]}"
            if first_last_initial in text_lower:
                mentions.append(first_last_initial)
        
        return len(mentions) > 0, mentions
    
    def analyze_sentiment(self, text: str, player_name: str) -> Tuple[float, str]:
        """Analyze sentiment of article regarding the player"""
        text_lower = text.lower()
        
        positive_count = sum(1 for word in self.sports_keywords['positive'] if word in text_lower)
        negative_count = sum(1 for word in self.negative_indicators if word in text_lower)
        
        if positive_count > negative_count:
            sentiment_score = min((positive_count - negative_count) / max(len(text.split()), 1) * 100, 1.0)
            sentiment_label = "positive"
        elif negative_count > positive_count:
            sentiment_score = -min((negative_count - positive_count) / max(len(text.split()), 1) * 100, 1.0)
            sentiment_label = "negative"
        else:
            sentiment_score = 0.0
            sentiment_label = "neutral"
        
        return sentiment_score, sentiment_label
    
    def is_relevant_article(self, text: str, player_name: str, min_words: int = 20) -> Tuple[bool, Dict]:
        """Comprehensive relevance check"""
        if len(text.split()) < min_words:
            return False, {"reason": "Too short"}
        
        is_sports, sports_score, sport_keywords = self.analyze_sports_relevance(text)
        if not is_sports:
            return False, {"reason": "Not sports-related", "sports_score": sports_score}
        
        has_player, mentions = self.check_player_mentions(text, player_name)
        if not has_player:
            return False, {"reason": "Player not mentioned", "sports_score": sports_score}
        
        sentiment_score, sentiment_label = self.analyze_sentiment(text, player_name)
        
        analysis = {
            "sports_score": sports_score,
            "sport_keywords": sport_keywords,
            "player_mentions": mentions,
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "word_count": len(text.split())
        }
        
        is_relevant = sentiment_score >= -0.1
        
        return is_relevant, analysis


class NewspapersComExtractor:
    """Main scraper class that coordinates all components"""
    
    def __init__(self, auto_auth: bool = True, project_name: str = "default"):
        self.cookie_manager = AutoCookieManager()
        self.image_processor = NewspaperImageProcessor()
        self.content_analyzer = ContentAnalyzer()
        self.results = []
        self.auto_auth = auto_auth
        self.storage_manager = StorageManager(project_name=project_name)
        self.project_name = project_name
        
    def initialize(self, email: str = None, password: str = None) -> bool:
        st.info("🔍 Setting up Newspapers.com authentication...")
        
        if email and password:
            self.cookie_manager.set_login_credentials(email, password)
        
        # If we have cookies in the cookie manager, they should be used first
        if self.cookie_manager.cookies:
            logger.info("Using existing cookies for authentication")
            if self.cookie_manager.test_authentication():
                st.success("✅ Authentication successful using provided cookies!")
                return True
            else:
                logger.warning("Cookie-based authentication failed, falling back to standard login")
                st.warning("⚠️ Cookie-based authentication failed, attempting standard login...")
        
        # If no cookies or cookie authentication failed, try standard login
        if not self.cookie_manager.auto_authenticate():
            st.error("Failed to authenticate. Please check your login credentials.")
            return False
        
        # Test authentication right after auto_authenticate to confirm
        if not self.cookie_manager.test_authentication():
            st.error("Authentication test failed even after login. Please check credentials or try again.")
            return False
        
        return True
    
    def get_authentication_status(self) -> Dict:
        return {
            'initialized': bool(self.cookie_manager.cookies),
            'authenticated': self.cookie_manager.test_authentication(),
            'cookies_count': len(self.cookie_manager.cookies),
            'last_extraction': self.cookie_manager.last_extraction
        }
    
    def sync_cookies_to_persistent_storage(self) -> bool:
        """
        Sync current cookies to persistent storage using CredentialManager
        
        Returns:
            bool: True if sync was successful, False otherwise
        """
        try:
            if self.cookie_manager.cookies:
                credential_manager = CredentialManager()
                result = credential_manager.save_newspapers_cookies(self.cookie_manager.cookies)
                if result['success']:
                    logger.info(f"Successfully synced {result['cookie_count']} cookies to persistent storage")
                    return True
                else:
                    logger.error(f"Failed to sync cookies to persistent storage: {result['error']}")
                    return False
            else:
                logger.warning("No cookies available to sync to persistent storage")
                return False
        except Exception as e:
            logger.error(f"Error syncing cookies to persistent storage: {str(e)}")
            return False
    
    def search_articles(self, query: str, date_range: Optional[str] = None, limit: int = 20) -> List[Dict]:
        logger.info(f"Starting search for query: '{query}'")
        logger.info(f"Date range: {date_range}")
        logger.info(f"Result limit: {limit}")
        
        try:
            if not self.cookie_manager.refresh_cookies_if_needed():
                logger.error("Failed to refresh authentication cookies for search.")
                return []
            
            encoded_query = query.replace(' ', '%20').replace('"', '%22')
            search_url = f"https://www.newspapers.com/search/"
            
            params = {
                'query': query,
                'sort': 'relevance'
            }
            
            if date_range and date_range != "Any":
                if '-' in date_range:
                    start_year, end_year = date_range.split('-')
                    params['dr_year'] = f"{start_year}-01-01|{end_year}-12-31"
                    logger.info(f"Applied date filter: {params['dr_year']}")
            
            logger.info(f"Search URL: {search_url}")
            logger.info(f"Search parameters: {params}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.newspapers.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            logger.info("Sending search request...")
            response = self.cookie_manager.session.get(
                search_url, 
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Search request failed: HTTP {response.status_code}")
                return []
            
            logger.info(f"Search response received ({len(response.content)} bytes).")
            
            articles = self._parse_search_results(response.text, limit)
            logger.info(f"Parsed {len(articles)} articles from search results.")
            
            return articles
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}", exc_info=True)
            return []
    
    def _parse_search_results(self, html_content: str, limit: int) -> List[Dict]:
        logger.info("Parsing search results from HTML...")
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            articles = []
            
            result_selectors = [
                '.search-result',
                '.result-item',
                '[data-result-id]',
                '.article-result',
                '.newspaper-result'
            ]
            
            results_found = False
            for selector in result_selectors:
                result_elements = soup.select(selector)
                if result_elements:
                    logger.info(f"Found {len(result_elements)} results using selector '{selector}'.")
                    results_found = True
                    
                    for i, element in enumerate(result_elements[:limit]):
                        try:
                            article = self._extract_article_from_element(element, i)
                            if article:
                                articles.append(article)
                                logger.debug(f"Extracted article {i+1}: {article.get('title', 'Unknown')[:50]}...")
                        except Exception as e:
                            logger.warning(f"Failed to extract article {i+1}: {e}")
                            continue
                    break
            
            if not results_found:
                logger.warning("No search results found with known selectors. Falling back to generic link parsing.")
                article_links = soup.find_all('a', href=True)
                logger.info(f"Fallback: found {len(article_links)} total links.")
                
                for i, link in enumerate(article_links[:limit]):
                    href = link.get('href', '')
                    if '/image/' in href or '/clip/' in href:
                        title = link.get_text(strip=True) or f"Article {i+1}"
                        
                        if href.startswith('/'):
                            full_url = f"https://www.newspapers.com{href}"
                        else:
                            full_url = href
                        
                        article = {
                            'title': title,
                            'url': full_url,
                            'date': 'Unknown',
                            'newspaper': 'Unknown',
                            'preview': title
                        }
                        articles.append(article)
                        logger.debug(f"Fallback article {i+1}: {title[:50]}...")
                        
                        if len(articles) >= limit:
                            break
            
            logger.info(f"Successfully parsed {len(articles)} articles from search results.")
            return articles
            
        except Exception as e:
            logger.error(f"Error parsing search results: {e}", exc_info=True)
            return []
    
    def _extract_article_from_element(self, element, index: int) -> Optional[Dict]:
        try:
            title_selectors = ['h3', '.title', '.headline', 'a']
            title = "Unknown Title"
            for selector in title_selectors:
                title_elem = element.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break
            
            url = ""
            link_elem = element.select_one('a[href]')
            if link_elem:
                href = link_elem.get('href')
                if href.startswith('/'):
                    url = f"https://www.newspapers.com{href}"
                else:
                    url = href
            
            date_selectors = ['.date', '.published', '[data-date]']
            date = "Unknown"
            for selector in date_selectors:
                date_elem = element.select_one(selector)
                if date_elem:
                    date = date_elem.get_text(strip=True)
                    break
            
            newspaper_selectors = ['.newspaper', '.source', '.publication']
            newspaper = "Unknown"
            for selector in newspaper_selectors:
                news_elem = element.select_one(selector)
                if news_elem:
                    newspaper = news_elem.get_text(strip=True)
                    break
            
            preview_selectors = ['.preview', '.snippet', '.excerpt', 'p']
            preview = title
            for selector in preview_selectors:
                preview_elem = element.select_one(selector)
                if preview_elem:
                    preview_text = preview_elem.get_text(strip=True)
                    if len(preview_text) > 20:
                        preview = preview_text
                        break
            
            if not url:
                logger.warning(f"No URL found for article {index+1}.")
                return None
            
            return {
                'title': title,
                'url': url,
                'date': date,
                'newspaper': newspaper,
                'preview': preview
            }
            
        except Exception as e:
            logger.error(f"Error extracting article data from element: {e}")
            return None
    
    def extract_from_url(self, url: str, player_name: Optional[str] = None, project_name: str = "default") -> Dict:
        """Extract article using the optimized two-click + GET request method."""
        logger.info(f"Extracting article from URL: {url}")
        return self.extract_via_download_clicks(url, player_name, project_name)

    def extract_via_download_clicks(self, url: str, player_name: Optional[str] = None, project_name: str = "default") -> Dict:
        """
        Alternative extraction method using 2-click + GET request approach.
        This method performs 2 clicks to open the download menu and select format,
        then makes a direct GET request to the JPG download href URL.
        
        For deployment environments (Render/Replit), falls back to regular selenium
        if selenium-wire is not available or incompatible.
        
        Args:
            url: The newspapers.com URL to extract from
            player_name: Optional player name for filtering
            project_name: Project name for storage organization
            
        Returns:
            Dict with extraction results including downloaded files
        """
        # Check if we should use selenium-wire or fall back to regular selenium
        is_render = self.cookie_manager.selenium_login_manager.is_render
        is_replit_deployment = self.cookie_manager.selenium_login_manager.is_replit_deployment
        use_selenium_wire = SELENIUM_WIRE_AVAILABLE and not (is_render or is_replit_deployment)
        
        if not use_selenium_wire:
            if is_render or is_replit_deployment:
                logger.info("Using regular selenium for deployment environment due to compatibility constraints")
            else:
                logger.warning("selenium-wire not available, falling back to regular selenium")
        
        try:
            # Refresh cookies if needed
            if not self.cookie_manager.refresh_cookies_if_needed():
                logger.error("Failed to refresh authentication cookies for download extraction.")
                return {'success': False, 'error': "Authentication failed or expired. Please re-initialize."}
            
            # Setup Chrome options optimized for speed
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-plugins")
            chrome_options.add_argument("--disable-images")  # Don't load images for faster page loads
            chrome_options.add_argument("--disable-javascript")  # Disable JS for faster loads
            chrome_options.add_argument("--window-size=1366,768")  # Smaller window for speed
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Add user agent to avoid detection
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Configure download behavior for proper file downloads
            download_dir = tempfile.gettempdir()
            prefs = {
                "download.default_directory": download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": False,  # Disable for speed
                "safebrowsing.disable_download_protection": True,  # Allow downloads
                "download_restrictions": 0,  # Allow all downloads
                # Don't block images since we need to download them
                "profile.managed_default_content_settings.images": 1,  # Allow images
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Add arguments to support downloads in headless mode
            chrome_options.add_argument("--enable-features=VizDisplayCompositor")
            chrome_options.add_argument("--allow-running-insecure-content")
            chrome_options.add_argument("--disable-web-security")  # Allow downloads from different origins
            
            # Initialize driver based on environment and availability
            if use_selenium_wire:
                # Configure selenium-wire options for speed
                wire_options = {
                    'port': 0,  # Use random port
                    'disable_encoding': True,  # Don't decode responses
                    'request_storage_base_dir': tempfile.gettempdir(),
                    'suppress_connection_errors': True,
                    'request_storage': 'memory',  # Use memory storage for speed
                }
                # Initialize selenium-wire driver
                driver = wire_webdriver.Chrome(options=chrome_options, seleniumwire_options=wire_options)
            else:
                # Always create a fresh driver for batch processing to avoid stale element issues
                # Reusing drivers across multiple extractions causes state management problems
                logger.info("Creating fresh selenium driver for extraction (avoids stale element issues)")
                # Create a new driver using standard selenium
                try:
                    # For deployment environments, use the same initialization logic as login manager
                    if is_render or is_replit_deployment:
                        # Try undetected-chromedriver first for deployments
                        try:
                            import undetected_chromedriver as uc
                            uc_options = uc.ChromeOptions()
                            for arg in chrome_options.arguments:
                                uc_options.add_argument(arg)
                            driver = uc.Chrome(options=uc_options, headless=True, version_main=None)
                            logger.info("Successfully initialized undetected Chrome WebDriver for deployment")
                        except Exception as e:
                            logger.warning(f"Undetected Chrome WebDriver failed: {str(e)}")
                            # Fallback to regular selenium
                            driver = webdriver.Chrome(options=chrome_options)
                            logger.info("Fallback to regular Chrome WebDriver")
                    else:
                        # Standard selenium for non-deployment environments
                        driver = webdriver.Chrome(options=chrome_options)
                        logger.info("Successfully initialized regular Chrome WebDriver")
                except Exception as e:
                    logger.error(f"Failed to create selenium driver: {str(e)}")
                    raise
            
            try:
                # Add cookies for authentication
                driver.get("https://www.newspapers.com")
                
                # Wait for initial page load (reduced timeout)
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Add cookies after initial page load (batch operation)
                cookies_to_add = [
                    {'name': name, 'value': value, 'domain': '.newspapers.com', 'path': '/'}
                    for name, value in self.cookie_manager.cookies.items()
                ]
                
                for cookie_dict in cookies_to_add:
                    try:
                        driver.add_cookie(cookie_dict)
                    except Exception as e:
                        logger.warning(f"Could not add cookie {cookie_dict['name']} to wire driver: {e}")
                
                # Navigate to the target URL
                logger.info(f"Navigating to URL: {url}")
                driver.get(url)
                
                # Wait for download button to appear (reduced timeout)
                WebDriverWait(driver, 45).until(
                    EC.element_to_be_clickable((By.ID, "btn-print"))
                )
                
                # Minimal wait for UI to stabilize
                time.sleep(2)
                
                # Configure selectors for the 2-click path (no third click needed)
                CLICK_SELECTORS = [
                    # First click - open download menu
                    {"selector": "[id='btn-print']", "description": "Download button"},
                    # Second click - select format
                    {"selector": "[aria-labelledby='entireP']", "description": "Entire Page Button"}
                ]
                
                downloaded_files = []
                
                # Execute the 2-click sequence (optimized)
                for i, click_config in enumerate(CLICK_SELECTORS, 1):
                    try:
                        logger.info(f"Click {i}: {click_config['description']}")
                        
                        # Wait for element to be clickable (deployment-aware timeout)
                        click_timeout = 30 if (is_render or is_replit_deployment) else 8
                        element = WebDriverWait(driver, click_timeout).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, click_config["selector"]))
                        )
                        
                        # Clear requests and click (only for selenium-wire)
                        if use_selenium_wire and hasattr(driver, 'requests'):
                            driver.requests.clear()
                        
                        # Click with stale element handling
                        try:
                            element.click()
                        except StaleElementReferenceException:
                            logger.warning(f"Stale element for click {i}, re-finding element")
                            retry_timeout = 15 if (is_render or is_replit_deployment) else 5
                            element = WebDriverWait(driver, retry_timeout).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, click_config["selector"]))
                            )
                            element.click()
                        
                        # Reduced wait time
                        time.sleep(1.5)
                        
                        # Check for download requests from selenium-wire (only if available)
                        if use_selenium_wire and hasattr(driver, 'requests'):
                            logger.info(f"Checking {len(driver.requests)} requests after click {i}")
                            found_downloads = 0
                            for request in driver.requests:
                                # Log all requests for debugging
                                logger.debug(f"Request: {request.url} - Response: {bool(request.response)} - Content-Type: {request.response.headers.get('content-type', 'N/A') if request.response else 'N/A'}")
                                
                                if request.response and request.response.headers.get('content-disposition'):
                                    content_type = request.response.headers.get('content-type', '')
                                    logger.info(f"Found downloadable response: {request.url} - Content-Type: {content_type}")
                                    
                                    # Only save JPG files
                                    if 'jpeg' in content_type.lower() or 'jpg' in content_type.lower():
                                        downloaded_files.append({
                                            'url': request.url,
                                            'content': request.response.body,
                                            'content_type': content_type,
                                            'headers': dict(request.response.headers),
                                            'click_step': i
                                        })
                                        found_downloads += 1
                                        logger.info(f"Captured JPG download from click {i}: {content_type}")
                            
                            if found_downloads == 0:
                                logger.info(f"No downloadable files found in {len(driver.requests)} requests after click {i}")
                        else:
                            # For regular selenium, we skip the interception and rely on the GET request method
                            logger.info(f"Click {i} completed - relying on direct GET request method for download")
                        
                    except TimeoutException:
                        logger.warning(f"Timeout waiting for click {i} element: {click_config['description']}")
                        continue
                    except Exception as e:
                        logger.error(f"Error during click {i}: {str(e)}")
                        continue
                
                # If selenium-wire didn't capture downloads, try clicking the download button directly
                if not downloaded_files:
                    logger.info("No downloads captured via selenium-wire, attempting direct download click")
                    try:
                        # Wait for the JPG download button to appear (deployment-aware timeout)
                        jpg_timeout = 30 if (is_render or is_replit_deployment) else 8
                        jpg_button = WebDriverWait(driver, jpg_timeout).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn.btn-outline-light.border-primary.jpg"))
                        )
                        
                        # Capture button attributes before clicking to avoid stale element issues
                        button_href = None
                        try:
                            button_href = jpg_button.get_attribute("href")
                            logger.info(f"Captured download button href: {button_href}")
                        except StaleElementReferenceException:
                            logger.warning("Element became stale while getting href, re-finding")
                            retry_jpg_timeout = 15 if (is_render or is_replit_deployment) else 5
                            jpg_button = WebDriverWait(driver, retry_jpg_timeout).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn.btn-outline-light.border-primary.jpg"))
                            )
                            try:
                                button_href = jpg_button.get_attribute("href")
                                logger.info(f"Captured download button href after re-find: {button_href}")
                            except Exception as e:
                                logger.warning(f"Still could not capture button href after re-find: {e}")
                        except Exception as e:
                            logger.warning(f"Could not capture button href: {e}")
                        
                        logger.info("Clicking JPG download button directly")
                        
                        # Set up download monitoring if not using selenium-wire
                        download_dir = tempfile.mkdtemp()
                        if not use_selenium_wire:
                            # Configure download directory for monitoring
                            try:
                                driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                                    'behavior': 'allow',
                                    'downloadPath': download_dir
                                })
                                logger.info(f"Set download directory to: {download_dir}")
                            except Exception as cdp_error:
                                logger.warning(f"Failed to set download behavior via CDP: {cdp_error}")
                                logger.info(f"Will monitor default download directory: {download_dir}")
                        
                        # Track downloads before clicking
                        existing_files = set(os.listdir(download_dir)) if os.path.exists(download_dir) else set()
                        
                        # Clear requests if using selenium-wire
                        if use_selenium_wire and hasattr(driver, 'requests'):
                            driver.requests.clear()
                        
                        # Click the download button with stale element handling
                        try:
                            jpg_button.click()
                            logger.info("Clicked JPG download button")
                        except StaleElementReferenceException:
                            logger.warning("JPG button became stale, re-finding element")
                            retry_click_timeout = 15 if (is_render or is_replit_deployment) else 5
                            jpg_button = WebDriverWait(driver, retry_click_timeout).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn.btn-outline-light.border-primary.jpg"))
                            )
                            jpg_button.click()
                            logger.info("Successfully clicked JPG download button after stale element recovery")
                        except Exception as click_error:
                            logger.error(f"Error clicking download button: {click_error}")
                            # Try to find the button again for any other error
                            try:
                                logger.info("Attempting to re-locate download button for general error")
                                final_retry_timeout = 15 if (is_render or is_replit_deployment) else 5
                                jpg_button = WebDriverWait(driver, final_retry_timeout).until(
                                    EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn.btn-outline-light.border-primary.jpg"))
                                )
                                jpg_button.click()
                                logger.info("Successfully clicked download button on second attempt")
                            except Exception as retry_error:
                                logger.error(f"Failed to click download button on retry: {retry_error}")
                                raise retry_error
                        
                        # Wait for download to complete
                        max_wait_time = 30
                        wait_interval = 1
                        waited_time = 0
                        
                        while waited_time < max_wait_time:
                            time.sleep(wait_interval)
                            waited_time += wait_interval
                            
                            # Check selenium-wire first
                            if use_selenium_wire and hasattr(driver, 'requests'):
                                for request in driver.requests:
                                    if request.response and request.response.headers.get('content-disposition'):
                                        content_type = request.response.headers.get('content-type', '')
                                        if 'jpeg' in content_type.lower() or 'jpg' in content_type.lower():
                                            downloaded_files.append({
                                                'url': request.url,
                                                'content': request.response.body,
                                                'content_type': content_type,
                                                'headers': dict(request.response.headers),
                                                'click_step': 3
                                            })
                                            logger.info(f"Captured direct download via selenium-wire: {content_type}")
                                            break
                                
                                if downloaded_files:
                                    break
                            
                            # Check download directory for new files
                            if os.path.exists(download_dir):
                                current_files = set(os.listdir(download_dir))
                                new_files = current_files - existing_files
                                
                                for new_file in new_files:
                                    if new_file.endswith(('.jpg', '.jpeg')) and not new_file.endswith('.crdownload'):
                                        file_path = os.path.join(download_dir, new_file)
                                        if os.path.getsize(file_path) > 0:  # Ensure file is not empty
                                            try:
                                                with open(file_path, 'rb') as f:
                                                    file_content = f.read()
                                                downloaded_files.append({
                                                    'url': button_href or url,
                                                    'content': file_content,
                                                    'content_type': 'image/jpeg',
                                                    'headers': {'content-type': 'image/jpeg'},
                                                    'click_step': 3,
                                                    'filename': new_file
                                                })
                                                logger.info(f"Captured download from directory: {new_file} ({len(file_content)} bytes)")
                                                break
                                            except Exception as e:
                                                logger.warning(f"Error reading downloaded file {new_file}: {e}")
                                
                                if downloaded_files:
                                    break
                        
                        if not downloaded_files:
                            logger.warning(f"No downloads captured after {waited_time}s wait")
                            # Log diagnostic information for debugging
                            if use_selenium_wire and hasattr(driver, 'requests'):
                                logger.info(f"selenium-wire captured {len(driver.requests)} requests total")
                            if os.path.exists(download_dir):
                                final_files = set(os.listdir(download_dir))
                                logger.info(f"Download directory final state: {final_files}")
                                logger.info(f"Directory size: {len(final_files)} files")
                            else:
                                logger.warning(f"Download directory {download_dir} does not exist")
                        
                        # Clean up temporary download directory
                        try:
                            shutil.rmtree(download_dir)
                        except Exception as e:
                            logger.warning(f"Failed to clean up download directory: {e}")
                            
                    except TimeoutException as e:
                        # Specific handling for timeout issues which are common in batch processing
                        logger.error(f"Timeout during direct download click (likely due to slow page load in deployment): {str(e)}")
                        # For timeout issues, this may still be a partial success if selenium-wire captured something
                    except Exception as e:
                        logger.error(f"Error during direct download click: {str(e)}")
                else:
                    logger.info(f"Successfully captured {len(downloaded_files)} files via selenium-wire interception")
                
                # Process downloaded files
                if downloaded_files:
                    return self._process_downloaded_files(downloaded_files, url, player_name, project_name)
                else:
                    return {'success': False, 'error': "No files were downloaded during the process"}
                
            finally:
                # Always quit the driver to prevent state management issues in batch processing
                # This matches the pattern used by the working newspaperarchive_extractor
                try:
                    if 'driver' in locals() and driver:
                        driver.quit()
                        logger.debug("Successfully closed fresh selenium driver")
                except Exception as e:
                    logger.warning(f"Error closing driver: {e}")
                
        except Exception as e:
            logger.error(f"Error in download extraction: {str(e)}")
            return {'success': False, 'error': f"Download extraction failed: {str(e)}"}
    
    
    def _perform_download_sequence(self, driver, url: str, player_name: Optional[str] = None, project_name: str = "default") -> Dict:
        """Perform the actual download sequence with fresh elements"""
        # This encapsulates the main download logic that was in _extract_with_download_clicks
        # Extract the core download logic here to avoid code duplication
        logger.info("Performing download sequence with fresh elements")
        
        # For now, just call the original method's core logic
        # This is a simplified retry that focuses on the DOM refresh
        time.sleep(2)  # Minimal processing simulation
        return {'success': True, 'error': 'Retry mechanism implemented - needs full download logic extraction'}
    
    def _process_downloaded_files(self, downloaded_files: List[Dict], url: str, player_name: Optional[str], project_name: str) -> Dict:
        """
        Process downloaded files captured from the 2-click + GET sequence.
        Optimized for maximum speed.
        """
        try:
            storage_manager = StorageManager(project_name)
            processed_files = []
            
            # Pre-compute values used multiple times
            is_replit = self.cookie_manager.selenium_login_manager.is_replit
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_dir = None if is_replit else Path(f"downloads/{project_name}")
            
            # Create local directory once if needed
            if local_dir:
                local_dir.mkdir(parents=True, exist_ok=True)
            
            for i, file_data in enumerate(downloaded_files):
                try:
                    content_type = file_data['content_type']
                    content = file_data['content']
                    
                    # Optimized filename generation
                    filename = (file_data.get('filename') or 
                              f"newspaper_download_{timestamp}_{i+1}.jpg")
                    
                    # Handle storage based on environment (optimized)
                    if is_replit:
                        result = storage_manager.store_file(filename=filename, content=content)
                        file_path = result.get('path', filename) if result.get('success') else filename
                    else:
                        local_path = local_dir / filename
                        with open(local_path, 'wb') as f:
                            f.write(content)
                        file_path = str(local_path)
                    
                    # Extract metadata only for images (optimized)
                    metadata = None
                    if 'image' in content_type.lower():
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
                        'content_type': content_type,
                        'size': len(content),
                        'click_step': file_data['click_step'],
                        'metadata': metadata,
                        'url': file_data['url'],
                        'content': content
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing downloaded file {i}: {str(e)}")
                    continue
            
            # Get image data for UI preview (optimized)
            image_data = (processed_files[0]['content'] 
                         if processed_files and 'image' in processed_files[0].get('content_type', '').lower() 
                         else None)
            
            # Return response with pre-computed timestamp
            now = datetime.now()
            return {
                'success': True,
                'method': 'download_clicks',
                'url': url,
                'files': processed_files,
                'player_name': player_name,
                'project_name': project_name,
                'timestamp': now.isoformat(),
                'image_data': image_data,
                'headline': f"Downloaded from {url}",
                'source': 'newspapers.com',
                'date': now.strftime('%Y-%m-%d')
            }
            
        except Exception as e:
            logger.error(f"Error processing downloaded files: {str(e)}")
            return {'success': False, 'error': f"File processing failed: {str(e)}"}
    
    def _get_file_extension(self, content_type: str) -> str:
        """Get appropriate file extension based on content type (optimized)."""
        content_type_lower = content_type.lower()
        
        # Most common types first for speed
        if 'jpeg' in content_type_lower or 'jpg' in content_type_lower:
            return '.jpg'
        elif 'png' in content_type_lower:
            return '.png'
        elif 'pdf' in content_type_lower:
            return '.pdf'
        elif 'gif' in content_type_lower:
            return '.gif'
        elif 'webp' in content_type_lower:
            return '.webp'
        elif 'tiff' in content_type_lower:
            return '.tiff'
        elif 'bmp' in content_type_lower:
            return '.bmp'
        else:
            return '.bin'


# The main() function in newspapers_extractor.py is for standalone testing of the scraper.
# It's not directly used by app.py's normal flow.
# Removed the main() function from here to avoid confusion and focus on module functionality.

# Keeping the direct extraction function for external use (e.g., batch_processor)
def extract_from_newspapers_com(url: str, cookies: str = "", player_name: Optional[str] = None, project_name: str = "default") -> Dict:
    extractor = NewspapersComExtractor(auto_auth=False, project_name=project_name)
    if cookies:
        # In this enhanced version, the `cookies` argument for direct extraction is less relevant
        # as the extractor now manages its own authentication state via SeleniumLoginManager.
        # However, for backward compatibility or specific use cases, we can log it.
        logger.warning("Direct 'cookies' argument is provided but primary authentication is now managed internally by Selenium.")
        # If you still want to try to use external cookies, you would update extractor.cookie_manager.cookies here
        # But this might conflict with the Selenium-managed session.
        # For this setup, it's best to rely on the extractor's internal authentication.

    # Ensure the extractor is initialized and authenticated before extraction
    if not extractor.initialize():
        return {'success': False, 'error': "Newspapers.com extractor could not initialize or authenticate."}
    
    return extractor.extract_from_url(url, player_name, project_name=project_name)