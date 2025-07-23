#!/usr/bin/env python3
"""
Test script for Replit Google Drive authentication
"""

import os
import sys
from utils.google_drive_manager import GoogleDriveManager

def test_replit_environment():
    """Test Replit environment detection and configuration"""
    print("🔍 Testing Replit Environment Configuration")
    print("=" * 50)
    
    # Create Google Drive manager
    drive_manager = GoogleDriveManager(auto_init=False)
    
    # Test environment detection
    is_replit = bool(os.environ.get('REPL_ID') or os.environ.get('REPL_SLUG'))
    print(f"Environment Detection: {'Replit' if is_replit else 'Local'}")
    
    # Test Replit URL generation
    if is_replit:
        replit_url = drive_manager._get_replit_url()
        print(f"Replit URL: {replit_url}")
        print(f"Redirect URI: https://{replit_url}/oauth/callback")
    
    # Test validation
    validation = drive_manager.validate_replit_environment()
    print(f"\nValidation Results:")
    print(f"- Is Replit: {validation['is_replit']}")
    print(f"- REPL_SLUG: {validation['repl_slug']}")
    print(f"- REPL_OWNER: {validation['repl_owner']}")
    print(f"- REPL_ID: {validation['repl_id']}")
    
    if validation['issues']:
        print(f"\n⚠️ Issues Found:")
        for issue in validation['issues']:
            print(f"  - {issue}")
    else:
        print(f"\n✅ No issues detected")
    
    # Test setup instructions
    if is_replit:
        print(f"\n📋 Replit Setup Instructions:")
        instructions = drive_manager.get_replit_setup_instructions()
        if instructions['success']:
            print(f"Redirect URI: {instructions['redirect_uri']}")
            print(f"\nSetup Steps:")
            for step in instructions['setup_steps']:
                print(f"  {step}")
        else:
            print(f"❌ Error getting instructions: {instructions['error']}")
    
    print("\n" + "=" * 50)

def test_auth_url_generation():
    """Test authorization URL generation"""
    print("🔗 Testing Authorization URL Generation")
    print("=" * 50)
    
    # Create Google Drive manager
    drive_manager = GoogleDriveManager(auto_init=False)
    
    # Test getting auth URL
    try:
        auth_result = drive_manager.get_auth_url()
        if auth_result['success']:
            print(f"✅ Auth URL generated successfully")
            print(f"Environment: {auth_result['environment']}")
            print(f"Redirect URI: {auth_result['redirect_uri']}")
            print(f"Auth URL: {auth_result['auth_url'][:100]}...")
        else:
            print(f"❌ Failed to generate auth URL: {auth_result['error']}")
    except Exception as e:
        print(f"❌ Error testing auth URL generation: {str(e)}")
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    print("🧪 Testing Replit Google Drive Authentication Updates")
    print("=" * 60)
    
    test_replit_environment()
    test_auth_url_generation()
    
    print("✅ Testing completed!") 