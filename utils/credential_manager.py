import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from utils.logger import setup_logging

logger = setup_logging(__name__)

class CredentialManager:
    """
    Manages persistent credential storage optimized for both local and Replit environments
    """
    
    def __init__(self):
        """Initialize credential manager with environment-appropriate storage paths"""
        self.is_replit = bool(os.environ.get('REPL_ID'))
        self.credentials_dir = self._get_credentials_directory()
        self.newspapers_cookies_file = os.path.join(self.credentials_dir, 'newspapers_cookies.json')
        self.lapl_cookies_file = os.path.join(self.credentials_dir, 'lapl_cookies.json')
        
        # Ensure credentials directory exists
        os.makedirs(self.credentials_dir, exist_ok=True)
        
        logger.info(f"Credential manager initialized for {'Replit' if self.is_replit else 'local'} environment")
        logger.info(f"Credentials directory: {self.credentials_dir}")
    
    def _get_credentials_directory(self) -> str:
        """Get the appropriate directory for storing credentials based on environment"""
        if self.is_replit:
            # In Replit, use a persistent directory that survives restarts
            # Replit provides persistent storage in the project root
            return os.path.join(os.getcwd(), '.credentials')
        else:
            # In local environment, use current directory
            return os.getcwd()
    
    def save_newspapers_cookies(self, cookies_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save newspapers.com cookies to persistent storage
        
        Args:
            cookies_data: Dictionary or list of cookies from uploaded JSON
            
        Returns:
            dict: Result of save operation
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
                        logger.warning(f"Skipping malformed newspapers.com cookie: {cookie}")
            else:
                normalized_cookies = cookies_data
            
            # Add metadata
            cookies_with_metadata = {
                'cookies': normalized_cookies,
                'saved_at': __import__('datetime').datetime.now().isoformat(),
                'environment': 'replit' if self.is_replit else 'local',
                'cookie_count': len(normalized_cookies)
            }
            
            # Save to file
            with open(self.newspapers_cookies_file, 'w') as f:
                json.dump(cookies_with_metadata, f, indent=2)
            
            logger.info(f"Saved newspapers.com cookies: {len(normalized_cookies)} cookies to {self.newspapers_cookies_file}")
            
            return {
                'success': True,
                'message': f'Saved {len(normalized_cookies)} cookies',
                'file_path': self.newspapers_cookies_file,
                'cookie_count': len(normalized_cookies)
            }
            
        except Exception as e:
            logger.error(f"Failed to save newspapers.com cookies: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def load_newspapers_cookies(self) -> Dict[str, Any]:
        """
        Load newspapers.com cookies from persistent storage
        
        Returns:
            dict: Result with cookies data or error
        """
        try:
            if not os.path.exists(self.newspapers_cookies_file):
                return {
                    'success': False,
                    'error': 'No saved newspapers.com cookies found'
                }
            
            with open(self.newspapers_cookies_file, 'r') as f:
                cookies_data = json.load(f)
            
            # Extract just the cookies dictionary
            cookies = cookies_data.get('cookies', {})
            metadata = {
                'saved_at': cookies_data.get('saved_at'),
                'cookie_count': cookies_data.get('cookie_count', len(cookies)),
                'environment': cookies_data.get('environment')
            }
            
            logger.info(f"Loaded newspapers.com cookies: {len(cookies)} cookies from {self.newspapers_cookies_file}")
            
            return {
                'success': True,
                'cookies': cookies,
                'metadata': metadata,
                'file_path': self.newspapers_cookies_file
            }
            
        except Exception as e:
            logger.error(f"Failed to load newspapers.com cookies: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def save_lapl_cookies(self, cookies_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save LAPL cookies to persistent storage
        
        Args:
            cookies_data: Dictionary or list of cookies from uploaded JSON
            
        Returns:
            dict: Result of save operation
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
                        logger.warning(f"Skipping malformed LAPL cookie: {cookie}")
            else:
                normalized_cookies = cookies_data
            
            # Add metadata
            cookies_with_metadata = {
                'cookies': normalized_cookies,
                'saved_at': __import__('datetime').datetime.now().isoformat(),
                'environment': 'replit' if self.is_replit else 'local',
                'cookie_count': len(normalized_cookies)
            }
            
            # Save to file
            with open(self.lapl_cookies_file, 'w') as f:
                json.dump(cookies_with_metadata, f, indent=2)
            
            logger.info(f"Saved LAPL cookies: {len(normalized_cookies)} cookies to {self.lapl_cookies_file}")
            
            return {
                'success': True,
                'message': f'Saved {len(normalized_cookies)} cookies',
                'file_path': self.lapl_cookies_file,
                'cookie_count': len(normalized_cookies)
            }
            
        except Exception as e:
            logger.error(f"Failed to save LAPL cookies: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def load_lapl_cookies(self) -> Dict[str, Any]:
        """
        Load LAPL cookies from persistent storage
        
        Returns:
            dict: Result with cookies data or error
        """
        try:
            if not os.path.exists(self.lapl_cookies_file):
                return {
                    'success': False,
                    'error': 'No saved LAPL cookies found'
                }
            
            with open(self.lapl_cookies_file, 'r') as f:
                cookies_data = json.load(f)
            
            # Extract just the cookies dictionary
            cookies = cookies_data.get('cookies', {})
            metadata = {
                'saved_at': cookies_data.get('saved_at'),
                'cookie_count': cookies_data.get('cookie_count', len(cookies)),
                'environment': cookies_data.get('environment')
            }
            
            logger.info(f"Loaded LAPL cookies: {len(cookies)} cookies from {self.lapl_cookies_file}")
            
            return {
                'success': True,
                'cookies': cookies,
                'metadata': metadata,
                'file_path': self.lapl_cookies_file
            }
            
        except Exception as e:
            logger.error(f"Failed to load LAPL cookies: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
