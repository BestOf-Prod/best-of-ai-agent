import os
import io
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
import tempfile
import zipfile
from pathlib import Path

from utils.logger import setup_logging

# Setup logging
logger = setup_logging(__name__)

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseUpload, MediaFileUpload
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    GOOGLE_DRIVE_AVAILABLE = True
    logger.info("Google Drive API libraries imported successfully")
except ImportError as e:
    # Create dummy classes to prevent NameError
    build = None
    MediaIoBaseUpload = None
    MediaFileUpload = None
    Credentials = None
    Request = None
    InstalledAppFlow = None
    GOOGLE_DRIVE_AVAILABLE = False
    logger.warning(f"Google Drive API libraries not available: {str(e)}")

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Check if running on Replit by looking for REPL_ID environment variable
IS_REPLIT = bool(os.environ.get('REPL_ID') or os.environ.get('REPL_SLUG'))

class GoogleDriveManager:
    """
    Manages interactions with Google Drive API for uploading documents and images
    """
    
    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None, auto_init: bool = False):
        """
        Initialize the Google Drive manager
        
        Args:
            credentials_path (str, optional): Path to credentials.json file
            token_path (str, optional): Path to token.json file for stored credentials
            auto_init (bool): Whether to automatically initialize service (default: False)
        """
        self.credentials_path = credentials_path or 'credentials.json'
        self.token_path = token_path or 'token.json'
        self.service = None
        self.creds = None
        
        if GOOGLE_DRIVE_AVAILABLE and auto_init:
            try:
                self._initialize_service()
                logger.info("Google Drive manager initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Google Drive service: {str(e)}")
        else:
            logger.info("Google Drive manager created (not auto-initialized)")
    
    def _get_replit_url(self) -> str:
        """
        Get the current Replit URL in the correct format
        
        Returns:
            str: The Replit URL in the format slug.owner.replit.co
        """
        repl_slug = os.environ.get('REPL_SLUG', 'best-of-ai-agent')
        repl_owner = os.environ.get('REPL_OWNER', 'ajoelfischer')
        
        # Validate that we have the required environment variables
        if not repl_slug or repl_slug == 'best-of-ai-agent':
            logger.warning("REPL_SLUG not found or using default value")
        if not repl_owner or repl_owner == 'ajoelfischer':
            logger.warning("REPL_OWNER not found or using default value")
            
        return f"{repl_slug}-{repl_owner}.replit.app"
    
    def validate_replit_environment(self) -> Dict[str, Any]:
        """
        Validate Replit environment configuration and provide diagnostics
        
        Returns:
            dict: Validation results and diagnostic information
        """
        try:
            is_replit = IS_REPLIT
            repl_slug = os.environ.get('REPL_SLUG')
            repl_owner = os.environ.get('REPL_OWNER')
            repl_id = os.environ.get('REPL_ID')
            
            validation = {
                'is_replit': is_replit,
                'repl_slug': repl_slug,
                'repl_owner': repl_owner,
                'repl_id': repl_id,
                'replit_url': self._get_replit_url() if is_replit else None,
                'redirect_uri': f"https://{self._get_replit_url()}/oauth/callback" if is_replit else None,
                'issues': []
            }
            
            if is_replit:
                if not repl_slug:
                    validation['issues'].append("REPL_SLUG environment variable not found")
                if not repl_owner:
                    validation['issues'].append("REPL_OWNER environment variable not found")
                if not repl_id:
                    validation['issues'].append("REPL_ID environment variable not found")
                    
                # Check if credentials file exists
                if not os.path.exists(self.credentials_path):
                    validation['issues'].append(f"Credentials file not found: {self.credentials_path}")
                    
            return validation
            
        except Exception as e:
            logger.error(f"Error validating Replit environment: {str(e)}")
            return {
                'is_replit': False,
                'error': str(e),
                'issues': [f"Validation error: {str(e)}"]
            }
    
    def _initialize_service(self):
        """Initialize Google Drive service with authentication"""
        creds = None
        
        # The file token.json stores the user's access and refresh tokens.
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise Exception(f"Google Drive credentials file not found: {self.credentials_path}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES)
                
                # Configure flow to request offline access for refresh tokens
                flow.redirect_uri = None  # Will be set appropriately by each method
                
                # Handle Replit environment differently
                if IS_REPLIT:
                    logger.info("Detected Replit environment - using manual authentication flow")
                    try:
                        # For Replit, we need to use the external URL with proper format
                        replit_url = self._get_replit_url()
                        redirect_uri = f"https://{replit_url}/oauth/callback"
                        logger.info(f"Using Replit redirect URI: {redirect_uri}")
                        
                        # Configure flow for Replit environment
                        flow.redirect_uri = redirect_uri
                        flow.prompt = 'consent'
                        flow.access_type = 'offline'
                        flow.include_granted_scopes = True
                        
                        # Create authorization URL for manual process
                        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
                        
                        raise Exception(f"""
                        Replit OAuth Setup Required:
                        
                        1. Open this URL in your browser: {auth_url}
                        2. Authorize the application  
                        3. Copy the authorization code from the redirect URL
                        4. Use the 'Manual Auth Code' option in the sidebar
                        
                        Google Cloud Console Setup:
                        - Add this redirect URI: {redirect_uri}
                        - Make sure Google Drive API is enabled in your project
                        """)
                    except Exception as replit_error:
                        logger.error(f"Replit-specific auth failed: {replit_error}")
                        raise Exception("Authentication failed in Replit environment. Please use manual authentication method.")
                else:
                    # Standard local development environment
                    logger.info("Using standard local server authentication with fixed port")
                    
                    # Use a fixed port order to ensure consistency
                    preferred_ports = [8080, 8000, 3000, 5000, 9000]
                    
                    creds = None
                    successful_port = None
                    
                    # First configure the flow for offline access
                    flow.prompt = 'consent'
                    flow.access_type = 'offline'
                    flow.include_granted_scopes = True
                    
                    for port in preferred_ports:
                        try:
                            logger.info(f"Trying local server on port {port} with offline access")
                            creds = flow.run_local_server(port=port, open_browser=True)
                            successful_port = port
                            logger.info(f"Successfully authenticated using port {port}")
                            
                            # Verify we got a refresh token
                            if hasattr(creds, 'refresh_token') and creds.refresh_token:
                                logger.info("✅ Refresh token obtained successfully")
                            else:
                                logger.warning("⚠️ No refresh token obtained - this may cause future authentication issues")
                            break
                        except Exception as port_error:
                            logger.warning(f"Port {port} failed: {port_error}")
                            continue
                    
                    if creds is None:
                        # If all ports fail, provide manual auth instructions
                        auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
                        raise Exception(f"""
                        Local server authentication failed on all ports. Please use manual authentication:
                        
                        1. Open this URL in your browser: {auth_url}
                        2. Complete the authorization process
                        3. Add these redirect URIs to your Google Cloud Console:
                           - http://localhost:8080/
                           - http://localhost:8000/
                           - http://localhost:3000/
                           - http://localhost:5000/
                           - http://localhost:9000/
                        4. Use the manual authentication method in the sidebar
                        
                        Most likely issue: Missing redirect URI in Google Cloud Console
                        """)
            
            # Save the credentials for the next run
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
        
        self.creds = creds
        self.service = build('drive', 'v3', credentials=creds)
        logger.info("Google Drive service initialized and authenticated")
    
    def initialize_if_ready(self) -> Dict[str, Any]:
        """
        Initialize service only if credentials are available (non-interactive)
        
        Returns:
            dict: Result of initialization attempt
        """
        try:
            if not GOOGLE_DRIVE_AVAILABLE:
                return {'success': False, 'error': 'Google Drive libraries not available'}
            
            if not os.path.exists(self.credentials_path):
                return {'success': False, 'error': 'Credentials file not found'}
            
            # Only initialize if we have a valid token file (no interactive auth)
            if os.path.exists(self.token_path):
                from google.oauth2.credentials import Credentials
                from google.auth.transport.requests import Request
                
                try:
                    creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
                except Exception as token_error:
                    logger.error(f"Failed to load token file: {str(token_error)}")
                    return {'success': False, 'error': f'Invalid token file: {str(token_error)}'}
                
                # Check if credentials have refresh token
                if not hasattr(creds, 'refresh_token') or not creds.refresh_token:
                    logger.warning("Token file missing refresh_token - full re-authentication required")
                    return {
                        'success': False, 
                        'error': 'Missing refresh token - please re-authenticate to get offline access',
                        'requires_reauth': True
                    }
                
                # Check if credentials are valid or can be refreshed
                if creds.valid:
                    self.creds = creds
                    self.service = build('drive', 'v3', credentials=creds)
                    logger.info("Google Drive service initialized from existing token")
                    return {'success': True, 'message': 'Initialized from existing credentials'}
                elif creds.expired and creds.refresh_token:
                    try:
                        logger.info("Refreshing expired Google Drive token...")
                        creds.refresh(Request())
                        self.creds = creds
                        self.service = build('drive', 'v3', credentials=creds)
                        
                        # Save refreshed credentials
                        with open(self.token_path, 'w') as token:
                            token.write(creds.to_json())
                        
                        logger.info("Google Drive service initialized with refreshed token")
                        return {'success': True, 'message': 'Initialized with refreshed credentials'}
                    except Exception as e:
                        logger.warning(f"Token refresh failed: {str(e)}")
                        
                        # If refresh fails, the refresh token might be invalid
                        if 'refresh_token' in str(e).lower():
                            return {
                                'success': False, 
                                'error': f'Refresh token invalid - please re-authenticate: {str(e)}',
                                'requires_reauth': True
                            }
                        else:
                            return {'success': False, 'error': f'Token refresh failed: {str(e)}'}
                else:
                    return {
                        'success': False, 
                        'error': 'Authentication required - expired token without refresh capability',
                        'requires_reauth': True
                    }
            else:
                return {'success': False, 'error': 'No authentication token found'}
                
        except Exception as e:
            logger.error(f"Initialization check failed: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def create_folder(self, folder_name: str, parent_folder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a folder in Google Drive
        
        Args:
            folder_name (str): Name of the folder to create
            parent_folder_id (str, optional): ID of parent folder. If None, creates in root
            
        Returns:
            dict: Result with folder information or error
        """
        logger.info(f"Creating Google Drive folder: {folder_name}")
        
        try:
            if not GOOGLE_DRIVE_AVAILABLE or not self.service:
                return {
                    'success': False,
                    'error': 'Google Drive service not available'
                }
            
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            folder = self.service.files().create(body=file_metadata, fields='id,name,webViewLink').execute()
            
            logger.info(f"Successfully created folder: {folder_name} (ID: {folder.get('id')})")
            
            return {
                'success': True,
                'folder_id': folder.get('id'),
                'folder_name': folder.get('name'),
                'folder_url': folder.get('webViewLink'),
                'created_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to create Google Drive folder {folder_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'folder_name': folder_name
            }
    
    def upload_file(self, file_path: str, filename: Optional[str] = None, 
                   folder_id: Optional[str] = None, mime_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a file to Google Drive
        
        Args:
            file_path (str): Path to the file to upload
            filename (str, optional): Name for the file in Drive. If None, uses original filename
            folder_id (str, optional): ID of folder to upload to. If None, uploads to root
            mime_type (str, optional): MIME type of the file. If None, auto-detects
            
        Returns:
            dict: Result with file information or error
        """
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': f'File not found: {file_path}'
            }
        
        upload_filename = filename or os.path.basename(file_path)
        logger.info(f"Uploading file to Google Drive: {upload_filename}")
        
        try:
            if not GOOGLE_DRIVE_AVAILABLE or not self.service:
                return {
                    'success': False,
                    'error': 'Google Drive service not available'
                }
            
            file_metadata = {'name': upload_filename}
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            # Auto-detect MIME type if not provided
            if not mime_type:
                if upload_filename.endswith('.docx'):
                    mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                elif upload_filename.endswith('.pdf'):
                    mime_type = 'application/pdf'
                elif upload_filename.endswith('.zip'):
                    mime_type = 'application/zip'
                elif upload_filename.endswith(('.png', '.jpg', '.jpeg')):
                    mime_type = 'image/jpeg' if upload_filename.endswith(('.jpg', '.jpeg')) else 'image/png'
                else:
                    mime_type = 'application/octet-stream'
            
            media = MediaFileUpload(file_path, mimetype=mime_type)
            file = self.service.files().create(
                body=file_metadata, 
                media_body=media,
                fields='id,name,webViewLink,size'
            ).execute()
            
            logger.info(f"Successfully uploaded file: {upload_filename} (ID: {file.get('id')})")
            
            return {
                'success': True,
                'file_id': file.get('id'),
                'file_name': file.get('name'),
                'file_url': file.get('webViewLink'),
                'file_size': file.get('size', 0),
                'uploaded_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to upload file {upload_filename}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'file_path': file_path
            }
    
    def upload_folder_as_zip(self, folder_path: str, zip_name: Optional[str] = None, 
                           drive_folder_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload a local folder as a zip file to Google Drive
        
        Args:
            folder_path (str): Path to the folder to zip and upload
            zip_name (str, optional): Name for the zip file. If None, uses folder name
            drive_folder_id (str, optional): ID of Drive folder to upload to
            
        Returns:
            dict: Result with zip file information or error
        """
        if not os.path.exists(folder_path):
            return {
                'success': False,
                'error': f'Folder not found: {folder_path}'
            }
        
        folder_name = os.path.basename(folder_path.rstrip('/'))
        zip_filename = zip_name or f"{folder_name}.zip"
        
        logger.info(f"Creating zip from folder and uploading to Google Drive: {zip_filename}")
        
        try:
            # Create temporary zip file
            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
                temp_zip_path = temp_zip.name
            
            # Create zip file from folder
            with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Get relative path from the folder being zipped
                        arcname = os.path.relpath(file_path, folder_path)
                        zipf.write(file_path, arcname)
                        logger.debug(f"Added to zip: {arcname}")
            
            # Upload the zip file
            result = self.upload_file(
                file_path=temp_zip_path,
                filename=zip_filename,
                folder_id=drive_folder_id,
                mime_type='application/zip'
            )
            
            # Clean up temporary file
            try:
                os.unlink(temp_zip_path)
            except Exception as e:
                logger.warning(f"Failed to clean up temporary zip file: {str(e)}")
            
            if result['success']:
                logger.info(f"Successfully uploaded folder as zip: {zip_filename}")
                result['original_folder'] = folder_path
                result['zip_name'] = zip_filename
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to upload folder as zip {zip_filename}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'folder_path': folder_path
            }
    
    def upload_document_and_images(self, document_path: str, images_folder_path: str, 
                                 project_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload both a Word document and images folder to a new Google Drive folder
        
        Args:
            document_path (str): Path to the Word document
            images_folder_path (str): Path to the images folder
            project_name (str, optional): Name for the project folder. If None, generates from timestamp
            
        Returns:
            dict: Result with uploaded files information or error
        """
        if not os.path.exists(document_path):
            return {
                'success': False,
                'error': f'Document not found: {document_path}'
            }
        
        if not os.path.exists(images_folder_path):
            return {
                'success': False,
                'error': f'Images folder not found: {images_folder_path}'
            }
        
        # Generate project folder name
        if not project_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            project_name = f"Article_Export_{timestamp}"
        
        logger.info(f"Uploading document and images to Google Drive project: {project_name}")
        
        try:
            # Create main project folder
            folder_result = self.create_folder(project_name)
            if not folder_result['success']:
                return folder_result
            
            project_folder_id = folder_result['folder_id']
            project_folder_url = folder_result['folder_url']
            
            # Upload the Word document
            doc_result = self.upload_file(
                file_path=document_path,
                folder_id=project_folder_id
            )
            
            if not doc_result['success']:
                logger.error(f"Failed to upload document: {doc_result['error']}")
                return doc_result
            
            # Upload images folder as zip
            images_result = self.upload_folder_as_zip(
                folder_path=images_folder_path,
                zip_name="article_images.zip",
                drive_folder_id=project_folder_id
            )
            
            if not images_result['success']:
                logger.error(f"Failed to upload images: {images_result['error']}")
                return images_result
            
            logger.info(f"Successfully uploaded document and images to Google Drive project: {project_name}")
            
            return {
                'success': True,
                'project_name': project_name,
                'project_folder_id': project_folder_id,
                'project_folder_url': project_folder_url,
                'document': {
                    'file_id': doc_result['file_id'],
                    'file_name': doc_result['file_name'],
                    'file_url': doc_result['file_url'],
                    'file_size': doc_result['file_size']
                },
                'images_zip': {
                    'file_id': images_result['file_id'],
                    'file_name': images_result['file_name'], 
                    'file_url': images_result['file_url'],
                    'file_size': images_result['file_size']
                },
                'uploaded_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to upload document and images: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'document_path': document_path,
                'images_folder_path': images_folder_path
            }
    
    def set_file_permissions(self, file_id: str, role: str = 'reader', type: str = 'anyone') -> Dict[str, Any]:
        """
        Set sharing permissions for a file or folder
        
        Args:
            file_id (str): ID of the file or folder
            role (str): Permission role ('reader', 'writer', 'owner')
            type (str): Permission type ('user', 'group', 'domain', 'anyone')
            
        Returns:
            dict: Result of permission setting
        """
        logger.info(f"Setting permissions for file {file_id}: {role} for {type}")
        
        try:
            if not GOOGLE_DRIVE_AVAILABLE or not self.service:
                return {
                    'success': False,
                    'error': 'Google Drive service not available'
                }
            
            permission = {
                'role': role,
                'type': type
            }
            
            self.service.permissions().create(
                fileId=file_id,
                body=permission
            ).execute()
            
            logger.info(f"Successfully set permissions for file {file_id}")
            
            return {
                'success': True,
                'file_id': file_id,
                'role': role,
                'type': type
            }
            
        except Exception as e:
            logger.error(f"Failed to set permissions for file {file_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'file_id': file_id
            }
    
    def authenticate_with_code(self, auth_code: str) -> Dict[str, Any]:
        """
        Authenticate using manual authorization code (for Replit/cloud environments)
        
        Args:
            auth_code (str): Authorization code from OAuth flow
            
        Returns:
            dict: Result of authentication
        """
        logger.info("Attempting manual authentication with authorization code")
        
        try:
            if not GOOGLE_DRIVE_AVAILABLE:
                return {
                    'success': False,
                    'error': 'Google Drive service not available'
                }
            
            if not os.path.exists(self.credentials_path):
                return {
                    'success': False,
                    'error': f'Credentials file not found: {self.credentials_path}'
                }
            
            # Create flow and exchange code for credentials
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, SCOPES)
            
            # Configure flow for offline access to get refresh tokens
            flow.prompt = 'consent'
            flow.access_type = 'offline'
            flow.include_granted_scopes = True
            
            # For Replit, set up proper redirect URI
            if IS_REPLIT:
                # Use the correct .replit.co domain format for Replit apps
                replit_url = self._get_replit_url()
                flow.redirect_uri = f"https://{replit_url}/oauth/callback"
            
            # Exchange authorization code for credentials
            flow.fetch_token(code=auth_code)
            creds = flow.credentials
            
            # Verify we got a refresh token
            if hasattr(creds, 'refresh_token') and creds.refresh_token:
                logger.info("✅ Refresh token obtained successfully via manual authentication")
            else:
                logger.warning("⚠️ No refresh token obtained via manual authentication - this may cause future issues")
            
            # Save the credentials
            with open(self.token_path, 'w') as token:
                token.write(creds.to_json())
            
            # Initialize the service
            self.creds = creds
            self.service = build('drive', 'v3', credentials=creds)
            
            logger.info("Manual authentication successful")
            
            return {
                'success': True,
                'message': 'Authentication successful! Google Drive is now configured.'
            }
            
        except Exception as e:
            logger.error(f"Manual authentication failed: {str(e)}")
            return {
                'success': False,
                'error': f'Authentication failed: {str(e)}'
            }
    
    def get_auth_url(self) -> Dict[str, Any]:
        """
        Get authorization URL for manual authentication (Replit-friendly)
        
        Returns:
            dict: Result with authorization URL
        """
        try:
            if not os.path.exists(self.credentials_path):
                return {
                    'success': False,
                    'error': f'Credentials file not found: {self.credentials_path}'
                }
            
            flow = InstalledAppFlow.from_client_secrets_file(
                self.credentials_path, SCOPES)
            
            # For Replit, configure proper redirect URI
            if IS_REPLIT:
                # Use the correct .replit.co domain format for Replit apps
                replit_url = self._get_replit_url()
                flow.redirect_uri = f"https://{replit_url}/oauth/callback"
                
                auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
                
                return {
                    'success': True,
                    'auth_url': auth_url,
                    'redirect_uri': flow.redirect_uri,
                    'environment': 'replit'
                }
            else:
                # Local development
                auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
                
                return {
                    'success': True,
                    'auth_url': auth_url,
                    'redirect_uri': flow.redirect_uri,
                    'environment': 'local'
                }
                
        except Exception as e:
            logger.error(f"Failed to get auth URL: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_available_port(self) -> int:
        """
        Get the first available port from our preferred list
        
        Returns:
            int: Available port number, or None if none available
        """
        import socket
        
        preferred_ports = [8080, 8000, 3000, 5000, 9000]
        
        for port in preferred_ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return port
            except OSError:
                continue
        return None
    
    def get_redirect_uri_info(self) -> Dict[str, Any]:
        """
        Get information about redirect URIs for Google Cloud Console setup
        
        Returns:
            dict: Redirect URI configuration info
        """
        is_replit = IS_REPLIT
        
        if is_replit:
            # Use the correct .replit.co domain format for Replit apps
            replit_url = self._get_replit_url()
            return {
                'environment': 'replit',
                'redirect_uris': [
                    f'https://{replit_url}/oauth/callback'
                ],
                'instructions': f'Add this URI to your Google Cloud Console for Replit: https://{replit_url}/oauth/callback'
            }
        else:
            available_port = self.get_available_port()
            return {
                'environment': 'local',
                'redirect_uris': [
                    'http://localhost:8080/',
                    'http://localhost:8000/',
                    'http://localhost:3000/',
                    'http://localhost:5000/',
                    'http://localhost:9000/'
                ],
                'preferred_port': available_port,
                'primary_uri': f'http://localhost:{available_port}/' if available_port else 'http://localhost:8080/',
                'instructions': 'Add these URIs to your Google Cloud Console for local development'
            }
    
    def get_replit_setup_instructions(self) -> Dict[str, Any]:
        """
        Get detailed setup instructions for Replit environment
        
        Returns:
            dict: Setup instructions and configuration details
        """
        try:
            if not IS_REPLIT:
                return {
                    'success': False,
                    'error': 'Not running in Replit environment'
                }
            
            replit_url = self._get_replit_url()
            redirect_uri = f"https://{replit_url}/oauth/callback"
            
            instructions = {
                'success': True,
                'environment': 'replit',
                'replit_url': replit_url,
                'redirect_uri': redirect_uri,
                'setup_steps': [
                    "1. Open Google Cloud Console: https://console.cloud.google.com/",
                    "2. Navigate to APIs & Services → Credentials",
                    "3. Click on your OAuth 2.0 Client ID",
                    f"4. Add this redirect URI: {redirect_uri}",
                    "5. Make sure Google Drive API is enabled in your project",
                    "6. Save the changes",
                    "7. Return to this app and use the authentication flow"
                ],
                'common_issues': [
                    "Make sure you're using the correct redirect URI format",
                    "Ensure Google Drive API is enabled in your Google Cloud project",
                    "Check that your OAuth consent screen is configured properly",
                    "Verify that your credentials.json file is uploaded correctly"
                ],
                'validation': self.validate_replit_environment()
            }
            
            return instructions
            
        except Exception as e:
            logger.error(f"Error generating Replit setup instructions: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def is_available(self) -> bool:
        """
        Check if Google Drive integration is available and configured
        
        Returns:
            bool: True if Google Drive is available and configured
        """
        return GOOGLE_DRIVE_AVAILABLE and self.service is not None