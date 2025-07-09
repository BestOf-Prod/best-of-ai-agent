# utils/batch_processor.py
# Enhanced batch processor with auto-authentication support

import concurrent.futures
import time
import logging
import io
from datetime import datetime
from typing import List, Dict, Callable, Optional
import requests
import threading

from extractors.url_extractor import extract_from_url
from extractors.newspapers_extractor import extract_from_newspapers_com

logger = logging.getLogger(__name__)

class BatchProcessor:
    """Enhanced batch processor with auto-authentication support"""
    
    def __init__(self, storage_manager, max_workers: int = 3, newspapers_cookies: str = "", 
                 newspapers_extractor: Optional = None):
        self.storage_manager = storage_manager
        self.max_workers = max_workers
        self.newspapers_cookies = newspapers_cookies
        self.newspapers_extractor = newspapers_extractor
        self.total_processed = 0
        self.total_successful = 0
        self.total_failed = 0
        self.start_time = None
        self.executor = None  # Initialize as None, create on demand
        self._lock = threading.Lock()  # Add thread safety
        
        logger.info(f"Initialized BatchProcessor with {max_workers} workers")
        if newspapers_extractor:
            logger.info("Using enhanced Newspapers.com extractor with auto-authentication")
    
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
        
        results = []
        errors = []
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
                    errors.append({
                        'url': url,
                        'error': f"Task submission failed: {str(e)}",
                        'processing_time_seconds': 0.0
                    })
                    self.total_failed += 1
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                processed_count += 1
                
                try:
                    result = future.result(timeout=180)  # Reduced timeout from 300 to 180 seconds (3 minutes)
                    
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
                        results.append(result_dict)
                        self.total_successful += 1
                        logger.info(f"Successfully processed: {url}")
                    else:
                        error_dict = {
                            'url': url,
                            'error': result.get('error', '') if isinstance(result, dict) else getattr(result, 'error', 'General extraction failed'),
                            'processing_time_seconds': result.get('processing_time_seconds', 0.0) if isinstance(result, dict) else getattr(result, 'processing_time_seconds', 0.0)
                        }
                        errors.append(error_dict)
                        self.total_failed += 1
                        logger.warning(f"Failed to process: {url} - {error_dict['error']}")
                    
                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(processed_count, len(urls), result_dict if is_success else error_dict)
                        
                except concurrent.futures.TimeoutError:
                    error_dict = {
                        'url': url,
                        'error': "Processing timed out after 3 minutes",
                        'processing_time_seconds': 180.0
                    }
                    errors.append(error_dict)
                    self.total_failed += 1
                    logger.error(f"Timeout processing {url}")
                    
                except Exception as e:
                    error_dict = {
                        'url': url,
                        'error': f"Unexpected error: {str(e)}",
                        'processing_time_seconds': 0.0
                    }
                    errors.append(error_dict)
                    self.total_failed += 1
                    logger.error(f"Unexpected error processing {url}: {str(e)}", exc_info=True)
                    
                    if progress_callback:
                        progress_callback(processed_count, len(urls), error_dict)
                
                self.total_processed += 1
                
        except Exception as e:
            logger.error(f"Critical error in batch processing: {str(e)}", exc_info=True)
            # Ensure we return partial results even if there's a critical error
            return {
                'total_urls': len(urls),
                'processed': processed_count,
                'successful': len(results),
                'failed': len(errors),
                'processing_time_seconds': time.time() - self.start_time,
                'results': results,
                'errors': errors,
                'critical_error': str(e)
            }
        finally:
            # Don't shutdown executor here, let it be reused
            pass
        
        total_time = time.time() - self.start_time
        
        # Compile final results
        batch_results = {
            'total_urls': len(urls),
            'processed': processed_count,
            'successful': len(results),
            'failed': len(errors),
            'processing_time_seconds': total_time,
            'average_time_per_url': total_time / len(urls) if urls else 0,
            'results': results,
            'errors': errors,
            'statistics': {
                'newspapers_com_urls': len([url for url in urls if 'newspapers.com' in url.lower()]),
                'other_urls': len([url for url in urls if 'newspapers.com' not in url.lower()]),
                'success_rate': (len(results) / len(urls) * 100) if urls else 0,
                'enhanced_processing_enabled': enable_advanced_processing,
                'auto_authentication_used': self.newspapers_extractor is not None
            }
        }
        
        logger.info(f"Batch processing completed: {len(results)}/{len(urls)} successful in {total_time:.2f}s")
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
            thread_extractor = NewspapersComExtractor(auto_auth=True, project_name=project_name)
            
            # Copy authentication state from the main extractor
            thread_extractor.cookie_manager = self.newspapers_extractor.cookie_manager
            
            # Use the thread-safe extractor instance
            return thread_extractor.extract_from_url(url, player_name=player_name, project_name=project_name)
        else:
            # Fall back to standard extraction
            logger.debug("Using standard Newspapers.com extraction")
            return extract_from_newspapers_com(
                url=url,
                cookies=self.newspapers_cookies,
                player_name=player_name,
                project_name=project_name
            )
    
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
                simple_result.date = result.get('date', datetime.now().strftime('%Y-%m-%d'))
                simple_result.content = result.get('text', '')
                simple_result.image_data = result.get('clipping_image')
                simple_result.image_url = result.get('image_url')  # Store the original image URL
                logger.info(f"Markdown path in batch processor: {result.get('markdown_path')}")
                simple_result.markdown_path = result.get('markdown_path')
                simple_result.word_count = result.get('word_count', 0)  # Pass through word count
                simple_result.typography_capsule = result.get('typography_capsule')  # Pass through capsule data
                simple_result.structured_content = result.get('structured_content', [])  # Pass through structured content
                simple_result.metadata = {
                    'url': url,
                    'extraction_method': 'general',
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
                    'processing_method': result.metadata.get('extraction_method', 'unknown') if result.metadata else 'unknown',
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
                            content_type='image/png',
                            metadata={
                                'url': url,
                                'headline': result.headline,
                                'source': result.source,
                                'date': result.date,
                                'processing_method': 'multi_image_stitched',
                                'upload_timestamp': datetime.now().isoformat(),
                                'image_type': 'stitched_full_article',
                                'dimensions': f"{result.stitched_image.width}x{result.stitched_image.height}"
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
        """Process URLs with retry logic for failed extractions"""
        logger.info(f"Starting batch processing with retry (max {max_retries} retries)")
        
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
            
            # Merge results
            result['results'].extend(retry_result['results'])
            result['successful'] += retry_result['successful']
            result['failed'] = len(retry_result['errors'])
            result['errors'] = retry_result['errors']
            result['processing_time_seconds'] += retry_result['processing_time_seconds']
            
            # Update statistics
            result['statistics']['retry_attempts'] = retry_count
            result['statistics']['final_success_rate'] = (result['successful'] / result['total_urls'] * 100)
        
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