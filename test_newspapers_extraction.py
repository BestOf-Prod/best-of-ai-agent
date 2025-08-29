#!/usr/bin/env python3
"""
Test script for newspapers.com extraction with stale element reference fixes.
This script tests the robust clicking methods and Render optimizations.
"""

import sys
import os
import json
import logging
from datetime import datetime

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extractors.newspapers_extractor import extract_from_newspapers_com
from utils.logger import setup_logging

# Setup logging
logger = setup_logging(__name__)

def test_newspapers_extraction():
    """Test newspapers.com extraction with a known article URL."""
    
    # Load cookies
    cookies_file = 'newspapers_cookies.json'
    if not os.path.exists(cookies_file):
        logger.error(f"Cookies file not found: {cookies_file}")
        return False
    
    try:
        with open(cookies_file, 'r') as f:
            cookies_data = json.load(f)
            cookies = cookies_data.get('cookies', {})
        logger.info(f"Loaded {len(cookies)} cookies from {cookies_file}")
    except Exception as e:
        logger.error(f"Error loading cookies: {e}")
        return False
    
    # Test URL - a newspapers.com article
    test_url = "https://www.newspapers.com/article/the-akron-beacon-journal-james-lebron/148755027/"
    
    logger.info("="*80)
    logger.info("TESTING NEWSPAPERS.COM EXTRACTION WITH STALE ELEMENT FIXES")
    logger.info("="*80)
    logger.info(f"Test URL: {test_url}")
    logger.info(f"Total cookies: {len(cookies)}")
    logger.info("-"*80)
    
    try:
        # Convert cookies dict to JSON string for the function
        cookies_json = json.dumps(cookies)
        
        # Extract the article using the standalone function
        result = extract_from_newspapers_com(
            url=test_url,
            cookies=cookies_json,
            player_name="LeBron James",
            project_name="test_extraction"
        )
        
        logger.info("="*80)
        logger.info("EXTRACTION RESULTS")
        logger.info("="*80)
        
        if result.get('success'):
            logger.info("✅ EXTRACTION SUCCESSFUL!")
            logger.info(f"Title: {result.get('title', 'N/A')}")
            logger.info(f"Date: {result.get('date', 'N/A')}")
            logger.info(f"Newspaper: {result.get('newspaper', 'N/A')}")
            logger.info(f"Content length: {len(result.get('content', ''))} characters")
            
            # Check if image was generated
            if result.get('image_data'):
                logger.info(f"✅ Image generated: {len(result['image_data'])} bytes")
            else:
                logger.warning("⚠️  No image data generated")
            
            # Check storage result
            storage_result = result.get('storage_result', {})
            if storage_result.get('success'):
                logger.info(f"✅ Storage successful: {storage_result.get('filename', 'N/A')}")
            else:
                logger.warning(f"⚠️  Storage failed: {storage_result.get('error', 'Unknown error')}")
            
            return True
        else:
            logger.error("❌ EXTRACTION FAILED!")
            logger.error(f"Error: {result.get('error', 'Unknown error')}")
            
            # Check for stale element reference specifically
            error_msg = str(result.get('error', '')).lower()
            if 'stale element reference' in error_msg:
                logger.error("🚨 STALE ELEMENT REFERENCE ERROR STILL OCCURRING!")
                logger.error("The robust clicking fixes may need further adjustment.")
            elif 'timeout' in error_msg:
                logger.warning("⏰ Timeout occurred - may need to increase timeout values for Render")
            elif 'memory' in error_msg or 'out of memory' in error_msg:
                logger.warning("💾 Memory issue - Render resource constraints may need further optimization")
            
            return False
            
    except Exception as e:
        logger.error(f"❌ UNEXPECTED ERROR DURING EXTRACTION: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        
        # Check for specific error types
        if 'StaleElementReferenceException' in str(e):
            logger.error("🚨 STALE ELEMENT REFERENCE EXCEPTION STILL OCCURRING!")
        elif 'TimeoutException' in str(e):
            logger.warning("⏰ Selenium TimeoutException - may need timeout adjustments")
        
        return False
    
    finally:
        # Cleanup is handled internally by the standalone function
        logger.info("✅ Test completed - cleanup handled internally")

def main():
    """Main test function."""
    print(f"\n{'='*80}")
    print("NEWSPAPERS.COM EXTRACTION TEST")
    print(f"{'='*80}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print(f"{'='*80}\n")
    
    success = test_newspapers_extraction()
    
    print(f"\n{'='*80}")
    if success:
        print("🎉 TEST COMPLETED SUCCESSFULLY!")
        print("The stale element reference fixes appear to be working.")
    else:
        print("❌ TEST FAILED!")
        print("Check the logs above for specific error details.")
    print(f"{'='*80}\n")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())