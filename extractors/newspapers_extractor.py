# newspaper_scraper_suite.py
# Complete Newspaper.com Scraping Suite with Auto Cookie Extraction

import streamlit as st
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import cv2
import pytesseract
from PIL import Image, ImageEnhance
import numpy as np
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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


class EnhancedSeleniumLoginManager:
    """Enhanced Selenium login manager with better authentication handling"""
    
    def __init__(self):
        self.driver = None
        self.cookies = {}
        self.last_login = None
        self.login_credentials = None
        self.is_replit = 'REPL_ID' in os.environ or 'REPL_SLUG' in os.environ
        self.auth_data = {}  # Store complete authentication data
    
    def set_credentials(self, email: str, password: str):
        """Set login credentials"""
        self.login_credentials = {'email': email, 'password': password}
    
    def setup_enhanced_chrome_options(self):
        """Set up enhanced Chrome options for better stealth"""
        chrome_options = Options()
        
        # Basic headless options
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        # Enhanced stealth options
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-popup-blocking')
        
        # Add realistic user agent
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        # Replit-specific options
        if self.is_replit:
            chrome_options.add_argument('--disable-setuid-sandbox')
            chrome_options.add_argument('--single-process')
            chrome_options.add_argument('--no-zygote')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-gpu-sandbox')
            chrome_options.add_argument('--disable-accelerated-2d-canvas')
            chrome_options.add_argument('--disable-accelerated-jpeg-decoding')
            chrome_options.add_argument('--disable-accelerated-mjpeg-decode')
            chrome_options.add_argument('--disable-accelerated-video-decode')
            chrome_options.add_argument('--disable-accelerated-video')
            chrome_options.add_argument('--disable-webgl')
            chrome_options.add_argument('--disable-webgl2')
            chrome_options.add_argument('--disable-features=site-per-process')
            
            # Try to find Chrome binary
            possible_chrome_paths = [
                '/usr/bin/google-chrome',
                '/usr/bin/google-chrome-stable',
                '/usr/bin/chromium',
                '/usr/bin/chromium-browser',
                '/snap/bin/chromium',
                '/nix/store/*/bin/chromium',
                '/nix/store/*/bin/google-chrome',
                '/nix/store/3qnxr5x6gw3k9a9i7d0akz0m6bksbwff-chromedriver-125.0.6422.141/bin/chromedriver'
            ]
            
            chrome_binary = None
            for path in possible_chrome_paths:
                if '*' in path:
                    import glob
                    matches = glob.glob(path)
                    if matches:
                        chrome_binary = matches[0]
                        break
                elif os.path.exists(path):
                    chrome_binary = path
                    break
            
            if chrome_binary:
                logger.info(f"Found Chrome binary at: {chrome_binary}")
                chrome_options.binary_location = chrome_binary
            else:
                logger.warning("Chrome binary not found in standard locations")
        
        return chrome_options

    def perform_human_like_login(self, email: str, password: str) -> bool:
        """Perform enhanced human-like login sequence with better error handling"""
        try:
            # 1. Start from main page to establish session context
            logger.info("Loading main page to establish session...")
            self.driver.get('https://www.newspapers.com/')
            time.sleep(3)
            
            # 2. Navigate to login page directly (more reliable)
            logger.info("Navigating directly to login page...")
            self.driver.get('https://www.newspapers.com/signin/')
            time.sleep(3)
            
            # 3. Wait for login form with multiple strategies
            try:
                # Try different selectors for the email field
                email_selectors = ["#email", "input[name='email']", "input[type='email']"]
                email_field = None
                
                for selector in email_selectors:
                    try:
                        email_field = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        logger.info(f"Found email field with selector: {selector}")
                        break
                    except:
                        continue
                
                if not email_field:
                    logger.error("Could not find email field with any selector")
                    return False
                
                # Find password field
                password_selectors = ["#password", "input[name='password']", "input[type='password']"]
                password_field = None
                
                for selector in password_selectors:
                    try:
                        password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                        logger.info(f"Found password field with selector: {selector}")
                        break
                    except:
                        continue
                
                if not password_field:
                    logger.error("Could not find password field")
                    return False
                    
                logger.info("Login form fields found successfully")
                
            except Exception as e:
                logger.error(f"Failed to find login form: {str(e)}")
                # Save debug HTML to see what's on the page
                self._save_debug_html_simple()
                return False
            
            # 4. Clear fields and fill with human-like behavior
            try:
                # Focus and clear email field
                email_field.click()
                time.sleep(0.5)
                email_field.clear()
                time.sleep(0.5)
                
                # Type email slowly
                for char in email:
                    email_field.send_keys(char)
                    time.sleep(0.08)  # Slightly slower typing
                
                time.sleep(1.5)
                
                # Focus and clear password field
                password_field.click()
                time.sleep(0.5)
                password_field.clear()
                time.sleep(0.5)
                
                # Type password slowly
                for char in password:
                    password_field.send_keys(char)
                    time.sleep(0.08)
                
                time.sleep(2)
                logger.info("Form filled successfully")
                
            except Exception as e:
                logger.error(f"Failed to fill login form: {str(e)}")
                return False
            
            # 5. Submit form with multiple strategies
            try:
                # Strategy 1: Try to find and click submit button
                submit_selectors = [
                    "input[type='submit']",
                    "button[type='submit']", 
                    "button:contains('Sign In')",
                    ".btn-primary",
                    "#signin-button",
                    "form button"
                ]
                
                submit_clicked = False
                for selector in submit_selectors:
                    try:
                        if ":contains" in selector:
                            # Handle pseudo-selector differently
                            submit_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Sign In') or contains(text(), 'Log In') or contains(text(), 'Submit')]")
                        else:
                            submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                        
                        if submit_button and submit_button.is_enabled():
                            submit_button.click()
                            logger.info(f"Clicked submit button with selector: {selector}")
                            submit_clicked = True
                            break
                    except:
                        continue
                
                # Strategy 2: Submit the form directly
                if not submit_clicked:
                    try:
                        password_field.submit()
                        logger.info("Submitted form via password field")
                        submit_clicked = True
                    except:
                        pass
                
                # Strategy 3: Press Enter in password field
                if not submit_clicked:
                    try:
                        from selenium.webdriver.common.keys import Keys
                        password_field.send_keys(Keys.RETURN)
                        logger.info("Pressed Enter in password field")
                        submit_clicked = True
                    except:
                        pass
                
                if not submit_clicked:
                    logger.error("Could not submit login form with any method")
                    return False
                
            except Exception as e:
                logger.error(f"Failed to submit login form: {str(e)}")
                return False
            
            # 6. Wait for login to complete with multiple checks
            try:
                # Wait a bit for the form to process
                time.sleep(3)
                
                # Check multiple conditions for successful login
                login_success = False
                
                # Check 1: URL changed away from login/signin
                current_url = self.driver.current_url.lower()
                if "login" not in current_url and "signin" not in current_url:
                    logger.info("URL indicates successful login")
                    login_success = True
                
                # Check 2: Look for login success indicators
                success_indicators = [
                    "account",
                    "dashboard", 
                    "profile",
                    "logout"
                ]
                
                page_content = self.driver.page_source.lower()
                for indicator in success_indicators:
                    if indicator in page_content:
                        logger.info(f"Found login success indicator: {indicator}")
                        login_success = True
                        break
                
                # Check 3: Look for absence of login form
                try:
                    email_still_present = self.driver.find_element(By.ID, "email")
                    if not email_still_present.is_displayed():
                        logger.info("Login form no longer visible")
                        login_success = True
                except:
                    # Email field not found, which is good
                    logger.info("Login form not found on page")
                    login_success = True
                
                if not login_success:
                    logger.error("Login appears to have failed - still on login page")
                    self._save_debug_html_simple()
                    return False
                
            except Exception as e:
                logger.error(f"Error checking login status: {str(e)}")
                return False
            
            # 7. Additional wait for JavaScript session setup
            time.sleep(5)
            
            # 8. Verify authentication by checking user object
            try:
                user_data = self.driver.execute_script("return window.ncom ? window.ncom.user : null;")
                
                if user_data and user_data != 'null' and user_data != 0:
                    logger.info(f"Successfully authenticated as user: {user_data}")
                    return True
                else:
                    logger.warning(f"Authentication may not be complete - user data: {user_data}")
                    # Continue anyway as cookies might still be valid
                    return True
                    
            except Exception as e:
                logger.warning(f"Could not verify user authentication: {str(e)}")
                # Continue anyway
                return True
                
        except Exception as e:
            logger.error(f"Enhanced login sequence failed: {str(e)}")
            return False

    def extract_complete_authentication_data(self):
        """Extract all possible authentication data"""
        auth_data = {}
        
        try:
            # Get all cookies
            auth_data['cookies'] = self.driver.get_cookies()
            
            # Get JavaScript session data
            ncom_data = self.driver.execute_script("return window.ncom || {};")
            auth_data['ncom'] = ncom_data
            
            # Get page data
            page_data = self.driver.execute_script("return window.page || {};")
            auth_data['page'] = page_data
            
            # Get localStorage if available
            try:
                local_storage = self.driver.execute_script("""
                    var ls = {};
                    for (var i = 0; i < localStorage.length; i++) {
                        var key = localStorage.key(i);
                        ls[key] = localStorage.getItem(key);
                    }
                    return ls;
                """)
                auth_data['localStorage'] = local_storage
            except:
                auth_data['localStorage'] = {}
            
            # Get sessionStorage if available
            try:
                session_storage = self.driver.execute_script("""
                    var ss = {};
                    for (var i = 0; i < sessionStorage.length; i++) {
                        var key = sessionStorage.key(i);
                        ss[key] = sessionStorage.getItem(key);
                    }
                    return ss;
                """)
                auth_data['sessionStorage'] = session_storage
            except:
                auth_data['sessionStorage'] = {}
            
            # Store authentication timestamp
            auth_data['timestamp'] = datetime.now().isoformat()
            
            return auth_data
            
        except Exception as e:
            logger.error(f"Error extracting authentication data: {str(e)}")
            return {}

    def login(self) -> bool:
        """Enhanced login using improved authentication strategy with fallback"""
        if not self.login_credentials:
            logger.error("No login credentials set")
            return False
            
        try:
            # Set up enhanced Chrome options
            chrome_options = self.setup_enhanced_chrome_options()
            
            logger.info("Attempting to initialize Chrome with enhanced options...")
            
            try:
                # Initialize Chrome with enhanced options
                if self.is_replit:
                    from selenium.webdriver.chrome.service import Service
                    service = Service('/nix/store/3qnxr5x6gw3k9a9i7d0akz0m6bksbwff-chromedriver-125.0.6422.141/bin/chromedriver')
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    self.driver = webdriver.Chrome(options=chrome_options)
                
                logger.info("Chrome initialization successful")
                
                # Remove webdriver property to avoid detection
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                # Set page load timeout
                self.driver.set_page_load_timeout(30)
                
                # Perform enhanced human-like login
                login_attempted = self.perform_human_like_login(
                    self.login_credentials['email'], 
                    self.login_credentials['password']
                )
                
                if login_attempted:
                    # Extract complete authentication data regardless of login status
                    self.auth_data = self.extract_complete_authentication_data()
                    
                    # Extract cookies for backward compatibility
                    self.cookies = {}
                    for cookie in self.auth_data.get('cookies', []):
                        self.cookies[cookie['name']] = cookie['value']
                    
                    # Check if we have any cookies at all
                    if self.cookies:
                        logger.info(f"Successfully extracted {len(self.cookies)} cookies with enhanced method")
                        self.last_login = datetime.now()
                        
                        # Save auth data for debugging
                        try:
                            with open('enhanced_auth_data.json', 'w') as f:
                                import json
                                # json.dump(self.auth_data, f, indent=2, default=str)
                            logger.info("Saved enhanced authentication data for debugging")
                        except Exception as e:
                            logger.warning(f"Could not save auth data: {e}")
                        
                        return True
                    else:
                        logger.error("No cookies found after enhanced login attempt")
                        return False
                else:
                    logger.error("Enhanced login sequence failed completely")
                    return False
                    
            except Exception as e:
                logger.error(f"Enhanced Chrome initialization failed: {str(e)}")
                return False
            
        except Exception as e:
            logger.error(f"Enhanced login failed with unexpected error: {str(e)}")
            return False
            
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
                self.driver = None
    
    def refresh_if_needed(self) -> bool:
        """Check if session needs refreshing and do so if needed"""
        if not self.last_login:
            return self.login()
            
        # Refresh if login is older than 6 hours
        if datetime.now() - self.last_login > timedelta(hours=6):
            logger.info("Session expired, refreshing login...")
            return self.login()
            
        return True

class EnhancedAutoCookieManager:
    """Enhanced cookie manager with improved authentication"""
    
    def __init__(self):
        self.cookies = {}
        self.session = requests.Session()
        self.last_extraction = None
        self.selenium_login = EnhancedSeleniumLoginManager()  # Use enhanced version
        
    def set_login_credentials(self, email: str, password: str):
        """Set login credentials for Selenium authentication"""
        self.selenium_login.set_credentials(email, password)
        
    def auto_extract_cookies(self, domain: str = "newspapers.com") -> bool:
        """Automatically extract cookies using enhanced Selenium login"""
        try:
            # Try enhanced Selenium login
            if self.selenium_login.login():
                self.cookies = self.selenium_login.cookies
                self.last_extraction = datetime.now()

                # Update session cookies with enhanced data
                self.session.cookies.clear()
                
                # Use the complete auth data for better session management
                auth_data = self.selenium_login.auth_data
                
                # Set cookies from the enhanced extraction
                for cookie in auth_data.get('cookies', []):
                    try:
                        self.session.cookies.set(
                            cookie['name'],
                            cookie['value'],
                            domain=cookie.get('domain'),
                            path=cookie.get('path', '/'),
                            secure=cookie.get('secure', False)
                        )
                    except Exception as e:
                        logger.warning(f"Failed to set cookie {cookie['name']}: {e}")

                # Also update from self.cookies dict for redundancy
                for name, value in self.cookies.items():
                    self.session.cookies.set(name, value)

                logger.info(f"Session cookies after enhanced transfer: {len(self.session.cookies.get_dict())} cookies")

                # Save complete auth data for future use
                try:
                    with open('enhanced_auth_data.json', 'w') as f:
                        import json
                        json.dump(auth_data, f, indent=2, default=str)
                    logger.info("Saved enhanced authentication data")
                except Exception as e:
                    logger.warning(f"Could not save auth data: {e}")

                st.success("✅ Successfully logged in to Newspapers.com with enhanced authentication")
                return True

            st.error("❌ Enhanced authentication failed")
            return False

        except Exception as e:
            logger.error(f"Enhanced cookie extraction failed: {str(e)}")
            return False
    
    def test_authentication(self, test_url: str = "https://www.newspapers.com/") -> bool:
        """Test if extracted cookies provide valid authentication with better detection"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }

            # Clear and set cookies
            self.session.cookies.clear()
            for name, value in self.cookies.items():
                self.session.cookies.set(name, value)

            logger.info(f"Testing enhanced authentication with {len(self.cookies)} cookies")
            logger.debug(f"Cookies: {list(self.cookies.keys())}")

            response = self.session.get(test_url, headers=headers, timeout=15)

            if response.status_code == 200:
                content = response.text.lower()
                
                # Multiple checks for authentication status
                auth_checks = {
                    'has_logout': 'logout' in content,
                    'has_account': 'account' in content or 'profile' in content,
                    'has_subscription': 'subscription' in content or 'premium' in content,
                    'not_login_page': 'sign-in' not in response.url and 'login' not in response.url,
                    'no_login_form': 'id="email"' not in content or 'signin' not in content
                }
                
                # Check for user ID in various formats
                import re
                user_id_patterns = [
                    r'"user":(\d+)',
                    r'"userID":"(\d+)"',
                    r'"userId":(\d+)',
                    r'user_id["\']:\s*["\']?(\d+)'
                ]
                
                user_id = None
                for pattern in user_id_patterns:
                    match = re.search(pattern, content)
                    if match and match.group(1) != '0' and match.group(1) != 'null':
                        user_id = match.group(1)
                        break
                
                auth_checks['has_user_id'] = user_id is not None
                
                # Count positive indicators
                positive_indicators = sum(1 for check, result in auth_checks.items() if result)
                
                logger.info(f"Authentication check results: {auth_checks}")
                logger.info(f"Positive indicators: {positive_indicators}/6")
                
                if user_id:
                    logger.info(f"User ID found: {user_id}")
                
                # Determine authentication status based on indicators
                if positive_indicators >= 4:  # Need at least 4 out of 6 positive indicators
                    if user_id:
                        st.success("🔓 Enhanced authentication verified - Premium access detected")
                        logger.info("Full authentication confirmed")
                    else:
                        st.success("🔓 Authentication verified - Good access detected")
                        logger.info("Authentication confirmed without user ID")
                    return True
                    
                elif positive_indicators >= 2:
                    st.warning("⚠️ Partial authentication detected - may have limited functionality")
                    logger.warning("Partial authentication - some indicators missing")
                    return True
                    
                else:
                    st.error("❌ Authentication verification failed - no access detected")
                    logger.error("Authentication failed - insufficient positive indicators")
                    
                    # Log what we found for debugging
                    logger.debug(f"Page URL: {response.url}")
                    logger.debug(f"Content preview: {content[:500]}...")
                    
                    return False
                    
            else:
                st.error(f"❌ Authentication failed - HTTP {response.status_code}")
                logger.error(f"HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            st.error(f"❌ Authentication test failed: {str(e)}")
            logger.error(f"Authentication test exception: {str(e)}")
            return False
        
    # Also add a method to check specific premium page access
    def test_premium_access(self, test_url: str = "https://www.newspapers.com/image/635076099/") -> bool:
        """Test access to a specific premium newspaper page"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.newspapers.com/'
            }

            response = self.session.get(test_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                content = response.text.lower()
                
                # Check for paywall indicators
                paywall_indicators = [
                    'you need a subscription',
                    'start a 7-day free trial', 
                    'subscribe to view',
                    'sign in to view this page',
                    'subscription required'
                ]
                
                has_paywall = any(indicator in content for indicator in paywall_indicators)
                
                # Check for successful page load indicators
                success_indicators = [
                    'image-viewer',
                    'newspaper-image',
                    'clip', 
                    'print',
                    'download'
                ]
                
                has_content = any(indicator in content for indicator in success_indicators)
                
                if not has_paywall and has_content:
                    logger.info("Premium page access confirmed")
                    return True
                elif has_paywall:
                    logger.warning("Premium page shows paywall")
                    return False
                else:
                    logger.warning("Premium page status unclear")
                    return False
                    
            else:
                logger.error(f"Premium page returned HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Premium access test failed: {str(e)}")
            return False
    
    def refresh_cookies_if_needed(self) -> bool:
        """Check if cookies need refreshing and do so automatically"""
        if not self.last_extraction:
            return self.auto_extract_cookies()
        
        # Check if cookies are older than 6 hours
        if datetime.now() - self.last_extraction > timedelta(hours=6):
            st.info("🔄 Refreshing cookies (6+ hours old)")
            return self.auto_extract_cookies()
        
        # Test if current cookies still work
        if not self.test_authentication():
            st.info("🔄 Refreshing expired cookies")
            return self.auto_extract_cookies()
        
        return True


class NewspaperImageProcessor:
    """Advanced image processing for newspaper clippings"""
    
    def __init__(self):
        self.min_article_area = 30000  # Minimum area for article detection
        self.text_confidence_threshold = 30  # Minimum OCR confidence
    
    def enhance_image_quality(self, image: Image.Image) -> Image.Image:
        """Enhance image quality for better OCR"""
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Increase contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        # Increase sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        # Convert to numpy for OpenCV processing
        img_array = np.array(image)
        
        # Noise reduction
        denoised = cv2.fastNlMeansDenoising(img_array)
        
        # Adaptive thresholding for better text detection
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        return Image.fromarray(binary)
    
    def detect_article_regions(self, image: Image.Image) -> List[Tuple[int, int, int, int]]:
        """Detect individual article regions in newspaper page"""
        logger.info(f"Detecting article regions in image of size: {image.size}")
        
        # Convert to OpenCV format
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # For full page screenshots, we need a different approach
        # Look for large rectangular regions that might contain newspaper content
        
        # Apply edge detection to find newspaper boundaries
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        
        # Apply morphological operations to connect text regions
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        morphed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        # Find contours
        contours, _ = cv2.findContours(
            morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        logger.info(f"Found {len(contours)} total contours")
        
        # Much more permissive filtering for full page screenshots
        article_regions = []
        min_area = 5000  # Much smaller minimum area
        
        for i, contour in enumerate(contours):
            area = cv2.contourArea(contour)
            
            if area > min_area:
                x, y, w, h = cv2.boundingRect(contour)
                
                # Add padding and ensure bounds
                padding = 10
                x = max(0, x - padding)
                y = max(0, y - padding)
                w = min(image.width - x, w + 2 * padding)
                h = min(image.height - y, h + 2 * padding)
                
                # Much more permissive aspect ratio (any reasonable rectangle)
                aspect_ratio = h / w if w > 0 else 0
                
                # Accept any rectangle that's not extremely thin or extremely square
                if 0.1 < aspect_ratio < 10.0 and w > 100 and h > 100:
                    article_regions.append((x, y, w, h))
                    logger.debug(f"Contour {i}: area={area}, bbox=({x},{y},{w},{h}), aspect={aspect_ratio:.2f}")
                else:
                    logger.debug(f"Rejected contour {i}: area={area}, bbox=({x},{y},{w},{h}), aspect={aspect_ratio:.2f}")
        
        # If we found very few regions with edge detection, try a different approach
        if len(article_regions) < 3:
            logger.info("Few regions found with edge detection, trying simpler grid approach")
            
            # Divide the image into a grid and treat each cell as a potential region
            grid_regions = []
            
            # Try different grid sizes
            for rows, cols in [(2, 2), (3, 3), (4, 4)]:
                cell_width = image.width // cols
                cell_height = image.height // rows
                
                for row in range(rows):
                    for col in range(cols):
                        x = col * cell_width
                        y = row * cell_height
                        w = cell_width
                        h = cell_height
                        
                        # Make sure the region is reasonable size
                        if w > 200 and h > 200:
                            grid_regions.append((x, y, w, h))
            
            logger.info(f"Generated {len(grid_regions)} grid regions")
            article_regions.extend(grid_regions)
        
        # Sort by area (largest first) and limit results
        article_regions.sort(key=lambda r: r[2] * r[3], reverse=True)
        final_regions = article_regions[:20]  # Return top 20 regions
        
        logger.info(f"Returning {len(final_regions)} article regions for processing")
        return final_regions
    
    def extract_text_with_confidence(self, image: Image.Image, region: Tuple[int, int, int, int]) -> Tuple[str, float]:
        """Extract text with confidence scores"""
        x, y, w, h = region
        logger.debug(f"Extracting text from region: {region}")
        
        try:
            # Crop region
            cropped = image.crop((x, y, x + w, y + h))
            logger.debug(f"Cropped region to size: {cropped.size}")
            
            # Enhance for OCR
            enhanced = self.enhance_image_quality(cropped)
            logger.debug(f"Enhanced image for OCR, mode: {enhanced.mode}")
            
            # Check if Tesseract is available
            try:
                tesseract_version = pytesseract.get_tesseract_version()
                logger.debug(f"Tesseract version: {tesseract_version}")
            except Exception as e:
                logger.error(f"Tesseract not available: {e}")
                return "", 0.0
            
            # OCR with detailed output (using threading for timeout if needed)
            try:
                # Use a queue to get results from the OCR thread
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
                
                # Start OCR in a separate thread
                ocr_thread = threading.Thread(target=ocr_worker)
                ocr_thread.daemon = True
                ocr_thread.start()
                
                # Wait for result with timeout
                ocr_thread.join(timeout=15.0)  # 15 second timeout
                
                # Check if OCR completed
                if ocr_thread.is_alive():
                    logger.warning(f"OCR extraction timed out for region {region}")
                    return "", 0.0
                
                # Check for exceptions
                if not exception_queue.empty():
                    ocr_exception = exception_queue.get()
                    if isinstance(ocr_exception, pytesseract.TesseractError):
                        logger.error(f"Tesseract error during OCR: {ocr_exception}")
                    else:
                        logger.error(f"Unexpected error during OCR: {ocr_exception}")
                    return "", 0.0
                
                # Get the result
                if result_queue.empty():
                    logger.error("OCR completed but no result available")
                    return "", 0.0
                
                data = result_queue.get()
                
                # Filter out low-confidence words
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
        
        # Calculate relevance score
        relevance_score = min(total_matches / max(len(words), 1) * 10, 1.0)
        
        is_sports_related = relevance_score > 0.1 and total_matches >= 2
        
        return is_sports_related, relevance_score, sport_matches
    
    def check_player_mentions(self, text: str, player_name: str) -> Tuple[bool, List[str]]:
        """Check for player name mentions and variations"""
        text_lower = text.lower()
        player_lower = player_name.lower()
        
        # Split player name into parts
        name_parts = player_lower.split()
        
        mentions = []
        
        # Check for full name
        if player_lower in text_lower:
            mentions.append(player_name)
        
        # Check for last name only (if multiple parts)
        if len(name_parts) > 1:
            last_name = name_parts[-1]
            if last_name in text_lower and len(last_name) > 2:
                mentions.append(last_name)
        
        # Check for first name + last initial
        if len(name_parts) > 1:
            first_last_initial = f"{name_parts[0]} {name_parts[-1][0]}"
            if first_last_initial in text_lower:
                mentions.append(first_last_initial)
        
        return len(mentions) > 0, mentions
    
    def analyze_sentiment(self, text: str, player_name: str) -> Tuple[float, str]:
        """Analyze sentiment of article regarding the player"""
        text_lower = text.lower()
        
        # Count positive and negative indicators
        positive_count = sum(1 for word in self.sports_keywords['positive'] if word in text_lower)
        negative_count = sum(1 for word in self.negative_indicators if word in text_lower)
        
        # Simple sentiment scoring
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
        
        # Check sports relevance
        is_sports, sports_score, sport_keywords = self.analyze_sports_relevance(text)
        if not is_sports:
            return False, {"reason": "Not sports-related", "sports_score": sports_score}
        
        # Check player mentions
        has_player, mentions = self.check_player_mentions(text, player_name)
        if not has_player:
            return False, {"reason": "Player not mentioned", "sports_score": sports_score}
        
        # Analyze sentiment
        sentiment_score, sentiment_label = self.analyze_sentiment(text, player_name)
        
        analysis = {
            "sports_score": sports_score,
            "sport_keywords": sport_keywords,
            "player_mentions": mentions,
            "sentiment_score": sentiment_score,
            "sentiment_label": sentiment_label,
            "word_count": len(text.split())
        }
        
        # Only accept positive or neutral articles
        is_relevant = sentiment_score >= -0.1  # Allow slightly negative but not clearly negative
        
        return is_relevant, analysis


class StorageManager:
    """Manage storage and retrieval of clipping results"""
    
    def __init__(self, storage_dir: str = "clippings"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        logger.info(f"Initialized storage manager with directory: {storage_dir}")
    
    def save_clipping(self, result: ClippingResult) -> bool:
        """Save a clipping result to storage"""
        try:
            # Create subdirectory for the player
            player_dir = os.path.join(self.storage_dir, result.filename.split('_')[0])
            os.makedirs(player_dir, exist_ok=True)
            
            # Save image
            image_path = os.path.join(player_dir, f"{result.filename}.png")
            result.image.save(image_path)
            
            # Save metadata
            metadata_path = os.path.join(player_dir, f"{result.filename}_metadata.json")
            metadata_dict = {
                'title': result.metadata.title,
                'date': result.metadata.date,
                'url': result.metadata.url,
                'newspaper': result.metadata.newspaper,
                'sentiment_score': result.metadata.sentiment_score,
                'text_preview': result.metadata.text_preview,
                'player_mentions': result.metadata.player_mentions,
                'bounding_box': result.bounding_box,
                'filename': result.filename,
                'saved_timestamp': datetime.now().isoformat()
            }
            
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Successfully saved clipping: {result.filename}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save clipping {result.filename}: {e}")
            return False
    
    def load_clippings(self, player_name: str) -> List[Dict]:
        """Load saved clippings for a player"""
        try:
            player_dir = os.path.join(self.storage_dir, player_name.lower().replace(' ', '_'))
            if not os.path.exists(player_dir):
                return []
            
            clippings = []
            for filename in os.listdir(player_dir):
                if filename.endswith('_metadata.json'):
                    metadata_path = os.path.join(player_dir, filename)
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # Load corresponding image
                    image_filename = filename.replace('_metadata.json', '.png')
                    image_path = os.path.join(player_dir, image_filename)
                    if os.path.exists(image_path):
                        metadata['image_path'] = image_path
                    
                    clippings.append({'metadata': metadata})
            
            # Sort by date (newest first)
            clippings.sort(key=lambda x: x['metadata'].get('date', ''), reverse=True)
            logger.info(f"Loaded {len(clippings)} clippings for {player_name}")
            return clippings
            
        except Exception as e:
            logger.error(f"Failed to load clippings for {player_name}: {e}")
            return []


class NewspapersComExtractor:
    """Main scraper class that coordinates all components"""
    
    def __init__(self, auto_auth: bool = True):
        self.cookie_manager = EnhancedAutoCookieManager()
        self.image_processor = NewspaperImageProcessor()
        self.content_analyzer = ContentAnalyzer()
        self.results = []
        self.auto_auth = auto_auth
        
    def initialize(self, email: str = None, password: str = None) -> bool:
        """Initialize the scraper with automatic authentication"""
        st.info("🔍 Setting up Newspapers.com authentication...")
        
        if email and password:
            self.cookie_manager.set_login_credentials(email, password)
        
        if not self.cookie_manager.auto_extract_cookies():
            st.error("Failed to authenticate. Please check your login credentials.")
            return False
        
        return self.cookie_manager.test_authentication()
    
    def get_authentication_status(self) -> Dict:
        """Get current authentication status"""
        return {
            'initialized': bool(self.cookie_manager.cookies),
            'authenticated': self.cookie_manager.test_authentication(),
            'cookies_count': len(self.cookie_manager.cookies),
            'last_extraction': self.cookie_manager.last_extraction
        }
    
    def search_articles(self, query: str, date_range: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Search for articles about a player on newspapers.com"""
        logger.info(f"Starting search for query: '{query}'")
        logger.info(f"Date range: {date_range}")
        logger.info(f"Result limit: {limit}")
        
        try:
            # Refresh cookies if needed
            if not self.cookie_manager.refresh_cookies_if_needed():
                logger.error("Failed to refresh authentication cookies for search")
                return []
            
            # Construct search URL with proper encoding
            encoded_query = query.replace(' ', '%20').replace('"', '%22')
            search_url = f"https://www.newspapers.com/search/"
            
            # Build search parameters
            params = {
                'query': query,
                'sort': 'relevance'
            }
            
            if date_range and date_range != "Any":
                # Parse date range (e.g., "2010-2019")
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
            
            # Perform search request
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
            
            logger.info(f"Search response received ({len(response.content)} bytes)")
            
            # Parse search results from HTML
            articles = self._parse_search_results(response.text, limit)
            logger.info(f"Parsed {len(articles)} articles from search results")
            
            return articles
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}", exc_info=True)
            return []
    
    def _parse_search_results(self, html_content: str, limit: int) -> List[Dict]:
        """Parse search results from newspapers.com search page HTML"""
        logger.info("Parsing search results from HTML...")
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            articles = []
            
            # Look for search result containers (these selectors may need adjustment based on actual HTML structure)
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
                    logger.info(f"Found {len(result_elements)} results using selector '{selector}'")
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
                logger.warning("No search results found with known selectors")
                # Fallback: look for any links that might be article links
                article_links = soup.find_all('a', href=True)
                logger.info(f"Fallback: found {len(article_links)} total links")
                
                for i, link in enumerate(article_links[:limit]):
                    href = link.get('href', '')
                    if '/image/' in href or '/clip/' in href:
                        # This looks like an article link
                        title = link.get_text(strip=True) or f"Article {i+1}"
                        
                        # Construct full URL if needed
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
            
            logger.info(f"Successfully parsed {len(articles)} articles from search results")
            return articles
            
        except Exception as e:
            logger.error(f"Error parsing search results: {e}", exc_info=True)
            return []
    
    def _extract_article_from_element(self, element, index: int) -> Optional[Dict]:
        """Extract article data from a search result element"""
        try:
            # Extract title
            title_selectors = ['h3', '.title', '.headline', 'a']
            title = "Unknown Title"
            for selector in title_selectors:
                title_elem = element.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break
            
            # Extract URL
            url = ""
            link_elem = element.select_one('a[href]')
            if link_elem:
                href = link_elem.get('href')
                if href.startswith('/'):
                    url = f"https://www.newspapers.com{href}"
                else:
                    url = href
            
            # Extract date
            date_selectors = ['.date', '.published', '[data-date]']
            date = "Unknown"
            for selector in date_selectors:
                date_elem = element.select_one(selector)
                if date_elem:
                    date = date_elem.get_text(strip=True)
                    break
            
            # Extract newspaper name
            newspaper_selectors = ['.newspaper', '.source', '.publication']
            newspaper = "Unknown"
            for selector in newspaper_selectors:
                news_elem = element.select_one(selector)
                if news_elem:
                    newspaper = news_elem.get_text(strip=True)
                    break
            
            # Extract preview/snippet
            preview_selectors = ['.preview', '.snippet', '.excerpt', 'p']
            preview = title  # Default to title
            for selector in preview_selectors:
                preview_elem = element.select_one(selector)
                if preview_elem:
                    preview_text = preview_elem.get_text(strip=True)
                    if len(preview_text) > 20:  # Only use if substantial
                        preview = preview_text
                        break
            
            if not url:
                logger.warning(f"No URL found for article {index+1}")
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
    
    def extract_from_url(self, url: str, player_name: Optional[str] = None, extract_multi_page: bool = True) -> Dict:
        """Extract content from a specific newspapers.com URL with improved multi-page detection"""
        try:
            # Refresh cookies if needed
            if not self.cookie_manager.refresh_cookies_if_needed():
                logger.error("Failed to refresh authentication cookies")
                return {'success': False, 'error': "Authentication failed"}
            
            # CRITICAL: Use the SAME session that was used for authentication
            logger.info("Using requests session with authenticated cookies first...")
            
            # Try using the authenticated requests session first
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.newspapers.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
            }
            
            try:
                # Use the existing authenticated session
                response = self.cookie_manager.session.get(url, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    # Check if we got the actual content (not a paywall redirect)
                    if 'subscription' not in response.text.lower() and 'sign in' not in response.url.lower():
                        logger.info("Successfully fetched page using authenticated requests session")
                        response_text = response.text
                    else:
                        logger.warning("Requests session hit paywall, falling back to Selenium with fresh auth")
                        return self._extract_with_fresh_selenium_auth(url, player_name, extract_multi_page)
                else:
                    logger.warning(f"Requests session failed with status {response.status_code}, falling back to Selenium")
                    return self._extract_with_fresh_selenium_auth(url, player_name, extract_multi_page)
                    
            except Exception as e:
                logger.warning(f"Requests session failed: {e}, falling back to Selenium")
                return self._extract_with_fresh_selenium_auth(url, player_name, extract_multi_page)
            
            # Continue with existing extraction logic...
            logger.info(f"Successfully fetched page ({len(response_text)} bytes)")
            
            # Parse the page content to extract image metadata
            image_metadata = self._extract_image_metadata(response_text)
            if not image_metadata:
                logger.error("Failed to extract image metadata from page")
                return {'success': False, 'error': "Could not find image metadata in page"}
            
            # Add the original URL to metadata for Selenium fallback
            image_metadata['url'] = url
            
            logger.info(f"Extracted image metadata: {image_metadata}")
            
            # Find multi-page images if requested (with improved detection)
            all_images = []
            base_image_id = image_metadata.get('image_id')
            
            if extract_multi_page and base_image_id:
                logger.info("Searching for genuine multi-page article indicators...")
                multi_page_data = self._find_multi_page_images(response_text, str(base_image_id))
                
                if multi_page_data:
                    logger.info(f"Found {len(multi_page_data)} genuine additional pages")
                    
                    # Process each additional page
                    for page_info in multi_page_data:
                        # Create proper URL for the additional page
                        additional_page_url = f"https://www.newspapers.com/image/{page_info['image_id']}/"
                        page_metadata = image_metadata.copy()
                        page_metadata['image_id'] = page_info['image_id']
                        page_metadata['url'] = additional_page_url  # Use correct URL for additional page
                        page_metadata['page_offset'] = page_info['page_offset']
                        page_metadata['source'] = page_info['source']
                        
                        logger.info(f"Processing genuine additional page: image_id={page_info['image_id']}, URL={additional_page_url}")
                        
                        # Try to download this additional page with timeout
                        try:
                            additional_image = self._download_newspaper_image(page_metadata)
                            if additional_image:
                                all_images.append({
                                    'image': additional_image,
                                    'metadata': page_metadata,
                                    'page_number': len(all_images) + 2  # Start from 2 since main image is page 1
                                })
                                logger.info(f"Successfully extracted additional page {len(all_images) + 1}: {additional_image.size}")
                            else:
                                logger.warning(f"Failed to extract additional page with image_id {page_info['image_id']}")
                        except Exception as e:
                            logger.warning(f"Error processing additional page {page_info['image_id']}: {e}")
                            continue
                else:
                    logger.info("No genuine multi-page article found - processing as single page with multiple regions")
            
            # Download the main newspaper image
            logger.info("Downloading main newspaper image...")
            main_newspaper_image = self._download_newspaper_image(image_metadata)
            if not main_newspaper_image:
                logger.error("Failed to download main newspaper image")
                return {'success': False, 'error': "Failed to download newspaper image"}
            
            logger.info(f"Downloaded main newspaper image: {main_newspaper_image.size}")
            
            # Add main image to the beginning of the list
            all_images.insert(0, {
                'image': main_newspaper_image,
                'metadata': image_metadata,
                'page_number': 1
            })
            
            # SAFETY LIMIT: Absolute maximum of 4 total images to process
            if len(all_images) > 4:
                logger.warning(f"Limiting image processing from {len(all_images)} to 4 images")
                all_images = all_images[:4]
            
            logger.info(f"Total images to process: {len(all_images)} (main + {len(all_images)-1} additional)")
            
            # Process each image to find relevant content
            best_results = []
            
            for img_data in all_images:
                img = img_data['image']
                img_metadata = img_data['metadata']
                page_num = img_data['page_number']
                
                logger.info(f"Processing page {page_num} of {len(all_images)}: {img.size}")
                
                try:
                    # Detect article regions with timeout protection
                    logger.info("Detecting article regions...")
                    regions = self.image_processor.detect_article_regions(img)
                    logger.info(f"Found {len(regions)} potential article regions on page {page_num}")
                    
                    # SAFETY LIMIT: Only process top 5 regions per page for single pages
                    # For single newspaper pages, we want to check more regions to find article sections
                    max_regions = 5 if len(all_images) == 1 else 3
                    limited_regions = regions[:max_regions]
                    if len(regions) > max_regions:
                        logger.info(f"Limiting region processing from {len(regions)} to {max_regions} regions")
                    
                    # Process each region to find relevant content
                    page_best_result = None
                    page_best_score = 0
                    
                    for i, region in enumerate(limited_regions):
                        logger.info(f"Processing page {page_num}, region {i+1}/{len(limited_regions)}: {region}")
                        
                        try:
                            # Extract text from region with timeout protection
                            text, confidence = self.image_processor.extract_text_with_confidence(img, region)
                            
                            logger.info(f"Page {page_num}, region {i+1} OCR confidence: {confidence:.1f}%")
                            
                            if confidence < 30:  # Skip low-confidence extractions
                                logger.info(f"Skipping page {page_num}, region {i+1} due to low OCR confidence")
                                continue
                            
                            # Analyze relevance if player name provided
                            if player_name:
                                is_relevant, analysis = self.content_analyzer.is_relevant_article(text, player_name)
                                logger.info(f"Page {page_num}, region {i+1} relevance: relevant={is_relevant}")
                                
                                if not is_relevant:
                                    logger.info(f"Skipping page {page_num}, region {i+1} - not relevant to {player_name}")
                                    continue
                                
                                # Check if this is the best result so far for this page
                                combined_score = analysis.get('sports_score', 0) + (confidence / 100)
                                if combined_score > page_best_score:
                                    page_best_score = combined_score
                                    page_best_result = {
                                        'region': region,
                                        'text': text,
                                        'confidence': confidence,
                                        'analysis': analysis,
                                        'page_number': page_num,
                                        'image': img,
                                        'metadata': img_metadata
                                    }
                                    logger.info(f"New best result for page {page_num} with score {combined_score:.3f}")
                            else:
                                # If no player specified, take the first high-confidence region
                                page_best_result = {
                                    'region': region,
                                    'text': text,
                                    'confidence': confidence,
                                    'analysis': {'sentiment_score': 0, 'player_mentions': []},
                                    'page_number': page_num,
                                    'image': img,
                                    'metadata': img_metadata
                                }
                                logger.info(f"Using page {page_num}, region {i+1} as result (no player filter)")
                                break
                                
                        except Exception as e:
                            logger.warning(f"Error processing page {page_num}, region {i+1}: {e}")
                            continue
                    
                    if page_best_result:
                        best_results.append(page_best_result)
                        logger.info(f"Added best result from page {page_num}")
                        
                except Exception as e:
                    logger.error(f"Error processing page {page_num}: {e}")
                    continue
            
            if not best_results:
                logger.warning("No relevant content found in any image/region")
                return {'success': False, 'error': "No relevant content found"}
            
            # Use the best overall result (highest score) for main response
            overall_best = max(best_results, key=lambda r: r['analysis'].get('sports_score', 0) + (r['confidence'] / 100))
            logger.info(f"Selected overall best result from page {overall_best['page_number']}")
            
            # Extract the best clipping
            x, y, w, h = overall_best['region']
            clipping = overall_best['image'].crop((x, y, x + w, y + h))
            
            # Create comprehensive metadata
            metadata = {
                'title': image_metadata.get('title', 'Unknown Article'),
                'date': image_metadata.get('date', datetime.now().strftime('%Y-%m-%d')),
                'newspaper': image_metadata.get('publication_title', 'Unknown Newspaper'),
                'location': image_metadata.get('location', 'Unknown Location'),
                'url': url,
                'sentiment_score': overall_best['analysis'].get('sentiment_score', 0),
                'player_mentions': overall_best['analysis'].get('player_mentions', []),
                'extraction_method': 'newspapers.com_enhanced',
                'ocr_confidence': overall_best['confidence'],
                'sports_score': overall_best['analysis'].get('sports_score', 0),
                'word_count': len(overall_best['text'].split()),
                'extraction_timestamp': datetime.now().isoformat(),
                'total_pages_found': len(all_images),
                'selected_page': overall_best['page_number'],
                'all_pages_analyzed': len(best_results)
            }
            
            logger.info(f"Successfully extracted content from {len(all_images)} pages, selected page {overall_best['page_number']}")
            
            # Prepare response with multi-page information
            response = {
                'success': True,
                'headline': metadata['title'],
                'source': metadata['newspaper'],
                'date': metadata['date'],
                'location': metadata['location'],
                'content': overall_best['text'][:500] + "..." if len(overall_best['text']) > 500 else overall_best['text'],
                'image_data': clipping,
                'metadata': metadata,
                'full_text': overall_best['text']
            }
            
            # Add multi-page information
            if len(all_images) > 1:
                response['multi_page_info'] = {
                    'total_pages': len(all_images),
                    'pages_with_content': len(best_results),
                    'selected_page': overall_best['page_number'],
                    'all_page_results': [
                        {
                            'page_number': r['page_number'],
                            'confidence': r['confidence'],
                            'text_preview': r['text'][:100] + "..." if len(r['text']) > 100 else r['text'],
                            'sports_score': r['analysis'].get('sports_score', 0)
                        }
                        for r in best_results
                    ]
                }
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing article page: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _extract_with_fresh_selenium_auth(self, url: str, player_name: Optional[str] = None, extract_multi_page: bool = True) -> Dict:
        """Fallback method: Use Selenium with fresh authentication in the same session"""
        logger.info("Using Selenium with session continuity...")
        
        driver = None
        try:
            # CRITICAL CHANGE: Reuse the login process but stay in the same session
            if not self.cookie_manager.selenium_login.login_credentials:
                return {'success': False, 'error': "No login credentials available for fresh auth"}
            
            # Set up Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # Initialize driver
            driver = webdriver.Chrome(options=chrome_options)
            
            # Perform login in this session
            logger.info("Performing login in extraction session...")
            driver.get('https://www.newspapers.com/signin/')
            
            # Wait for login form
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "email"))
            )
            
            # Fill in login form
            email_field = driver.find_element(By.ID, "email")
            password_field = driver.find_element(By.ID, "password")
            
            email_field.clear()
            password_field.clear()
            
            email_field.send_keys(self.cookie_manager.selenium_login.login_credentials['email'])
            time.sleep(0.5)
            password_field.send_keys(self.cookie_manager.selenium_login.login_credentials['password'])
            time.sleep(0.5)
            
            # Submit form
            password_field.submit()
            
            # Wait for login to complete
            WebDriverWait(driver, 20).until(
                lambda driver: "login" not in driver.current_url.lower()
            )
            
            # Give extra time for authentication to settle
            time.sleep(3)
            
            # NOW navigate to the target page IN THE SAME SESSION
            logger.info(f"Navigating to target page in authenticated session: {url}")
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Give extra time for JavaScript to load content
            time.sleep(5)
            
            # Check for paywall indicators
            paywall_indicators = [
                'you need a subscription',
                'start a 7-day free trial',
                'sign in to view this page',
                'already have an account',
                'subscribe',
                'paywall',
                'please sign in',
                'log in to view'
            ]
            
            page_source = driver.page_source.lower()
            if any(ind in page_source for ind in paywall_indicators):
                logger.error("Still encountering paywall after fresh authentication")
                self._save_debug_html(driver, url)
                return {'success': False, 'error': "Paywall detected even after fresh authentication - account may not have access"}
            
            # Success! Get the page content
            response_text = driver.page_source
            logger.info("Successfully fetched page with fresh authentication")
            
            # Parse the page content to extract image metadata
            image_metadata = self._extract_image_metadata(response_text)
            if not image_metadata:
                logger.error("Failed to extract image metadata from page")
                return {'success': False, 'error': "Could not find image metadata in page"}
            
            # Add the original URL to metadata for Selenium fallback
            image_metadata['url'] = url
            
            # Continue with the rest of your existing extraction logic...
            # ... (rest of the method remains the same as your original code)
            
        except Exception as e:
            logger.error(f"Fresh Selenium auth failed: {e}")
            return {'success': False, 'error': f"Failed to fetch article with fresh auth: {e}"}
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def _extract_image_metadata(self, page_content: str) -> Optional[Dict]:
        """Extract image metadata from newspapers.com JavaScript objects"""
        logger.info("Parsing HTML for image metadata...")
        
        try:
            image_data = {}
            
            # Extract basic image info from the nested "image" object
            # The image object is complex with nested structures, so we need a more sophisticated approach
            image_match = re.search(r'"image":\s*\{.*?"imageId":(\d+).*?\}', page_content, re.DOTALL)
            if not image_match:
                logger.error("Could not find 'image' section with imageId in page object")
                return None
            
            # Extract image ID
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
            
            # Look for ncom object for image URL construction
            ncom_match = re.search(r'Object\.defineProperty\(window,\s*[\'"]ncom[\'"],\s*\{value:\s*Object\.freeze\(({.*?})\)', page_content, re.DOTALL)
            if ncom_match:
                ncom_content = ncom_match.group(1)
                if match := re.search(r'"image":"([^"]+)"', ncom_content):
                    image_data['base_image_url'] = match.group(1)
                    logger.info(f"Found base image URL: {image_data['base_image_url']}")
            else:
                # Fallback to default base URL
                image_data['base_image_url'] = 'https://img.newspapers.com'
                logger.info("Using default base image URL")
            
            # Extract the original URL from the page
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
        """Download the actual newspaper image using extracted metadata with high quality priority"""
        logger.info("Downloading newspaper image with high quality priority...")
        
        try:
            # First try direct URL approach with high-quality URLs
            possible_urls = self._get_possible_image_urls(metadata)
            if possible_urls:
                # SAFETY LIMIT: Only try first 10 URLs to prevent endless loops
                limited_urls = possible_urls[:10]
                logger.info(f"Will try {len(limited_urls)} URL patterns (limited from {len(possible_urls)} total)")
                
                # Enhanced headers with authentication
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Referer': 'https://www.newspapers.com/',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Sec-Fetch-Dest': 'image',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Sec-Fetch-Site': 'same-site',
                    'Pragma': 'no-cache',
                    'Cache-Control': 'no-cache',
                    'Origin': 'https://www.newspapers.com'
                }
                
                # First make a request to the main site to potentially get/update Cloudflare cookies
                try:
                    main_site_response = self.cookie_manager.session.get(
                        'https://www.newspapers.com/',
                        headers=headers,
                        timeout=10
                    )
                except Exception as e:
                    logger.debug(f"Failed to access main site: {e}")
                
                # Try each URL pattern until one works (high-quality first)
                for i, image_url in enumerate(limited_urls):
                    logger.info(f"Trying high-quality URL pattern {i+1}/{len(limited_urls)}: {image_url}")
                    
                    try:
                        response = self.cookie_manager.session.get(
                            image_url, 
                            headers=headers,
                            timeout=15,  # Reduced timeout to prevent hanging
                            allow_redirects=True
                        )
                        
                        if response.status_code == 200:
                            content_type = response.headers.get('content-type', '').lower()
                            if 'image' in content_type:
                                image = Image.open(io.BytesIO(response.content))
                                logger.info(f"Successfully downloaded high-quality image from URL pattern {i+1}: {image.size} ({len(response.content)} bytes)")
                                
                                # Check if this is a good quality image
                                if image.size[0] > 1000 and image.size[1] > 1000:
                                    logger.info(f"High-quality image confirmed: {image.size}")
                                    return image
                                else:
                                    logger.info(f"Image quality may be low: {image.size}, continuing search...")
                                    
                            else:
                                logger.warning(f"URL pattern {i+1} returned 200 but content-type is not image: {content_type}")
                        else:
                            logger.debug(f"URL pattern {i+1} failed: HTTP {response.status_code}")
                            
                    except Exception as e:
                        logger.debug(f"Error trying URL pattern {i+1}: {e}")
                        continue
                
                logger.info("Direct high-quality URL download unsuccessful, falling back to enhanced Selenium approach")
            
            # Fallback to enhanced Selenium-based extraction
            return self._extract_high_quality_image_with_selenium(metadata)
                
        except Exception as e:
            logger.error(f"Error downloading newspaper image: {e}", exc_info=True)
            return None
    
    def _extract_high_quality_image_with_selenium(self, metadata: Dict) -> Optional[Image.Image]:
        """Extract high-quality newspaper image using Selenium with better settings"""
        logger.info("Starting high-quality Selenium image extraction...")
        
        original_url = metadata.get('url')
        if not original_url:
            logger.error("No original URL available for Selenium extraction")
            return None
        
        driver = None
        try:
            # Set up Chrome options for high-quality screenshots
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=2560,1440')
            chrome_options.add_argument('--force-device-scale-factor=2')
            chrome_options.add_argument('--high-dpi-support=1')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.set_window_size(2560, 1440)
            
            # CRITICAL: Use existing authenticated cookies, don't login again
            logger.info("Loading main site to set authenticated cookies...")
            driver.get('https://www.newspapers.com/')
            
            # Add authenticated cookies
            for name, value in self.cookie_manager.cookies.items():
                try:
                    driver.add_cookie({'name': name, 'value': value, 'domain': '.newspapers.com'})
                except Exception as e:
                    logger.debug(f"Could not add cookie {name}: {e}")
            
            # Now load the target page
            logger.info(f"Loading target page: {original_url}")
            driver.get(original_url)
            
            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Give extra time for high-res images to load
            time.sleep(5)
            
            # Save debug HTML
            self._save_debug_html(driver, original_url)
            
            # Look for the highest quality newspaper image
            high_quality_selectors = [
                # Try to find the main newspaper image with highest quality
                'img[src*="img.newspapers.com"][src*="quality=100"]',
                'img[src*="img.newspapers.com"][src*="size=full"]',
                'img[src*="img.newspapers.com"][src*="w=4000"]',
                'img[src*="img.newspapers.com"][src*="w=2000"]',
                'img[src*="img.newspapers.com"]',
                'img[src*="newspapers.com/img"]',
                '.newspaper-image img',
                '.image-viewer img',
                'img[class*="newspaper"]',
                'canvas',  # Sometimes images are rendered on canvas
            ]
            
            best_image_element = None
            best_quality_score = 0
            
            for selector in high_quality_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        try:
                            # Get image dimensions and source
                            width = element.get_attribute('width') or driver.execute_script("return arguments[0].naturalWidth;", element)
                            height = element.get_attribute('height') or driver.execute_script("return arguments[0].naturalHeight;", element)
                            src = element.get_attribute('src') or ''
                            
                            if width and height:
                                width, height = int(width), int(height)
                                # Calculate quality score based on size and URL quality indicators
                                quality_score = width * height
                                
                                # Bonus for quality indicators in URL
                                if 'quality=100' in src:
                                    quality_score *= 2
                                elif 'size=full' in src:
                                    quality_score *= 1.8
                                elif 'w=4000' in src or 'w=6000' in src:
                                    quality_score *= 1.5
                                elif 'w=2000' in src:
                                    quality_score *= 1.2
                                
                                if quality_score > best_quality_score and width > 800 and height > 600:
                                    best_quality_score = quality_score
                                    best_image_element = element
                                    logger.info(f"Found better quality image: {width}x{height}, score: {quality_score}")
                                    
                        except Exception as e:
                            logger.debug(f"Error evaluating image element: {e}")
                            continue
                            
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            if best_image_element:
                # Try to get the high-quality image source URL and download it
                try:
                    img_src = best_image_element.get_attribute('src')
                    if img_src and img_src.startswith('http'):
                        logger.info(f"Found high-quality image src: {img_src}")
                        
                        # Try to get an even higher quality version by modifying the URL
                        high_quality_urls = [img_src]
                        
                        # Try to upgrade the URL to higher quality
                        if '?' in img_src:
                            base_url = img_src.split('?')[0]
                            high_quality_urls.extend([
                                f"{base_url}?quality=100&w=4000",
                                f"{base_url}?size=full&quality=100",
                                f"{base_url}?w=6000&q=100",
                                f"{base_url}?w=4000&q=100",
                                img_src  # Original as fallback
                            ])
                        
                        # Try each URL for best quality
                        for url in high_quality_urls:
                            try:
                                response = self.cookie_manager.session.get(url, timeout=30)
                                if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
                                    image = Image.open(io.BytesIO(response.content))
                                    logger.info(f"Successfully downloaded high-quality image: {image.size} from {url}")
                                    return image
                            except Exception as e:
                                logger.debug(f"Failed to download from {url}: {e}")
                                continue
                        
                except Exception as e:
                    logger.debug(f"Failed to download high-quality image via src URL: {e}")
                
                # Fallback: take a high-resolution screenshot of the image element
                try:
                    logger.info("Taking high-resolution screenshot of image element...")
                    # Scroll the element into view
                    driver.execute_script("arguments[0].scrollIntoView(true);", best_image_element)
                    time.sleep(1)
                    
                    screenshot_data = best_image_element.screenshot_as_png
                    image = Image.open(io.BytesIO(screenshot_data))
                    logger.info(f"High-res element screenshot captured: {image.size}")
                    return image
                except Exception as e:
                    logger.debug(f"Failed to screenshot image element: {e}")
            
            # Final fallback: take a high-resolution screenshot of the whole page
            logger.info("Taking high-resolution full page screenshot as last resort...")
            
            # Increase page zoom for better quality
            driver.execute_script("document.body.style.zoom='200%'")
            time.sleep(2)
            
            screenshot_data = driver.get_screenshot_as_png()
            full_screenshot = Image.open(io.BytesIO(screenshot_data))
            
            logger.info(f"High-res full page screenshot captured: {full_screenshot.size}")
            return full_screenshot
            
        except Exception as e:
            logger.error(f"High-quality Selenium extraction failed: {e}", exc_info=True)
            return None
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                
    def _save_debug_html_simple(self):
        """Save debug HTML for troubleshooting"""
        try:
            debug_dir = "debug_html"
            os.makedirs(debug_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"login_debug_{timestamp}.html"
            filepath = os.path.join(debug_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            
            logger.info(f"Saved login debug HTML to: {filepath}")
            
            # Also log current URL and title
            logger.info(f"Current URL: {self.driver.current_url}")
            logger.info(f"Page title: {self.driver.title}")
            
        except Exception as e:
            logger.error(f"Failed to save debug HTML: {e}")
    
    def _save_debug_html(self, driver, url: str) -> None:
        """Save the current page HTML for debugging purposes"""
        try:
            # Create debug directory if it doesn't exist
            debug_dir = "debug_html"
            os.makedirs(debug_dir, exist_ok=True)
            
            # Get the page HTML
            page_html = driver.page_source
            
            # Generate a filename based on URL and timestamp
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"debug_page_{timestamp}_{url_hash}.html"
            filepath = os.path.join(debug_dir, filename)
            
            # Save the HTML
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(page_html)
            
            logger.info(f"Saved debug HTML to: {filepath}")
            
            # Also save a summary file with metadata
            summary_filename = f"debug_summary_{timestamp}_{url_hash}.json"
            summary_filepath = os.path.join(debug_dir, summary_filename)
            
            summary_data = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'html_file': filename,
                'page_title': driver.title,
                'cookies_count': len(self.cookie_manager.cookies),
                'page_size_bytes': len(page_html),
                'user_agent': driver.execute_script("return navigator.userAgent;"),
                'viewport_size': driver.get_window_size(),
                'elements_found': {
                    'images': len(driver.find_elements(By.TAG_NAME, 'img')),
                    'scripts': len(driver.find_elements(By.TAG_NAME, 'script')),
                    'divs': len(driver.find_elements(By.TAG_NAME, 'div')),
                    'total_elements': len(driver.find_elements(By.XPATH, '//*'))
                }
            }
            
            with open(summary_filepath, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved debug summary to: {summary_filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save debug HTML: {e}")

    def capture_page_html(self, url: str, save_debug: bool = True) -> Dict:
        """Capture HTML content from a newspapers.com page using Selenium"""
        logger.info(f"Capturing HTML content from: {url}")
        
        driver = None
        try:
            # Refresh cookies if needed
            if not self.cookie_manager.refresh_cookies_if_needed():
                logger.error("Failed to refresh authentication cookies")
                return {'success': False, 'error': "Authentication failed"}
            
            # Set up Chrome options
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # Run in background
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # Initialize driver
            driver = webdriver.Chrome(options=chrome_options)
            
            # First visit the main site to set cookies
            logger.info("Loading main site to set cookies...")
            driver.get('https://www.newspapers.com/')
            
            # Add our extracted cookies
            cookie_count = 0
            for name, value in self.cookie_manager.cookies.items():
                try:
                    driver.add_cookie({'name': name, 'value': value, 'domain': '.newspapers.com'})
                    cookie_count += 1
                except Exception as e:
                    logger.debug(f"Could not add cookie {name}: {e}")
            
            logger.info(f"Added {cookie_count} cookies to browser")
            
            # Now load the target page
            logger.info(f"Loading target page: {url}")
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Give extra time for JavaScript to load content
            time.sleep(3)
            
            # Get page HTML
            page_html = driver.page_source
            page_title = driver.title
            
            logger.info(f"Captured HTML content: {len(page_html)} characters")
            logger.info(f"Page title: {page_title}")
            
            # Save debug HTML if requested
            if save_debug:
                self._save_debug_html(driver, url)
            
            # Extract some useful information
            elements_info = {
                'images': len(driver.find_elements(By.TAG_NAME, 'img')),
                'scripts': len(driver.find_elements(By.TAG_NAME, 'script')),
                'divs': len(driver.find_elements(By.TAG_NAME, 'div')),
                'forms': len(driver.find_elements(By.TAG_NAME, 'form')),
                'links': len(driver.find_elements(By.TAG_NAME, 'a')),
                'total_elements': len(driver.find_elements(By.XPATH, '//*'))
            }
            
            # Look for specific newspaper.com elements
            newspaper_elements = {
                'newspaper_images': len(driver.find_elements(By.CSS_SELECTOR, 'img[src*="img.newspapers.com"]')),
                'image_viewers': len(driver.find_elements(By.CSS_SELECTOR, '.image-viewer')),
                'article_containers': len(driver.find_elements(By.CSS_SELECTOR, '[class*="article"]')),
                'search_results': len(driver.find_elements(By.CSS_SELECTOR, '[class*="search"]')),
            }
            
            return {
                'success': True,
                'html_content': page_html,
                'page_title': page_title,
                'url': url,
                'elements_info': elements_info,
                'newspaper_elements': newspaper_elements,
                'html_size': len(page_html),
                'capture_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to capture page HTML: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
            
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def _get_possible_image_urls(self, metadata: Dict) -> List[str]:
        """Generate multiple possible image URLs to try, prioritizing high-resolution versions"""
        logger.info("Generating possible image URLs with focus on high resolution...")
        
        urls = []
        image_id = metadata.get('image_id')
        wfm_path_original = metadata.get('wfm_image_path')
        base_url = metadata.get('base_image_url', 'https://img.newspapers.com')
        
        if image_id:
            # Try high-resolution patterns first
            urls.extend([
                # Full resolution patterns (highest priority)
                f"{base_url}/{image_id}/image.jpg",
                f"{base_url}/{image_id}/full.jpg",
                f"{base_url}/{image_id}/large.jpg",
                f"{base_url}/{image_id}/original.jpg",
                f"{base_url}/{image_id}?size=full",
                f"{base_url}/{image_id}?quality=100",
                f"{base_url}/{image_id}?resolution=high",
                
                # Try with different size parameters
                f"{base_url}/{image_id}?w=2000&q=100",
                f"{base_url}/{image_id}?w=4000&q=100", 
                f"{base_url}/{image_id}?w=6000&q=100",
                f"{base_url}/{image_id}?width=2000&quality=100",
                f"{base_url}/{image_id}?width=4000&quality=100",
                
                # Standard patterns as fallback
                f"{base_url}/{image_id}.jpg",
                f"{base_url}/image/{image_id}/full.jpg",
                f"{base_url}/image/{image_id}.jpg",
                f"https://www.newspapers.com/img/{image_id}/full.jpg",
                f"https://www.newspapers.com/img/{image_id}.jpg",
                f"https://www.newspapers.com/image/{image_id}/full.jpg",
                f"https://www.newspapers.com/image/{image_id}.jpg",
            ])
        
        if wfm_path_original:
            # Process WFM path with emphasis on high quality
            processed_wfm_path = wfm_path_original
            
            if ':' in processed_wfm_path:
                path_part, suffix_part = processed_wfm_path.split(':', 1)
                for path_to_try in [path_part, suffix_part]:
                    if path_to_try.upper().endswith('.PDF'):
                        path_to_try = path_to_try[:-4]
                    
                    # Try high-res extensions first
                    for ext in ['.jpg', '.jpeg', '.png', '']:
                        clean_path = f"{path_to_try}{ext}".lstrip('/')
                        urls.extend([
                            f"{base_url}/{clean_path}?quality=100",
                            f"{base_url}/{clean_path}?size=full",
                            f"{base_url}/{clean_path}?w=4000&q=100",
                            f"{base_url}/{clean_path}",
                            f"https://www.newspapers.com/img/{clean_path}",
                            f"{base_url}/image/{clean_path}",
                            f"https://www.newspapers.com/image/{clean_path}",
                        ])
            else:
                if processed_wfm_path.upper().endswith('.PDF'):
                    processed_wfm_path = processed_wfm_path[:-4]
                
                for ext in ['.jpg', '.jpeg', '.png', '']:
                    clean_path = f"{processed_wfm_path}{ext}".lstrip('/')
                    urls.extend([
                        f"{base_url}/{clean_path}?quality=100",
                        f"{base_url}/{clean_path}?size=full", 
                        f"{base_url}/{clean_path}?w=4000&q=100",
                        f"{base_url}/{clean_path}",
                        f"https://www.newspapers.com/img/{clean_path}",
                        f"{base_url}/image/{clean_path}",
                        f"https://www.newspapers.com/image/{clean_path}",
                    ])
        
        # Remove duplicates while preserving order
        unique_urls = []
        seen = set()
        for url in urls:
            if url not in seen:
                unique_urls.append(url)
                seen.add(url)
        
        logger.info(f"Generated {len(unique_urls)} unique URL patterns, prioritizing high resolution")
        return unique_urls

    def _find_multi_page_images(self, html_content: str, base_image_id: str) -> List[Dict]:
        """Find all images that are part of a multi-page article"""
        logger.info(f"Searching for multi-page images related to base image {base_image_id}")
        
        multi_page_images = []
        
        try:
            # Safety limit - don't spend too much time on this
            import time
            start_time = time.time()
            MAX_SEARCH_TIME = 5  # Reduced to 5 seconds
            
            # Look for image navigation or page indicators in the HTML
            # Common patterns for multi-page articles
            import re
            
            # IMPORTANT: Only look for explicit multi-page indicators, NOT sequential IDs
            # Sequential newspaper page IDs are different pages of the same newspaper issue,
            # not continuation of the same article
            
            # Pattern 1: Look for explicit "next page" or "previous page" navigation
            nav_link_patterns = [
                r'data-next-image="(\d+)"',
                r'data-prev-image="(\d+)"',
                r'href="[^"]*image/(\d+)[^"]*"[^>]*(?:next\s+page|previous\s+page|continue|continued)',
                r'class="[^"]*next[^"]*"[^>]*href="[^"]*image/(\d+)',
                r'class="[^"]*prev[^"]*"[^>]*href="[^"]*image/(\d+)'
            ]
            
            found_ids = set()
            found_ids.add(base_image_id)  # Don't re-add the base image
            
            for pattern in nav_link_patterns:
                if time.time() - start_time > MAX_SEARCH_TIME:
                    break
                    
                try:
                    matches = re.findall(pattern, html_content, re.IGNORECASE)
                    for match in matches[:2]:  # Only first 2 matches per pattern
                        if match != base_image_id and match not in found_ids and len(found_ids) < 4:
                            found_ids.add(match)
                            multi_page_images.append({
                                'image_id': match,
                                'page_offset': 0,
                                'source': 'navigation_link'
                            })
                            logger.info(f"Found explicit navigation link to image {match}")
                            
                        if len(multi_page_images) >= 3:  # Maximum 3 additional pages
                            break
                            
                    if len(multi_page_images) >= 3:
                        break
                        
                except re.error as e:
                    logger.debug(f"Regex error with nav pattern {pattern}: {e}")
                    continue
            
            # Pattern 2: Look for specific article continuation indicators
            continuation_patterns = [
                r'"continued"[^>]*image/(\d+)',
                r'"continuation"[^>]*image/(\d+)',
                r'data-article-continues="(\d+)"',
                r'data-article-page="(\d+)"'
            ]
            
            for pattern in continuation_patterns:
                if time.time() - start_time > MAX_SEARCH_TIME or len(multi_page_images) >= 3:
                    break
                    
                try:
                    matches = re.findall(pattern, html_content, re.IGNORECASE)
                    for match in matches[:2]:
                        if match != base_image_id and match not in found_ids:
                            found_ids.add(match)
                            multi_page_images.append({
                                'image_id': match,
                                'page_offset': 0,
                                'source': 'article_continuation'
                            })
                            logger.info(f"Found article continuation indicator for image {match}")
                            
                        if len(multi_page_images) >= 3:
                            break
                except re.error as e:
                    logger.debug(f"Regex error with continuation pattern {pattern}: {e}")
                    continue
            
            # REMOVED: Sequential ID detection - this was causing the false positives
            # Sequential newspaper page IDs don't mean article continuation
            
            # Final safety limit
            multi_page_images = multi_page_images[:3]  # Maximum 3 additional images
            
            if len(multi_page_images) == 0:
                logger.info("No genuine multi-page article indicators found - treating as single page")
            else:
                logger.info(f"Found {len(multi_page_images)} genuine multi-page indicators")
            
            return multi_page_images
            
        except Exception as e:
            logger.error(f"Error finding multi-page images: {e}")
            return []


def extract_from_newspapers_com(url: str, cookies: str = "", player_name: Optional[str] = None) -> Dict:
    """Legacy function for backward compatibility"""
    extractor = NewspapersComExtractor(auto_auth=False)
    if cookies:
        extractor.cookie_manager.cookies = json.loads(cookies)
        extractor.cookie_manager.session.cookies.update(extractor.cookie_manager.cookies)
    return extractor.extract_from_url(url, player_name)


def main():
    """Main Streamlit interface"""
    st.set_page_config(
        page_title="Newspaper.com Scraper Suite",
        page_icon="📰",
        layout="wide"
    )
    
    st.title("📰 Newspaper.com Scraping Suite")
    st.write("Automatically extract positive sports articles about players")
    
    # Initialize scraper
    if 'scraper' not in st.session_state:
        st.session_state.scraper = NewspapersComExtractor()
        st.session_state.storage = StorageManager()
        st.session_state.initialized = False
    
    # Authentication status
    if not st.session_state.initialized:
        st.info("🔐 Please enter your Newspapers.com login credentials in the sidebar to begin")
        st.stop()
    
    if st.session_state.initialized:
        st.success("✅ Authentication successful! Ready to scrape.")
        
        # Main interface
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🏃 Extract Player Clippings")
            
            player_name = st.text_input(
                "Player Name", 
                placeholder="e.g., Tom Brady, Michael Jordan"
            )
            
            date_range = st.selectbox(
                "Date Range (optional)",
                ["Any", "2020-2025", "2010-2019", "2000-2009", "1990-1999", "1980-1989"]
            )
            
            if st.button("🔍 Extract Clippings", disabled=not player_name):
                with st.spinner(f"Extracting clippings for {player_name}..."):
                    date_filter = None if date_range == "Any" else date_range
                    results = st.session_state.scraper.extract_player_clippings(
                        player_name, date_filter
                    )
                    
                    if results:
                        st.success(f"✅ Found {len(results)} relevant clippings!")
                        
                        # Save results
                        saved_count = 0
                        for result in results:
                            if st.session_state.storage.save_clipping(result):
                                saved_count += 1
                        
                        st.info(f"💾 Saved {saved_count} clippings to storage")
                        
                        # Display results
                        for i, result in enumerate(results):
                            with st.expander(f"Clipping {i+1}: {result.filename}"):
                                col_img, col_meta = st.columns([1, 1])
                                
                                with col_img:
                                    st.image(result.image, caption="Extracted Clipping")
                                
                                with col_meta:
                                    st.write("**Metadata:**")
                                    st.write(f"📰 Source: {result.metadata.newspaper}")
                                    st.write(f"📅 Date: {result.metadata.date}")
                                    st.write(f"😊 Sentiment: {result.metadata.sentiment_score:.2f}")
                                    st.write(f"👤 Mentions: {', '.join(result.metadata.player_mentions)}")
                                    st.write("**Preview:**")
                                    st.write(result.metadata.text_preview)
                    else:
                        st.warning("No relevant clippings found")
            
            # Single URL extraction section
            st.subheader("🎯 Extract from Specific URL")
            
            single_url = st.text_input(
                "Newspapers.com Article URL",
                placeholder="https://www.newspapers.com/image/..."
            )
            
            extract_multi_page = st.checkbox("Extract Multi-Page Articles", value=True)
            
            if st.button("🔍 Extract from URL", disabled=not single_url):
                with st.spinner("Extracting content from URL..."):
                    try:
                        result = st.session_state.scraper.extract_from_url(
                            single_url, 
                            player_name=player_name if player_name else None,
                            extract_multi_page=extract_multi_page
                        )
                        
                        if result['success']:
                            st.success("✅ Successfully extracted content!")
                            
                            # Display basic information
                            col_info, col_img = st.columns([1, 1])
                            
                            with col_info:
                                st.write("**Article Information:**")
                                st.write(f"📰 Headline: {result['headline']}")
                                st.write(f"📅 Date: {result['date']}")
                                st.write(f"📍 Source: {result['source']}")
                                st.write(f"📍 Location: {result['location']}")
                                
                                # Show multi-page info if available
                                if 'multi_page_info' in result:
                                    mp_info = result['multi_page_info']
                                    st.write("**Multi-Page Article:**")
                                    st.write(f"📄 Total pages found: {mp_info['total_pages']}")
                                    st.write(f"📄 Pages with content: {mp_info['pages_with_content']}")
                                    st.write(f"🎯 Selected page: {mp_info['selected_page']}")
                                    
                                    # Show details for each page
                                    if mp_info['all_page_results']:
                                        st.write("**Page Analysis:**")
                                        for page_result in mp_info['all_page_results']:
                                            st.write(f"• Page {page_result['page_number']}: "
                                                   f"Confidence {page_result['confidence']:.1f}%, "
                                                   f"Sports Score {page_result['sports_score']:.2f}")
                            
                            with col_img:
                                st.image(result['image_data'], caption="Extracted Content")
                            
                            # Show extracted text
                            st.write("**Extracted Content:**")
                            st.write(result['content'])
                            
                            # Show full text in expander
                            with st.expander("📖 Full Extracted Text"):
                                st.write(result['full_text'])
                            
                            # Show metadata
                            with st.expander("🔧 Technical Metadata"):
                                st.json(result['metadata'])
                                
                        else:
                            st.error(f"❌ Extraction failed: {result.get('error', 'Unknown error')}")
                            
                    except Exception as e:
                        st.error(f"❌ Extraction error: {str(e)}")
        
        with col2:
            st.subheader("📚 Saved Clippings")
            
            if player_name:
                saved_clippings = st.session_state.storage.load_clippings(player_name)
                
                if saved_clippings:
                    st.write(f"Found {len(saved_clippings)} saved clippings for {player_name}")
                    
                    for clipping in saved_clippings[:3]:  # Show first 3
                        metadata = clipping['metadata']
                        st.write(f"📰 {metadata['title'][:50]}...")
                        st.write(f"📅 {metadata['date']}")
                        st.write("---")
                else:
                    st.info("No saved clippings found")
    
    # Footer
    st.write("---")
    st.write("💡 **Tips:**")
    st.write("• Enter your Newspapers.com login credentials in the sidebar to begin")
    st.write("• The system will automatically handle authentication and session management")
    st.write("• Results are saved locally and can be accessed anytime")


if __name__ == "__main__":
    main()