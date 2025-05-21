# Logging configuration
import logging
import sys
import os
from datetime import datetime

def setup_logging(module_name, log_level=logging.INFO, log_file=None):
    """
    Configure logging for the application
    
    Args:
        module_name (str): The name of the module
        log_level (int): The logging level
        log_file (str, optional): Path to a log file. If None, logs to console only.
        
    Returns:
        logger: Configured logger object
    """
    # Create logger
    logger = logging.getLogger(module_name)
    logger.setLevel(log_level)
    
    # Only add handlers if they don't exist
    if not logger.handlers:
        # Create logs directory if it doesn't exist and log_file is specified
        if log_file is None:
            # Use default log file in logs directory
            os.makedirs('logs', exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"logs/article_extractor_{timestamp}.log"
        
        # Create log formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Create file handler
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        logger.info(f"Logging initialized for {module_name}")
    
    return logger