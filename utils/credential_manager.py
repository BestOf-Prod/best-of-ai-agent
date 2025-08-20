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
        self.google_credentials_file = os.path.join(self.credentials_dir, 'credentials.json')
        self.google_token_file = os.path.join(self.credentials_dir, 'token.json')
        
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
    
    def save_google_credentials(self, credentials_content: str) -> Dict[str, Any]:
        """
        Save Google Drive credentials to persistent storage
        
        Args:
            credentials_content: JSON content of Google credentials file
            
        Returns:
            dict: Result of save operation
        """
        try:
            # Validate JSON format
            try:
                credentials_json = json.loads(credentials_content)
                if 'installed' not in credentials_json and 'web' not in credentials_json:
                    return {
                        'success': False,
                        'error': 'Invalid credentials format - should contain "installed" or "web" key'
                    }
            except json.JSONDecodeError as e:
                return {
                    'success': False,
                    'error': f'Invalid JSON format: {str(e)}'
                }
            
            # Save to file
            with open(self.google_credentials_file, 'w') as f:
                f.write(credentials_content)
            
            logger.info(f"Saved Google Drive credentials to {self.google_credentials_file}")
            
            return {
                'success': True,
                'message': 'Google Drive credentials saved successfully',
                'file_path': self.google_credentials_file,
                'type': 'installed' if 'installed' in credentials_json else 'web'
            }
            
        except Exception as e:
            logger.error(f"Failed to save Google Drive credentials: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def has_google_credentials(self) -> bool:
        """Check if Google Drive credentials exist"""
        return os.path.exists(self.google_credentials_file)
    
    def has_google_token(self) -> bool:
        """Check if Google Drive token exists"""
        return os.path.exists(self.google_token_file)
    
    def has_newspapers_cookies(self) -> bool:
        """Check if newspapers.com cookies exist"""
        return os.path.exists(self.newspapers_cookies_file)
    
    def has_lapl_cookies(self) -> bool:
        """Check if LAPL cookies exist"""
        return os.path.exists(self.lapl_cookies_file)
    
    def get_google_credentials_status(self) -> Dict[str, Any]:
        """
        Get status of Google Drive credentials
        
        Returns:
            dict: Status information
        """
        has_creds = self.has_google_credentials()
        has_token = self.has_google_token()
        
        status = {
            'has_credentials': has_creds,
            'has_token': has_token,
            'credentials_path': self.google_credentials_file,
            'token_path': self.google_token_file,
            'ready_for_auth': has_creds,
            'authenticated': has_creds and has_token
        }
        
        if has_creds:
            try:
                # Get credentials type
                with open(self.google_credentials_file, 'r') as f:
                    creds_data = json.load(f)
                status['credentials_type'] = 'installed' if 'installed' in creds_data else 'web'
            except Exception as e:
                logger.warning(f"Could not read credentials file: {str(e)}")
                status['credentials_type'] = 'unknown'
        
        return status
    
    def get_newspapers_status(self) -> Dict[str, Any]:
        """
        Get status of newspapers.com cookies
        
        Returns:
            dict: Status information
        """
        has_cookies = self.has_newspapers_cookies()
        
        status = {
            'has_cookies': has_cookies,
            'cookies_path': self.newspapers_cookies_file,
            'ready_for_auth': has_cookies
        }
        
        if has_cookies:
            try:
                # Get cookie metadata
                with open(self.newspapers_cookies_file, 'r') as f:
                    cookies_data = json.load(f)
                status.update({
                    'cookie_count': cookies_data.get('cookie_count', 0),
                    'saved_at': cookies_data.get('saved_at'),
                    'environment': cookies_data.get('environment')
                })
            except Exception as e:
                logger.warning(f"Could not read cookies file: {str(e)}")
                status['cookie_count'] = 0
        
        return status
    
    def get_lapl_status(self) -> Dict[str, Any]:
        """
        Get status of LAPL cookies
        
        Returns:
            dict: Status information
        """
        has_cookies = self.has_lapl_cookies()
        
        status = {
            'has_cookies': has_cookies,
            'cookies_path': self.lapl_cookies_file,
            'ready_for_auth': has_cookies
        }
        
        if has_cookies:
            try:
                # Get cookie metadata
                with open(self.lapl_cookies_file, 'r') as f:
                    cookies_data = json.load(f)
                status.update({
                    'cookie_count': cookies_data.get('cookie_count', 0),
                    'saved_at': cookies_data.get('saved_at'),
                    'environment': cookies_data.get('environment')
                })
            except Exception as e:
                logger.warning(f"Could not read LAPL cookies file: {str(e)}")
                status['cookie_count'] = 0
        
        return status
    
    def clear_lapl_cookies(self) -> Dict[str, Any]:
        """
        Clear saved LAPL cookies
        
        Returns:
            dict: Result of clear operation
        """
        try:
            if os.path.exists(self.lapl_cookies_file):
                os.remove(self.lapl_cookies_file)
                logger.info("Cleared LAPL cookies")
                return {
                    'success': True,
                    'message': 'LAPL cookies cleared'
                }
            else:
                return {
                    'success': True,
                    'message': 'No cookies to clear'
                }
        except Exception as e:
            logger.error(f"Failed to clear LAPL cookies: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def clear_newspapers_cookies(self) -> Dict[str, Any]:
        """
        Clear saved newspapers.com cookies
        
        Returns:
            dict: Result of clear operation
        """
        try:
            if os.path.exists(self.newspapers_cookies_file):
                os.remove(self.newspapers_cookies_file)
                logger.info("Cleared newspapers.com cookies")
                return {
                    'success': True,
                    'message': 'Newspapers.com cookies cleared'
                }
            else:
                return {
                    'success': True,
                    'message': 'No cookies to clear'
                }
        except Exception as e:
            logger.error(f"Failed to clear newspapers.com cookies: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def clear_google_credentials(self) -> Dict[str, Any]:
        """
        Clear saved Google Drive credentials and tokens
        
        Returns:
            dict: Result of clear operation
        """
        try:
            files_removed = []
            
            if os.path.exists(self.google_credentials_file):
                os.remove(self.google_credentials_file)
                files_removed.append('credentials.json')
            
            if os.path.exists(self.google_token_file):
                os.remove(self.google_token_file)
                files_removed.append('token.json')
            
            if files_removed:
                logger.info(f"Cleared Google Drive files: {', '.join(files_removed)}")
                return {
                    'success': True,
                    'message': f'Cleared {", ".join(files_removed)}'
                }
            else:
                return {
                    'success': True,
                    'message': 'No credentials to clear'
                }
        except Exception as e:
            logger.error(f"Failed to clear Google Drive credentials: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def clear_invalid_google_token(self) -> Dict[str, Any]:
        """
        Clear only the Google Drive token file (keeping credentials for re-auth)
        
        Returns:
            dict: Result of clear operation
        """
        try:
            if os.path.exists(self.google_token_file):
                os.remove(self.google_token_file)
                logger.info("Cleared invalid Google Drive token file")
                return {
                    'success': True,
                    'message': 'Cleared invalid token file - credentials preserved for re-authentication'
                }
            else:
                return {
                    'success': True,
                    'message': 'No token file to clear'
                }
        except Exception as e:
            logger.error(f"Failed to clear Google Drive token: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_storage_info(self) -> Dict[str, Any]:
        """
        Get information about credential storage
        
        Returns:
            dict: Storage information
        """
        return {
            'environment': 'replit' if self.is_replit else 'local',
            'credentials_directory': self.credentials_dir,
            'newspapers_cookies_file': self.newspapers_cookies_file,
            'lapl_cookies_file': self.lapl_cookies_file,
            'google_credentials_file': self.google_credentials_file,
            'google_token_file': self.google_token_file,
            'newspapers_status': self.get_newspapers_status(),
            'lapl_status': self.get_lapl_status(),
            'google_status': self.get_google_credentials_status()
        }