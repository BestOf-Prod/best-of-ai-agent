import os
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
import io
from utils.logger import setup_logging

# Setup logging
logger = setup_logging(__name__)

# Check if running on Replit by looking for REPL_ID environment variable
REPLIT_STORAGE_AVAILABLE = bool(os.environ.get('REPL_ID'))

if REPLIT_STORAGE_AVAILABLE:
    try:
        from replit.object_storage import Client
        logger.info("Replit Object Storage client imported successfully")
    except ImportError:
        REPLIT_STORAGE_AVAILABLE = False
        logger.warning("Replit Object Storage client not available - running in development mode")
else:
    logger.info("Running in development mode - Replit Object Storage not available")

class StorageManager:
    """
    Manages interactions with Replit Object Storage for uploading generated newspaper clippings
    """
    
    def __init__(self, project_name: Optional[str] = None):
        """
        Initialize the storage manager
        
        Args:
            project_name (str, optional): Name of the project folder to use. If not provided, will use 'default'
        """
        self.project_name = project_name or 'default'
        self.client = None
        
        if REPLIT_STORAGE_AVAILABLE:
            try:
                # If no bucket_id is provided, it uses the default bucket from .replit config
                self.client = Client()
                logger.info(f"Storage manager initialized for project: {self.project_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Replit Storage client: {str(e)}")
        else:
            logger.info("Storage manager initialized in development mode (no uploads)")
    
    def get_project_path(self, filename: str) -> str:
        """
        Get the full path for a file within the project folder
        
        Args:
            filename (str): The filename to get the path for
            
        Returns:
            str: The full path including project folder
        """
        return f"{self.project_name}/{filename}"
    
    def _get_project_path(self, filename: str) -> str:
        """
        Get the full path for a file within the project folder (private method for internal use)
        
        Args:
            filename (str): The filename to get the path for
            
        Returns:
            str: The full path including project folder
        """
        return f"{self.project_name}/{filename}"
    
    def upload_image(self, image_data: bytes, filename: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Upload a newspaper clipping image to Replit Object Storage
        
        Args:
            image_data (bytes): The image data to upload
            filename (str): The filename for the uploaded image
            metadata (dict, optional): Additional metadata to store with the image
            
        Returns:
            dict: Result of the upload operation with success status and details
        """
        logger.info(f"Starting image upload: {filename} to project: {self.project_name}")
        
        try:
            if not REPLIT_STORAGE_AVAILABLE:
                # Development mode - save locally instead
                return self._save_locally(image_data, filename, metadata)
            
            if not self.client:
                raise Exception("Storage client not initialized")
            
            # Add timestamp to filename to avoid conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            
            # Get the full path including project folder
            full_path = self._get_project_path(unique_filename)
            
            # Upload using the official SDK method
            logger.debug(f"Uploading with path '{full_path}'")
            
            self.client.upload_from_bytes(full_path, image_data)
            
            logger.info(f"Successfully uploaded image: {full_path}")
            
            # Prepare metadata for return (the SDK doesn't support metadata in upload)
            upload_metadata = {
                'uploaded_at': datetime.now().isoformat(),
                'content_type': 'image/png',
                'source': 'best-of-ai-agent',
                'project': self.project_name
            }
            
            if metadata:
                upload_metadata.update(metadata)
            
            return {
                'success': True,
                'filename': unique_filename,
                'project': self.project_name,
                'full_path': full_path,
                'metadata': upload_metadata
            }
            
        except Exception as e:
            logger.error(f"Failed to upload image {filename}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }
    
    def _save_locally(self, image_data: bytes, filename: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Save image locally when Replit Object Storage is not available (development mode)
        
        Args:
            image_data (bytes): The image data to save
            filename (str): The filename for the saved image
            metadata (dict, optional): Metadata (will be logged but not stored)
            
        Returns:
            dict: Result of the local save operation
        """
        logger.info(f"Saving image locally (development mode): {filename} to project: {self.project_name}")
        
        try:
            # Ensure local storage directory exists with project subdirectory
            local_storage_dir = os.path.join('local_storage', self.project_name)
            os.makedirs(local_storage_dir, exist_ok=True)
            
            # Add timestamp to filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            local_path = os.path.join(local_storage_dir, unique_filename)
            
            # Save the image
            with open(local_path, 'wb') as f:
                f.write(image_data)
            
            logger.info(f"Successfully saved image locally: {local_path}")
            
            if metadata:
                logger.debug(f"Metadata for {filename}: {metadata}")
            
            return {
                'success': True,
                'filename': unique_filename,
                'project': self.project_name,
                'local_path': local_path,
                'metadata': metadata or {},
                'note': 'Saved locally - Replit Object Storage not available'
            }
            
        except Exception as e:
            logger.error(f"Failed to save image locally {filename}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }
    
    def list_uploaded_images(self) -> Dict[str, Any]:
        """
        List all images in the bucket for the current project
        
        Returns:
            dict: Result with list of images or error information
        """
        logger.info(f"Listing uploaded images for project: {self.project_name}")
        
        try:
            if not REPLIT_STORAGE_AVAILABLE:
                # Development mode - list local files
                return self._list_local_images()
            
            if not self.client:
                raise Exception("Storage client not initialized")
            
            # List objects with project prefix using the official SDK
            prefix = f"{self.project_name}/"
            objects = self.client.list(prefix=prefix)
            
            images = []
            for obj in objects:
                # Remove project prefix from display name
                display_name = obj.name[len(prefix):] if obj.name.startswith(prefix) else obj.name
                
                # Try to get object metadata for size and creation time
                size = 0
                created = 'Unknown'
                try:
                    # Download the object to get its size
                    obj_data = self.client.download_as_bytes(obj.name)
                    size = len(obj_data)
                    
                    # Try to extract creation time from filename timestamp
                    if display_name.startswith('2'):  # Timestamp format: YYYYMMDD_HHMMSS_
                        timestamp_part = display_name.split('_')[0] + '_' + display_name.split('_')[1]
                        try:
                            created_dt = datetime.strptime(timestamp_part, '%Y%m%d_%H%M%S')
                            created = created_dt.isoformat()
                        except ValueError:
                            pass
                except Exception as e:
                    logger.warning(f"Could not get metadata for {obj.name}: {str(e)}")
                
                images.append({
                    'name': display_name,
                    'full_path': obj.name,
                    'size': size,
                    'created': created
                })
            
            logger.info(f"Found {len(images)} images in project {self.project_name}")
            
            return {
                'success': True,
                'project': self.project_name,
                'images': images,
                'count': len(images)
            }
            
        except Exception as e:
            logger.error(f"Failed to list images: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _list_local_images(self) -> Dict[str, Any]:
        """
        List locally saved images (development mode)
        
        Returns:
            dict: Result with list of local images
        """
        try:
            local_storage_dir = os.path.join('local_storage', self.project_name)
            if not os.path.exists(local_storage_dir):
                return {'success': True, 'project': self.project_name, 'images': [], 'count': 0}
            
            images = []
            for filename in os.listdir(local_storage_dir):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    filepath = os.path.join(local_storage_dir, filename)
                    stat = os.stat(filepath)
                    images.append({
                        'name': filename,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'local_path': filepath
                    })
            
            logger.info(f"Found {len(images)} local images in project {self.project_name}")
            
            return {
                'success': True,
                'project': self.project_name,
                'images': images,
                'count': len(images),
                'note': 'Local images - Replit Object Storage not available'
            }
            
        except Exception as e:
            logger.error(f"Failed to list local images: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def download_image(self, object_name: str) -> Dict[str, Any]:
        """
        Download an image from Replit Object Storage
        
        Args:
            object_name (str): The name/path of the object to download
            
        Returns:
            dict: Result with image data or error information
        """
        logger.info(f"Downloading image: {object_name}")
        
        try:
            if not REPLIT_STORAGE_AVAILABLE:
                return {
                    'success': False,
                    'error': 'Replit Object Storage not available in development mode'
                }
            
            if not self.client:
                raise Exception("Storage client not initialized")
            
            # Download using the official SDK
            image_data = self.client.download_as_bytes(object_name)
            
            logger.info(f"Successfully downloaded image: {object_name}")
            
            return {
                'success': True,
                'object_name': object_name,
                'data': image_data,
                'size': len(image_data)
            }
            
        except Exception as e:
            logger.error(f"Failed to download image {object_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'object_name': object_name
            }
    
    def delete_image(self, object_name: str) -> Dict[str, Any]:
        """
        Delete an image from Replit Object Storage
        
        Args:
            object_name (str): The name/path of the object to delete
            
        Returns:
            dict: Result of the delete operation
        """
        logger.info(f"Deleting image: {object_name}")
        
        try:
            if not REPLIT_STORAGE_AVAILABLE:
                return {
                    'success': False,
                    'error': 'Replit Object Storage not available in development mode'
                }
            
            if not self.client:
                raise Exception("Storage client not initialized")
            
            # Delete using the official SDK
            self.client.delete(object_name)
            
            logger.info(f"Successfully deleted image: {object_name}")
            
            return {
                'success': True,
                'object_name': object_name
            }
            
        except Exception as e:
            logger.error(f"Failed to delete image {object_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'object_name': object_name
            }
    
    def check_image_exists(self, object_name: str) -> bool:
        """
        Check if an image exists in Replit Object Storage
        
        Args:
            object_name (str): The name/path of the object to check
            
        Returns:
            bool: True if the object exists, False otherwise
        """
        try:
            if not REPLIT_STORAGE_AVAILABLE or not self.client:
                return False
            
            return self.client.exists(object_name)
            
        except Exception as e:
            logger.error(f"Failed to check if image exists {object_name}: {str(e)}")
            return False

    def get_image_preview(self, object_name: str) -> Dict[str, Any]:
        """
        Get image data for preview display
        
        Args:
            object_name (str): The name/path of the object to preview
            
        Returns:
            dict: Result with image data for preview or error information
        """
        logger.info(f"Getting image preview: {object_name}")
        
        try:
            if not REPLIT_STORAGE_AVAILABLE:
                # Try to load local file for preview
                local_storage_dir = os.path.join('local_storage', self.project_name)
                local_path = os.path.join(local_storage_dir, object_name)
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        image_data = f.read()
                    return {
                        'success': True,
                        'data': image_data,
                        'size': len(image_data),
                        'is_local': True
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Local file not found'
                    }
            
            if not self.client:
                raise Exception("Storage client not initialized")
            
            # Download image from object storage
            image_data = self.client.download_as_bytes(object_name)
            
            logger.info(f"Successfully retrieved image preview: {object_name} ({len(image_data)} bytes)")
            
            return {
                'success': True,
                'data': image_data,
                'size': len(image_data),
                'is_local': False
            }
            
        except Exception as e:
            logger.error(f"Failed to get image preview {object_name}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def store_file(self, filename: str, content: bytes, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Store a file (text, binary, etc.) to storage
        
        Args:
            filename (str): The filename for the file
            content (bytes): The file content as bytes
            metadata (dict, optional): Additional metadata to store with the file
            
        Returns:
            dict: Result of the storage operation with success status and details
        """
        logger.info(f"Starting file storage: {filename} to project: {self.project_name}")
        
        try:
            if not REPLIT_STORAGE_AVAILABLE:
                # Development mode - save locally instead
                return self._store_file_locally(filename, content, metadata)
            
            if not self.client:
                raise Exception("Storage client not initialized")
            
            # Get the full path including project folder
            full_path = self._get_project_path(filename)
            
            # Upload using the official SDK method
            logger.debug(f"Storing file with path '{full_path}'")
            
            self.client.upload_from_bytes(full_path, content)
            
            logger.info(f"Successfully stored file: {full_path}")
            
            return {
                'success': True,
                'filename': filename,
                'project': self.project_name,
                'path': full_path,
                'size': len(content),
                'metadata': metadata or {}
            }
            
        except Exception as e:
            logger.error(f"Failed to store file {filename}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }
    
    def _store_file_locally(self, filename: str, content: bytes, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Store file locally in development mode
        
        Args:
            filename (str): The filename
            content (bytes): The file content
            metadata (dict, optional): Additional metadata
            
        Returns:
            dict: Result of the local storage operation
        """
        try:
            # Create project directory structure
            local_storage_dir = os.path.join('local_storage', self.project_name)
            
            # Handle nested paths in filename
            file_dir = os.path.dirname(filename)
            if file_dir:
                full_dir = os.path.join(local_storage_dir, file_dir)
                os.makedirs(full_dir, exist_ok=True)
            else:
                os.makedirs(local_storage_dir, exist_ok=True)
            
            local_path = os.path.join(local_storage_dir, filename)
            
            # Save the file
            with open(local_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"Successfully stored file locally: {local_path}")
            
            if metadata:
                logger.debug(f"Metadata for {filename}: {metadata}")
            
            return {
                'success': True,
                'filename': filename,
                'project': self.project_name,
                'local_path': local_path,
                'size': len(content),
                'metadata': metadata or {},
                'note': 'Stored locally - Replit Object Storage not available'
            }
            
        except Exception as e:
            logger.error(f"Failed to store file locally {filename}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }
