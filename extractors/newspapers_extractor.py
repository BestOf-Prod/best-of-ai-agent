import streamlit as st
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
        self.driver = None  # Keep driver instance for session reuse
        self.cookies = {}
        self.last_login = None
        self.login_credentials = None
        self.is_replit = 'REPL_ID' in os.environ or 'REPL_SLUG' in os.environ
        self.auth_data = {}  # Store complete authentication data
    
    def set_credentials(self, email: str, password: str):
        """Set login credentials"""
        self.login_credentials = {'email': email, 'password': password}
    
    def setup_enhanced_chrome_options(self):
        from undetected_chromedriver import ChromeOptions
        chrome_options = ChromeOptions()
        
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        if self.is_replit:
            chrome_options.add_argument('--disable-setuid-sandbox')
            chrome_options.add_argument('--single-process')
            chrome_options.add_argument('--no-zygote')
            chrome_options.add_argument('--disable-software-rasterizer')
        
        return chrome_options

    def perform_human_like_login(self, email: str, password: str) -> bool:
        """Perform enhanced human-like login sequence with robust verification"""
        try:
            # Start from main page to establish session context
            logger.info("Loading main page to establish session...")
            self.driver.get('https://www.newspapers.com/')
            time.sleep(random.uniform(2, 4))  # Random delay for human-like behavior
            
            # Navigate to login page directly
            logger.info("Navigating directly to login page...")
            self.driver.get('https://www.newspapers.com/signin/')
            time.sleep(random.uniform(2, 4))
            
            # Wait for login form with multiple strategies
            try:
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
                    self._save_debug_html_simple()
                    return False
                
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
                    self._save_debug_html_simple()
                    return False
                    
                logger.info("Login form fields found successfully")
                
            except Exception as e:
                logger.error(f"Failed to find login form: {str(e)}")
                self._save_debug_html_simple()
                return False
            
            # Clear and fill form fields with human-like behavior
            try:
                email_field.click()
                time.sleep(random.uniform(0.3, 0.7))
                email_field.clear()
                time.sleep(random.uniform(0.3, 0.7))
                
                # Type email slowly
                for char in email:
                    email_field.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.1))
                
                time.sleep(random.uniform(1, 2))
                
                password_field.click()
                time.sleep(random.uniform(0.3, 0.7))
                password_field.clear()
                time.sleep(random.uniform(0.3, 0.7))
                
                # Type password slowly
                for char in password:
                    password_field.send_keys(char)
                    time.sleep(random.uniform(0.05, 0.1))
                
                time.sleep(random.uniform(1.5, 2.5))
                logger.info("Form filled successfully")
                
            except Exception as e:
                logger.error(f"Failed to fill login form: {str(e)}")
                self._save_debug_html_simple()
                return False
            
            # Submit form with multiple strategies
            try:
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
                
                if not submit_clicked:
                    try:
                        password_field.submit()
                        logger.info("Submitted form via password field")
                        submit_clicked = True
                    except:
                        pass
                
                if not submit_clicked:
                    try:
                        password_field.send_keys(Keys.RETURN)
                        logger.info("Pressed Enter in password field")
                        submit_clicked = True
                    except:
                        pass
                
                if not submit_clicked:
                    logger.error("Could not submit login form with any method")
                    self._save_debug_html_simple()
                    return False
                
            except Exception as e:
                logger.error(f"Failed to submit login form: {str(e)}")
                self._save_debug_html_simple()
                return False
            
            # Wait for login to complete with enhanced verification
            try:
                time.sleep(random.uniform(2, 4))
                
                # Check if redirected away from login page
                current_url = self.driver.current_url.lower()
                if "login" in current_url or "signin" in current_url:
                    logger.error("Still on login page after submission")
                    self._save_debug_html_simple()
                    return False
                
                # Verify premium access by checking a known premium page
                logger.info("Verifying premium access...")
                test_premium_url = "https://www.newspapers.com/image/635076099/"
                self.driver.get(test_premium_url)
                time.sleep(random.uniform(3, 5))
                
                paywall_indicators = [
                    'you need a subscription',
                    'start a 7-day free trial', 
                    'subscribe to view',
                    'sign in to view this page',
                    'subscription required'
                ]
                
                page_content = self.driver.page_source.lower()
                if any(indicator in page_content for indicator in paywall_indicators):
                    logger.error("Premium access not granted - paywall detected")
                    self._save_debug_html_simple()
                    return False
                
                # Check for premium content indicators
                premium_indicators = ['image-viewer', 'newspaper-image', 'clip', 'print', 'download']
                if not any(indicator in page_content for indicator in premium_indicators):
                    logger.error("Premium content not found on test page")
                    self._save_debug_html_simple()
                    return False
                
                logger.info("Premium access verified successfully")
                
                # After verifying premium access
                logger.info("Capturing additional JavaScript tokens...")
                try:
                    js_tokens = self.driver.execute_script("""
                        return {
                            'ncom': window.ncom || {},
                            'page': window.page || {},
                            'csrf': document.querySelector('meta[name="csrf-token"]')?.content || null
                        };
                    """)
                    self.auth_data['js_tokens'] = js_tokens
                    logger.debug(f"Captured JS tokens: {js_tokens}")
                except Exception as e:
                    logger.warning(f"Failed to capture JS tokens: {e}")
                
            except Exception as e:
                logger.error(f"Error verifying login status: {str(e)}")
                self._save_debug_html_simple()
                return False
            
            # Additional wait for session setup
            time.sleep(random.uniform(3, 5))
            
            # Verify user authentication
            try:
                user_data = self.driver.execute_script("return window.ncom ? window.ncom.user : null;")
                if user_data and user_data != 'null' and user_data != 0:
                    logger.info(f"Successfully authenticated as user: {user_data}")
                    return True
                else:
                    logger.warning(f"User data not found: {user_data}")
                    return True  # Proceed anyway, as premium access was verified
                
            except Exception as e:
                logger.warning(f"Could not verify user authentication: {str(e)}")
                return True
                
        except Exception as e:
            logger.error(f"Enhanced login sequence failed: {str(e)}")
            self._save_debug_html_simple()
            return False

    def extract_complete_authentication_data(self):
        auth_data = {}
        
        try:
            auth_data['cookies'] = self.driver.get_cookies()
            auth_data['ncom'] = self.driver.execute_script("return window.ncom || {};")
            auth_data['page'] = self.driver.execute_script("return window.page || {};")
            
            auth_data['localStorage'] = self.driver.execute_script("""
                var ls = {};
                for (var i = 0; i < localStorage.length; i++) {
                    var key = localStorage.key(i);
                    ls[key] = localStorage.getItem(key);
                }
                return ls;
            """)
            
            auth_data['sessionStorage'] = self.driver.execute_script("""
                var ss = {};
                for (var i = 0; i < sessionStorage.length; i++) {
                    var key = sessionStorage.key(i);
                    ss[key] = sessionStorage.getItem(key);
                }
                return ss;
            """)
            
            # Capture additional tokens
            auth_data['js_tokens'] = self.driver.execute_script("""
                return {
                    'csrf': document.querySelector('meta[name="csrf-token"]')?.content || null,
                    'session_id': window.sessionId || null,
                    'auth_token': window.authToken || null
                };
            """)
            
            auth_data['timestamp'] = datetime.now().isoformat()
            
            # Log for debugging
            logger.debug(f"Auth data: cookies={len(auth_data['cookies'])}, "
                        f"localStorage={auth_data['localStorage']}, "
                        f"sessionStorage={auth_data['sessionStorage']}, "
                        f"js_tokens={auth_data['js_tokens']}")
            
            return auth_data
            
        except Exception as e:
            logger.error(f"Error extracting authentication data: {str(e)}")
            return {}

    def login(self) -> bool:
        if not self.login_credentials:
            logger.error("No login credentials set")
            return False
            
        try:
            if not self.driver:
                from undetected_chromedriver import Chrome
                chrome_options = self.setup_enhanced_chrome_options()
                
                logger.info("Initializing Chrome with enhanced options...")
                if self.is_replit:
                    from selenium.webdriver.chrome.service import Service
                    service = Service('/nix/store/3qnxr5x6gw3k9a9i7d0akz0m6bksbwff-chromedriver-125.0.6422.141/bin/chromedriver')
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    self.driver = Chrome(options=chrome_options)
                logger.info("Chrome initialization successful")
                self.driver.set_page_load_timeout(30)
            
            login_success = self.perform_human_like_login(
                self.login_credentials['email'], 
                self.login_credentials['password']
            )
            
            if login_success:
                self.auth_data = self.extract_complete_authentication_data()
                self.cookies = {cookie['name']: cookie['value'] for cookie in self.auth_data.get('cookies', [])}
                
                if self.cookies:
                    logger.info(f"Extracted {len(self.cookies)} cookies")
                    self.last_login = datetime.now()
                    
                    try:
                        with open('enhanced_auth_data.json', 'w') as f:
                            json.dump(self.auth_data, f, indent=2, default=str)
                        logger.info("Saved enhanced authentication data")
                    except Exception as e:
                        logger.warning(f"Could not save auth data: {e}")
                    
                    return True
                else:
                    logger.error("No cookies extracted after login")
                    return False
            else:
                logger.error("Login sequence failed")
                return False
                
        except Exception as e:
            logger.error(f"Login failed: {str(e)}")
            return False
            
    def cleanup(self):
        """Clean up Selenium driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    def refresh_if_needed(self) -> bool:
        """Check if session needs refreshing"""
        if not self.last_login or (datetime.now() - self.last_login > timedelta(hours=6)):
            logger.info("Session expired or not initialized, refreshing login...")
            return self.login()
        return True
    
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

class EnhancedAutoCookieManager:
    """Enhanced cookie manager with improved authentication"""
    
    def __init__(self):
        self.cookies = {}
        self.session = requests.Session()
        self.last_extraction = None
        self.selenium_login = EnhancedSeleniumLoginManager()
        self.auth_headers = {}  # Store additional headers from storage
        
    def set_login_credentials(self, email: str, password: str):
        """Set login credentials for Selenium authentication"""
        self.selenium_login.set_credentials(email, password)
        
    def auto_extract_cookies(self, domain: str = "newspapers.com") -> bool:
        try:
            if self.selenium_login.login():
                self.cookies = self.selenium_login.cookies
                self.last_extraction = datetime.now()

                self.session.cookies.clear()
                auth_data = self.selenium_login.auth_data
                
                # Log auth data for debugging
                logger.debug(f"Captured auth data: cookies={len(auth_data.get('cookies', []))}, "
                            f"localStorage={auth_data.get('localStorage', {})}, "
                            f"sessionStorage={auth_data.get('sessionStorage', {})}")
                
                # Set cookies
                for cookie in auth_data.get('cookies', []):
                    try:
                        self.session.cookies.set(
                            cookie['name'],
                            cookie['value'],
                            domain=cookie.get('domain', '.newspapers.com'),
                            path=cookie.get('path', '/'),
                            secure=cookie.get('secure', False)
                        )
                    except Exception as e:
                        logger.warning(f"Failed to set cookie {cookie['name']}: {e}")

                # Use localStorage and sessionStorage for headers
                for storage in [auth_data.get('localStorage', {}), auth_data.get('sessionStorage', {})]:
                    for key, value in storage.items():
                        self.auth_headers[f'X-{key}'] = value
                
                logger.info(f"Session cookies: {len(self.session.cookies.get_dict())}")
                
                try:
                    with open('enhanced_auth_data.json', 'w') as f:
                        json.dump(auth_data, f, indent=2, default=str)
                    logger.info("Saved enhanced authentication data")
                except Exception as e:
                    logger.warning(f"Could not save auth data: {e}")

                st.success("✅ Successfully logged in with enhanced authentication")
                return True

            logger.warning("Selenium login failed, falling back to browser cookies")
            return self._extract_browser_cookies(domain)

        except Exception as e:
            logger.error(f"Cookie extraction failed: {str(e)}")
            return self._extract_browser_cookies(domain)
    
    def _extract_browser_cookies(self, domain: str) -> bool:
        """Fallback to extract cookies from browser"""
        try:
            cookies = browser_cookie3.chrome(domain_name=domain)
            self.cookies = {cookie.name: cookie.value for cookie in cookies}
            self.session.cookies.clear()
            for name, value in self.cookies.items():
                self.session.cookies.set(name, value)
            self.last_extraction = datetime.now()
            st.success(f"✅ Extracted {len(self.cookies)} cookies from browser")
            return True
        except Exception as e:
            logger.error(f"Browser cookie extraction failed: {e}")
            st.error("❌ Could not extract cookies from browser")
            return False
    
    def test_authentication(self, test_url: str = "https://www.newspapers.com/") -> bool:
        """Test authentication with robust checks"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                **self.auth_headers
            }

            self.session.cookies.clear()
            for name, value in self.cookies.items():
                self.session.cookies.set(name, value)

            logger.info(f"Testing authentication with {len(self.cookies)} cookies")
            response = self.session.get(test_url, headers=headers, timeout=15)

            if response.status_code == 200:
                content = response.text.lower()
                
                auth_checks = {
                    'has_logout': 'logout' in content,
                    'has_account': 'account' in content or 'profile' in content,
                    'has_subscription': 'subscription' in content or 'premium' in content,
                    'not_login_page': 'sign-in' not in response.url and 'login' not in response.url,
                    'no_login_form': 'id="email"' not in content or 'signin' not in content
                }
                
                user_id = None
                user_id_patterns = [
                    r'"user":(\d+)',
                    r'"userID":"(\d+)"',
                    r'"userId":(\d+)',
                    r'user_id["\']:\s*["\']?(\d+)'
                ]
                
                for pattern in user_id_patterns:
                    match = re.search(pattern, content)
                    if match and match.group(1) != '0' and match.group(1) != 'null':
                        user_id = match.group(1)
                        break
                
                auth_checks['has_user_id'] = user_id is not None
                positive_indicators = sum(1 for check, result in auth_checks.items() if result)
                
                logger.info(f"Authentication check results: {auth_checks}")
                logger.info(f"Positive indicators: {positive_indicators}/6")
                
                if positive_indicators >= 4:
                    st.success("🔓 Authentication verified - Premium access detected")
                    return True
                elif positive_indicators >= 2:
                    st.warning("⚠️ Partial authentication detected")
                    return True
                else:
                    st.error("❌ Authentication verification failed")
                    return False
            else:
                st.error(f"❌ Authentication failed - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            st.error(f"❌ Authentication test failed: {str(e)}")
            return False
    
    def test_premium_access(self, test_url: str = "https://www.newspapers.com/image/635076099/") -> bool:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.newspapers.com/',
                **self.auth_headers
            }

            response = self.session.get(test_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                content = response.text.lower()
                
                paywall_indicators = [
                    'you need a subscription',
                    'start a 7-day free trial', 
                    'subscribe to view',
                    'sign in to view this page',
                    'subscription required',
                    'publisher extra'
                ]
                
                has_paywall = any(indicator in content for indicator in paywall_indicators)
                
                # Stricter content check
                required_indicators = [
                    '"imageid":635076099',  # Confirm article ID
                    'wfmimagepath'  # Confirm image metadata
                ]
                
                has_content = all(indicator in content for indicator in required_indicators)
                
                if not has_paywall and has_content:
                    logger.info("Premium page access confirmed with article content")
                    return True
                elif has_paywall:
                    logger.warning(f"Premium page shows paywall: {paywall_indicators}")
                    return False
                else:
                    logger.warning("Premium page lacks required article content")
                    return False
                    
            else:
                logger.error(f"Premium page returned HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Premium access test failed: {str(e)}")
            return False
    
    def refresh_cookies_if_needed(self) -> bool:
        """Refresh cookies if needed"""
        if not self.last_extraction or (datetime.now() - self.last_extraction > timedelta(hours=6)):
            st.info("🔄 Refreshing cookies")
            return self.auto_extract_cookies()
        
        if not self.test_authentication() or not self.test_premium_access():
            st.info("🔄 Refreshing expired cookies")
            return self.auto_extract_cookies()
        
        return True

    def cleanup(self):
        """Clean up resources"""
        self.selenium_login.cleanup()

class NewspaperImageProcessor:
    """Advanced image processing for newspaper clippings"""
    
    def __init__(self):
        self.min_article_area = 30000
        self.text_confidence_threshold = 30
    
    def enhance_image_quality(self, image: Image.Image) -> Image.Image:
        """Enhance image quality for better OCR"""
        if image.mode != 'L':
            image = image.convert('L')
        
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.5)
        
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        img_array = np.array(image)
        denoised = cv2.fastNlMeansDenoising(img_array)
        binary = cv2.adaptiveThreshold(
            denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        )
        
        return Image.fromarray(binary)
    
    def detect_article_regions(self, image: Image.Image) -> List[Tuple[int, int, int, int]]:
        """Detect individual article regions in newspaper page"""
        logger.info(f"Detecting article regions in image of size: {image.size}")
        
        img_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        morphed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(
            morphed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        logger.info(f"Found {len(contours)} total contours")
        
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
            logger.info("Few regions found, trying grid approach")
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
            
            logger.info(f"Generated {len(grid_regions)} grid regions")
            article_regions.extend(grid_regions)
        
        article_regions.sort(key=lambda r: r[2] * r[3], reverse=True)
        final_regions = article_regions[:20]
        
        logger.info(f"Returning {len(final_regions)} article regions")
        return final_regions
    
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
            
            result_queue = queue.Queue()
            exception_queue = queue.Queue()
            
            def ocr_worker():
                try:
                    data = pytesseract.image_to_data(
                        enhanced, 
                        output_type=pytesseract.Output.DICT,
                        config='--psm 6'
                    )
                    result_queue.put(data)
                except Exception as e:
                    exception_queue.put(e)
            
            ocr_thread = threading.Thread(target=ocr_worker)
            ocr_thread.daemon = True
            ocr_thread.start()
            ocr_thread.join(timeout=15.0)
            
            if ocr_thread.is_alive():
                logger.warning(f"OCR timed out for region {region}")
                return "", 0.0
            
            if not exception_queue.empty():
                ocr_exception = exception_queue.get()
                logger.error(f"OCR error: {ocr_exception}")
                return "", 0.0
            
            if result_queue.empty():
                logger.error("OCR completed but no result")
                return "", 0.0
            
            data = result_queue.get()
            confidences = [int(conf) for conf in data['conf'] if int(conf) > self.text_confidence_threshold]
            words = [word for word, conf in zip(data['text'], data['conf']) if int(conf) > self.text_confidence_threshold]
            
            logger.debug(f"Found {len(words)} words above confidence threshold")
            if not words:
                logger.debug("No words found above confidence threshold")
                return "", 0.0
            
            text = ' '.join(words)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            
            logger.debug(f"Extracted text preview: '{text[:100]}...' with confidence {avg_confidence:.1f}")
            return text.strip(), avg_confidence
            
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
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
        """Determine if text is sports-related"""
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
        """Check for player name mentions"""
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
            first_last_initial = f"{name_parts[0]} {name_parts[-1][0]}"
            if first_last_initial in text_lower:
                mentions.append(first_last_initial)
        
        return len(mentions) > 0, mentions
    
    def analyze_sentiment(self, text: str, player_name: str) -> Tuple[float, str]:
        """Analyze sentiment of article"""
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

class StorageManager:
    """Manage storage and retrieval of clipping results"""
    
    def __init__(self, storage_dir: str = "clippings"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        logger.info(f"Initialized storage manager with directory: {storage_dir}")
    
    def save_clipping(self, result: ClippingResult) -> bool:
        """Save a clipping result to storage"""
        try:
            player_dir = os.path.join(self.storage_dir, result.filename.split('_')[0])
            os.makedirs(player_dir, exist_ok=True)
            
            image_path = os.path.join(player_dir, f"{result.filename}.png")
            result.image.save(image_path)
            
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
                    
                    image_filename = filename.replace('_metadata.json', '.png')
                    image_path = os.path.join(player_dir, image_filename)
                    if os.path.exists(image_path):
                        metadata['image_path'] = image_path
                    
                    clippings.append({'metadata': metadata})
            
            clippings.sort(key=lambda x: x['metadata'].get('date', ''), reverse=True)
            logger.info(f"Loaded {len(clippings)} clippings for {player_name}")
            return clippings
            
        except Exception as e:
            logger.error(f"Failed to load clippings for {player_name}: {e}")
            return []

class NewspapersComExtractor:
    """Main scraper class"""
    
    def __init__(self, auto_auth: bool = True):
        self.cookie_manager = EnhancedAutoCookieManager()
        self.image_processor = NewspaperImageProcessor()
        self.content_analyzer = ContentAnalyzer()
        self.results = []
        self.auto_auth = auto_auth
        
    def initialize(self, email: str = None, password: str = None) -> bool:
        """Initialize the scraper"""
        st.info("🔍 Setting up Newspapers.com authentication...")
        
        if email and password:
            self.cookie_manager.set_login_credentials(email, password)
        
        if not self.cookie_manager.auto_extract_cookies():
            st.error("Failed to authenticate. Please check your credentials or browser login.")
            return False
        
        if not self.cookie_manager.test_premium_access():
            st.error("Premium access not detected. Please ensure your account has premium access.")
            return False
        
        return self.cookie_manager.test_authentication()
    
    def get_authentication_status(self) -> Dict:
        """Get authentication status"""
        return {
            'initialized': bool(self.cookie_manager.cookies),
            'authenticated': self.cookie_manager.test_authentication(),
            'premium_access': self.cookie_manager.test_premium_access(),
            'cookies_count': len(self.cookie_manager.cookies),
            'last_extraction': self.cookie_manager.last_extraction
        }
    
    def search_articles(self, query: str, date_range: Optional[str] = None, limit: int = 20) -> List[Dict]:
        """Search for articles"""
        logger.info(f"Starting search for query: '{query}'")
        try:
            if not self.cookie_manager.refresh_cookies_if_needed():
                logger.error("Failed to refresh authentication cookies")
                return []
            
            encoded_query = query.replace(' ', '%20').replace('"', '%22')
            search_url = f"https://www.newspapers.com/search/"
            params = {'query': query, 'sort': 'relevance'}
            
            if date_range and date_range != "Any":
                if '-' in date_range:
                    start_year, end_year = date_range.split('-')
                    params['dr_year'] = f"{start_year}-01-01|{end_year}-12-31"
                    logger.info(f"Applied date filter: {params['dr_year']}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://www.newspapers.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                **self.cookie_manager.auth_headers
            }
            
            response = self.cookie_manager.session.get(
                search_url, 
                params=params,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Search request failed: HTTP {response.status_code}")
                return []
            
            articles = self._parse_search_results(response.text, limit)
            logger.info(f"Parsed {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
    
    def _parse_search_results(self, html_content: str, limit: int) -> List[Dict]:
        """Parse search results"""
        logger.info("Parsing search results...")
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
                    logger.info(f"Found {len(result_elements)} results using selector '{selector}'")
                    results_found = True
                    
                    for i, element in enumerate(result_elements[:limit]):
                        try:
                            article = self._extract_article_from_element(element, i)
                            if article:
                                articles.append(article)
                        except Exception as e:
                            logger.warning(f"Failed to extract article {i+1}: {e}")
                    break
            
            if not results_found:
                logger.warning("No search results found")
                article_links = soup.find_all('a', href=True)
                for i, link in enumerate(article_links[:limit]):
                    href = link.get('href', '')
                    if '/image/' in href or '/clip/' in href:
                        title = link.get_text(strip=True) or f"Article {i+1}"
                        full_url = f"https://www.newspapers.com{href}" if href.startswith('/') else href
                        article = {
                            'title': title,
                            'url': full_url,
                            'date': 'Unknown',
                            'newspaper': 'Unknown',
                            'preview': title
                        }
                        articles.append(article)
            
            logger.info(f"Parsed {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error parsing search results: {e}")
            return []
    
    def _extract_article_from_element(self, element, index: int) -> Optional[Dict]:
        """Extract article data from search result element"""
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
                url = f"https://www.newspapers.com{href}" if href.startswith('/') else href
            
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
            logger.error(f"Error extracting article data: {e}")
            return None
    
    def extract_from_url(self, url: str, player_name: Optional[str] = None, extract_multi_page: bool = True) -> Dict:
        max_retries = 2
        for attempt in range(max_retries):
            try:
                if not self.cookie_manager.refresh_cookies_if_needed():
                    logger.error("Failed to refresh authentication cookies")
                    return {'success': False, 'error': "Authentication failed"}
                
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
                    **self.cookie_manager.auth_headers
                }
                
                try:
                    response = self.cookie_manager.session.get(url, headers=headers, timeout=30)
                    if response.status_code == 200:
                        logger.info("Fetched page using requests session")
                        response_text = response.text
                    else:
                        logger.warning(f"Requests session hit paywall or redirect on attempt {attempt+1}")
                        response_text = self._fetch_with_selenium(url)
                        if not response_text:
                            if attempt < max_retries - 1:
                                logger.info("Retrying after Selenium failure...")
                                self.cookie_manager.auto_extract_cookies()  # Force refresh
                                continue
                            return {'success': False, 'error': "Failed to fetch article with Selenium"}
                except Exception as e:
                    logger.warning(f"Requests session failed on attempt {attempt+1}: {e}")
                    response_text = self._fetch_with_selenium(url)
                    if not response_text:
                        if attempt < max_retries - 1:
                            logger.info("Retrying after Selenium failure...")
                            self.cookie_manager.auto_extract_cookies()
                            continue
                        return {'success': False, 'error': f"Failed to fetch article: {e}"}
                
                # Extract metadata from the response
                metadata = self._extract_image_metadata(response_text)
                metadata['url'] = url
                if not metadata:
                    logger.error("Failed to extract article metadata")
                    return {'success': False, 'error': "Failed to extract article metadata"}
                
                # Download the newspaper image
                image = self._download_newspaper_image(metadata)
                if not image:
                    logger.error("Failed to download article image")
                    return {'success': False, 'error': "Failed to download article image"}
                
                # Process the image to find article regions
                article_regions = self.image_processor.detect_article_regions(image)
                if not article_regions:
                    logger.error("No article regions found in image")
                    return {'success': False, 'error': "No article regions found in image"}
                
                # Extract text from the first (largest) region
                text, confidence = self.image_processor.extract_text_with_confidence(image, article_regions[0])
                
                # Analyze content if player name is provided
                sentiment_score = 0.0
                player_mentions = []
                if player_name:
                    is_relevant, analysis = self.content_analyzer.is_relevant_article(text, player_name)
                    if is_relevant:
                        sentiment_score = analysis.get('sentiment_score', 0.0)
                        player_mentions = analysis.get('player_mentions', [])
                
                # Return the complete article data
                return {
                    'success': True,
                    'headline': metadata.get('title', 'Unknown Title'),
                    'source': metadata.get('publication_title', 'Unknown Source'),
                    'date': metadata.get('date', 'Unknown Date'),
                    'image_data': image,
                    'content': text,
                    'metadata': {
                        'sentiment_score': sentiment_score,
                        'player_mentions': player_mentions,
                        'confidence': confidence,
                        'location': metadata.get('location', 'Unknown Location'),
                        'image_id': metadata.get('image_id'),
                        'url': url
                    }
                }
                
            except Exception as e:
                logger.error(f"Error processing article page on attempt {attempt+1}: {e}")
                if attempt < max_retries - 1:
                    logger.info("Retrying after error...")
                    self.cookie_manager.auto_extract_cookies()
                    continue
                return {'success': False, 'error': str(e)}
        return {'success': False, 'error': "Max retries exceeded"}
    
    def _fetch_with_selenium(self, url: str) -> Optional[str]:
        logger.info(f"Fetching {url} with Selenium...")
        try:
            driver = self.cookie_manager.selenium_login.driver
            
            # Apply cookies and storage
            driver.get('https://www.newspapers.com/')
            for name, value in self.cookie_manager.cookies.items():
                try:
                    driver.add_cookie({'name': name, 'value': value, 'domain': '.newspapers.com'})
                except Exception as e:
                    logger.debug(f"Could not add cookie {name}: {e}")
            
            # Apply localStorage and sessionStorage
            auth_data = self.cookie_manager.selenium_login.auth_data
            driver.execute_script("""
                arguments[0].forEach(([key, value]) => localStorage.setItem(key, value));
                arguments[1].forEach(([key, value]) => sessionStorage.setItem(key, value));
            """, list(auth_data.get('localStorage', {}).items()), list(auth_data.get('sessionStorage', {}).items()))
            
            driver.get(url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(5)
            
            paywall_indicators = [
                'you need a subscription',
                'start a 7-day free trial',
                'sign in to view this page',
                'already have an account',
                'paywall',
                'please sign in',
                'log in to view',
                'publisher extra'
            ]
            
            page_source = driver.page_source
            if any(ind in page_source.lower() for ind in paywall_indicators):
                logger.error(f"Paywall detected: {paywall_indicators}")
                self._save_debug_html(driver, url)
                return None
            
            logger.info("Successfully fetched page with Selenium")
            return page_source
            
        except Exception as e:
            logger.error(f"Selenium fetch failed: {e}")
            return None
    
    def _extract_image_metadata(self, page_content: str) -> Optional[Dict]:
        """Extract image metadata"""
        logger.info("Parsing HTML for image metadata...")
        try:
            image_data = {}
            
            # First try to find the image data in the page's JavaScript
            image_data_patterns = [
                r'"image":\s*\{[^}]*"imageId":\s*(\d+)',
                r'"imageId":\s*(\d+)',
                r'data-image-id="(\d+)"',
                r'data-imageid="(\d+)"'
            ]
            
            for pattern in image_data_patterns:
                if match := re.search(pattern, page_content):
                    image_data['image_id'] = int(match.group(1))
                    logger.info(f"Found image ID: {image_data['image_id']}")
                    break
            
            # Extract other metadata using more robust patterns
            metadata_patterns = {
                'date': r'"date":\s*"([^"]+)"',
                'publication_title': r'"publicationTitle":\s*"([^"]+)"',
                'location': r'"location":\s*"([^"]+)"',
                'title': r'"title":\s*"([^"]+)"',
                'width': r'"width":\s*(\d+)',
                'height': r'"height":\s*(\d+)',
                'wfm_image_path': r'"wfmImagePath":\s*"([^"]+)"'
            }
            
            for key, pattern in metadata_patterns.items():
                if match := re.search(pattern, page_content):
                    value = match.group(1)
                    if key in ['width', 'height']:
                        value = int(value)
                    image_data[key] = value
                    logger.debug(f"Found {key}: {value}")
            
            # Try to find the base image URL
            base_url_patterns = [
                r'"image":"([^"]+)"',
                r'data-image-url="([^"]+)"',
                r'data-src="([^"]+)"'
            ]
            
            for pattern in base_url_patterns:
                if match := re.search(pattern, page_content):
                    image_data['base_image_url'] = match.group(1)
                    logger.debug(f"Found base image URL: {image_data['base_image_url']}")
                    break
            
            if 'base_image_url' not in image_data:
                image_data['base_image_url'] = 'https://img.newspapers.com'
            
            # Extract canonical URL
            url_patterns = [
                r'<link\s+rel="canonical"\s+href="([^"]+)"',
                r'<meta\s+property="og:url"\s+content="([^"]+)"',
                r'data-canonical-url="([^"]+)"'
            ]
            
            for pattern in url_patterns:
                if match := re.search(pattern, page_content):
                    image_data['url'] = match.group(1)
                    logger.debug(f"Found canonical URL: {image_data['url']}")
                    break
            
            # Validate required fields
            required_fields = ['image_id', 'title', 'date', 'publication_title']
            missing_fields = [field for field in required_fields if field not in image_data]
            
            if missing_fields:
                logger.warning(f"Missing required fields: {missing_fields}")
                # Try to extract missing fields from HTML elements as fallback
                soup = BeautifulSoup(page_content, 'html.parser')
                
                if 'title' in missing_fields:
                    title_elem = soup.find('h1') or soup.find(class_='headline')
                    if title_elem:
                        image_data['title'] = title_elem.get_text(strip=True)
                
                if 'date' in missing_fields:
                    date_elem = soup.find(class_='date') or soup.find(class_='published')
                    if date_elem:
                        image_data['date'] = date_elem.get_text(strip=True)
                
                if 'publication_title' in missing_fields:
                    pub_elem = soup.find(class_='newspaper') or soup.find(class_='publication')
                    if pub_elem:
                        image_data['publication_title'] = pub_elem.get_text(strip=True)
            
            # Final validation
            if not all(field in image_data for field in required_fields):
                logger.error("Missing required metadata fields after fallback")
                return None
            
            logger.info(f"Successfully extracted image metadata: {image_data}")
            return image_data
            
        except Exception as e:
            logger.error(f"Error parsing image metadata: {e}")
            return None
    
    def _download_newspaper_image(self, metadata: Dict) -> Optional[Image.Image]:
        """Download newspaper image"""
        logger.info("Downloading newspaper image...")
        
        try:
            possible_urls = self._get_possible_image_urls(metadata)
            if possible_urls:
                limited_urls = possible_urls[:5]  # Reduced to 5 for speed
                headers = {
                    'User-Agent': 'Mozilla/5.0',
                    'Accept': 'image/webp,image/jpeg,*/*;q=0.8',
                    'Referer': 'https://www.newspapers.com/',
                    **self.cookie_manager.auth_headers
                }
                
                try:
                    self.cookie_manager.session.get('https://www.newspapers.com/', headers=headers, timeout=10)
                except Exception as e:
                    logger.debug(f"Failed to access main site: {e}")
                
                for i, image_url in enumerate(limited_urls):
                    logger.info(f"Trying URL {i+1}/{len(limited_urls)}: {image_url}")
                    try:
                        response = self.cookie_manager.session.get(
                            image_url, 
                            headers=headers,
                            timeout=15,
                            allow_redirects=True
                        )
                        if response.status_code == 200 and 'image' in response.headers.get('content-type', '').lower():
                            image = Image.open(io.BytesIO(response.content))
                            if image.size[0] > 1000 and image.size[1] > 1000:
                                logger.info(f"High-quality image downloaded: {image.size()} from {i+1}")
                                return image
                            else:
                                logger.info("Low quality image found, continuing...")
                        else:
                            logger.debug(f"URL {i+1} failed: HTTP {response.status_code}")
                    except Exception as e:
                        logger.debug(f"Error trying URL {i+1}: {e}")
                        continue
                
                logger.info("Direct URL download failed, falling back to Selenium")
                return self._extract_with_selenium_high_quality_image(metadata)
                
        except Exception as e:
            logger.error(f"Error downloading image: {e}")
            return None
    
    def _extract_with_selenium_high_quality_image(self, metadata: Dict) -> Optional[Image.Image]:
        """Extract high-quality image with Selenium"""
        logger.info("Starting Selenium image extraction...")
        original_url = metadata.get('url')
        if not original_url:
            logger.error("No URL available for Selenium extraction")
            return None
        
        try:
            if not self.cookie_manager.selenium_login.driver:
                if not self.cookie_manager.selenium_login.login():
                    logger.error("Failed to authenticate for Selenium extraction")
                    return None
            
            driver = self.cookie_manager.selenium_login.driver
            driver.get('https://www.newspapers.com/')
            
            for name, value in self.cookie_manager.cookies.items():
                try:
                    driver.add_cookie({'name': name, 'value': value, 'domain': '.newspapers.com'})
                except Exception as e:
                    logger.debug(f"Could not add cookie {name}: {e}")
            
            driver.get(original_url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body'))
            )
            time.sleep(5)
            
            high_quality_selectors = [
                'img[src*="img.newspapers.com"][src*="quality=100"]',
                'img[src*="img.newspapers.com"][src*="size=full"]',
                'img[src*="img.newspapers.com"][src*="w=4000"]',
                'img[src*="img.newspapers.com"][src*="w=2000"]',
                'img[src*="img.newspapers.com"]',
                'img[src*="newspapers.com/img"]',
                '.newspaper-image img',
                '.image-viewer img',
                'img[class*="newspaper"]',
                'canvas'
            ]
            
            best_image_element = None
            best_quality_score = 0
            
            for selector in high_quality_selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    try:
                        width = element.get_attribute('width') or driver.execute_script("return arguments[0].naturalWidth;", element)
                        height = element.get_attribute('height') or driver.execute_script("return arguments[0].naturalHeight;", element)
                        src = element.get_attribute('src') or ''
                        
                        if width and height:
                            width, height = int(width), int(height)
                            quality_score = width * height
                            
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
                                logger.info(f"Better quality image: {width}x{height}, score: {quality_score}")
                                    
                    except Exception as e:
                        logger.debug(f"Error evaluating image element: {e}")
                            
            if best_image_element:
                try:
                    img_src = best_image_element.get_attribute('src')
                    if img_src and img_src.startswith('http'):
                        high_quality_urls = [img_src]
                        if '?' in img_src:
                            base_url = img_src.split('?')[0]
                            high_quality_urls.extend([
                                f"{base_url}?quality=100&w=4000",
                                f"{base_url}?size=full&quality=100",
                                f"{base_url}?w=6000&q=100",
                                f"{base_url}?w=4000&q=100",
                                img_src
                            ])
                        
                        for url in high_quality_urls:
                            try:
                                response = self.cookie_manager.session.get(url, timeout=30)
                                if response.status_code == 200 and 'image' in response.headers.get('content-type', ''):
                                    image = Image.open(io.BytesIO(response.content))
                                    logger.info(f"Downloaded high-quality image: {image.size}")
                                    return image
                            except Exception as e:
                                logger.debug(f"Failed to download {url}: {e}")
                        
                except Exception as e:
                    logger.debug(f"Failed to download via src: {e}")
                
                try:
                    logger.info("Taking screenshot of image element...")
                    driver.execute_script("arguments[0].scrollIntoView(true);", best_image_element)
                    time.sleep(1)
                    screenshot_data = best_image_element.screenshot_as_png
                    image = Image.open(io.BytesIO(screenshot_data))
                    logger.info(f"Element screenshot: {image.size}")
                    return image
                except Exception as e:
                    logger.debug(f"Failed to screenshot element: {e}")
            
            logger.info("Taking full page screenshot...")
            driver.execute_script("document.body.style.zoom='200%'")
            time.sleep(2)
            screenshot_data = driver.get_screenshot_as_png()
            full_screenshot = Image.open(io.BytesIO(screenshot_data))
            logger.info(f"Full page screenshot: {full_screenshot.size}")
            return full_screenshot
            
        except Exception as e:
            logger.error(f"Selenium extraction failed: {e}")
            return None
    
    def _save_debug_html(self, driver, url: str) -> None:
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
            
            logger.info(f"Saved debug HTML to: {filepath}")
            
            summary_filename = f"debug_summary_{timestamp}_{url_hash}.json"
            summary_filepath = os.path.join(debug_dir, summary_filename)
            
            # Capture client-side state
            try:
                local_storage = driver.execute_script("""
                    var ls = {};
                    for (var i = 0; i < localStorage.length; i++) {
                        ls[localStorage.key(i)] = localStorage.getItem(localStorage.key(i));
                    }
                    return ls;
                """)
                session_storage = driver.execute_script("""
                    var ss = {};
                    for (var i = 0; i < sessionStorage.length; i++) {
                        ss[sessionStorage.key(i)] = sessionStorage.getItem(sessionStorage.key(i));
                    }
                    return ss;
                """)
                js_tokens = driver.execute_script("""
                    return {
                        'ncom': window.ncom || {},
                        'page': window.page || {},
                        'csrf': document.querySelector('meta[name="csrf-token"]')?.content || null
                    };
                """)
            except Exception as e:
                logger.warning(f"Failed to capture client-side state: {e}")
                local_storage, session_storage, js_tokens = {}, {}, {}
            
            summary_data = {
                'url': url,
                'timestamp': datetime.now().isoformat(),
                'html_file': filename,
                'page_title': driver.title,
                'cookies_count': len(self.cookie_manager.cookies),
                'cookies': list(self.cookie_manager.cookies.keys()),
                'local_storage': local_storage,
                'session_storage': session_storage,
                'js_tokens': js_tokens,
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
                json.dump(summary_data, f, indent=2, default=str)
            
            logger.info(f"Saved debug summary to: {summary_filepath}")
            
        except Exception as e:
            logger.error(f"Failed to save debug HTML: {e}")
        
    def capture_page_html(self, url: str, save_debug: bool = True) -> Dict:
        """Capture HTML content"""
        logger.info(f"Capturing HTML from: {url}")
        try:
            if not self.cookie_manager.refresh_cookies_if_needed():
                return {'success': False, 'error': "Authentication failed"}
            
            if not self.cookie_manager.selenium_login.driver:
                if not self.cookie_manager.selenium_login.login():
                    return {'success': False, 'error': "Failed to authenticate"}
            
            driver = self.cookie_manager.selenium_login.driver
            driver.get('https://www.newspapers.com/')
            
            for name, value in self.cookie_manager.cookies.items():
                try:
                    driver.add_cookie({'name': name, 'value': value, 'domain': '.newspapers.com'})
                except Exception as e:
                    logger.debug(f"Could not add cookie {name}: {e}")
            
            driver.get(url)
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)
            
            page_html = driver.page_source
            page_title = driver.title
            
            if save_debug:
                self._save_debug_html(driver, url)
            
            elements_info = {
                'images': len(driver.find_elements(By.TAG_NAME, 'img')),
                'scripts': len(driver.find_elements(By.TAG_NAME, 'script')),
                'divs': len(driver.find_elements(By.TAG_NAME, 'div')),
                'forms': len(driver.find_elements(By.TAG_NAME, 'form')),
                'links': len(driver.find_elements(By.TAG_NAME, 'a')),
                'total_elements': len(driver.find_elements(By.XPATH, '//*'))
            }
            
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
            logger.error(f"Failed to capture HTML: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_possible_image_urls(self, metadata: Dict) -> List[str]:
        """Generate possible image URLs"""
        logger.info("Generating URLs...")
        urls = []
        image_id = metadata.get('image_id')
        wfm_path = metadata.get('wfm_image_path')
        base_url = metadata.get('base_image_url', 'https://img.newspapers.com')
        
        if image_id:
            urls.extend([
                f"{base_url}/{image_id}/image.jpg",
                f"{base_url}/{image_id}/full.jpg",
                f"{base_url}/{image_id}/large.jpg",
                f"{base_url}/{image_id}/original.jpg",
                f"{base_url}/{image_id}?size=full",
                f"{base_url}/{image_id}?quality=100",
                f"{base_url}/{image_id}?w=2000&q=100",
                f"{base_url}/{image_id}?w=4000&q=100",
                f"{base_url}/{image_id}.jpg",
                f"https://www.newspapers.com/image/{image_id}/full.jpg",
                f"https://www.newspapers.com/image/{image_id}.jpg",
            ])
        
        if wfm_path:
            processed_wfm_path = wfm_path
            if ':' in processed_wfm_path:
                path_part, suffix_part = processed_wfm_path.split(':', 1)
                for path_to_try in [path_part, suffix_part]:
                    if path_to_try.upper().endswith('.PDF'):
                        path_to_try = path_to_try[:-4]
                    for ext in ['.jpg', '.jpeg', '.png', '']:
                        clean_path = f"{path_to_try}{ext}".lstrip('/')
                        urls.extend([
                            f"{base_url}/{clean_path}?quality=100",
                            f"{base_url}/{clean_path}?size=full",
                            f"{base_url}/{clean_path}",
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
                        f"{base_url}/{clean_path}",
                        f"https://www.newspapers.com/image/{clean_path}",
                    ])
        
        unique_urls = list(dict.fromkeys(urls))
        logger.info(f"Generated {len(unique_urls)} unique URLs")
        return unique_urls

    def _find_multi_page_images(self, html_content: str, base_image_id: str) -> List[Dict]:
        """Find multi-page images"""
        logger.info(f"Searching for multi-page images for {base_image_id}")
        multi_page_images = []
        try:
            start_time = time.time()
            MAX_SEARCH_TIME = 5
            
            nav_link_patterns = [
                r'data-next-image="(\d+)"',
                r'data-prev-image="(\d+)"',
                r'href="[^"]*image/(\d+)[^"]*"[^>]*(?:next\s+page|previous\s+page|continue|continued)',
                r'class="[^"]*next[^"]*"[^>]*href="[^"]*image/(\d+)',
                r'class="[^"]*prev[^"]*"[^>]*href="[^"]*image/(\d+)'
            ]
            
            found_ids = {base_image_id}
            for pattern in nav_link_patterns:
                if time.time() - start_time > MAX_SEARCH_TIME:
                    break
                try:
                    matches = re.findall(pattern, html_content, re.IGNORECASE)
                    for match in matches[:2]:
                        if match not in found_ids and len(found_ids) < 4:
                            found_ids.add(match)
                            multi_page_images.append({
                                'image_id': match,
                                'page_offset': 0,
                                'source': 'navigation_link'
                            })
                        if len(multi_page_images) >= 3:
                            break
                    if len(multi_page_images) >= 3:
                        break
                except re.error as e:
                    logger.debug(f"Regex error with nav pattern {pattern}: {e}")
            
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
                        if match not in found_ids:
                            found_ids.add(match)
                            multi_page_images.append({
                                'image_id': match,
                                'page_offset': 0,
                                'source': 'article_continuation'
                            })
                        if len(multi_page_images) >= 3:
                            break
                except re.error as e:
                    logger.debug(f"Regex error with continuation pattern {pattern}: {e}")
            
            multi_page_images = multi_page_images[:3]
            logger.info(f"Found {len(multi_page_images)} multi-page indicators")
            return multi_page_images
            
        except Exception as e:
            logger.error(f"Error finding multi-page images: {e}")
            return []

def extract_from_newspapers_com(url: str, cookies: str = "", player_name: Optional[str] = None) -> Dict:
    """Legacy function for backward compatibility"""
    extractor = NewspapersComExtractor(auto_auth=False)
    if cookies:
        extractor.cookie_manager.cookies = json