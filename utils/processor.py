# Article processing
import uuid
from datetime import datetime
import logging
import re
from utils.logger import setup_logging

# Setup logging
logger = setup_logging(__name__)

def process_article(article_data):
    """
    Process and standardize the article data
    
    Args:
        article_data (dict): The raw article data extracted from the source
        
    Returns:
        dict: The processed and standardized article data
    """
    logger.info("Processing extracted article data")
    
    if not article_data.get("success", False):
        logger.error("Cannot process unsuccessful extraction")
        return None
    
    try:
        # Generate a unique ID for the article
        unique_id = str(uuid.uuid4())[:8]
        logger.debug(f"Generated unique ID: {unique_id}")
        
        # Process date string to a standard format if possible
        formatted_date = None
        date_text = article_data.get("date", "")
        
        logger.debug(f"Formatting date: {date_text}")
        
        # Try multiple date formats
        date_formats = [
            "%B %d, %Y",  # January 1, 2023
            "%b %d, %Y",  # Jan 1, 2023
            "%m/%d/%Y",   # 01/01/2023
            "%d %B %Y",   # 1 January 2023
            "%Y-%m-%d",   # 2023-01-01
        ]
        
        for date_format in date_formats:
            try:
                date_obj = datetime.strptime(date_text, date_format)
                formatted_date = date_obj.strftime("%Y%m%d")
                logger.debug(f"Successfully parsed date as: {formatted_date}")
                break
            except ValueError:
                continue
        
        # If all parsing attempts fail, use current date with a flag
        if not formatted_date:
            logger.warning(f"Could not parse date: {date_text}, using current date")
            formatted_date = datetime.now().strftime("%Y%m%d") + "_est"
        
        # Clean headline for filename - remove any characters that would be invalid
        safe_headline = re.sub(r'[^\w\s-]', '', article_data.get("headline", "Unknown"))
        safe_headline = re.sub(r'\s+', '_', safe_headline)
        safe_headline = safe_headline[:30]  # Limit length
        logger.debug(f"Safe headline for filename: {safe_headline}")
        
        # Create the filename according to conventions
        filename = f"{formatted_date}_ESPN_{safe_headline}_{unique_id}"
        logger.info(f"Generated filename: {filename}")
        
        # Truncate content preview
        content_text = article_data.get("text", "")
        content_preview = content_text[:500] + "..." if len(content_text) > 500 else content_text
        logger.debug(f"Created content preview of length: {len(content_preview)}")
        
        # Process content
        content_stats = {
            "length": len(content_text),
            "paragraphs": content_text.count("\n\n") + 1,
            "words": len(content_text.split())
        }
        logger.debug(f"Content stats: {content_stats}")
        
        # Create the processed article object
        processed = {
            "id": unique_id,
            "source_url": article_data.get("url", ""),
            "filename": filename,
            "headline": article_data.get("headline", "Unknown Headline"),
            "date": article_data.get("date", "Unknown Date"),
            "author": article_data.get("author", "Unknown Author"),
            "source": article_data.get("source", "ESPN"),
            "content": content_text,
            "content_preview": content_preview,
            "content_stats": content_stats,
            "image_url": article_data.get("image_url"),
            "processed_date": datetime.now().strftime("%Y-%m-%d")
        }
        
        logger.info("Article processing completed")
        return processed
        
    except Exception as e:
        logger.exception(f"Error processing article: {str(e)}")
        return None