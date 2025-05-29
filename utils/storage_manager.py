import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import io
from utils.logger import setup_logging

# Setup logging
logger = setup_logging(__name__)

try:
    from replit.object_storage import Client as ReplitStorageClient
    REPLIT_STORAGE_AVAILABLE = True
    logger.info("Replit Object Storage client imported successfully")
except ImportError:
    REPLIT_STORAGE_AVAILABLE = False
    logger.warning("Replit Object Storage client not available - running in development mode")

class StorageManager:
    """
    Manages interactions with Replit Object Storage for uploading generated newspaper clippings
    """
    
    def __init__(self, bucket_name: Optional[str] = None, project_name: Optional[str] = None):
        """
        Initialize the storage manager
        
        Args:
            bucket_name (str, optional): Name of the bucket to use. If not provided, will try to get from environment
            project_name (str, optional): Name of the project folder to use. If not provided, will use 'default'
        """
        self.bucket_name = bucket_name or os.environ.get('REPLIT_BUCKET_NAME', 'newspaper-clippings')
        self.project_name = project_name or 'default'
        self.client = None
        self.bucket = None
        
        if REPLIT_STORAGE_AVAILABLE:
            try:
                self.client = ReplitStorageClient()
                logger.info(f"Storage manager initialized for bucket: {self.bucket_name}, project: {self.project_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Replit Storage client: {str(e)}")
        else:
            logger.info("Storage manager initialized in development mode (no uploads)")
    
    def _get_project_path(self, filename: str) -> str:
        """
        Get the full path for a file within the project folder
        
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
            
            # Ensure we have a bucket
            self._ensure_bucket_exists()
            
            # Prepare the file for upload
            image_file = io.BytesIO(image_data)
            
            # Add timestamp to filename to avoid conflicts
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            unique_filename = f"{timestamp}_{filename}"
            
            # Get the full path including project folder
            full_path = self._get_project_path(unique_filename)
            
            # Prepare metadata
            upload_metadata = {
                'uploaded_at': datetime.now().isoformat(),
                'content_type': 'image/png',
                'source': 'best-of-ai-agent',
                'project': self.project_name
            }
            
            if metadata:
                upload_metadata.update(metadata)
            
            # Upload to Replit Object Storage
            logger.debug(f"Uploading to bucket '{self.bucket_name}' with path '{full_path}'")
            
            result = self.client.upload_file(
                bucket_name=self.bucket_name,
                object_name=full_path,
                file_data=image_file,
                metadata=upload_metadata
            )
            
            logger.info(f"Successfully uploaded image: {full_path}")
            
            return {
                'success': True,
                'filename': unique_filename,
                'project': self.project_name,
                'bucket': self.bucket_name,
                'metadata': upload_metadata,
                'url': f"gs://{self.bucket_name}/{full_path}"  # GCS-style URL
            }
            
        except Exception as e:
            logger.error(f"Failed to upload image {filename}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'filename': filename
            }
    
    def _ensure_bucket_exists(self):
        """
        Ensure the bucket exists, create it if it doesn't
        """
        try:
            if not self.bucket:
                logger.debug(f"Checking if bucket '{self.bucket_name}' exists")
                
                # Try to access the bucket first
                try:
                    self.bucket = self.client.get_bucket(self.bucket_name)
                    logger.debug(f"Bucket '{self.bucket_name}' already exists")
                except Exception:
                    # Bucket doesn't exist, create it
                    logger.info(f"Creating new bucket: {self.bucket_name}")
                    self.bucket = self.client.create_bucket(self.bucket_name)
                    logger.info(f"Successfully created bucket: {self.bucket_name}")
                    
        except Exception as e:
            logger.error(f"Error ensuring bucket exists: {str(e)}")
            raise Exception(f"Failed to ensure bucket '{self.bucket_name}' exists: {str(e)}")
    
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
            
            self._ensure_bucket_exists()
            
            # List objects in the bucket with project prefix
            prefix = f"{self.project_name}/"
            objects = self.client.list_objects(self.bucket_name, prefix=prefix)
            
            images = []
            for obj in objects:
                # Remove project prefix from display name
                display_name = obj.name[len(prefix):] if obj.name.startswith(prefix) else obj.name
                images.append({
                    'name': display_name,
                    'size': obj.size,
                    'created': obj.time_created,
                    'url': f"gs://{self.bucket_name}/{obj.name}"
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