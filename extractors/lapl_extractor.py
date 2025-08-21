import os
import json
import logging
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import time
from typing import Dict, Any, Optional
from urllib.parse import urlparse
from utils.logger import setup_logging

logger = setup_logging(__name__)

class LAPLExtractor:
    """
    LAPL (Los Angeles Public Library) extractor for accessing newspaper archives
    through LAPL's SSO system using uploaded cookies
    """
    
    def __init__(self, auto_auth: bool = True):
        """
        Initialize LAPL extractor
        
        Args:
            auto_auth: Whether to automatically load saved cookies
        """
        self.cookies = {}
        self.session = requests.Session()
        self.driver = None
        self.is_authenticated = False
        self.base_domain = "lapl.idm.oclc.org"
        self.newspaper_archive_domain = "access-newspaperarchive-com.lapl.idm.oclc.org"
        self.is_render = 'RENDER' in os.environ or 'RENDER_SERVICE_ID' in os.environ
        
        logger.info("LAPL Extractor initialized")
        
        if auto_auth:
            self._load_saved_cookies()
    
    def _load_saved_cookies(self):
        """Load saved LAPL cookies from credential manager"""
        try:
            from utils.credential_manager import CredentialManager
            cred_manager = CredentialManager()
            cookies_result = cred_manager.load_lapl_cookies()
            
            if cookies_result['success']:
                self.cookies = cookies_result['cookies']
                self._apply_cookies_to_session()
                logger.info(f"Loaded {len(self.cookies)} LAPL cookies from storage")
                self.is_authenticated = True
            else:
                logger.info("No saved LAPL cookies found")
                
        except Exception as e:
            logger.error(f"Failed to load saved LAPL cookies: {str(e)}")
    
    def _apply_cookies_to_session(self):
        """Apply loaded cookies to requests session"""
        for name, value in self.cookies.items():
            self.session.cookies.set(name, value, domain=self.base_domain)
            # Also set for newspaper archive domain
            self.session.cookies.set(name, value, domain=self.newspaper_archive_domain)
    
    def load_cookies_from_data(self, cookies_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Load cookies from uploaded JSON data
        
        Args:
            cookies_data: Dictionary or list of cookies from uploaded JSON
            
        Returns:
            dict: Result of cookie loading
        """
        try:
            # Normalize cookies data to consistent format
            if isinstance(cookies_data, list):
                # Convert list of cookie objects to name-value dictionary
                # Skip cookies that are missing required name or value fields
                normalized_cookies = {}
                for cookie in cookies_data:
                    if isinstance(cookie, dict) and 'name' in cookie and 'value' in cookie:
                        normalized_cookies[cookie['name']] = cookie['value']
                    else:
                        logger.warning(f"Skipping malformed cookie: {cookie}")
            else:
                normalized_cookies = cookies_data
            
            self.cookies = normalized_cookies
            self._apply_cookies_to_session()
            self.is_authenticated = True
            
            logger.info(f"Loaded {len(normalized_cookies)} LAPL cookies")
            
            return {
                'success': True,
                'message': f'Loaded {len(normalized_cookies)} cookies',
                'cookie_count': len(normalized_cookies)
            }
            
        except Exception as e:
            logger.error(f"Failed to load LAPL cookies: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def test_authentication(self) -> Dict[str, Any]:
        """
        Test LAPL authentication by navigating to a specific newspaper page with Selenium
        and checking for PIN/payment prompts
        
        Returns:
            dict: Authentication test result
        """
        # Use a specific newspaper URL that should require authentication
        test_url = "https://access-newspaperarchive-com.lapl.idm.oclc.org/us/california/marysville/marysville-appeal-democrat/2014/12-12/page-10"
        
        try:
            logger.info(f"Testing LAPL authentication with {len(self.cookies)} cookies using Selenium")
            
            # Set up Chrome options for headless browsing
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
            
            # Add Render-specific memory optimizations
            if self.is_render:
                chrome_options.add_argument('--memory-pressure-off')
                chrome_options.add_argument('--max_old_space_size=256')
                chrome_options.add_argument('--disable-background-mode')
                chrome_options.add_argument('--disable-plugins')
                chrome_options.add_argument('--disable-java')
                chrome_options.add_argument('--disable-component-extensions-with-background-pages')
                chrome_options.add_argument('--disable-software-rasterizer')
                chrome_options.add_argument('--disable-accelerated-2d-canvas')
                chrome_options.add_argument('--disable-accelerated-video-decode')
                chrome_options.add_argument('--disable-accelerated-video-encode')
                chrome_options.add_argument('--max-memory-usage=128MB')
                chrome_options.add_argument('--single-process')
                chrome_options.add_argument('--disable-site-isolation-trials')
                chrome_options.add_argument('--disable-features=VizDisplayCompositor,VizHitTestSurfaceLayer')
                chrome_options.add_argument('--aggressive-cache-discard')
                chrome_options.add_argument('--disable-shared-workers')
                chrome_options.add_argument('--disable-service-worker-navigation-preload')
                logger.info("Applied Render-specific ultra-low memory Chrome options for LAPL extractor")
            
            # Initialize driver
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            
            # Load the test URL
            logger.info(f"Navigating to test URL: {test_url}")
            self.driver.get(test_url)
            
            # Add cookies to the driver
            for name, value in self.cookies.items():
                try:
                    self.driver.add_cookie({
                        'name': name,
                        'value': value,
                        'domain': '.lapl.idm.oclc.org'
                    })
                except Exception as cookie_error:
                    logger.warning(f"Failed to add cookie {name}: {str(cookie_error)}")
            
            # Reload the page with cookies
            logger.info("Reloading page with cookies")
            self.driver.refresh()
            
            # Wait for page to load
            time.sleep(3)
            
            # Get page content and URL after potential redirects
            current_url = self.driver.current_url
            page_source = self.driver.page_source.lower()
            page_title = self.driver.title.lower()
            
            logger.info(f"Final URL: {current_url}")
            logger.info(f"Page Title: {page_title}")
            
            # Check for LAPL-specific authentication prompts (indicating auth failure)
            lapl_auth_indicators = [
                'please enter your lapl card number',
                'por favor ingresa tu número de tarjeta de biblioteca',
                'lapl card number',
                'please enter your pin',
                'por favor ingresa tu contraseña pin',
                'last 4 digits of your phone number',
                'últimos cuatro dígitos de tu número telefónico',
                'los angeles public library',
                'login button',
                'entrar'
            ]
            
            # Check for general authentication failure indicators
            auth_failure_indicators = [
                'login required',
                'sign in',
                'authentication required',
                'access denied',
                'unauthorized',
                'please log in'
            ]
            
            # Check for successful authentication indicators
            success_indicators = [
                'marysville appeal democrat',
                'december 12, 2014',
                'newspaper viewer',
                'article text',
                'page view',
                'zoom in',
                'zoom out'
            ]
            
            has_lapl_auth_prompts = any(indicator in page_source for indicator in lapl_auth_indicators)
            has_auth_failures = any(indicator in page_source for indicator in auth_failure_indicators)
            has_success_content = any(indicator in page_source for indicator in success_indicators)
            
            # Clean up driver
            self.driver.quit()
            self.driver = None
            
            # Determine authentication status
            if has_lapl_auth_prompts:
                logger.warning("LAPL authentication test found LAPL card/PIN prompts")
                return {
                    'success': True,
                    'authenticated': False,
                    'message': 'Authentication failed - LAPL card/PIN prompts detected',
                    'final_url': current_url,
                    'page_title': page_title,
                    'has_lapl_auth_prompts': True,
                    'has_auth_failures': has_auth_failures,
                    'has_success_content': has_success_content
                }
            elif has_auth_failures:
                logger.warning("LAPL authentication test found login prompts")
                return {
                    'success': True,
                    'authenticated': False,
                    'message': 'Authentication failed - login required',
                    'final_url': current_url,
                    'page_title': page_title,
                    'has_lapl_auth_prompts': False,
                    'has_auth_failures': True,
                    'has_success_content': has_success_content
                }
            elif has_success_content:
                logger.info("LAPL authentication test successful - newspaper content accessible")
                return {
                    'success': True,
                    'authenticated': True,
                    'message': 'Successfully authenticated - newspaper content accessible',
                    'final_url': current_url,
                    'page_title': page_title,
                    'has_lapl_auth_prompts': False,
                    'has_auth_failures': False,
                    'has_success_content': True
                }
            else:
                logger.warning("LAPL authentication test - unclear page state")
                return {
                    'success': True,
                    'authenticated': False,
                    'message': 'Authentication unclear - no definitive indicators found',
                    'final_url': current_url,
                    'page_title': page_title,
                    'has_lapl_auth_prompts': False,
                    'has_auth_failures': False,
                    'has_success_content': False
                }
                
        except TimeoutException:
            logger.error("LAPL authentication test timed out")
            if self.driver:
                self.driver.quit()
                self.driver = None
            return {
                'success': False,
                'authenticated': False,
                'error': 'Page load timeout',
                'message': 'Authentication test timed out'
            }
        except WebDriverException as e:
            logger.error(f"LAPL authentication test WebDriver error: {str(e)}")
            if self.driver:
                self.driver.quit()
                self.driver = None
            return {
                'success': False,
                'authenticated': False,
                'error': str(e),
                'message': f'WebDriver error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"LAPL authentication test failed: {str(e)}")
            if self.driver:
                self.driver.quit()
                self.driver = None
            return {
                'success': False,
                'authenticated': False,
                'error': str(e),
                'message': f'Authentication test failed: {str(e)}'
            }
    
    def access_specific_url(self, url: str) -> Dict[str, Any]:
        """
        Test access to a specific LAPL newspaper URL
        
        Args:
            url: The specific LAPL URL to test access to
            
        Returns:
            dict: Access test result with content information
        """
        try:
            logger.info(f"Testing access to specific LAPL URL: {url}")
            
            # Validate URL is from LAPL domain
            parsed_url = urlparse(url)
            if not parsed_url.netloc.endswith('lapl.idm.oclc.org'):
                return {
                    'success': False,
                    'error': 'URL is not from LAPL domain'
                }
            
            # Set proper headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://access-newspaperarchive-com.lapl.idm.oclc.org/',
            }
            
            response = self.session.get(url, headers=headers, timeout=30, allow_redirects=True)
            
            if response.status_code == 200:
                content = response.text
                content_length = len(content)
                
                # Check for newspaper content indicators
                newspaper_indicators = [
                    'newspaper',
                    'article',
                    'page',
                    'archive',
                    'marysville appeal democrat',
                    'december 12, 2014'
                ]
                
                error_indicators = [
                    'access denied',
                    'authentication required',
                    'login required',
                    'session expired',
                    'forbidden'
                ]
                
                has_newspaper_content = any(indicator in content.lower() for indicator in newspaper_indicators)
                has_error_indicators = any(indicator in content.lower() for indicator in error_indicators)
                
                logger.info(f"LAPL URL access successful - Content length: {content_length}")
                
                return {
                    'success': True,
                    'status_code': response.status_code,
                    'content_length': content_length,
                    'has_newspaper_content': has_newspaper_content,
                    'has_errors': has_error_indicators,
                    'final_url': response.url,
                    'cookies_used': len(self.cookies),
                    'content_preview': content[:500] if content else '',
                    'message': 'Successfully accessed LAPL URL'
                }
            else:
                logger.warning(f"LAPL URL access failed with status {response.status_code}")
                return {
                    'success': False,
                    'status_code': response.status_code,
                    'final_url': response.url,
                    'message': f'HTTP {response.status_code} error accessing URL'
                }
                
        except Exception as e:
            logger.error(f"Failed to access LAPL URL: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Error accessing URL: {str(e)}'
            }
    
    def is_newsbank_url(self, url: str) -> bool:
        """
        Check if URL is from NewsBank via LAPL
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if NewsBank URL
        """
        parsed = urlparse(url)
        newsbank_indicators = [
            'infoweb-newsbank',
            'newsbank',
            'access-world-news',
            'world-news'
        ]
        return any(indicator in parsed.netloc.lower() for indicator in newsbank_indicators) and 'lapl.idm.oclc.org' in parsed.netloc
    
    def is_proquest_url(self, url: str) -> bool:
        """
        Check if URL is from ProQuest via LAPL
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if ProQuest URL
        """
        parsed = urlparse(url)
        proquest_indicators = [
            'search-proquest',
            'proquest',
            'hnpla',
            'latimes'
        ]
        # Also check for direct proquest.com URLs (ex: https://www.proquest.com/usnews/docview/...)
        return (any(indicator in parsed.netloc.lower() for indicator in proquest_indicators) and 'lapl.idm.oclc.org' in parsed.netloc) or \
               ('proquest.com' in parsed.netloc and ('docview' in url or 'usnews' in url))
    
    def is_lapl_news_url(self, url: str) -> bool:
        """
        Check if URL is from a LAPL news source (NewsBank or ProQuest)
        
        Args:
            url: URL to check
            
        Returns:
            bool: True if LAPL news source URL
        """
        return self.is_newsbank_url(url) or self.is_proquest_url(url)
    
    def extract_newsbank_content(self, url: str) -> Dict[str, Any]:
        """
        Extract article content from NewsBank URLs via LAPL
        
        Args:
            url: NewsBank article URL
            
        Returns:
            dict: Extracted article data
        """
        try:
            logger.info(f"Extracting content from NewsBank URL: {url}")
            
            if not self.is_authenticated:
                return {
                    'success': False,
                    'error': 'LAPL authentication required for NewsBank access'
                }
            
            # Set proper headers for NewsBank
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://infoweb-newsbank-com.lapl.idm.oclc.org/',
            }
            
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract headline
            headline = "Unknown Headline"
            headline_selectors = [
                '.article-title',
                '.headline',
                'h1',
                '.title',
                '.story-headline'
            ]
            
            for selector in headline_selectors:
                headline_elem = soup.select_one(selector)
                if headline_elem and len(headline_elem.text.strip()) > 5:
                    headline = headline_elem.text.strip()
                    break
            
            # Extract date
            date_text = "Unknown Date"
            date_selectors = [
                '.publication-date',
                '.pub-date',
                '.date',
                '.article-date',
                'time'
            ]
            
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_text = date_elem.text.strip()
                    break
            
            # Extract author
            author = "Unknown Author"
            author_selectors = [
                '.author',
                '.byline',
                '.writer',
                '.contributor'
            ]
            
            for selector in author_selectors:
                author_elem = soup.select_one(selector)
                if author_elem:
                    author = author_elem.text.strip()
                    # Clean up common prefixes
                    import re
                    author = re.sub(r'^By\s+', '', author, flags=re.IGNORECASE)
                    break
            
            # Extract article content
            content = ""
            content_selectors = [
                '.article-text',
                '.article-body',
                '.content',
                '.story-text',
                '#story-body'
            ]
            
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    # Get all paragraphs and clean them
                    paragraphs = []
                    for p in content_elem.find_all(['p', 'div']):
                        text = p.get_text().strip()
                        if len(text) > 20:  # Skip short fragments
                            paragraphs.append('    ' + text)  # Add indentation
                    content = "\n\n".join(paragraphs)
                    break
            
            # Fallback content extraction
            if not content:
                paragraphs = []
                for p in soup.find_all('p'):
                    text = p.get_text().strip()
                    if len(text) > 40:
                        paragraphs.append('    ' + text)
                content = "\n\n".join(paragraphs)
            
            # Determine source
            parsed_url = urlparse(url)
            source = "NewsBank via LAPL"
            
            logger.info(f"Successfully extracted NewsBank article: {headline}")
            
            return {
                'success': True,
                'headline': headline,
                'date': date_text,
                'author': author,
                'text': content,
                'source': source,
                'url': url,
                'content_type': 'newsbank',
                'word_count': len(content.split()) if content else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to extract NewsBank content: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f'NewsBank extraction failed: {str(e)}'
            }
    
    def extract_proquest_content(self, url: str) -> Dict[str, Any]:
        """
        Extract article content from ProQuest URLs via LAPL
        
        Args:
            url: ProQuest article URL
            
        Returns:
            dict: Extracted article data
        """
        try:
            logger.info(f"Extracting content from ProQuest URL: {url}")
            
            if not self.is_authenticated:
                return {
                    'success': False,
                    'error': 'LAPL authentication required for ProQuest access'
                }
            
            # Set proper headers for ProQuest with appropriate referer
            parsed_url = urlparse(url)
            referer_url = f"{parsed_url.scheme}://{parsed_url.netloc}/"
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Referer': referer_url,
            }
            
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"ProQuest response status: {response.status_code}, content length: {len(response.content)}")
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check if we have the expected ProQuest content structure
            has_docview = bool(soup.select_one('.docview-header, #docview-contents-wrapper, .docView'))
            has_fulltext = bool(soup.select_one('#fullTextZone, .fullTextHeader, #fulltext_field_MSTAR'))
            logger.info(f"ProQuest page analysis - has docview structure: {has_docview}, has fulltext: {has_fulltext}")
            
            # Extract headline with debugging
            headline = "Unknown Headline"
            headline_selectors = [
                '.documentTitle',  # New ProQuest structure
                '.truncatedDocumentTitle',
                '#documentTitle',
                'h1.documentTitle',
                'h1.truncatedDocumentTitle',
                '.titleLink',
                '.docTitle',
                'h1',
                '.title',
                '.headline',
                '.article-title'
            ]
            
            logger.info("Attempting headline extraction from ProQuest page")
            for selector in headline_selectors:
                headline_elem = soup.select_one(selector)
                if headline_elem:
                    headline_text = headline_elem.text.strip()
                    logger.info(f"Found element with selector '{selector}': '{headline_text[:50]}...'")
                    if len(headline_text) > 5:
                        headline = headline_text
                        logger.info(f"Selected headline: '{headline}'")
                        break
                else:
                    logger.debug(f"No element found for selector: {selector}")
            
            if headline == "Unknown Headline":
                logger.warning("No headline found with BeautifulSoup, checking for any h1 elements on page")
                all_h1s = soup.find_all('h1')
                for h1 in all_h1s:
                    logger.info(f"Found h1 element: '{h1.text.strip()[:100]}...' with classes: {h1.get('class', [])}")
                
                # If we still have no headline, try using Selenium as fallback
                if not all_h1s or not any(len(h1.text.strip()) > 5 for h1 in all_h1s):
                    logger.info("Attempting ProQuest extraction with Selenium as fallback")
                    selenium_result = self._extract_proquest_with_selenium(url)
                    if selenium_result.get('success'):
                        return selenium_result
            
            # Extract date and publication info
            date_text = "Unknown Date"
            date_selectors = [
                '.pubDate',
                '.publication-date',
                '.date',
                '.pub-date',
                'time'
            ]
            
            # First try standard date selectors
            for selector in date_selectors:
                date_elem = soup.select_one(selector)
                if date_elem:
                    date_text = date_elem.text.strip()
                    break
                    
            # For new ProQuest structure, extract from newspaperArticle span
            if date_text == "Unknown Date":
                newspaper_elem = soup.select_one('.newspaperArticle')
                if newspaper_elem:
                    import re
                    text = newspaper_elem.get_text()
                    # Look for date pattern like "26 Aug 2024"
                    date_match = re.search(r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}', text)
                    if date_match:
                        date_text = date_match.group()
                        
            # Extract publication name
            publication = "Unknown Publication"
            pub_elem = soup.select_one('.newspaperArticle strong')
            if pub_elem:
                publication = pub_elem.get_text().strip()
            
            # Extract author
            author = "Unknown Author"
            author_selectors = [
                '.author-name',  # New ProQuest structure
                '.truncatedAuthor .author-name',
                '.author',
                '.byline',
                '.docAuthor',
                '.contributor',
                '.scholUnivAuthors .author-name'
            ]
            
            for selector in author_selectors:
                author_elem = soup.select_one(selector)
                if author_elem:
                    author = author_elem.text.strip()
                    # Clean up common prefixes
                    import re
                    author = re.sub(r'^By\s+', '', author, flags=re.IGNORECASE)
                    break
            
            # Extract article content with debugging
            content = ""
            content_selectors = [
                'text[htmlcontent="true"]',  # New ProQuest structure
                '.display_record_text_copy text',
                '#fulltext_field_MSTAR text',
                'text[wordcount]',  # Alternative ProQuest text element selector
                '.docFullText',
                '.article-content',
                '.content',
                '.docText',
                '.full-text'
            ]
            
            logger.info("Attempting content extraction from ProQuest page")
            for selector in content_selectors:
                content_elem = soup.select_one(selector)
                if content_elem:
                    logger.info(f"Found content element with selector '{selector}'")
                    
                    # For the new ProQuest text element, extract paragraphs
                    paragraphs = []
                    for p in content_elem.find_all('p'):
                        text = p.get_text().strip()
                        if len(text) > 20:  # Skip short fragments
                            paragraphs.append('    ' + text)  # Add indentation
                    
                    if paragraphs:
                        content = "\n\n".join(paragraphs)
                        logger.info(f"Extracted {len(paragraphs)} paragraphs, total content length: {len(content)}")
                        break
                    
                    # Fallback to get all text if no paragraphs
                    text = content_elem.get_text().strip()
                    if len(text) > 100:
                        content = text
                        logger.info(f"Used fallback text extraction, content length: {len(content)}")
                        break
                else:
                    logger.debug(f"No content element found for selector: {selector}")
            
            # Additional fallback for new ProQuest structure
            if not content:
                fulltext_zone = soup.select_one('#fullTextZone')
                if fulltext_zone:
                    paragraphs = []
                    for p in fulltext_zone.find_all('p'):
                        text = p.get_text().strip()
                        if len(text) > 40:
                            paragraphs.append('    ' + text)
                    content = "\n\n".join(paragraphs)
            
            # Final fallback content extraction
            if not content:
                paragraphs = []
                for p in soup.find_all('p'):
                    text = p.get_text().strip()
                    if len(text) > 40:
                        paragraphs.append('    ' + text)
                content = "\n\n".join(paragraphs)
            
            # Determine source
            parsed_url = urlparse(url)
            if publication and publication != "Unknown Publication":
                source = f"{publication} via ProQuest/LAPL"
            else:
                source = "ProQuest via LAPL"
            
            logger.info(f"Successfully extracted ProQuest article: {headline}")
            
            return {
                'success': True,
                'headline': headline,
                'date': date_text,
                'author': author,
                'text': content,
                'source': source,
                'url': url,
                'content_type': 'proquest',
                'publication': publication,
                'word_count': len(content.split()) if content else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to extract ProQuest content: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f'ProQuest extraction failed: {str(e)}'
            }
    
    def _extract_proquest_with_selenium(self, url: str) -> Dict[str, Any]:
        """
        Fallback method to extract ProQuest content using Selenium when regular HTTP fails
        
        Args:
            url: ProQuest article URL
            
        Returns:
            dict: Extracted article data
        """
        try:
            logger.info(f"Using Selenium fallback for ProQuest URL: {url}")
            
            if not self.driver:
                # Use the Chrome options already defined for this environment
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                chrome_options.add_argument("--no-sandbox")
                chrome_options.add_argument("--disable-dev-shm-usage")
                chrome_options.add_argument("--disable-gpu")
                chrome_options.add_argument("--window-size=1920,1080")
                chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
                
                # Add Render-specific memory optimizations if needed
                if self.is_render:
                    chrome_options.add_argument('--memory-pressure-off')
                    chrome_options.add_argument('--max_old_space_size=256')
                    chrome_options.add_argument('--single-process')
                    logger.info("Applied Render-specific Chrome options for ProQuest Selenium fallback")
                
                from selenium import webdriver
                self.driver = webdriver.Chrome(options=chrome_options)
                self.driver.set_page_load_timeout(30)
            
            # Navigate to the page
            self.driver.get(url)
            
            # Wait for content to load
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.common.by import By
            
            wait = WebDriverWait(self.driver, 10)
            
            # Wait for headline element to be present
            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.documentTitle, h1')))
            except:
                logger.warning("Timeout waiting for ProQuest content to load")
            
            # Extract data from the loaded page
            from bs4 import BeautifulSoup
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract headline
            headline = "Unknown Headline"
            headline_elem = soup.select_one('.documentTitle, #documentTitle, h1.documentTitle')
            if headline_elem:
                headline = headline_elem.text.strip()
                logger.info(f"Selenium extracted headline: {headline}")
            
            # Extract author
            author = "Unknown Author"
            author_elem = soup.select_one('.author-name')
            if author_elem:
                author = author_elem.text.strip()
            
            # Extract date and publication
            date_text = "Unknown Date"
            publication = "Unknown Publication"
            newspaper_elem = soup.select_one('.newspaperArticle')
            if newspaper_elem:
                import re
                text = newspaper_elem.get_text()
                date_match = re.search(r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}', text)
                if date_match:
                    date_text = date_match.group()
                
                pub_elem = soup.select_one('.newspaperArticle strong')
                if pub_elem:
                    publication = pub_elem.get_text().strip()
            
            # Extract content
            content = ""
            content_elem = soup.select_one('text[htmlcontent="true"], text[wordcount]')
            if content_elem:
                paragraphs = []
                for p in content_elem.find_all('p'):
                    text = p.get_text().strip()
                    if len(text) > 20:
                        paragraphs.append('    ' + text)
                content = "\n\n".join(paragraphs)
                logger.info(f"Selenium extracted {len(paragraphs)} paragraphs")
            
            # Determine source
            if publication and publication != "Unknown Publication":
                source = f"{publication} via ProQuest/LAPL"
            else:
                source = "ProQuest via LAPL"
            
            return {
                'success': True,
                'headline': headline,
                'date': date_text,
                'author': author,
                'text': content,
                'source': source,
                'url': url,
                'content_type': 'proquest',
                'publication': publication,
                'word_count': len(content.split()) if content else 0,
                'extraction_method': 'selenium'
            }
            
        except Exception as e:
            logger.error(f"Selenium ProQuest extraction failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f'Selenium ProQuest extraction failed: {str(e)}'
            }
        finally:
            # Clean up driver if we created it for this extraction
            if self.driver:
                try:
                    self.driver.quit()
                    self.driver = None
                except:
                    pass
    
    def extract_article_content(self, url: str, project_name: str = "lapl_extracts") -> Dict[str, Any]:
        """
        Main method to extract article content from LAPL news sources
        
        Args:
            url: Article URL from NewsBank or ProQuest via LAPL
            project_name: Project name for organizing storage
            
        Returns:
            dict: Extracted article data with enhanced metadata
        """
        try:
            logger.info(f"Starting LAPL article extraction for: {url}")
            
            # Check if this is a supported LAPL news URL
            if not self.is_lapl_news_url(url):
                return {
                    'success': False,
                    'error': 'URL is not from a supported LAPL news source (NewsBank or ProQuest)'
                }
            
            # Check authentication
            if not self.is_authenticated:
                return {
                    'success': False,
                    'error': 'LAPL authentication required. Please upload valid cookies.'
                }
            
            # Route to appropriate extractor
            if self.is_newsbank_url(url):
                article_data = self.extract_newsbank_content(url)
            elif self.is_proquest_url(url):
                article_data = self.extract_proquest_content(url)
            else:
                return {
                    'success': False,
                    'error': 'Unknown LAPL news source type'
                }
            
            if not article_data.get('success', False):
                return article_data
            
            # Enhance with storage and formatting
            try:
                from utils.storage_manager import StorageManager
                from utils.paragraph_formatter import format_article_paragraphs
                import re
                from datetime import datetime
                
                # Apply paragraph formatting
                context = {
                    'headline': article_data.get('headline', ''),
                    'source': article_data.get('source', ''),
                    'author': article_data.get('author', ''),
                    'date': article_data.get('date', '')
                }
                
                formatted_content = format_article_paragraphs(article_data.get('text', ''), context)
                if formatted_content and formatted_content != article_data.get('text', ''):
                    article_data['text'] = formatted_content
                    logger.info(f"Applied paragraph formatting to LAPL content")
                
                # Initialize storage manager
                storage_manager = StorageManager(project_name=project_name)
                
                # Create descriptive filename
                date_str = datetime.now().strftime('%Y%m%d')
                source_type = article_data.get('content_type', 'lapl')
                safe_headline = re.sub(r'[^\w\s-]', '', article_data.get('headline', 'article'))
                safe_headline = re.sub(r'\s+', '_', safe_headline)[:50]
                
                markdown_filename = f"{date_str}_LAPL_{source_type}_{safe_headline}.md"
                markdown_path = storage_manager.get_project_path(markdown_filename)
                article_data["markdown_path"] = markdown_path
                
                # Generate markdown content
                from extractors.url_extractor import generate_markdown_content
                markdown_content = generate_markdown_content(article_data)
                
                # Save using storage manager
                storage_manager.store_file(markdown_filename, markdown_content.encode('utf-8'))
                
                logger.info(f"Saved LAPL article content to {markdown_path}")
                
                return article_data
                
            except Exception as e:
                logger.warning(f"Storage/formatting enhancement failed: {str(e)}")
                # Return the basic extracted data even if enhancement fails
                return article_data
            
        except Exception as e:
            logger.error(f"LAPL article extraction failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': f'LAPL article extraction failed: {str(e)}'
            }
    
    def get_authentication_status(self) -> Dict[str, Any]:
        """
        Get current authentication status
        
        Returns:
            dict: Current authentication information
        """
        return {
            'authenticated': self.is_authenticated,
            'cookie_count': len(self.cookies),
            'base_domain': self.base_domain,
            'newspaper_archive_domain': self.newspaper_archive_domain,
            'session_active': bool(self.session.cookies)
        }
    
    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        
        if self.session:
            self.session.close()