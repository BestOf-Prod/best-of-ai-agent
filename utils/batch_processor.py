import logging
from typing import List, Dict, Any, Callable, Optional
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from utils.logger import setup_logging
from utils.storage_manager import StorageManager
from extractors.url_extractor import extract_from_url
from extractors.newspapers_extractor import extract_from_newspapers_com
from utils.processor import process_article

# Setup logging
logger = setup_logging(__name__)

def is_newspapers_com_url(url: str) -> bool:
    """Check if the URL is from Newspapers.com"""
    return "newspapers.com" in url.lower()

class BatchProcessor:
    """
    Handles batch processing of multiple URLs for article extraction and image generation
    """
    
    def __init__(self, storage_manager: Optional[StorageManager] = None, max_workers: int = 3, newspapers_cookies: str = None):
        """
        Initialize the batch processor
        
        Args:
            storage_manager (StorageManager, optional): Storage manager for uploading images
            max_workers (int): Maximum number of concurrent workers for processing
            newspapers_cookies (str, optional): Session cookies for Newspapers.com
        """
        self.storage_manager = storage_manager or StorageManager()
        self.max_workers = max_workers
        self.newspapers_cookies = newspapers_cookies
        self.results = []
        self.errors = []
        logger.info(f"Batch processor initialized with {max_workers} max workers")
    
    def process_url(self, url: str) -> Dict[str, Any]:
        """
        Process a single URL using the appropriate extractor
        
        Args:
            url (str): The URL to process
            
        Returns:
            dict: The processing results
        """
        start_time = time.time()
        logger.info(f"Processing URL: {url}")
        
        try:
            # Choose extractor based on URL type
            if is_newspapers_com_url(url):
                logger.info("Using Newspapers.com extractor")
                article_data = extract_from_newspapers_com(url, self.newspapers_cookies)
            else:
                logger.info("Using generic URL extractor")
                article_data = extract_from_url(url)
            
            # Process the article data
            if article_data.get("success", False):
                processed_data = process_article(article_data)
                if processed_data:
                    # Upload image if available
                    if "clipping_image" in article_data:
                        upload_result = self.storage_manager.upload_image(
                            image_data=article_data["clipping_image"],
                            filename=processed_data["filename"]
                        )
                        processed_data["upload_result"] = upload_result
                    
                    return {
                        "success": True,
                        "url": url,
                        "headline": processed_data.get("headline", "Unknown"),
                        "source": processed_data.get("source", "Unknown"),
                        "upload_result": processed_data.get("upload_result", {}),
                        "processing_time_seconds": time.time() - start_time
                    }
            
            return {
                "success": False,
                "url": url,
                "error": article_data.get("error", "Unknown error"),
                "processing_time_seconds": time.time() - start_time
            }
            
        except Exception as e:
            logger.error(f"Error processing URL {url}: {str(e)}")
            return {
                "success": False,
                "url": url,
                "error": str(e),
                "processing_time_seconds": time.time() - start_time
            }
    
    def process_urls_batch(self, urls: List[str], progress_callback: Optional[Callable] = None, delay_between_requests: float = 1.0) -> Dict[str, Any]:
        """
        Process a batch of URLs concurrently
        
        Args:
            urls (List[str]): List of URLs to process
            progress_callback (Callable, optional): Callback function for progress updates
            delay_between_requests (float): Delay between requests in seconds
            
        Returns:
            dict: Summary of batch processing results
        """
        logger.info(f"Starting batch processing of {len(urls)} URLs")
        start_time = time.time()
        
        results = []
        errors = []
        processed = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all URLs for processing
            future_to_url = {executor.submit(self.process_url, url): url for url in urls}
            
            # Process results as they complete
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    processed += 1
                    
                    if result["success"]:
                        results.append(result)
                    else:
                        errors.append(result)
                    
                    # Call progress callback if provided
                    if progress_callback:
                        progress_callback(processed, len(urls), result)
                    
                    # Add delay between requests
                    time.sleep(delay_between_requests)
                    
                except Exception as e:
                    logger.error(f"Error processing {url}: {str(e)}")
                    errors.append({
                        "success": False,
                        "url": url,
                        "error": str(e),
                        "processing_time_seconds": time.time() - start_time
                    })
                    processed += 1
                    if progress_callback:
                        progress_callback(processed, len(urls), {
                            "success": False,
                            "url": url,
                            "error": str(e)
                        })
        
        processing_time = time.time() - start_time
        logger.info(f"Batch processing completed in {processing_time:.2f} seconds")
        
        return {
            "total_urls": len(urls),
            "processed": processed,
            "successful": len(results),
            "failed": len(errors),
            "processing_time_seconds": processing_time,
            "results": results,
            "errors": errors
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