# newspapers_extractor_optimized.py
# Streamlined Newspapers.com Screenshot Extractor
# Focus: Zoom out → Screenshot → Crop → Save

import os
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from PIL import Image
import io
from typing import Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class OptimizedNewspapersExtractor:
    """Optimized newspapers.com extractor focusing only on screenshot and crop functionality"""
    
    def __init__(self, cookies: str = ""):
        self.driver = None
        self.cookies = self._parse_cookies(cookies) if cookies else {}
        self.is_replit = 'REPL_ID' in os.environ or 'REPL_SLUG' in os.environ
        
    def _parse_cookies(self, cookie_string: str) -> dict:
        """Parse cookie string into dictionary"""
        cookies = {}
        if cookie_string:
            for cookie in cookie_string.split(';'):
                if '=' in cookie:
                    name, value = cookie.strip().split('=', 1)
                    cookies[name] = value
        return cookies
    
    def _initialize_chrome_driver(self) -> bool:
        """Initialize Chrome driver with minimal configuration"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-popup-blocking')
            
            # Replit-specific optimizations
            if self.is_replit:
                chrome_options.add_argument('--single-process')
                chrome_options.add_argument('--disable-features=VizDisplayCompositor')
                chrome_options.add_argument('--disable-background-timer-throttling')
                chrome_options.add_argument('--renderer-timeout=30000')
                logger.info("Applied Replit optimizations")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Set timeouts
            timeout = 120 if self.is_replit else 30
            self.driver.set_page_load_timeout(timeout)
            self.driver.implicitly_wait(20 if self.is_replit else 10)
            
            return True
            
        except WebDriverException as e:
            logger.error(f"Failed to initialize Chrome driver: {str(e)}")
            return False
    
    def _apply_cookies(self):
        """Apply cookies to the driver"""
        if not self.cookies:
            return
            
        self.driver.get('https://www.newspapers.com/')
        
        for name, value in self.cookies.items():
            try:
                self.driver.add_cookie({
                    'name': name,
                    'value': value,
                    'domain': '.newspapers.com',
                    'path': '/'
                })
            except Exception as e:
                logger.warning(f"Could not add cookie {name}: {e}")
        
        # Refresh to apply cookies
        self.driver.refresh()
        time.sleep(2)
    
    def _zoom_out(self, zoom_clicks: int = 3):
        """Zoom out to get full article view"""
        try:
            for i in range(zoom_clicks):
                self.driver.execute_script("document.body.style.zoom='0.7'")
                time.sleep(1)
            logger.info(f"Applied {zoom_clicks} zoom out operations")
        except Exception as e:
            logger.warning(f"Zoom out failed: {e}")
    
    def _capture_screenshot(self) -> Optional[Image.Image]:
        """Capture screenshot of the current page"""
        try:
            screenshot_data = self.driver.get_screenshot_as_png()
            image = Image.open(io.BytesIO(screenshot_data))
            logger.info(f"Captured screenshot: {image.size}")
            return image
        except Exception as e:
            logger.error(f"Screenshot capture failed: {e}")
            return None
    
    def _crop_newspaper_clipping(self, image: Image.Image) -> Optional[Image.Image]:
        """Basic cropping to remove browser chrome and focus on content"""
        try:
            width, height = image.size
            
            # Simple crop - remove top browser chrome (approximately 100px)
            # and some padding from sides
            crop_top = 100
            crop_left = 50
            crop_right = width - 50
            crop_bottom = height - 50
            
            # Ensure crop dimensions are valid
            if crop_right > crop_left and crop_bottom > crop_top:
                cropped = image.crop((crop_left, crop_top, crop_right, crop_bottom))
                logger.info(f"Cropped image: {image.size} → {cropped.size}")
                return cropped
            else:
                logger.warning("Invalid crop dimensions, returning original image")
                return image
                
        except Exception as e:
            logger.error(f"Cropping failed: {e}")
            return image
    
    def extract_from_url(self, url: str) -> dict:
        """
        Extract screenshot from newspapers.com URL
        
        Args:
            url: Newspapers.com URL to extract from
            
        Returns:
            Dictionary with extraction result
        """
        start_time = time.time()
        
        try:
            # Initialize driver
            if not self._initialize_chrome_driver():
                return {
                    'success': False,
                    'error': 'Failed to initialize Chrome driver',
                    'processing_time_seconds': time.time() - start_time
                }
            
            # Apply cookies for authentication
            self._apply_cookies()
            
            # Navigate to the URL
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(3)  # Additional wait for content to render
            
            # Zoom out for better article view
            self._zoom_out()
            
            # Capture screenshot
            screenshot = self._capture_screenshot()
            if not screenshot:
                return {
                    'success': False,
                    'error': 'Failed to capture screenshot',
                    'processing_time_seconds': time.time() - start_time
                }
            
            # Crop the image
            cropped_image = self._crop_newspaper_clipping(screenshot)
            
            # Extract basic metadata from URL
            parsed_url = urlparse(url)
            title = f"Newspaper Clipping from {parsed_url.netloc}"
            
            return {
                'success': True,
                'image_data': cropped_image,
                'headline': title,
                'source': 'newspapers.com',
                'date': datetime.now().strftime('%Y-%m-%d'),
                'url': url,
                'processing_time_seconds': time.time() - start_time,
                'metadata': {
                    'extraction_method': 'optimized_screenshot',
                    'image_size': f"{cropped_image.width}x{cropped_image.height}",
                    'original_size': f"{screenshot.width}x{screenshot.height}"
                }
            }
            
        except TimeoutException:
            return {
                'success': False,
                'error': 'Page load timeout',
                'processing_time_seconds': time.time() - start_time
            }
        except Exception as e:
            logger.error(f"Extraction failed: {str(e)}")
            return {
                'success': False,
                'error': f'Extraction error: {str(e)}',
                'processing_time_seconds': time.time() - start_time
            }
        finally:
            self._cleanup()
    
    def _cleanup(self):
        """Cleanup driver resources"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("Driver cleanup completed")
            except Exception as e:
                logger.warning(f"Driver cleanup failed: {e}")

# Legacy function for compatibility
def extract_from_newspapers_com(url: str, cookies: str = "", **kwargs) -> dict:
    """
    Legacy wrapper function for backwards compatibility
    
    Args:
        url: Newspapers.com URL
        cookies: Cookie string for authentication
        **kwargs: Additional arguments (ignored for optimization)
        
    Returns:
        Extraction result dictionary
    """
    extractor = OptimizedNewspapersExtractor(cookies=cookies)
    return extractor.extract_from_url(url)

# Main function for testing
def main():
    """Test the optimized extractor"""
    test_url = "https://www.newspapers.com/article/example"
    
    extractor = OptimizedNewspapersExtractor()
    result = extractor.extract_from_url(test_url)
    
    if result['success']:
        print(f"✅ Extraction successful in {result['processing_time_seconds']:.2f}s")
        print(f"Image size: {result['metadata']['image_size']}")
    else:
        print(f"❌ Extraction failed: {result['error']}")

if __name__ == "__main__":
    main()