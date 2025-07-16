# newspapers_extractor.py
# Complete Newspaper.com Scraping Suite with Auto Cookie Extraction

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
    from seleniumwire import webdriver as wire_webdriver
    SELENIUM_WIRE_AVAILABLE = True
except ImportError:
    SELENIUM_WIRE_AVAILABLE = False
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
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import logging
from bs4 import BeautifulSoup
import signal
import threading
import queue
import tempfile
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
            if self.is_replit_deployment:
                chrome_options.add_argument('--memory-pressure-off')
                chrome_options.add_argument('--max_old_space_size=512')
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
                if self.is_replit_deployment:
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
                        cookie_domain = '.newspapers.com'
                        self.driver.add_cookie({'name': name, 'value': value, 'domain': cookie_domain, 'path': '/'})
                    except Exception as e:
                        logger.warning(f"Could not add cookie {name} to driver: {e}")
                
                # Refresh page to apply cookies
                self.driver.refresh()
                
                # Wait for the 'ncom' object and its 'isloggedin' property to be accessible and true
                try:
                    wait_timeout = 90 if self.is_replit else 30
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
                wait_timeout = 60 if self.is_replit else 20
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
                wait_timeout = 90 if self.is_replit else 30
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
            wait_timeout = 90 if self.selenium_login_manager.is_replit else 30
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
                
                ocr_timeout = 45.0 if self.cookie_manager.selenium_login_manager.is_replit else 15.0
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
    
    def extract_from_url(self, url: str, player_name: Optional[str] = None, extract_multi_page: bool = True, project_name: str = "default", extraction_method: str = "viewport_screenshot") -> Dict:
        try:
            # Route to download method if requested
            if extraction_method == "download_clicks":
                logger.info(f"Using download extraction method for URL: {url}")
                return self.extract_via_download_clicks(url, player_name, project_name)
            
            # Continue with original viewport screenshot method
            logger.info(f"Using viewport screenshot extraction method for URL: {url}")
            
            if not self.cookie_manager.refresh_cookies_if_needed():
                logger.error("Failed to refresh authentication cookies for article extraction.")
                return {'success': False, 'error': "Authentication failed or expired. Please re-initialize."}
            
            # Determine if this is a Newspapers.com URL
            is_newspapers_url = 'newspapers.com' in urlparse(url).netloc.lower()

            response_text = None
            if is_newspapers_url:
                logger.info(f"Newspapers.com URL detected. Forcing content fetch via Selenium for URL: {url}")
                html_content_from_selenium = self._get_page_content_with_selenium(url)
                if not html_content_from_selenium:
                    logger.error(f"Selenium failed to fetch content for Newspapers.com URL: {url} (paywall persistent or network issue).")
                    return {'success': False, 'error': f"Failed to fetch Newspapers.com article content with Selenium: {url}"}
                response_text = html_content_from_selenium
            else:
                # For non-Newspapers.com URLs, continue using requests.Session
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Referer': 'https://www.newspapers.com/'
                }
                
                try:
                    logger.info(f"Non-Newspapers.com URL detected. Attempting to fetch content using requests.Session for URL: {url}")
                    request_timeout = 90 if self.cookie_manager.selenium_login_manager.is_replit else 30
                    response = self.cookie_manager.session.get(url, headers=headers, timeout=request_timeout)
                    response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
                    response_text = response.text
                    logger.info(f"Successfully fetched non-Newspapers.com page with requests ({len(response_text)} bytes).")
                except requests.exceptions.RequestException as e:
                    logger.error(f"Failed to fetch non-Newspapers.com URL with requests: {str(e)}")
                    return {'success': False, 'error': f"Failed to fetch non-Newspapers.com article: {str(e)}"}
            
            # Ensure response_text is available before proceeding
            if response_text is None:
                logger.error("No content fetched for URL, neither by Selenium nor Requests.")
                return {'success': False, 'error': "Failed to fetch content for the given URL."}

            # ... rest of the method (extract_image_metadata, all_images processing, etc.) remains the same ...

            image_metadata = self._extract_image_metadata(response_text)
            if not image_metadata:
                logger.error("Failed to extract image metadata from page.")
                return {'success': False, 'error': "Could not find image metadata in page."}
            
            image_metadata['url'] = url
            logger.info(f"Extracted image metadata: {image_metadata}")
            
            all_images = []
            base_image_id = image_metadata.get('image_id')
            
            if extract_multi_page and base_image_id:
                logger.info("Searching for genuine multi-page article indicators...")
                multi_page_data = self._find_multi_page_images(response_text, str(base_image_id))
                
                if multi_page_data:
                    logger.info(f"Found {len(multi_page_data)} genuine additional pages.")
                    
                    for page_info in multi_page_data:
                        additional_page_url = f"https://www.newspapers.com/image/{page_info['image_id']}/"
                        page_metadata = image_metadata.copy()
                        page_metadata['image_id'] = page_info['image_id']
                        page_metadata['url'] = additional_page_url
                        page_metadata['page_offset'] = page_info.get('page_offset', 0)
                        page_metadata['source'] = page_info.get('source', 'multi-page detection')
                        
                        logger.info(f"Processing genuine additional page: image_id={page_info['image_id']}, URL={additional_page_url}")
                        
                        try:
                            # IMPORTANT: Now, _download_newspaper_image MUST also use Selenium if fetching from newspapers.com
                            # However, _download_newspaper_image already has a Selenium fallback, which is good.
                            # We just need to ensure the _get_page_content_with_selenium is robust enough for metadata extraction.
                            additional_image = self._download_newspaper_image(page_metadata)
                            if additional_image:
                                all_images.append({
                                    'image': additional_image,
                                    'metadata': page_metadata,
                                    'page_number': len(all_images) + 2
                                })
                                logger.info(f"Successfully extracted additional page {len(all_images) + 1}: {additional_image.size}.")
                            else:
                                logger.warning(f"Failed to extract additional page with image_id {page_info['image_id']}.")
                        except Exception as e:
                            logger.warning(f"Error processing additional page {page_info['image_id']}: {e}")
                            continue
                else:
                    logger.info("No genuine multi-page article found - processing as single page with multiple regions.")
            
            logger.info("Downloading main newspaper image...")
            # This call already correctly uses Selenium fallback in _download_newspaper_image
            main_newspaper_image = self._download_newspaper_image(image_metadata)
            if not main_newspaper_image:
                logger.error("Failed to download main newspaper image.")
                return {'success': False, 'error': "Failed to download newspaper image."}
            
            logger.info(f"Downloaded main newspaper image: {main_newspaper_image.size}")
            
            all_images.insert(0, {
                'image': main_newspaper_image,
                'metadata': image_metadata,
                'page_number': 1
            })
            
            if len(all_images) > 4:
                logger.warning(f"Limiting image processing from {len(all_images)} to 4 images.")
                all_images = all_images[:4]
            
            logger.info(f"Total images to process: {len(all_images)} (main + {len(all_images)-1} additional).")
            
            # Use the main image and auto-crop to clipping borders
            main_image = all_images[0]['image']
            main_metadata = all_images[0]['metadata']
            
            logger.info(f"Processing main image for clipping: {main_image.size}")
            
            # Detect and crop to newspaper clipping borders
            try:
                x, y, w, h = self.image_processor.detect_newspaper_clipping_borders(main_image)
                logger.info(f"Border detection returned: x={x}, y={y}, w={w}, h={h}")
                
                # Only crop if we actually detected a meaningful area (not the full image)
                if not (x == 0 and y == 0 and w == main_image.width and h == main_image.height):
                    cropped_image = main_image.crop((x, y, x + w, y + h))
                    logger.info(f"Auto-cropped clipping from {main_image.size} to {cropped_image.size}")
                    final_image = cropped_image
                else:
                    logger.info("Border detection returned full image bounds, no cropping applied")
                    final_image = main_image
            except Exception as e:
                logger.warning(f"Auto-cropping failed, using full image: {e}")
                final_image = main_image
            
            # Basic OCR for metadata extraction (optional, just for basic text preview)
            try:
                full_text = pytesseract.image_to_string(final_image)
                logger.info(f"Extracted basic text for preview: {len(full_text)} characters")
            except Exception as e:
                logger.warning(f"OCR failed for text preview: {e}")
                full_text = "Text extraction failed - manual review required"
            
            metadata = {
                'title': image_metadata.get('title', 'Unknown Article'),
                'date': image_metadata.get('date', datetime.now().strftime('%Y-%m-%d')),
                'newspaper': image_metadata.get('publication_title', 'Unknown Newspaper'),
                'location': image_metadata.get('location', 'Unknown Location'),
                'url': url,
                'sentiment_score': 0,
                'player_mentions': [],
                'extraction_method': 'newspapers.com_full_clipping',
                'ocr_confidence': 0,
                'sports_score': 0,
                'word_count': len(full_text.split()),
                'extraction_timestamp': datetime.now().isoformat(),
                'total_pages_found': len(all_images),
                'selected_page': 1,
                'all_pages_analyzed': 1
            }
            
            logger.info(f"Successfully captured full clipping from {len(all_images)} pages.")
            
            response = {
                'success': True,
                'headline': metadata['title'],
                'source': metadata['newspaper'],
                'date': metadata['date'],
                'location': metadata['location'],
                'content': full_text[:500] + "..." if len(full_text) > 500 else full_text,
                'image_data': final_image,  # Return the auto-cropped clipping
                'metadata': metadata,
                'full_text': full_text,
                'stitched_image': None,
                'article_boundaries': [],
                'processing_method': 'full_clipping'
            }
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing article page: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _get_page_content_with_selenium(self, url: str) -> Optional[str]:
        """Fetches page HTML content using Selenium, leveraging existing authentication."""
        driver = None
        try:
            # Re-use the driver from SeleniumLoginManager if it's still open, otherwise initialize a new one
            if self.cookie_manager.selenium_login_manager.driver and \
               self.cookie_manager.selenium_login_manager.driver.current_url != "data:,": # Check if driver is genuinely active
                driver = self.cookie_manager.selenium_login_manager.driver
                logger.info("Re-using existing Selenium driver for page content capture.")
            else:
                logger.info("Initializing new Selenium driver for page content capture and adding cookies.")
                # Ensure the driver is initialized. If not, this call will initialize it.
                if not self.cookie_manager.selenium_login_manager._initialize_chrome_driver():
                    logger.error("Failed to initialize Chrome driver in _get_page_content_with_selenium.")
                    return None
                driver = self.cookie_manager.selenium_login_manager.driver
                if not driver: return None

                # Add stored cookies to the new driver BEFORE navigating to the target URL
                driver.get('https://www.newspapers.com/') # Go to base domain to set cookies
                for name, value in self.cookie_manager.cookies.items():
                    try:
                        # Selenium cookie domains are strict; ensure it matches the actual domain or is generic
                        cookie_domain = '.newspapers.com' 
                        driver.add_cookie({'name': name, 'value': value, 'domain': cookie_domain, 'path': '/'})
                        logger.debug(f"Added cookie to new driver: {name}={value[:10]}...")
                    except Exception as e:
                        logger.warning(f"Could not add cookie {name} to new driver: {e}")
                time.sleep(2) # Give browser a moment to apply cookies before navigation

            logger.info(f"Loading target page with Selenium: {url}")
            driver.get(url)
            
            # --- START REVISED WAIT CONDITIONS ---
            # Wait for main page body to load, then for key elements of a logged-in page
            wait_timeout = 180 if self.cookie_manager.selenium_login_manager.is_replit else 60
            WebDriverWait(driver, wait_timeout).until( # Increased timeout for Replit
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Complex wait condition to ensure paywall is gone and content is loaded
            wait_timeout = 180 if self.cookie_manager.selenium_login_manager.is_replit else 60
            WebDriverWait(driver, wait_timeout).until( # Increased timeout for Replit
                EC.any_of(
                    # Scenario 1: Paywall element becomes invisible
                    EC.invisibility_of_element_located((By.XPATH, "//*[contains(text(), 'subscription') or contains(text(), 'sign in to view') or contains(text(), 'upgrade your access')]")),
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, '.paywall-modal, .subscription-overlay, .modal-dialog[aria-modal="true"]')),
                    # Scenario 2: Article image/viewer is present and visible
                    EC.visibility_of_element_located((By.CSS_SELECTOR, 'img[src*="img.newspapers.com"]')),
                    EC.visibility_of_element_located((By.CSS_SELECTOR, '.newspaper-image-viewer')),
                    # Scenario 3: Specific elements indicating logged-in state (e.g., account dropdown)
                    EC.presence_of_element_located((By.CSS_SELECTOR, '.account-menu-link, .my-account-link, #user-tools-dropdown, .logout-button'))
                )
            )
            time.sleep(10) # Final, longer wait for JS to render and paywall to truly vanish

            # --- END REVISED WAIT CONDITIONS ---

            # Check if an explicit paywall modal or overlay is still visible
            # Added a stricter check for display: none style
            if driver.find_elements(By.CSS_SELECTOR, '.paywall-modal[style*="display: block"], .subscription-overlay[style*="display: block"], .modal-dialog[aria-modal="true"][style*="display: block"]'):
                 logger.warning("Selenium detected a persistent paywall modal/overlay after wait. Attempting to close it.")
                 # Try to find and click a close button
                 try:
                     close_buttons = driver.find_elements(By.CSS_SELECTOR, '.close-button, .modal-close, [aria-label="Close"], .x-button, button[class*="close"]')
                     for btn in close_buttons:
                         if btn.is_displayed() and btn.is_enabled():
                             btn.click()
                             logger.info("Clicked a close button on paywall modal.")
                             time.sleep(5) # Give more time for modal to disappear
                             break
                 except Exception as close_e:
                     logger.warning(f"Failed to click close button: {close_e}")
                 
                 # Re-check for paywall indicators after attempting to close
                 if any(ind in driver.page_source.lower() for ind in paywall_indicators) or \
                    driver.find_elements(By.CSS_SELECTOR, '.paywall-modal[style*="display: block"], .subscription-overlay[style*="display: block"]'):
                     logger.warning("Selenium still encountering paywall after attempting to close modal. This is a hard paywall.")
                     self.cookie_manager.selenium_login_manager._save_debug_html(driver, url) # Save debug HTML if paywall persists
                     return None # Indicate failure

            page_html = driver.page_source
            
            # Final check for paywall indicators in the returned HTML (redundant but safe)
            paywall_indicators_final = [
                'you need a subscription', 'start a 7-day free trial', 'sign in to view this page',
                'already have an account', 'paywall', 'please sign in', 'log in to view', 'upgrade your access',
                'digital subscription', 'access to this content requires a subscription'
            ]
            is_paywalled_by_selenium = any(ind in page_html.lower() for ind in paywall_indicators_final)

            if is_paywalled_by_selenium:
                logger.warning("Selenium also encountered paywall after navigating to article and final checks.")
                self.cookie_manager.selenium_login_manager._save_debug_html(driver, url) # Save debug HTML if paywall persists
                return None # Indicate failure
            
            self.cookie_manager.selenium_login_manager._save_debug_html(driver, url) # Save debug HTML for inspection
            logger.info(f"Selenium successfully captured HTML content: {len(page_html)} bytes.")
            return page_html

        except TimeoutException:
            logger.error(f"Selenium page load/paywall disappearance timed out for URL: {url}. This indicates a persistent paywall or very slow loading.")
            
            # In Replit environment, try one more time with longer timeout
            if self.cookie_manager.selenium_login_manager.is_replit:
                logger.info("Replit environment detected - attempting one retry with extended timeout...")
                try:
                    time.sleep(10)  # Give system a moment to recover
                    
                    # Try one more time to wait for paywall to disappear
                    WebDriverWait(driver, 240).until(  # 4 minutes for Replit
                        EC.any_of(
                            EC.invisibility_of_element_located((By.XPATH, "//*[contains(text(), 'subscription') or contains(text(), 'sign in to view') or contains(text(), 'upgrade your access')]")),
                            EC.invisibility_of_element_located((By.CSS_SELECTOR, '.paywall-modal, .subscription-overlay, .modal-dialog[aria-modal="true"]')),
                            EC.visibility_of_element_located((By.CSS_SELECTOR, 'img[src*="img.newspapers.com"]')),
                            EC.visibility_of_element_located((By.CSS_SELECTOR, '.newspaper-image-viewer')),
                            EC.presence_of_element_located((By.CSS_SELECTOR, '.account-menu-link, .my-account-link, #user-tools-dropdown, .logout-button'))
                        )
                    )
                    
                    logger.info("Replit retry successful - paywall cleared on second attempt")
                    time.sleep(15)  # Extra time for Replit to fully render
                    
                    # Get the page HTML after successful retry
                    page_html = driver.page_source
                    logger.info(f"Selenium successfully captured HTML content after retry: {len(page_html)} bytes.")
                    return page_html
                    
                except TimeoutException:
                    logger.error("Replit retry also timed out - proceeding with available content")
                    # Try to get whatever content is available
                    try:
                        page_html = driver.page_source
                        if page_html and len(page_html) > 1000:  # If we have substantial content
                            logger.info("Using available content despite timeout")
                            return page_html
                    except Exception as e:
                        logger.error(f"Failed to get content after retry: {e}")
            
            try:
                if driver:
                    self.cookie_manager.selenium_login_manager._save_debug_html(driver, url) # Save debug HTML on timeout
            except Exception as debug_e:
                logger.error(f"Failed to save debug HTML on timeout: {debug_e}")
            return None
        except Exception as e:
            logger.error(f"Failed to capture page HTML with Selenium: {e}", exc_info=True)
            # Add debug info if driver is available
            try:
                if driver:
                    logger.info(f"Debug: Page source snippet: {driver.page_source[:500]}...")
                    logger.info(f"Debug: Page title: {driver.title}")
                    self.cookie_manager.selenium_login_manager._save_debug_html(driver, url) # Save debug HTML on unexpected error
            except Exception as debug_e:
                logger.error(f"Failed to get debug info: {debug_e}")
            return None
            
        finally:
            # We don't quit the driver here if it was reused from the login manager.
            # The SeleniumLoginManager itself or a higher-level function in app.py should manage quitting the persistent driver.
            # If a *new* driver was initialized within this method (which is the case if self.cookie_manager.selenium_login_manager.driver was not active), it should be quit.
            if driver and driver is not self.cookie_manager.selenium_login_manager.driver:
                try:
                    driver.quit()
                except:
                    pass

    def _extract_image_metadata(self, page_content: str) -> Optional[Dict]:
        logger.info("Parsing HTML for image metadata...")
        
        try:
            image_data = {}
            
            if match := re.search(r'"imageId":(\d+)', page_content):
                image_data['image_id'] = int(match.group(1))
                logger.info(f"Found image ID: {image_data['image_id']}")
            
            if match := re.search(r'"date":"([^"]+)"', page_content):
                image_data['date'] = match.group(1)
            
            if match := re.search(r'"publicationTitle":"([^"]+)"', page_content):
                image_data['publication_title'] = match.group(1)
            
            if match := re.search(r'"location":"([^"]+)"', page_content):
                image_data['location'] = match.group(1)
            
            if match := re.search(r'"title":"([^"]+)"', page_content):
                image_data['title'] = match.group(1)
            
            if match := re.search(r'"width":(\d+)', page_content):
                image_data['width'] = int(match.group(1))
            
            if match := re.search(r'"height":(\d+)', page_content):
                image_data['height'] = int(match.group(1))
            
            if match := re.search(r'"wfmImagePath":"([^"]+)"', page_content):
                image_data['wfm_image_path'] = match.group(1)
            
            ncom_match = re.search(r'Object\.defineProperty\(window,\s*[\'"]ncom[\'"],\s*\{value:\s*Object\.freeze\(({.*?})\)', page_content, re.DOTALL)
            if ncom_match:
                ncom_content = ncom_match.group(1)
                if match := re.search(r'"image":"([^"]+)"', ncom_content):
                    image_data['base_image_url'] = match.group(1)
                    logger.info(f"Found base image URL: {image_data['base_image_url']}")
            else:
                image_data['base_image_url'] = 'https://img.newspapers.com'
                logger.info("Using default base image URL.")
            
            if match := re.search(r'<link\s+rel="canonical"\s+href="([^"]+)"', page_content):
                image_data['url'] = match.group(1)
                logger.info(f"Found original URL: {image_data['url']}")
            elif match := re.search(r'<meta\s+property="og:url"\s+content="([^"]+)"', page_content):
                image_data['url'] = match.group(1)
                logger.info(f"Found original URL from og:url: {image_data['url']}")
            
            logger.info(f"Successfully extracted image metadata: {image_data}")
            return image_data if image_data else None
            
        except Exception as e:
            logger.error(f"Error parsing image metadata: {e}", exc_info=True)
            return None
    
    def _download_newspaper_image(self, metadata: Dict) -> Optional[Image.Image]:
        logger.info("Downloading newspaper article via screenshot...")
        
        try:
            # Always get a new driver for this specific task to ensure clean state and desired options
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=2560,1440') # High resolution window
            chrome_options.add_argument('--force-device-scale-factor=2') # Scale up for higher quality elements
            chrome_options.add_argument('--high-dpi-support=1')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            
            page_load_timeout = 120 if self.cookie_manager.selenium_login_manager.is_replit else 30
            driver.set_page_load_timeout(page_load_timeout)
            
            logger.info("Loading main site to set cookies for Selenium image download...")
            driver.get('https://www.newspapers.com/')
            
            for name, value in self.cookie_manager.cookies.items():
                try:
                    cookie_domain = '.newspapers.com' if 'newspapers.com' in (metadata.get('url') or '').lower() else None
                    if cookie_domain:
                         driver.add_cookie({'name': name, 'value': value, 'domain': cookie_domain, 'path': '/'})
                    else:
                        driver.add_cookie({'name': name, 'value': value, 'path': '/'})
                    logger.debug(f"Added cookie to driver for image extraction: {name}={value[:10]}...")
                except Exception as e:
                    logger.warning(f"Could not add cookie {name} to driver for image extraction: {e}")
            
            logger.info(f"Loading target page for article extraction: {metadata['url']}")
            driver.get(metadata['url'])
            
            # Wait for any of these conditions to be true:
            # 1. The subscription element is present (indicating logged in)
            # 2. The newspaper image viewer is present
            try:
                wait_timeout = 90 if self.cookie_manager.selenium_login_manager.is_replit else 30
                WebDriverWait(driver, wait_timeout).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "span.MemberNavigation_Subscription__RU0Cu")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, "svg[id*='svg-viewer']")),
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".newspaper-image-viewer"))
                    )
                )
            except TimeoutException:
                logger.warning("Initial wait timed out, checking page state...")
                
                # For Replit environment, give it one more chance
                if self.cookie_manager.selenium_login_manager.is_replit:
                    logger.info("Replit environment detected - attempting extended wait...")
                    try:
                        time.sleep(20)  # Give more time for slow Replit response
                        WebDriverWait(driver, 120).until(
                            EC.any_of(
                                EC.presence_of_element_located((By.CSS_SELECTOR, ".newspaper-image-viewer")),
                                EC.presence_of_element_located((By.TAG_NAME, "body"))
                            )
                        )
                        logger.info("Replit extended wait successful")
                    except TimeoutException:
                        logger.warning("Replit extended wait also timed out - proceeding with available content")
                
                # Check if we're actually on the right page
                if "newspapers.com" not in driver.current_url:
                    logger.error(f"Redirected to unexpected URL: {driver.current_url}")
                    return None
                
                # Check for common error states
                if any(text in driver.page_source.lower() for text in ["access denied", "blocked", "suspicious activity"]):
                    logger.error("Access denied or blocked by Newspapers.com")
                    return None
                
                # If we get here, try to proceed anyway - the page might be loaded but with different elements
                logger.info("Proceeding with article extraction despite timeout...")
            
            time.sleep(5) # Give more time for page to fully render after initial waits
            
            # Click the zoom-out button 6 times to capture the entire clipping
            logger.info("Clicking zoom-out button 6 times to capture entire clipping...")
            for i in range(6):
                try:
                    zoom_out_button = driver.find_element(By.ID, 'btn-zoom-out')
                    if zoom_out_button.is_displayed() and zoom_out_button.is_enabled():
                        zoom_out_button.click()
                        logger.info(f"Clicked zoom-out button {i + 1}/6")
                        time.sleep(1)  # Wait between clicks
                    else:
                        logger.warning(f"Zoom-out button not available on click {i + 1}/6")
                        break
                except Exception as e:
                    logger.warning(f"Could not click zoom-out button on attempt {i + 1}/6: {e}")
                    break
            
            # Wait for zoom changes to take effect
            time.sleep(2)
            
            # Scroll down slightly to avoid bottom navigation bar blocking content
            try:
                driver.execute_script("window.scrollBy(0, 50);")
                logger.info("Scrolled down 50px to avoid bottom navigation bar")
                time.sleep(1)
            except Exception as e:
                logger.warning(f"Could not scroll down: {e}")
            
            # Take full page screenshot to capture the entire clipping
            logger.info("Taking full page screenshot to capture entire clipping...")
            screenshot_data = driver.get_screenshot_as_png()
            full_screenshot = Image.open(io.BytesIO(screenshot_data))
            
            logger.info(f"Full page screenshot captured: {full_screenshot.size}")
            return full_screenshot
            
        except Exception as e:
            logger.error(f"Article extraction failed: {e}", exc_info=True)
            try:
                if driver:
                    logger.info(f"Debug: Page source snippet: {driver.page_source[:500]}...")
                    logger.info(f"Debug: Page title: {driver.title}")
                    logger.info(f"Debug: Current URL: {driver.current_url}")
            except Exception as debug_e:
                logger.error(f"Failed to get debug info: {debug_e}")
            return None
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def _get_possible_image_urls(self, metadata: Dict) -> List[str]:
        logger.info("Generating possible image URLs with focus on high resolution...")
        
        urls = []
        image_id = metadata.get('image_id')
        wfm_path_original = metadata.get('wfm_image_path')
        base_url = metadata.get('base_image_url', 'https://img.newspapers.com')
        
        # Prioritize larger sizes and quality parameters first
        if image_id:
            urls.extend([
                f"{base_url}/{image_id}?w=6000&q=100",
                f"{base_url}/{image_id}?w=4000&q=100",
                f"{base_url}/{image_id}?quality=100&w=2000",
                f"{base_url}/{image_id}?size=full&quality=100",
                f"{base_url}/{image_id}/full.jpg",
                f"{base_url}/{image_id}/large.jpg",
                f"{base_url}/{image_id}/original.jpg",
                f"{base_url}/{image_id}/image.jpg",
                f"{base_url}/{image_id}.jpg",
                f"https://www.newspapers.com/img/{image_id}/full.jpg",
                f"https://www.newspapers.com/image/{image_id}/full.jpg",
                f"{base_url}/image/{image_id}.jpg",
                f"https://www.newspapers.com/img/{image_id}.jpg",
            ])
        
        if wfm_path_original:
            processed_wfm_path = wfm_path_original
            
            # Clean path from potential leading slashes or PDF extensions for URL construction
            if processed_wfm_path.upper().endswith('.PDF'):
                processed_wfm_path = processed_wfm_path[:-4]
            
            # Handle paths that might contain ':', potentially from internal identifiers
            path_segments = processed_wfm_path.split(':')
            clean_path_candidates = [seg for seg in path_segments if '/' in seg or '.' in seg]
            if not clean_path_candidates and path_segments: # Fallback to last segment if no slashes/dots
                clean_path_candidates.append(path_segments[-1])

            for clean_path_base in clean_path_candidates:
                clean_path_base = clean_path_base.lstrip('/')
                for ext in ['.jpg', '.jpeg', '.png', '']: # Try common image extensions
                    urls.extend([
                        f"{base_url}/{clean_path_base}{ext}?quality=100",
                        f"{base_url}/{clean_path_base}{ext}?size=full", 
                        f"{base_url}/{clean_path_base}{ext}?w=4000&q=100",
                        f"{base_url}/{clean_path_base}{ext}", # Generic form
                        f"https://www.newspapers.com/img/{clean_path_base}{ext}",
                        f"https://www.newspapers.com/image/{clean_path_base}{ext}",
                    ])
        
        unique_urls = []
        seen = set()
        for url in urls:
            if url not in seen:
                unique_urls.append(url)
                seen.add(url)
        
        logger.info(f"Generated {len(unique_urls)} unique URL patterns, prioritizing high resolution.")
        return unique_urls

    def _find_multi_page_images(self, html_content: str, base_image_id: str) -> List[Dict]:
        logger.info(f"Searching for multi-page images related to base image {base_image_id}.")
        
        multi_page_images = []
        
        try:
            start_time = time.time()
            MAX_SEARCH_TIME = 5 # Limit search time to avoid delays
            
            # Patterns for explicit navigation links (next/prev page)
            nav_link_patterns = [
                r'data-next-image="(\d+)"',
                r'data-prev-image="(\d+)"',
                r'href="[^"]*image/(\d+)[^"]*"[^>]*(?:next\s+page|previous\s+page|continue|continued|page\s+\d+)',
                r'class="[^"]*next[^"]*"[^>]*href="[^"]*image/(\d+)',
                r'class="[^"]*prev[^"]*"[^>]*href="[^"]*image/(\d+)'
            ]
            
            # Patterns for article continuation indicators (e.g., "continued on page X")
            continuation_patterns = [
                r'"continued"[^>]*image/(\d+)',
                r'"continuation"[^>]*image/(\d+)',
                r'data-article-continues="(\d+)"',
                r'data-article-page="(\d+)"',
                r'page=(\d+)' # More generic page parameter
            ]
            
            found_ids = set()
            found_ids.add(base_image_id)
            
            # Combine all patterns and search
            all_patterns = nav_link_patterns + continuation_patterns
            for pattern in all_patterns:
                if time.time() - start_time > MAX_SEARCH_TIME or len(multi_page_images) >= 3:
                    break
                    
                try:
                    matches = re.findall(pattern, html_content, re.IGNORECASE)
                    for match in matches[:3]: # Limit matches per pattern to speed up
                        if match != base_image_id and match not in found_ids:
                            found_ids.add(match)
                            multi_page_images.append({
                                'image_id': match,
                                'page_offset': 0, # Placeholder, actual offset might need more logic
                                'source': 'dynamic_pattern_match'
                            })
                            logger.info(f"Found potential multi-page link to image {match} via pattern '{pattern}'.")
                            
                        if len(multi_page_images) >= 3:
                            break # Limit to max 3 additional pages
                            
                except re.error as e:
                    logger.debug(f"Regex error with pattern {pattern}: {e}")
                    continue
            
            # Sort by image_id (assuming sequential IDs for pages) or order of discovery
            multi_page_images.sort(key=lambda x: x['image_id'])
            
            if not multi_page_images:
                logger.info("No genuine multi-page article indicators found - treating as single page.")
            else:
                logger.info(f"Found {len(multi_page_images)} genuine multi-page indicators.")
            
            return multi_page_images
            
        except Exception as e:
            logger.error(f"Error finding multi-page images: {e}")
            return []

    def extract_via_download_clicks(self, url: str, player_name: Optional[str] = None, project_name: str = "default") -> Dict:
        """
        Alternative extraction method using 2-click + GET request approach.
        This method performs 2 clicks to open the download menu and select format,
        then makes a direct GET request to the JPG download href URL.
        
        Args:
            url: The newspapers.com URL to extract from
            player_name: Optional player name for filtering
            project_name: Project name for storage organization
            
        Returns:
            Dict with extraction results including downloaded files
        """
        if not SELENIUM_WIRE_AVAILABLE:
            logger.error("selenium-wire is not available. Cannot use download capture method.")
            return {'success': False, 'error': "selenium-wire not installed. Use: pip install selenium-wire"}
        
        try:
            # Refresh cookies if needed
            if not self.cookie_manager.refresh_cookies_if_needed():
                logger.error("Failed to refresh authentication cookies for download extraction.")
                return {'success': False, 'error': "Authentication failed or expired. Please re-initialize."}
            
            # Configure selenium-wire options
            wire_options = {
                'port': 0,  # Use random port
                'disable_encoding': True,  # Don't decode responses
                'request_storage_base_dir': tempfile.gettempdir(),
                'suppress_connection_errors': True,
            }
            
            # Setup Chrome options for download capture
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Add user agent to avoid detection
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Configure download behavior
            prefs = {
                "download.default_directory": tempfile.gettempdir(),
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            # Initialize selenium-wire driver
            driver = wire_webdriver.Chrome(options=chrome_options, seleniumwire_options=wire_options)
            
            try:
                # Add cookies for authentication
                driver.get("https://www.newspapers.com")
                
                # Wait for initial page load and potential Cloudflare challenge
                WebDriverWait(driver, 60).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                
                # Add cookies after initial page load
                for name, value in self.cookie_manager.cookies.items():
                    try:
                        cookie_dict = {
                            'name': name,
                            'value': value,
                            'domain': '.newspapers.com',
                            'path': '/'
                        }
                        driver.add_cookie(cookie_dict)
                        logger.debug(f"Added cookie: {name}")
                    except Exception as e:
                        logger.warning(f"Could not add cookie {name} to wire driver: {e}")
                
                # Navigate to the target URL
                logger.info(f"Navigating to URL: {url}")
                driver.get(url)
                
                # Wait for page to load completely and handle any Cloudflare challenges
                WebDriverWait(driver, 90).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.ID, "btn-print")),
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                )
                
                # Additional wait for JavaScript to settle
                time.sleep(5)
                
                # Configure selectors for the 2-click path (no third click needed)
                CLICK_SELECTORS = [
                    # First click - open download menu
                    {"selector": "[id='btn-print']", "description": "Download button"},
                    # Second click - select format
                    {"selector": "[aria-labelledby='entireP']", "description": "Entire Page Button"}
                ]
                
                downloaded_files = []
                
                # Execute the 2-click sequence
                for i, click_config in enumerate(CLICK_SELECTORS, 1):
                    try:
                        logger.info(f"Click {i}: {click_config['description']}")
                        
                        # Wait for element to be clickable
                        element = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, click_config["selector"]))
                        )
                        
                        # Clear any captured requests before clicking
                        driver.requests.clear()
                        
                        # Regular click for both buttons
                        element.click()
                        
                        # Wait a moment for any downloads to start
                        time.sleep(2)
                        
                        # Check for download requests from selenium-wire
                        for request in driver.requests:
                            if request.response and request.response.headers.get('content-disposition'):
                                # This looks like a file download
                                content_type = request.response.headers.get('content-type', '')
                                
                                # Only save JPG files
                                if not ('jpeg' in content_type.lower() or 'jpg' in content_type.lower()):
                                    logger.info(f"Skipping non-JPG file type: {content_type}")
                                    continue
                                
                                downloaded_files.append({
                                    'url': request.url,
                                    'content': request.response.body,
                                    'content_type': content_type,
                                    'headers': dict(request.response.headers),
                                    'click_step': i
                                })
                                logger.info(f"Captured JPG download from click {i}: {content_type}")
                        
                    except TimeoutException:
                        logger.warning(f"Timeout waiting for click {i} element: {click_config['description']}")
                        continue
                    except Exception as e:
                        logger.error(f"Error during click {i}: {str(e)}")
                        continue
                
                # After the 2 clicks, find the JPG download button and make direct GET request
                try:
                    logger.info("Looking for JPG download button to extract href URL")
                    
                    # Wait for the JPG download button to appear
                    jpg_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn.btn-outline-light.border-primary.jpg"))
                    )
                    
                    # Get the href URL from the button
                    href_url = jpg_button.get_attribute("href")
                    if href_url:
                        logger.info(f"Found JPG download href URL: {href_url}")
                        
                        # Extract filename from original URL
                        from urllib.parse import urlparse, parse_qs, urlencode
                        parsed_url = urlparse(href_url)
                        params = parse_qs(parsed_url.query)
                        
                        # Get filename from the original URL parameters
                        filename = None
                        if 'filename' in params:
                            filename = params['filename'][0] + '.jpg'
                        else:
                            # Fallback filename based on article ID
                            article_id = params.get('id', ['unknown'])[0]
                            filename = f"newspaper_article_{article_id}.jpg"
                        
                        logger.info(f"Extracted filename: {filename}")
                        
                        # Keep only essential parameters, remove problematic ones
                        essential_params = ['institutionId', 'id', 'user', 'iat']
                        filtered_params = {k: v for k, v in params.items() if k in essential_params}
                        
                        # Reconstruct the URL with filtered parameters
                        filtered_query = urlencode(filtered_params, doseq=True)
                        filtered_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}?{filtered_query}"
                        
                        logger.info(f"Filtered URL: {filtered_url}")
                        
                        # Make a GET request to the filtered URL to download the image
                        try:
                            # Add proper headers that newspapers.com expects
                            headers = {
                                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                                'Accept': 'image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                                'Accept-Language': 'en-US,en;q=0.9',
                                'Accept-Encoding': 'gzip, deflate, br',
                                'Referer': url,  # Use the current article URL as referrer
                                'Connection': 'keep-alive',
                                'Sec-Fetch-Dest': 'image',
                                'Sec-Fetch-Mode': 'no-cors',
                                'Sec-Fetch-Site': 'same-origin',
                            }
                            
                            # Use the session with cookies for authentication
                            response = self.cookie_manager.session.get(filtered_url, headers=headers, timeout=30)
                            response.raise_for_status()
                            
                            # Create a download file entry - only save JPG files
                            content_type = response.headers.get('content-type', 'image/jpeg')
                            if 'jpeg' in content_type.lower() or 'jpg' in content_type.lower():
                                downloaded_files.append({
                                    'url': href_url,
                                    'content': response.content,
                                    'content_type': content_type,
                                    'headers': dict(response.headers),
                                    'click_step': 3,  # Mark as step 3 for consistency
                                    'filename': filename
                                })
                                logger.info(f"Successfully downloaded JPG via GET request: {content_type}, filename: {filename}")
                            else:
                                logger.info(f"Skipping non-JPG file: {content_type}")
                        except Exception as req_e:
                            logger.error(f"Failed to download via GET request: {req_e}")
                    else:
                        logger.warning("No href found in JPG download button")
                        
                except Exception as e:
                    logger.error(f"Error finding JPG download button: {str(e)}")
                
                # Process downloaded files
                if downloaded_files:
                    return self._process_downloaded_files(downloaded_files, url, player_name, project_name)
                else:
                    return {'success': False, 'error': "No files were downloaded during the process"}
                
            finally:
                driver.quit()
                
        except Exception as e:
            logger.error(f"Error in download extraction: {str(e)}")
            return {'success': False, 'error': f"Download extraction failed: {str(e)}"}
    
    def _process_downloaded_files(self, downloaded_files: List[Dict], url: str, player_name: Optional[str], project_name: str) -> Dict:
        """
        Process downloaded files captured from the 3-click sequence.
        Handles storage for both local and Replit environments.
        """
        try:
            storage_manager = StorageManager(project_name)
            processed_files = []
            
            for i, file_data in enumerate(downloaded_files):
                try:
                    # Generate filename based on content type and URL
                    content_type = file_data['content_type']
                    file_extension = self._get_file_extension(content_type)
                    
                    # Use filename from href URL if available, otherwise create with timestamp
                    if 'filename' in file_data and file_data['filename']:
                        filename = file_data['filename']
                    else:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"newspaper_download_{timestamp}_{i+1}{file_extension}"
                    
                    # Handle storage based on environment
                    if self.cookie_manager.selenium_login_manager.is_replit:
                        # Save to Replit object storage
                        result = storage_manager.store_file(
                            filename=filename,
                            content=file_data['content']
                        )
                        if result.get('success'):
                            file_path = result.get('path', filename)
                            logger.info(f"Saved to Replit storage: {file_path}")
                        else:
                            logger.error(f"Failed to save to Replit storage: {result.get('error')}")
                            file_path = filename
                    else:
                        # Save to local directory
                        local_dir = Path(f"downloads/{project_name}")
                        local_dir.mkdir(parents=True, exist_ok=True)
                        local_path = local_dir / filename
                        
                        with open(local_path, 'wb') as f:
                            f.write(file_data['content'])
                        
                        file_path = str(local_path)
                        logger.info(f"Saved to local storage: {file_path}")
                    
                    # Extract metadata if it's an image
                    metadata = None
                    if 'image' in content_type.lower():
                        try:
                            image = Image.open(io.BytesIO(file_data['content']))
                            metadata = {
                                'size': image.size,
                                'format': image.format,
                                'mode': image.mode
                            }
                        except Exception as e:
                            logger.warning(f"Could not process image metadata: {e}")
                    
                    processed_files.append({
                        'filename': filename,
                        'path': file_path,
                        'content_type': content_type,
                        'size': len(file_data['content']),
                        'click_step': file_data['click_step'],
                        'metadata': metadata,
                        'url': file_data['url'],
                        'content': file_data['content']  # Add image content for preview
                    })
                    
                except Exception as e:
                    logger.error(f"Error processing downloaded file {i}: {str(e)}")
                    continue
            
            # Add image data for UI preview (use first image if available)
            image_data = None
            if processed_files:
                first_file = processed_files[0]
                if 'image' in first_file.get('content_type', '').lower():
                    image_data = first_file['content']
            
            return {
                'success': True,
                'method': 'download_clicks',
                'url': url,
                'files': processed_files,
                'player_name': player_name,
                'project_name': project_name,
                'timestamp': datetime.now().isoformat(),
                'image_data': image_data,  # Add image data for UI preview
                'headline': f"Downloaded from {url}",
                'source': 'newspapers.com',
                'date': datetime.now().strftime('%Y-%m-%d')
            }
            
        except Exception as e:
            logger.error(f"Error processing downloaded files: {str(e)}")
            return {'success': False, 'error': f"File processing failed: {str(e)}"}
    
    def _get_file_extension(self, content_type: str) -> str:
        """Get appropriate file extension based on content type."""
        content_type = content_type.lower()
        
        if 'pdf' in content_type:
            return '.pdf'
        elif 'jpeg' in content_type or 'jpg' in content_type:
            return '.jpg'
        elif 'png' in content_type:
            return '.png'
        elif 'gif' in content_type:
            return '.gif'
        elif 'tiff' in content_type:
            return '.tiff'
        elif 'bmp' in content_type:
            return '.bmp'
        elif 'webp' in content_type:
            return '.webp'
        else:
            return '.bin'  # Generic binary file


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