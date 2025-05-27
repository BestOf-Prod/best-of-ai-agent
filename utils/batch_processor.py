import logging
from typing import List, Dict, Any, Callable, Optional
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from utils.logger import setup_logging
from utils.storage_manager import StorageManager
from extractors.url_extractor import extract_from_url
from utils.processor import process_article

# Setup logging
logger = setup_logging(__name__)

class BatchProcessor:
    """
    Handles batch processing of multiple URLs for article extraction and image generation
    """
    
    def __init__(self, storage_manager: Optional[StorageManager] = None, max_workers: int = 3):
        """
        Initialize the batch processor
        
        Args:
            storage_manager (StorageManager, optional): Storage manager for uploading images
            max_workers (int): Maximum number of concurrent workers for processing
        """
        self.storage_manager = storage_manager or StorageManager()
        self.max_workers = max_workers
        self.results = []
        self.errors = []
        logger.info(f"Batch processor initialized with {max_workers} max workers")
    
    def process_urls_batch(
        self, 
        urls: List[str], 
        progress_callback: Optional[Callable] = None,
        delay_between_requests: float = 1.0
    ) -> Dict[str, Any]:
        """
        Process multiple URLs in batch, extracting articles and generating newspaper clippings
        
        Args:
            urls (List[str]): List of URLs to process
            progress_callback (Callable, optional): Callback function to report progress
            delay_between_requests (float): Delay between requests to be respectful to servers
            
        Returns:
            dict: Summary of batch processing results
        """
        logger.info(f"Starting batch processing of {len(urls)} URLs")
        start_time = datetime.now()
        
        self.results = []
        self.errors = []
        
        # Validate URLs first
        valid_urls = self._validate_urls(urls)
        logger.info(f"Validated {len(valid_urls)} out of {len(urls)} URLs")
        
        if not valid_urls:
            return {
                'success': False,
                'error': 'No valid URLs to process',
                'total_urls': len(urls),
                'processed': 0,
                'successful': 0,
                'failed': len(urls)
            }
        
        # Process URLs with limited concurrency to be respectful
        total_processed = 0
        successful = 0
        failed = 0
        
        # Process in smaller batches to avoid overwhelming servers
        batch_size = min(self.max_workers, len(valid_urls))
        
        for i in range(0, len(valid_urls), batch_size):
            batch_urls = valid_urls[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1}: {len(batch_urls)} URLs")
            
            # Process this batch
            batch_results = self._process_url_batch(batch_urls, delay_between_requests)
            
            for result in batch_results:
                total_processed += 1
                if result['success']:
                    successful += 1
                    self.results.append(result)
                else:
                    failed += 1
                    self.errors.append(result)
                
                # Report progress if callback provided
                if progress_callback:
                    progress_callback(total_processed, len(valid_urls), result)
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        logger.info(f"Batch processing completed in {processing_time:.2f} seconds")
        logger.info(f"Results: {successful} successful, {failed} failed out of {total_processed} processed")
        
        return {
            'success': True,
            'total_urls': len(urls),
            'valid_urls': len(valid_urls),
            'processed': total_processed,
            'successful': successful,
            'failed': failed,
            'processing_time_seconds': processing_time,
            'results': self.results,
            'errors': self.errors,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat()
        }
    
    def _validate_urls(self, urls: List[str]) -> List[str]:
        """
        Validate and filter the input URLs
        
        Args:
            urls (List[str]): List of URLs to validate
            
        Returns:
            List[str]: List of valid URLs
        """
        valid_urls = []
        
        for url in urls:
            if not url or not isinstance(url, str):
                logger.warning(f"Skipping invalid URL: {url}")
                continue
            
            url = url.strip()
            if not url:
                continue
            
            # Basic URL validation
            if not url.startswith(('http://', 'https://')):
                logger.warning(f"Skipping URL without proper protocol: {url}")
                continue
            
            # Check for minimum length and basic structure
            if len(url) < 10 or '.' not in url:
                logger.warning(f"Skipping malformed URL: {url}")
                continue
            
            valid_urls.append(url)
        
        return valid_urls
    
    def _process_url_batch(self, urls: List[str], delay: float) -> List[Dict[str, Any]]:
        """
        Process a batch of URLs with concurrency control
        
        Args:
            urls (List[str]): List of URLs to process
            delay (float): Delay between requests
            
        Returns:
            List[dict]: Results from processing each URL
        """
        results = []
        
        # Use ThreadPoolExecutor for concurrent processing
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(urls))) as executor:
            # Submit all tasks
            future_to_url = {
                executor.submit(self._process_single_url, url, delay): url 
                for url in urls
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    logger.error(f"Unexpected error processing {url}: {str(e)}")
                    results.append({
                        'success': False,
                        'url': url,
                        'error': f"Unexpected error: {str(e)}",
                        'timestamp': datetime.now().isoformat()
                    })
        
        return results
    
    def _process_single_url(self, url: str, delay: float) -> Dict[str, Any]:
        """
        Process a single URL: extract article, generate image, and upload to storage
        
        Args:
            url (str): The URL to process
            delay (float): Delay before processing (for rate limiting)
            
        Returns:
            dict: Result of processing this URL
        """
        logger.info(f"Processing URL: {url}")
        start_time = datetime.now()
        
        try:
            # Add delay for rate limiting
            if delay > 0:
                time.sleep(delay)
            
            # Extract article data
            logger.debug(f"Extracting article from: {url}")
            article_data = extract_from_url(url)
            
            if not article_data.get('success'):
                error_msg = article_data.get('error', 'Unknown extraction error')
                logger.error(f"Failed to extract article from {url}: {error_msg}")
                return {
                    'success': False,
                    'url': url,
                    'error': error_msg,
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds()
                }
            
            # Process the article
            logger.debug(f"Processing extracted article from: {url}")
            processed_article = process_article(article_data)
            
            # Get the newspaper clipping image
            clipping_image = article_data.get('clipping_image')
            if not clipping_image:
                logger.warning(f"No clipping image generated for: {url}")
                return {
                    'success': False,
                    'url': url,
                    'error': 'No newspaper clipping image generated',
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds()
                }
            
            # Upload to storage
            logger.debug(f"Uploading image to storage for: {url}")
            
            # Create a meaningful filename
            headline = processed_article.get('headline', 'article')
            # Clean filename of invalid characters
            clean_headline = "".join(c for c in headline if c.isalnum() or c in (' ', '-', '_')).rstrip()
            clean_headline = clean_headline[:50]  # Limit length
            filename = f"{clean_headline}_clipping.png"
            
            # Prepare metadata
            metadata = {
                'source_url': url,
                'headline': processed_article.get('headline'),
                'source': processed_article.get('source'),
                'date': processed_article.get('date'),
                'author': processed_article.get('author'),
                'extracted_at': processed_article.get('created_at')
            }
            
            # Upload the image
            upload_result = self.storage_manager.upload_image(
                image_data=clipping_image,
                filename=filename,
                metadata=metadata
            )
            
            if not upload_result.get('success'):
                logger.error(f"Failed to upload image for {url}: {upload_result.get('error')}")
                return {
                    'success': False,
                    'url': url,
                    'error': f"Failed to upload image: {upload_result.get('error')}",
                    'timestamp': datetime.now().isoformat(),
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds()
                }
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"Successfully processed {url} in {processing_time:.2f} seconds")
            
            return {
                'success': True,
                'url': url,
                'headline': processed_article.get('headline'),
                'source': processed_article.get('source'),
                'upload_result': upload_result,
                'article_data': {
                    'id': processed_article.get('id'),
                    'filename': processed_article.get('filename'),
                    'date': processed_article.get('date'),
                    'author': processed_article.get('author')
                },
                'timestamp': datetime.now().isoformat(),
                'processing_time_seconds': processing_time
            }
            
        except Exception as e:
            logger.exception(f"Error processing URL {url}: {str(e)}")
            return {
                'success': False,
                'url': url,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'processing_time_seconds': (datetime.now() - start_time).total_seconds()
            }
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the last batch processing operation
        
        Returns:
            dict: Summary statistics and information
        """
        return {
            'total_results': len(self.results),
            'total_errors': len(self.errors),
            'success_rate': len(self.results) / (len(self.results) + len(self.errors)) if (self.results or self.errors) else 0,
            'successful_uploads': len([r for r in self.results if r.get('upload_result', {}).get('success')]),
            'failed_uploads': len([r for r in self.results if not r.get('upload_result', {}).get('success')])
        } 