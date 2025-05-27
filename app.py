# Main application
import streamlit as st
import pandas as pd
import logging
from datetime import datetime
import uuid
import time
import io

# Import modules
from extractors.url_extractor import extract_from_url
from utils.logger import setup_logging
from utils.processor import process_article
from utils.document_processor import extract_urls_from_docx, validate_document_format
from utils.storage_manager import StorageManager
from utils.batch_processor import BatchProcessor

# Setup logging
logger = setup_logging(__name__, log_level=logging.INFO)

def main():
    """Main application entry point"""
    logger.info("Starting application")
    
    # Configure page
    st.set_page_config(
        page_title="Best of AI Agent - Batch Processor", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    logger.info("Page config set")
    
    # Initialize session state variables
    if 'extracted_urls' not in st.session_state:
        st.session_state.extracted_urls = []
        logger.info("Initialized extracted_urls session state")
    
    if 'batch_results' not in st.session_state:
        st.session_state.batch_results = None
        logger.info("Initialized batch_results session state")
    
    if 'processing_active' not in st.session_state:
        st.session_state.processing_active = False
        logger.info("Initialized processing_active session state")
    
    if 'uploaded_images' not in st.session_state:
        st.session_state.uploaded_images = []
        logger.info("Initialized uploaded_images session state")
    
    # Application title
    st.title("Best of AI Agent - Batch Document Processor")
    st.subheader("Upload a Word document with URLs for automated article extraction and newspaper clipping generation")
    logger.info("Rendered application header")
    
    # Get configuration from sidebar
    config = sidebar_config()
    
    # Display workflow visualization
    display_workflow()
    
    # Main content area
    handle_document_upload(config)
    
    # Display extracted URLs if available
    if st.session_state.extracted_urls:
        display_extracted_urls(config)
    
    # Display batch processing results
    if st.session_state.batch_results:
        display_batch_results()
    
    # Display uploaded images gallery
    display_images_gallery(config)
    
    # Footer
    display_footer()
    logger.info("Application fully rendered")

def sidebar_config():
    """Configure the sidebar controls"""
    logger.info("Setting up sidebar")
    st.sidebar.header("Processing Configuration")
    
    # Storage configuration
    st.sidebar.subheader("Storage Settings")
    bucket_name = st.sidebar.text_input(
        "Replit Storage Bucket Name", 
        value="newspaper-clippings",
        help="Name of the Replit Object Storage bucket to upload images to"
    )
    
    # Processing configuration
    st.sidebar.subheader("Batch Processing")
    max_workers = st.sidebar.slider("Concurrent Workers", 1, 5, 3, help="Number of URLs to process simultaneously")
    delay_between_requests = st.sidebar.slider("Delay Between Requests (sec)", 0.5, 5.0, 1.0, 0.5, help="Delay between requests to be respectful to servers")
    
    # Debug controls
    st.sidebar.divider()
    st.sidebar.subheader("Debug Options")
    
    if st.sidebar.checkbox("Enable Verbose Logging"):
        logger.setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    if st.sidebar.button("Clear Session State"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        logger.warning("Session state cleared")
        st.rerun()
    
    # Storage test
    st.sidebar.divider()
    st.sidebar.subheader("Storage Test")
    if st.sidebar.button("Test Storage Connection"):
        test_storage_connection(bucket_name)
    
    return {
        'bucket_name': bucket_name,
        'max_workers': max_workers,
        'delay_between_requests': delay_between_requests
    }

def test_storage_connection(bucket_name):
    """Test the connection to Replit Object Storage"""
    logger.info("Testing storage connection")
    try:
        storage_manager = StorageManager(bucket_name)
        result = storage_manager.list_uploaded_images()
        
        if result['success']:
            st.sidebar.success(f"✅ Storage connected! Found {result['count']} images.")
            if result.get('note'):
                st.sidebar.info(result['note'])
        else:
            st.sidebar.error(f"❌ Storage test failed: {result['error']}")
    except Exception as e:
        logger.error(f"Storage test error: {str(e)}")
        st.sidebar.error(f"❌ Storage test error: {str(e)}")

def display_workflow():
    """Display the workflow visualization"""
    logger.info("Rendering workflow visualization")
    st.write("## Workflow")
    cols = st.columns(5)
    with cols[0]:
        st.info("1. Upload Document")
    with cols[1]:
        st.info("2. Extract URLs")
    with cols[2]:
        st.info("3. Batch Process")
    with cols[3]:
        st.info("4. Generate Images")
    with cols[4]:
        st.info("5. Upload to Storage")
    logger.debug("Workflow visualization complete")

def handle_document_upload(config):
    """Handle Word document upload and URL extraction"""
    logger.info("Setting up document upload area")
    
    st.write("## Step 1: Upload Word Document")
    
    uploaded_file = st.file_uploader(
        "Choose a Word document (.docx) containing URLs",
        type=['docx'],
        help="Upload a Word document that contains URLs to articles you want to process"
    )
    
    if uploaded_file is not None:
        logger.info(f"File uploaded: {uploaded_file.name}")
        
        # Validate file format
        if not validate_document_format(uploaded_file.name):
            st.error("Please upload a valid Word document (.docx)")
            return
        
        # Show file details
        st.success(f"✅ Uploaded: {uploaded_file.name} ({uploaded_file.size:,} bytes)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("Extract URLs from Document", type="primary"):
                logger.info("Starting URL extraction from document")
                
                with st.spinner("Extracting URLs from document..."):
                    try:
                        # Extract URLs from the document
                        urls = extract_urls_from_docx(uploaded_file)
                        
                        if urls:
                            st.session_state.extracted_urls = urls
                            logger.info(f"Successfully extracted {len(urls)} URLs")
                            st.success(f"✅ Extracted {len(urls)} URLs from document!")
                            st.balloons()
                        else:
                            logger.warning("No URLs found in document")
                            st.warning("No URLs found in the document. Please check that the document contains valid URLs.")
                            
                    except Exception as e:
                        logger.error(f"Error extracting URLs: {str(e)}")
                        st.error(f"Error extracting URLs: {str(e)}")
        
        with col2:
            if st.button("Clear Extracted URLs"):
                st.session_state.extracted_urls = []
                st.session_state.batch_results = None
                logger.info("Cleared extracted URLs")
                st.success("Cleared extracted URLs")

def display_extracted_urls(config):
    """Display the extracted URLs and processing options"""
    logger.info("Displaying extracted URLs")
    
    st.write("## Step 2: Review Extracted URLs")
    
    urls = st.session_state.extracted_urls
    st.write(f"Found **{len(urls)}** URLs in the document:")
    
    # Display URLs in a dataframe for easy review
    url_df = pd.DataFrame({
        'Index': range(1, len(urls) + 1),
        'URL': urls,
        'Domain': [url.split('/')[2] if len(url.split('/')) > 2 else 'Unknown' for url in urls]
    })
    
    st.dataframe(url_df, use_container_width=True)
    
    # URL management
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Allow manual URL addition
        manual_url = st.text_input("Add URL manually:")
        if st.button("Add URL") and manual_url:
            if manual_url not in st.session_state.extracted_urls:
                st.session_state.extracted_urls.append(manual_url)
                logger.info(f"Manually added URL: {manual_url}")
                st.rerun()
    
    with col2:
        # Allow URL removal
        if urls:
            url_to_remove = st.selectbox("Remove URL:", ["Select URL to remove..."] + urls)
            if st.button("Remove URL") and url_to_remove != "Select URL to remove...":
                st.session_state.extracted_urls.remove(url_to_remove)
                logger.info(f"Removed URL: {url_to_remove}")
                st.rerun()
    
    with col3:
        # Processing controls
        st.write("**Processing Options:**")
        st.write(f"Concurrent Workers: {config['max_workers']}")
        st.write(f"Request Delay: {config['delay_between_requests']}s")
    
    # Start batch processing
    st.write("## Step 3: Start Batch Processing")
    
    if not st.session_state.processing_active:
        if st.button("🚀 Start Batch Processing", type="primary", disabled=len(urls) == 0):
            start_batch_processing(config)
    else:
        st.warning("⏳ Batch processing is currently active...")
        if st.button("Stop Processing"):
            st.session_state.processing_active = False
            st.rerun()

def start_batch_processing(config):
    """Start the batch processing of URLs"""
    logger.info("Starting batch processing")
    
    st.session_state.processing_active = True
    urls = st.session_state.extracted_urls
    
    # Initialize storage manager and batch processor
    storage_manager = StorageManager(config['bucket_name'])
    batch_processor = BatchProcessor(
        storage_manager=storage_manager, 
        max_workers=config['max_workers']
    )
    
    # Create progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.empty()
    
    def progress_callback(processed, total, result):
        """Callback to update progress"""
        progress = processed / total
        progress_bar.progress(progress)
        
        status_text.text(f"Processing: {processed}/{total} URLs completed")
        
        # Show latest result
        if result['success']:
            results_container.success(f"✅ {result['url']} - {result.get('headline', 'Success')}")
        else:
            results_container.error(f"❌ {result['url']} - {result.get('error', 'Failed')}")
    
    try:
        # Start batch processing
        with st.spinner("Processing URLs in batch..."):
            results = batch_processor.process_urls_batch(
                urls=urls,
                progress_callback=progress_callback,
                delay_between_requests=config['delay_between_requests']
            )
        
        # Store results
        st.session_state.batch_results = results
        st.session_state.processing_active = False
        
        # Update uploaded images list
        if results['successful'] > 0:
            storage_list = storage_manager.list_uploaded_images()
            if storage_list['success']:
                st.session_state.uploaded_images = storage_list['images']
        
        progress_bar.progress(1.0)
        status_text.text("✅ Batch processing completed!")
        
        logger.info(f"Batch processing completed: {results['successful']}/{results['processed']} successful")
        
        # Show completion message
        if results['successful'] > 0:
            st.success(f"🎉 Successfully processed {results['successful']} out of {results['processed']} URLs!")
            st.balloons()
        else:
            st.warning("No URLs were successfully processed. Check the logs for details.")
            
    except Exception as e:
        logger.error(f"Batch processing error: {str(e)}")
        st.error(f"Batch processing error: {str(e)}")
        st.session_state.processing_active = False

def display_batch_results():
    """Display the results of batch processing"""
    logger.info("Displaying batch results")
    
    results = st.session_state.batch_results
    
    st.write("## Batch Processing Results")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total URLs", results['total_urls'])
    with col2:
        st.metric("Successful", results['successful'], delta=results['successful'] - results['failed'])
    with col3:
        st.metric("Failed", results['failed'])
    with col4:
        st.metric("Processing Time", f"{results['processing_time_seconds']:.1f}s")
    
    # Success rate
    if results['processed'] > 0:
        success_rate = (results['successful'] / results['processed']) * 100
        st.progress(success_rate / 100)
        st.write(f"**Success Rate: {success_rate:.1f}%**")
    
    # Detailed results
    if results['results']:
        st.write("### Successful Extractions")
        success_df = pd.DataFrame([
            {
                'Headline': r.get('headline', 'Unknown'),
                'Source': r.get('source', 'Unknown'),
                'URL': r['url'],
                'Upload Status': '✅ Uploaded' if r.get('upload_result', {}).get('success') else '❌ Upload Failed',
                'Processing Time': f"{r['processing_time_seconds']:.2f}s"
            }
            for r in results['results']
        ])
        st.dataframe(success_df, use_container_width=True)
    
    if results['errors']:
        st.write("### Failed Extractions")
        error_df = pd.DataFrame([
            {
                'URL': e['url'],
                'Error': e.get('error', 'Unknown error'),
                'Processing Time': f"{e['processing_time_seconds']:.2f}s"
            }
            for e in results['errors']
        ])
        st.dataframe(error_df, use_container_width=True)

def display_images_gallery(config):
    """Display gallery of uploaded images"""
    logger.info("Displaying images gallery")
    
    st.write("## Uploaded Images Gallery")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if st.button("🔄 Refresh Images"):
            storage_manager = StorageManager(config['bucket_name'])
            result = storage_manager.list_uploaded_images()
            if result['success']:
                st.session_state.uploaded_images = result['images']
                st.success(f"Found {len(result['images'])} images")
            else:
                st.error(f"Failed to load images: {result['error']}")
    
    with col2:
        st.write(f"**Total Images: {len(st.session_state.uploaded_images)}**")
    
    if st.session_state.uploaded_images:
        # Display images in a grid
        images = st.session_state.uploaded_images
        
        # Create grid layout
        cols_per_row = 3
        for i in range(0, len(images), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                if i + j < len(images):
                    img = images[i + j]
                    with col:
                        st.write(f"**{img['name'][:30]}...**" if len(img['name']) > 30 else f"**{img['name']}**")
                        st.write(f"Size: {img['size']:,} bytes")
                        st.write(f"Created: {img['created'][:10]}")
                        
                        # For local images, display them
                        if 'local_path' in img:
                            try:
                                st.image(img['local_path'], use_column_width=True)
                            except Exception as e:
                                st.error(f"Could not load image: {str(e)}")
                        else:
                            st.info("Image stored in Replit Object Storage")
    else:
        st.info("No images uploaded yet. Process some URLs to generate newspaper clippings!")

def display_footer():
    """Display the footer with information"""
    logger.info("Rendering footer")
    st.write("---")
    st.write("### About This Application")
    st.info("""
    **Best of AI Agent - Batch Document Processor**
    
    This application processes Word documents containing multiple URLs, extracting articles and generating newspaper-style clippings that are automatically uploaded to Replit Object Storage.
    
    **Features:**
    - 📄 Word document URL extraction
    - 🔄 Concurrent batch processing
    - 🖼️ Newspaper clipping generation
    - ☁️ Replit Object Storage integration
    - 📊 Progress tracking and error handling
    
    **Usage:**
    1. Upload a Word document (.docx) containing URLs
    2. Review and modify the extracted URLs
    3. Configure processing settings in the sidebar
    4. Start batch processing to generate clippings
    5. View results and uploaded images
    """)
    logger.debug("Footer rendered")

if __name__ == "__main__":
    try:
        logger.info("Application starting...")
        main()
    except Exception as e:
        logger.critical(f"Critical application error: {str(e)}", exc_info=True)
        st.error(f"A critical error occurred: {str(e)}")