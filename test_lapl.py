#!/usr/bin/env python3
"""
LAPL Authentication Test Script
Test the LAPL cookie authentication outside of Streamlit
"""

import json
import sys
from extractors.lapl_extractor import LAPLExtractor

def test_lapl_authentication():
    """Test LAPL authentication with sample cookies"""
    print("🏛️ LAPL Authentication Test")
    print("=" * 50)
    
    # Check if we have saved cookies
    try:
        from utils.credential_manager import CredentialManager
        cred_manager = CredentialManager()
        cookies_result = cred_manager.load_lapl_cookies()
        
        if cookies_result['success']:
            print(f"✅ Found saved LAPL cookies: {cookies_result['metadata']['cookie_count']} cookies")
            
            # Initialize extractor
            extractor = LAPLExtractor(auto_auth=True)
            
            # Test authentication
            print("\n🔍 Testing LAPL authentication...")
            auth_test = extractor.test_authentication()
            
            print(f"Authentication Status: {'✅ Success' if auth_test['authenticated'] else '❌ Failed'}")
            print(f"Message: {auth_test['message']}")
            print(f"Status Code: {auth_test.get('status_code', 'N/A')}")
            print(f"Final URL: {auth_test.get('final_url', 'N/A')}")
            
            # Test specific URL access
            test_url = "https://access-newspaperarchive-com.lapl.idm.oclc.org/us/california/marysville/marysville-appeal-democrat/2014/12-12/page-10"
            print(f"\n🔍 Testing specific URL access...")
            print(f"URL: {test_url}")
            
            url_test = extractor.access_specific_url(test_url)
            
            print(f"URL Access: {'✅ Success' if url_test['success'] else '❌ Failed'}")
            if url_test['success']:
                print(f"Content Length: {url_test['content_length']:,} characters")
                print(f"Has Newspaper Content: {'✅ Yes' if url_test['has_newspaper_content'] else '❌ No'}")
                print(f"Has Errors: {'❌ Yes' if url_test['has_errors'] else '✅ No'}")
                print(f"Final URL: {url_test['final_url']}")
                
                if url_test.get('content_preview'):
                    print(f"\nContent Preview (first 200 chars):")
                    print("-" * 40)
                    print(url_test['content_preview'][:200] + "...")
                    print("-" * 40)
            else:
                print(f"Error: {url_test['message']}")
            
            # Cleanup
            extractor.cleanup()
            
        else:
            print("❌ No saved LAPL cookies found")
            print("💡 Upload cookies through the Streamlit interface first")
            
    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        return False
    
    return True

if __name__ == "__main__":
    test_lapl_authentication()