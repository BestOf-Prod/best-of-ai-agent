# utils/batch_processor.py
# Enhanced batch processor with auto-authentication support

import concurrent.futures
import time
import logging
import io
import os
from datetime import datetime
from typing import List, Dict, Callable, Optional
import requests
import threading

from extractors.url_extractor import extract_from_url
from extractors.newspapers_extractor import extract_from_newspapers_com

logger = logging.getLogger(__name__)

def categorize_failure(error_message: str) -> dict:
    """
    Categorize failure types for intelligent retry recommendations
    
    Args:
        error_message (str): The error message from failed extraction
        
    Returns:
        dict: Category information with retry recommendation
    """
    error_lower = error_message.lower()
    
    # Timeout and network issues - highly retryable
    if any(keyword in error_lower for keyword in ['timeout', 'timed out', 'connection', 'network', 'dns']):
        return {
            'category': 'network_timeout',
            'display_name': 'Network/Timeout',
            'retryable': True,
            'recommendation': 'Retry Recommended',
            'icon': '⏱️',
            'priority': 1
        }
    
    # Authentication issues - retryable after credential check
    if any(keyword in error_lower for keyword in ['authentication', 'login', 'unauthorized', 'credentials', 'cookies']):
        return {
            'category': 'authentication',
            'display_name': 'Authentication',
            'retryable': True,
            'recommendation': 'Check Credentials & Retry',
            'icon': '🔐',
            'priority': 2
        }
    
    # Rate limiting - retryable with delay
    if any(keyword in error_lower for keyword in ['rate limit', 'too many requests', '429']):
        return {
            'category': 'rate_limit',
            'display_name': 'Rate Limited',
            'retryable': True,
            'recommendation': 'Retry with Delay',
            'icon': '🚦',
            'priority': 3
        }
    
    # Server errors - moderately retryable
    if any(keyword in error_lower for keyword in ['server error', '500', '502', '503', '504']):
        return {
            'category': 'server_error',
            'display_name': 'Server Error',
            'retryable': True,
            'recommendation': 'Retry Possible',
            'icon': '🔧',
            'priority': 4
        }
    
    # URL/Content issues - generally not retryable
    if any(keyword in error_lower for keyword in ['404', 'not found', 'invalid url', 'malformed']):
        return {
            'category': 'url_invalid',
            'display_name': 'Invalid URL',
            'retryable': False,
            'recommendation': 'Manual Review Required',
            'icon': '🚫',
            'priority': 5
        }
    
    # Generic failures - potentially retryable
    return {
        'category': 'unknown',
        'display_name': 'Unknown Error',
        'retryable': True,
        'recommendation': 'Retry Possible',
        'icon': '❓',
        'priority': 6
    }

class BatchProcessor:
    """Enhanced batch processor with auto-authentication support"""
    
    def __init__(self, storage_manager, max_workers: int = 3, newspapers_cookies: str = "", 
                 newspapers_extractor: Optional = None, lapl_extractor: Optional = None):
        self.storage_manager = storage_manager
        self.max_workers = max_workers
        self.newspapers_cookies = newspapers_cookies
        self.newspapers_extractor = newspapers_extractor
        self.lapl_extractor = lapl_extractor
        # extraction_method parameter removed - using optimized download_clicks only
        self.total_processed = 0
        self.total_successful = 0
        self.total_failed = 0
        self.start_time = None
        self.executor = None  # Initialize as None, create on demand
        self._lock = threading.Lock()  # Add thread safety
        
        logger.info(f"Initialized BatchProcessor with {max_workers} workers")
        if newspapers_extractor:
            logger.info("Using enhanced Newspapers.com extractor with auto-authentication")
        if lapl_extractor:
            logger.info("Using LAPL extractor for NewsBank and ProQuest URLs")
    
    def __del__(self):
        """Cleanup ThreadPoolExecutor on object destruction"""
        self._shutdown_executor()
    
    def _shutdown_executor(self):
        """Safely shutdown the executor"""
        if self.executor is not None:
            try:
                logger.info("Shutting down ThreadPoolExecutor")
                self.executor.shutdown(wait=True)
                self.executor = None
            except Exception as e:
                logger.error(f"Error shutting down executor: {str(e)}")
    
    def _get_executor(self):
        """Get or create the ThreadPoolExecutor"""
        if self.executor is None:
            with self._lock:
                if self.executor is None:  # Double-check pattern
                    logger.info(f"Creating new ThreadPoolExecutor with {self.max_workers} workers")
                    self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers)
        return self.executor
    
    def process_urls_batch(
        self, 
        urls: List[str], 
        progress_callback: Optional[Callable] = None, 
        delay_between_requests: float = 1.0,
        player_name: Optional[str] = None,
        enable_advanced_processing: bool = True,
        project_name: str = "default"
    ) -> Dict:
        """
        Process multiple URLs in batch with enhanced features
        
        Args:
            urls: List of URLs to process
            progress_callback: Function to call with progress updates
            delay_between_requests: Delay between requests in seconds
            player_name: Optional player name for filtering
            enable_advanced_processing: Whether to use advanced image processing
            
        Returns:
            Dictionary with processing results and statistics
        """
        logger.info(f"Starting batch processing of {len(urls)} URLs")
        self.start_time = time.time()
        
        # Set batch processing flag for newspapers extractor timeout adjustments
        os.environ['BATCH_PROCESSING'] = 'true'
        
        # Initialize ordered results storage to preserve URL order
        url_to_index = {url: i for i, url in enumerate(urls)}
        ordered_results = [None] * len(urls)
        ordered_errors = [None] * len(urls)
        processed_count = 0
        
        try:
            # Get or create executor
            executor = self._get_executor()
            
            # Submit all tasks
            future_to_url = {}
            for url in urls:
                try:
                    future = executor.submit(
                        self._process_single_url_enhanced,
                        url,
                        player_name,
                        enable_advanced_processing,
                        project_name
                    )
                    future_to_url[future] = url
                    
                    # Add delay to respect rate limits
                    time.sleep(delay_between_requests)
                except Exception as e:
                    logger.error(f"Error submitting task for URL {url}: {str(e)}")
                    # Store error at correct index to preserve order
                    error_message = f"Task submission failed: {str(e)}"
                    failure_info = categorize_failure(error_message)
                    error_dict = {
                        'url': url,
                        'error': error_message,
                        'processing_time_seconds': 0.0,
                        'failure_category': failure_info['category'],
                        'failure_display_name': failure_info['display_name'],
                        'retryable': failure_info['retryable'],
                        'recommendation': failure_info['recommendation'],
                        'icon': failure_info['icon'],
                        'priority': failure_info['priority']
                    }
                    url_index = url_to_index[url]
                    ordered_errors[url_index] = error_dict
                    self.total_failed += 1
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                url_index = url_to_index[url]
                processed_count += 1
                
                try:
                    result = future.result(timeout=600)  # Increased timeout to 600 seconds (10 minutes)
                    
                    # Handle both dictionary and object results
                    is_success = False
                    if isinstance(result, dict):
                        is_success = result.get('success', False)
                    else:
                        is_success = getattr(result, 'success', False)
                    
                    if is_success:
                        # Upload to storage if successful
                        upload_result = self._upload_to_storage(result, url)
                        # Get full content and truncated preview - handle both 'content' and 'text' fields
                        if isinstance(result, dict):
                            full_content = result.get('content', '') or result.get('text', '')
                        else:
                            full_content = getattr(result, 'content', '') or getattr(result, 'text', '')
                        content_preview = full_content[:200] + '...' if len(full_content) > 200 else full_content
                        
                        # Check if this is a newspaper.com URL - if so, only include the enhanced image
                        is_newspaper_com = 'newspapers.com' in url.lower()
                        
                        if is_newspaper_com:
                            # For newspaper.com articles, only include the enhanced image with intelligent cropping
                            result_dict = {
                                'url': url,
                                'success': True,
                                'headline': result.get('headline', '') if isinstance(result, dict) else getattr(result, 'headline', ''),
                                'source': result.get('source', '') if isinstance(result, dict) else getattr(result, 'source', ''),
                                'author': result.get('author', '') if isinstance(result, dict) else getattr(result, 'author', ''),
                                'date': result.get('date', '') if isinstance(result, dict) else getattr(result, 'date', ''),
                                'content': '',  # No text content for newspaper clippings
                                'full_content': '',  # No text content for newspaper clippings
                                'markdown_path': '',  # No markdown for newspaper clippings
                                'processing_time_seconds': result.get('processing_time_seconds', 0.0) if isinstance(result, dict) else getattr(result, 'processing_time_seconds', 0.0),
                                'upload_result': upload_result,
                                'metadata': result.get('metadata', {}) if isinstance(result, dict) else getattr(result, 'metadata', {}),
                                'image_data': result.get('image_data') if isinstance(result, dict) else getattr(result, 'image_data', None),  # Enhanced image with intelligent cropping
                                'image_url': result.get('image_url') if isinstance(result, dict) else getattr(result, 'image_url', None),  # Original image URL for reference
                                'stitched_image': result.get('stitched_image') if isinstance(result, dict) else getattr(result, 'stitched_image', None),  # Stitched image if multi-page
                                'word_count': 0,  # No word count for image-only clippings
                                'typography_capsule': None,  # No typography capsule for image-only clippings
                                'structured_content': []  # No structured content for image-only clippings
                            }
                        else:
                            # For other URLs, include full content as before
                            result_dict = {
                                'url': url,
                                'success': True,
                                'headline': result.get('headline', '') if isinstance(result, dict) else getattr(result, 'headline', ''),
                                'source': result.get('source', '') if isinstance(result, dict) else getattr(result, 'source', ''),
                                'author': result.get('author', '') if isinstance(result, dict) else getattr(result, 'author', ''),
                                'date': result.get('date', '') if isinstance(result, dict) else getattr(result, 'date', ''),
                                'content': content_preview,  # Keep truncated for display
                                'full_content': full_content,  # Add full content for ICML conversion
                                'markdown_path': result.get('markdown_path', '') if isinstance(result, dict) else getattr(result, 'markdown_path', ''),
                                'processing_time_seconds': result.get('processing_time_seconds', 0.0) if isinstance(result, dict) else getattr(result, 'processing_time_seconds', 0.0),
                                'upload_result': upload_result,
                                'metadata': result.get('metadata', {}) if isinstance(result, dict) else getattr(result, 'metadata', {}),
                                'image_data': result.get('image_data') if isinstance(result, dict) else getattr(result, 'image_data', None),  # Preserve newspaper clipping images
                                'image_url': result.get('image_url') if isinstance(result, dict) else getattr(result, 'image_url', None),  # Preserve original image URL
                                'stitched_image': result.get('stitched_image') if isinstance(result, dict) else getattr(result, 'stitched_image', None),  # Preserve stitched images
                                'word_count': result.get('word_count', 0) if isinstance(result, dict) else getattr(result, 'word_count', 0),  # Preserve word count for capsule selection
                                'typography_capsule': result.get('typography_capsule') if isinstance(result, dict) else getattr(result, 'typography_capsule', None),  # Preserve capsule data
                                'structured_content': result.get('structured_content', []) if isinstance(result, dict) else getattr(result, 'structured_content', [])  # Preserve structured content
                            }
                        # Store result at correct index to preserve order
                        ordered_results[url_index] = result_dict
                        self.total_successful += 1
                        logger.info(f"Successfully processed: {url}")
                    else:
                        error_message = result.get('error', '') if isinstance(result, dict) else getattr(result, 'error', 'General extraction failed')
                        failure_info = categorize_failure(error_message)
                        error_dict = {
                            'url': url,
                            'error': error_message,
                            'processing_time_seconds': result.get('processing_time_seconds', 0.0) if isinstance(result, dict) else getattr(result, 'processing_time_seconds', 0.0),
                            'failure_category': failure_info['category'],
                            'failure_display_name': failure_info['display_name'],
                            'retryable': failure_info['retryable'],
                            'recommendation': failure_info['recommendation'],
                            'icon': failure_info['icon'],
                            'priority': failure_info['priority']
                        }
                        # Store error at correct index to preserve order
                        ordered_errors[url_index] = error_dict
                        self.total_failed += 1
                        logger.warning(f"Failed to process: {url} - {error_dict['error']}")
                    
                    # Call progress callback if provided
                    if progress_callback:
                        result_for_callback = ordered_results[url_index] if ordered_results[url_index] else ordered_errors[url_index]
                        progress_callback(processed_count, len(urls), result_for_callback)
                        
                except concurrent.futures.TimeoutError:
                    error_message = "Processing timed out after 10 minutes"
                    failure_info = categorize_failure(error_message)
                    error_dict = {
                        'url': url,
                        'error': error_message,
                        'processing_time_seconds': 600.0,
                        'failure_category': failure_info['category'],
                        'failure_display_name': failure_info['display_name'],
                        'retryable': failure_info['retryable'],
                        'recommendation': failure_info['recommendation'],
                        'icon': failure_info['icon'],
                        'priority': failure_info['priority']
                    }
                    # Store timeout error at correct index to preserve order
                    ordered_errors[url_index] = error_dict
                    self.total_failed += 1
                    logger.error(f"Timeout processing {url}")
                    
                except Exception as e:
                    error_message = f"Unexpected error: {str(e)}"
                    failure_info = categorize_failure(error_message)
                    error_dict = {
                        'url': url,
                        'error': error_message,
                        'processing_time_seconds': 0.0,
                        'failure_category': failure_info['category'],
                        'failure_display_name': failure_info['display_name'],
                        'retryable': failure_info['retryable'],
                        'recommendation': failure_info['recommendation'],
                        'icon': failure_info['icon'],
                        'priority': failure_info['priority']
                    }
                    # Store exception error at correct index to preserve order
                    ordered_errors[url_index] = error_dict
                    self.total_failed += 1
                    logger.error(f"Unexpected error processing {url}: {str(e)}", exc_info=True)
                    
                    if progress_callback:
                        progress_callback(processed_count, len(urls), error_dict)
                
                self.total_processed += 1
                
        except Exception as e:
            logger.error(f"Critical error in batch processing: {str(e)}", exc_info=True)
            # Convert ordered arrays to lists, filtering out None values but preserving order
            final_results = [item for item in ordered_results if item is not None]
            final_errors = [item for item in ordered_errors if item is not None]
            # Ensure we return partial results even if there's a critical error
            return {
                'total_urls': len(urls),
                'processed': processed_count,
                'successful': len(final_results),
                'failed': len(final_errors),
                'processing_time_seconds': time.time() - self.start_time,
                'results': final_results,
                'errors': final_errors,
                'critical_error': str(e)
            }
        finally:
            # Don't shutdown executor here, let it be reused
            pass
        
        total_time = time.time() - self.start_time
        
        # Convert ordered arrays to lists, filtering out None values but preserving order
        final_results = [item for item in ordered_results if item is not None]
        final_errors = [item for item in ordered_errors if item is not None]
        
        # Log order preservation confirmation with URL details
        logger.info(f"Order preservation: {len(final_results)} successful results, {len(final_errors)} errors in original URL order")
        
        # Log first few URLs from original input and final results for debugging
        if final_results and len(urls) > 0:
            logger.info(f"Original URL order (first 3): {urls[:3]}")
            result_urls = [r['url'] for r in final_results[:3]]
            logger.info(f"Final result order (first 3): {result_urls}")
            
            # Check if order is preserved for debugging
            first_three_match = True
            for i in range(min(3, len(urls), len(final_results))):
                if urls[i] != final_results[i]['url']:
                    first_three_match = False
                    logger.warning(f"Order mismatch at position {i}: expected {urls[i]}, got {final_results[i]['url']}")
            
            if first_three_match:
                logger.info("✅ URL order confirmed preserved for first 3 results")
            else:
                logger.error("❌ URL order NOT preserved - investigation needed")
        
        # Compile final results with preserved order
        batch_results = {
            'total_urls': len(urls),
            'processed': processed_count,
            'successful': len(final_results),
            'failed': len(final_errors),
            'processing_time_seconds': total_time,
            'average_time_per_url': total_time / len(urls) if urls else 0,
            'results': final_results,
            'errors': final_errors,
            'statistics': {
                'newspapers_com_urls': len([url for url in urls if 'newspapers.com' in url.lower()]),
                'other_urls': len([url for url in urls if 'newspapers.com' not in url.lower()]),
                'success_rate': (len(final_results) / len(urls) * 100) if urls else 0,
                'enhanced_processing_enabled': enable_advanced_processing,
                'auto_authentication_used': self.newspapers_extractor is not None,
                'order_preserved': True  # Flag to confirm order preservation
            }
        }
        
        logger.info(f"Batch processing completed: {len(final_results)}/{len(urls)} successful in {total_time:.2f}s")
        
        # Clean up batch processing flag
        if 'BATCH_PROCESSING' in os.environ:
            del os.environ['BATCH_PROCESSING']
        
        return batch_results
    
    def _process_single_url_enhanced(
        self, 
        url: str, 
        player_name: Optional[str] = None,
        enable_advanced_processing: bool = True,
        project_name: str = "default"
    ):
        """Process a single URL with enhanced features"""
        logger.debug(f"Processing URL with enhanced features: {url}")
        
        try:
            # Determine processing method based on URL type
            if 'newspapers.com' in url.lower():
                return self._process_newspapers_url(url, player_name, enable_advanced_processing, project_name)
            elif self.lapl_extractor and self.lapl_extractor.is_lapl_news_url(url):
                return self._process_lapl_url(url, project_name)
            else:
                return self._process_general_url(url, player_name, project_name)
                
        except Exception as e:
            logger.error(f"Error in enhanced processing for {url}: {str(e)}")
            # Create a simple result object for compatibility
            class SimpleResult:
                def __init__(self, success=False, error="", processing_time_seconds=0.0):
                    self.success = success
                    self.error = error
                    self.processing_time_seconds = processing_time_seconds
                    self.headline = ""
                    self.source = ""
                    self.author = ""
                    self.date = ""
                    self.content = ""
                    self.image_data = None
                    self.image_url = None  # Add image_url field
                    self.metadata = {}
                    self.markdown_path = None
                    self.word_count = 0  # Add word count for capsule selection
                    self.typography_capsule = None  # Add capsule data
                    self.structured_content = []  # Add structured content
                    
            return SimpleResult(
                success=False,
                error=f"Enhanced processing error: {str(e)}",
                processing_time_seconds=0.0
            )
    
    def _process_newspapers_url(
        self, 
        url: str, 
        player_name: Optional[str] = None,
        enable_advanced_processing: bool = True,
        project_name: str = "default"
    ):
        """Process Newspapers.com URL with enhanced authentication"""
        logger.debug(f"Processing Newspapers.com URL: {url}")
        
        if self.newspapers_extractor and enable_advanced_processing:
            # Create a separate extractor instance for thread safety during batch processing
            # The shared extractor instance might have concurrency issues with image processing
            logger.debug("Using enhanced Newspapers.com extractor (thread-safe copy)")
            
            from extractors.newspapers_extractor import NewspapersComExtractor
            
            # Create a new extractor instance for this thread
            thread_extractor = NewspapersComExtractor(auto_auth=False, project_name=project_name)
            
            # Copy authentication cookies but create independent cookie manager to prevent state corruption
            if self.newspapers_extractor.cookie_manager.cookies:
                # Create a deep copy of cookies to prevent reference sharing
                import copy
                thread_extractor.cookie_manager.cookies = copy.deepcopy(self.newspapers_extractor.cookie_manager.cookies)
                thread_extractor.cookie_manager.last_extraction = self.newspapers_extractor.cookie_manager.last_extraction
                logger.debug(f"Copied {len(thread_extractor.cookie_manager.cookies)} cookies to thread extractor")
            
            # Use the thread-safe extractor instance
            result = thread_extractor.extract_from_url(url, player_name=player_name, project_name=project_name)
            
            # Handle authentication failures by trying to refresh from main extractor
            if not result.get('success') and 'authentication' in result.get('error', '').lower():
                logger.warning("Authentication failure in batch thread, attempting recovery")
                # Try to test authentication first and refresh if needed
                try:
                    # Test current authentication without Streamlit dependencies
                    auth_valid = self.newspapers_extractor.cookie_manager.test_authentication()
                    if not auth_valid:
                        logger.info("Main extractor authentication also invalid, attempting refresh")
                        # Force refresh without Streamlit error messages
                        self.newspapers_extractor.cookie_manager.auto_authenticate()
                    
                    # Get fresh cookies and retry
                    if self.newspapers_extractor.cookie_manager.cookies:
                        logger.info("Got fresh cookies, retrying extraction")
                        thread_extractor.cookie_manager.cookies = copy.deepcopy(self.newspapers_extractor.cookie_manager.cookies)
                        thread_extractor.cookie_manager.last_extraction = self.newspapers_extractor.cookie_manager.last_extraction
                        # Retry the extraction once with fresh authentication
                        result = thread_extractor.extract_from_url(url, player_name=player_name, project_name=project_name)
                    else:
                        logger.error("No valid cookies available for authentication recovery")
                except Exception as auth_error:
                    logger.error(f"Authentication recovery failed: {auth_error}")
            
            # Only sync fresh cookies back if extraction succeeded and we got new cookies
            if result.get('success') and thread_extractor.cookie_manager.cookies:
                # Update main extractor's cookies without replacing the entire cookie manager
                self.newspapers_extractor.cookie_manager.cookies = thread_extractor.cookie_manager.cookies
                self.newspapers_extractor.cookie_manager.last_extraction = thread_extractor.cookie_manager.last_extraction
                self.newspapers_extractor.sync_cookies_to_persistent_storage()
                logger.debug("Synced fresh cookies back after successful batch extraction")
            
            return result
        else:
            # Fall back to standard extraction
            logger.debug("Using standard Newspapers.com extraction")
            return extract_from_newspapers_com(
                url=url,
                cookies=self.newspapers_cookies,
                player_name=player_name,
                project_name=project_name
            )
    
    def _process_lapl_url(self, url: str, project_name: str = "default"):
        """Process LAPL URL (NewsBank/ProQuest) with authenticated extraction"""
        logger.info(f"Processing LAPL URL: {url}")
        
        # Simple result class for compatibility
        class SimpleResult:
            def __init__(self, success=False, error="", processing_time_seconds=0.0):
                self.success = success
                self.error = error
                self.processing_time_seconds = processing_time_seconds
                self.headline = ""
                self.source = ""
                self.author = ""
                self.date = ""
                self.content = ""
                self.text = ""  # alias for content
                self.full_content = ""  # For Word doc compatibility
                self.image_data = None
                self.image_url = None
                self.markdown_path = ""
                self.word_count = 0
                self.typography_capsule = None
                self.structured_content = []
                self.metadata = {}
        
        start_time = time.time()
        
        try:
            # Use LAPL extractor for authenticated access
            result = self.lapl_extractor.extract_article_content(url, project_name=project_name)
            processing_time = time.time() - start_time
            
            if result.get('success', False):
                # Convert LAPL result to SimpleResult format
                simple_result = SimpleResult(success=True)
                simple_result.headline = result.get('headline', '')
                simple_result.source = result.get('source', 'LAPL')
                simple_result.date = result.get('date', datetime.now().strftime('%Y-%m-%d'))
                # Get text content and ensure it's available in both fields expected by Word doc generator
                text_content = result.get('text', result.get('content', ''))
                simple_result.content = text_content
                simple_result.text = text_content  # alias
                simple_result.full_content = text_content  # Add full_content field for Word doc compatibility
                
                # Create structured_content for proper Word doc indentation (like URL extractor)
                if text_content and not result.get('structured_content'):
                    # Split text into paragraphs and create structured content
                    paragraphs = text_content.split('\n\n')
                    structured_paragraphs = []
                    for para in paragraphs:
                        if para.strip():
                            # Detect if paragraph should be indented (starts with spaces or is a continuation)
                            is_indented = para.startswith('    ') or (len(structured_paragraphs) > 0)
                            structured_paragraphs.append({
                                'type': 'paragraph',
                                'text': para.strip(),
                                'indented': is_indented
                            })
                    simple_result.structured_content = structured_paragraphs
                    logger.info(f"Created structured_content with {len(structured_paragraphs)} paragraphs for Word doc formatting")
                else:
                    simple_result.structured_content = result.get('structured_content', [])
                # LAPL can now have images (e.g., from NewspaperArchive) - enhance quality like newspapers_extractor
                raw_image_data = result.get('image_data')
                if raw_image_data:
                    try:
                        # Convert raw bytes to PIL Image for enhancement
                        from PIL import Image, ImageEnhance
                        import io
                        
                        # Handle different image data formats
                        if isinstance(raw_image_data, bytes):
                            # Raw bytes - convert to PIL Image
                            img = Image.open(io.BytesIO(raw_image_data))
                            logger.info(f"Converting raw bytes to PIL Image: {img.size}, mode: {img.mode}")
                        elif hasattr(raw_image_data, 'save'):
                            # Already a PIL Image
                            img = raw_image_data
                            logger.info(f"Using existing PIL Image: {img.size}, mode: {img.mode}")
                        else:
                            # Unknown format, pass through as-is
                            logger.warning(f"Unknown image_data format: {type(raw_image_data)}, passing through")
                            simple_result.image_data = raw_image_data
                            simple_result.image_url = result.get('image_url')
                            # Continue without enhancement
                            img = None
                        
                        # Apply enhancement similar to newspapers_extractor
                        if img is not None:
                            # Ensure RGB mode for consistency 
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                                logger.info(f"Converted image to RGB mode")
                            
                            # Apply quality enhancements
                            enhancer = ImageEnhance.Contrast(img)
                            img = enhancer.enhance(1.2)  # Slight contrast boost
                            
                            enhancer = ImageEnhance.Sharpness(img)
                            img = enhancer.enhance(1.1)  # Slight sharpness boost
                            
                            # Save as high-quality PNG instead of compressed format
                            png_buffer = io.BytesIO()
                            img.save(png_buffer, format='PNG', optimize=False, compress_level=1)  # Minimal compression
                            enhanced_image_data = png_buffer.getvalue()
                            
                            # Use enhanced image as PIL Image object (like newspapers_extractor)
                            simple_result.image_data = img  # Pass PIL Image instead of bytes
                            logger.info(f"Enhanced NewspaperArchive image quality: {img.size}, format: PNG, size: {len(enhanced_image_data)} bytes")
                        
                    except Exception as e:
                        logger.warning(f"Failed to enhance NewspaperArchive image, using original: {str(e)}")
                        simple_result.image_data = raw_image_data  # Fallback to original
                else:
                    simple_result.image_data = None
                    
                simple_result.image_url = result.get('image_url')
                simple_result.markdown_path = result.get('markdown_path', '')
                simple_result.word_count = result.get('word_count', 0)
                simple_result.processing_time_seconds = processing_time
                
                # Debug: Log what we're storing for this LAPL result
                has_image_data = bool(simple_result.image_data)
                has_image_url = bool(simple_result.image_url)
                image_data_type = type(simple_result.image_data).__name__ if simple_result.image_data else 'None'
                logger.info(f"LAPL batch result: has_image_data={has_image_data}, has_image_url={has_image_url}, image_data_type={image_data_type}")
                logger.info(f"LAPL batch result image_url: {simple_result.image_url}")
                
                # Store additional LAPL-specific metadata
                simple_result.metadata = {
                    'content_type': result.get('content_type', 'unknown'),
                    'lapl_source': True
                }
                
                logger.info(f"Successfully processed LAPL URL: {url} in {processing_time:.2f}s")
                return simple_result
                
            else:
                error_msg = result.get('error', 'Unknown LAPL extraction error')
                logger.warning(f"LAPL extraction failed for {url}: {error_msg}")
                simple_result = SimpleResult(success=False, error=error_msg, processing_time_seconds=processing_time)
                return simple_result
                
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"LAPL processing error: {str(e)}"
            logger.error(f"Error processing LAPL URL {url}: {error_msg}")
            simple_result = SimpleResult(success=False, error=error_msg, processing_time_seconds=processing_time)
            return simple_result
    
    def _process_general_url(self, url: str, player_name: Optional[str] = None, project_name: str = "default"):
        """Process general URL with standard extraction"""
        logger.info(f"Processing general URL: {url}")
        
        # Simple result class for compatibility
        class SimpleResult:
            def __init__(self, success=False, error="", processing_time_seconds=0.0):
                self.success = success
                self.error = error
                self.processing_time_seconds = processing_time_seconds
                self.headline = ""
                self.source = ""
                self.author = ""
                self.date = ""
                self.content = ""
                self.image_data = None
                self.image_url = None  # Add image_url field
                self.metadata = {}
                self.markdown_path = None
                self.word_count = 0  # Add word count for capsule selection
                self.typography_capsule = None  # Add capsule data
                self.structured_content = []  # Add structured content
        
        try:
            # Use existing URL extractor for non-newspapers.com URLs
            result = extract_from_url(url, project_name=project_name)
            
            # Convert to compatible format
            if isinstance(result, dict) and result.get('success'):
                simple_result = SimpleResult(success=True)
                simple_result.headline = result.get('headline', 'Article')
                simple_result.source = result.get('source', 'Unknown')
                simple_result.author = result.get('author', '')
                simple_result.date = result.get('date', datetime.now().strftime('%Y-%m-%d'))
                simple_result.content = result.get('text', '')
                
                # Enhanced image processing for general URLs (consistent with NewspaperArchive)
                raw_image_data = result.get('clipping_image')
                if raw_image_data:
                    try:
                        # Convert raw bytes to PIL Image for enhancement
                        from PIL import Image, ImageEnhance
                        import io
                        
                        # Handle different image data formats
                        if isinstance(raw_image_data, bytes):
                            # Raw bytes - convert to PIL Image
                            img = Image.open(io.BytesIO(raw_image_data))
                            logger.info(f"Converting general URL raw bytes to PIL Image: {img.size}, mode: {img.mode}")
                        elif hasattr(raw_image_data, 'save'):
                            # Already a PIL Image
                            img = raw_image_data
                            logger.info(f"Using existing PIL Image for general URL: {img.size}, mode: {img.mode}")
                        else:
                            # Unknown format, pass through as-is
                            logger.warning(f"Unknown clipping_image format for general URL: {type(raw_image_data)}, passing through")
                            simple_result.image_data = raw_image_data
                            img = None
                        
                        # Apply enhancement similar to newspapers_extractor
                        if img is not None:
                            # Ensure RGB mode for consistency 
                            if img.mode != 'RGB':
                                img = img.convert('RGB')
                                logger.info(f"Converted general URL image to RGB mode")
                            
                            # Apply quality enhancements
                            enhancer = ImageEnhance.Contrast(img)
                            img = enhancer.enhance(1.2)  # Slight contrast boost
                            
                            enhancer = ImageEnhance.Sharpness(img)
                            img = enhancer.enhance(1.1)  # Slight sharpness boost
                            
                            # Use enhanced image as PIL Image object (like newspapers_extractor)
                            simple_result.image_data = img  # Pass PIL Image instead of bytes
                            logger.info(f"Enhanced general URL image quality: {img.size}")
                        
                    except Exception as e:
                        logger.warning(f"Failed to enhance general URL image, using original: {str(e)}")
                        simple_result.image_data = raw_image_data  # Fallback to original
                else:
                    simple_result.image_data = None
                    
                simple_result.image_url = result.get('image_url')  # Store the original image URL
                logger.info(f"Markdown path in batch processor: {result.get('markdown_path')}")
                simple_result.markdown_path = result.get('markdown_path')
                simple_result.word_count = result.get('word_count', 0)  # Pass through word count
                simple_result.typography_capsule = result.get('typography_capsule')  # Pass through capsule data
                simple_result.structured_content = result.get('structured_content', [])  # Pass through structured content
                simple_result.metadata = {
                    'url': url,
                    'extraction_method': 'general',  # This is for general extraction, not newspapers
                    'player_name': player_name,
                    'timestamp': datetime.now().isoformat()
                }
                simple_result.processing_time_seconds = result.get('processing_time_seconds', 0.0)
                return simple_result
            else:
                return SimpleResult(
                    success=False,
                    error=result.get('error', 'General extraction failed') if isinstance(result, dict) else 'General extraction failed',
                    processing_time_seconds=result.get('processing_time_seconds', 0.0) if isinstance(result, dict) else 0.0
                )
                
        except Exception as e:
            logger.error(f"Error in general URL processing: {str(e)}")
            return SimpleResult(
                success=False,
                error=f"General extraction error: {str(e)}",
                processing_time_seconds=0.0
            )
    
    def _upload_to_storage(self, result, url: str) -> Dict:
        """Upload processed result to storage"""
        try:
            if not result.image_data:
                logger.warning(f"No image data to upload for {url}")
                return {
                    'success': False,
                    'error': 'No image data available'
                }
            
            # Generate filename
            filename = self._generate_filename(result, url)
            
            upload_results = []
            
            # Upload main clipping image
            upload_result = self.storage_manager.upload_image(
                image_data=result.image_data,
                filename=filename,
                metadata={
                    'url': url,
                    'headline': result.headline,
                    'source': result.source,
                    'date': result.date,
                    'processing_method': result.metadata.get('extraction_method', 'download_clicks') if result.metadata else 'download_clicks',
                    'upload_timestamp': datetime.now().isoformat(),
                    'image_type': 'article_clipping'
                }
            )
            upload_results.append(upload_result)
            
            # NEW: Upload stitched image as PNG if available (for multi-page articles)
            if hasattr(result, 'stitched_image') and result.stitched_image:
                logger.info(f"Uploading stitched newspaper image as PNG for {url}")
                
                # Generate PNG filename
                base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                png_filename = f"{base_name}_stitched.png"
                
                # Use the newspapers_extractor PNG upload functionality
                if self.newspapers_extractor:
                    png_uploaded = self.newspapers_extractor.image_processor.save_png_to_storage(
                        result.stitched_image, 
                        png_filename, 
                        self.storage_manager
                    )
                    
                    if png_uploaded:
                        logger.info(f"Successfully uploaded stitched PNG for {url}")
                        upload_results.append({
                            'success': True,
                            'filename': png_filename,
                            'type': 'stitched_png',
                            'size': f"{result.stitched_image.width}x{result.stitched_image.height}"
                        })
                    else:
                        logger.warning(f"Failed to upload stitched PNG for {url}")
                        upload_results.append({
                            'success': False,
                            'error': 'PNG upload failed',
                            'type': 'stitched_png'
                        })
                else:
                    # Fallback: Convert to PNG bytes and upload directly
                    try:
                        png_buffer = io.BytesIO()
                        result.stitched_image.save(png_buffer, format='PNG', optimize=True)
                        png_data = png_buffer.getvalue()
                        
                        png_upload_result = self.storage_manager.upload_image(
                            image_data=png_data,
                            filename=png_filename,
                            metadata={
                                'url': url,
                                'headline': result.headline,
                                'source': result.source,
                                'date': result.date,
                                'processing_method': 'multi_image_stitched',
                                'upload_timestamp': datetime.now().isoformat(),
                                'image_type': 'stitched_full_article',
                                'dimensions': f"{result.stitched_image.width}x{result.stitched_image.height}",
                                'content_type': 'image/png'
                            }
                        )
                        upload_results.append(png_upload_result)
                        
                        if png_upload_result.get('success'):
                            logger.info(f"Successfully uploaded stitched PNG via fallback method for {url}")
                        else:
                            logger.warning(f"Failed to upload stitched PNG via fallback for {url}")
                            
                    except Exception as e:
                        logger.error(f"Error in PNG fallback upload for {url}: {str(e)}")
                        upload_results.append({
                            'success': False,
                            'error': f"PNG fallback failed: {str(e)}",
                            'type': 'stitched_png_fallback'
                        })
            
            # Return the main upload result with additional info about PNG uploads
            main_result = upload_results[0]
            if len(upload_results) > 1:
                main_result['additional_uploads'] = upload_results[1:]
                png_success_count = sum(1 for r in upload_results[1:] if r.get('success'))
                main_result['png_uploads_successful'] = png_success_count
            
            if main_result.get('success'):
                logger.info(f"Successfully uploaded image for {url}")
                return main_result
            else:
                logger.error(f"Failed to upload image for {url}: {main_result.get('error')}")
                return main_result
                
        except Exception as e:
            logger.error(f"Error uploading to storage for {url}: {str(e)}")
            return {
                'success': False,
                'error': f"Upload error: {str(e)}"
            }
    
    def _generate_filename(self, result, url: str) -> str:
        """Generate a unique filename for the processed result"""
        try:
            # Extract domain from URL
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace('www.', '').replace('.', '_')
            
            # Create timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Create safe headline
            safe_headline = ''.join(c for c in result.headline[:30] if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_headline = safe_headline.replace(' ', '_')
            
            if not safe_headline:
                safe_headline = 'article'
            
            filename = f"{domain}_{safe_headline}_{timestamp}.png"
            
            logger.debug(f"Generated filename: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error generating filename: {str(e)}")
            # Fallback filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return f"article_{timestamp}.png"
    
    def get_processing_statistics(self) -> Dict:
        """Get current processing statistics"""
        current_time = time.time()
        elapsed_time = current_time - self.start_time if self.start_time else 0
        
        return {
            'total_processed': self.total_processed,
            'total_successful': self.total_successful,
            'total_failed': self.total_failed,
            'success_rate': (self.total_successful / self.total_processed * 100) if self.total_processed > 0 else 0,
            'elapsed_time_seconds': elapsed_time,
            'average_time_per_url': elapsed_time / self.total_processed if self.total_processed > 0 else 0,
            'processing_rate_per_minute': (self.total_processed / elapsed_time * 60) if elapsed_time > 0 else 0
        }
    
    def reset_statistics(self):
        """Reset processing statistics"""
        self.total_processed = 0
        self.total_successful = 0
        self.total_failed = 0
        self.start_time = None
        logger.info("Processing statistics reset")
    
    def retry_selected_failures(
        self, 
        failed_urls: List[str], 
        progress_callback: Optional[Callable] = None,
        delay_between_requests: float = 1.0,
        player_name: Optional[str] = None,
        enable_advanced_processing: bool = True,
        project_name: str = "default"
    ) -> Dict:
        """
        Retry processing for user-selected failed URLs
        
        Args:
            failed_urls: List of URLs to retry
            progress_callback: Function to call with progress updates
            delay_between_requests: Delay between requests in seconds
            player_name: Optional player name for filtering
            enable_advanced_processing: Whether to use advanced image processing
            project_name: Project name for storage organization
            
        Returns:
            Dictionary with retry results
        """
        logger.info(f"Starting user-driven retry for {len(failed_urls)} URLs")
        
        # Reset counters for retry session
        retry_start_time = time.time()
        
        # Process the selected failed URLs using the same logic as regular batch processing
        retry_result = self.process_urls_batch(
            urls=failed_urls,
            progress_callback=progress_callback,
            delay_between_requests=delay_between_requests,
            player_name=player_name,
            enable_advanced_processing=enable_advanced_processing,
            project_name=project_name
        )
        
        # Add retry-specific metadata
        retry_result['retry_session'] = True
        retry_result['retry_time_seconds'] = time.time() - retry_start_time
        retry_result['retried_urls'] = failed_urls
        
        logger.info(f"User-driven retry completed: {retry_result['successful']}/{len(failed_urls)} successful")
        
        return retry_result

class EnhancedBatchProcessor(BatchProcessor):
    """Enhanced batch processor with additional features for newspapers.com"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.processing_history = []
        
    def process_urls_with_retry(
        self, 
        urls: List[str], 
        max_retries: int = 2,
        retry_delay: float = 5.0,
        **kwargs
    ) -> Dict:
        """Process URLs with retry logic for failed extractions while preserving original order"""
        logger.info(f"Starting batch processing with retry (max {max_retries} retries), preserving URL order")
        
        # Create URL index mapping for order preservation
        url_to_index = {url: i for i, url in enumerate(urls)}
        
        # Initial processing
        result = self.process_urls_batch(urls, **kwargs)
        
        # Retry failed URLs
        retry_count = 0
        while retry_count < max_retries and result['failed'] > 0:
            retry_count += 1
            logger.info(f"Retry attempt {retry_count}/{max_retries} for {result['failed']} failed URLs")
            
            # Extract failed URLs
            failed_urls = [error['url'] for error in result['errors']]
            
            # Wait before retry
            time.sleep(retry_delay)
            
            # Retry processing
            retry_result = self.process_urls_batch(failed_urls, **kwargs)
            
            # Merge results while preserving original order
            # Create a mapping from URL to retry result
            retry_url_to_result = {}
            retry_url_to_error = {}
            for retry_res in retry_result['results']:
                retry_url_to_result[retry_res['url']] = retry_res
            for retry_err in retry_result['errors']:
                retry_url_to_error[retry_err['url']] = retry_err
            
            # Rebuild results and errors in original URL order
            all_items = []  # Will store tuples of (index, item, type)
            
            # Add all current successful results
            for res in result['results']:
                url_index = url_to_index[res['url']]
                all_items.append((url_index, res, 'result'))
            
            # Process current errors: replace with retry results if available
            for error in result['errors']:
                url = error['url']
                url_index = url_to_index[url]
                
                if url in retry_url_to_result:
                    # This URL succeeded on retry
                    all_items.append((url_index, retry_url_to_result[url], 'result'))
                elif url in retry_url_to_error:
                    # This URL failed again
                    all_items.append((url_index, retry_url_to_error[url], 'error'))
                else:
                    # This URL wasn't retried - keep original error
                    all_items.append((url_index, error, 'error'))
            
            # Sort by original index to preserve order
            all_items.sort(key=lambda x: x[0])
            
            # Separate results and errors while maintaining order
            updated_results = [item[1] for item in all_items if item[2] == 'result']
            updated_errors = [item[1] for item in all_items if item[2] == 'error']
            
            # Update result with merged data
            result['results'] = updated_results
            result['successful'] = len(updated_results)
            result['failed'] = len(updated_errors)
            result['errors'] = updated_errors
            result['processing_time_seconds'] += retry_result['processing_time_seconds']
            
            # Update statistics
            result['statistics']['retry_attempts'] = retry_count
            result['statistics']['final_success_rate'] = (result['successful'] / result['total_urls'] * 100)
            result['statistics']['order_preserved_with_retries'] = True
        
        # Store in history
        self.processing_history.append({
            'timestamp': datetime.now().isoformat(),
            'total_urls': result['total_urls'],
            'successful': result['successful'],
            'failed': result['failed'],
            'retry_attempts': retry_count
        })
        
        logger.info(f"Batch processing completed with {retry_count} retry attempts")
        return result
    
    def get_processing_history(self) -> List[Dict]:
        """Get processing history"""
        return self.processing_history
    
    def export_results_summary(self, results: Dict) -> str:
        """Export results summary as text"""
        summary = f"""
                    Batch Processing Results Summary
                    ================================
                    Processed: {results['processed']}/{results['total_urls']} URLs
                    Successful: {results['successful']} ({results['statistics']['success_rate']:.1f}%)
                    Failed: {results['failed']}
                    Processing Time: {results['processing_time_seconds']:.2f} seconds
                    Average Time per URL: {results['average_time_per_url']:.2f} seconds

                    Breakdown:
                    - Newspapers.com URLs: {results['statistics']['newspapers_com_urls']}
                    - Other URLs: {results['statistics']['other_urls']}
                    - Auto-authentication: {'Yes' if results['statistics']['auto_authentication_used'] else 'No'}
                    - Enhanced Processing: {'Yes' if results['statistics']['enhanced_processing_enabled'] else 'No'}

                    Successful Extractions:
                    {chr(10).join([f"- {r['headline']} ({r['source']})" for r in results['results'][:10]])}
                    {'...' if len(results['results']) > 10 else ''}

                    Failed URLs:
                    {chr(10).join([f"- {e['url']}: {e['error']}" for e in results['errors'][:10]])}
                    {'...' if len(results['errors']) > 10 else ''}
                    """
        return summary