# app.py
# Enhanced main application with auto-cookie authentication
import streamlit as st
import pandas as pd
import logging
from datetime import datetime
import uuid
import time
import io
import json

# Import existing modules
from extractors.url_extractor import extract_from_url
from extractors.newspapers_extractor import NewspapersComExtractor, extract_from_newspapers_com
from utils.logger import setup_logging
from utils.processor import process_article
from utils.document_processor import extract_urls_from_docx, validate_document_format
from utils.storage_manager import StorageManager
from utils.batch_processor import BatchProcessor

# Setup logging
logger = setup_logging(__name__, log_level=logging.DEBUG)

def main():
    """Enhanced main application entry point"""
    logger.info("Starting enhanced application with auto-authentication")
    
    # Configure page
    st.set_page_config(
        page_title="Best of AI Agent - Enhanced Batch Processor", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize session state variables
    initialize_session_state()
    
    # Application title
    st.title("🚀 Best of AI Agent - Enhanced Batch Document Processor")
    st.subheader("Upload a Word document with URLs for automated article extraction with advanced Newspapers.com authentication")
    logger.info("Rendered enhanced application header")
    
    # Get configuration from sidebar
    config = enhanced_sidebar_config()
    
    # Display authentication status at the top
    display_authentication_status()
    
    # Display workflow visualization
    display_enhanced_workflow()
    
    # Main content area with tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📄 Document Processing", "🔬 Test Article", "🔍 Newspapers.com Search", "📊 Batch Results", "🖼️ Image Gallery"])
    
    with tab1:
        handle_document_upload(config)
        if st.session_state.extracted_urls:
            display_extracted_urls(config)
    
    with tab2:
        handle_article_test(config)
    
    with tab3:
        handle_newspapers_search(config)
    
    with tab4:
        display_batch_results()
    
    with tab5:
        display_images_gallery(config)
    
    # Footer
    display_enhanced_footer()
    logger.info("Enhanced application fully rendered")

def initialize_session_state():
    """Initialize all session state variables"""
    defaults = {
        'extracted_urls': [],
        'batch_results': None,
        'processing_active': False,
        'uploaded_images': [],
        'newspapers_extractor': None,
        'authentication_status': {},
        'search_results': [],
        'selected_articles': []
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
            logger.info(f"Initialized {key} session state")

def enhanced_sidebar_config():
    """Enhanced sidebar configuration with authentication options"""
    logger.info("Setting up enhanced sidebar")
    st.sidebar.header("🔧 Processing Configuration")
    
    # Authentication section
    st.sidebar.subheader("🔐 Newspapers.com Authentication")
    
    auth_method = st.sidebar.radio(
        "Authentication Method",
        ["Auto-detect cookies", "Manual cookies", "No authentication"],
        help="Choose how to authenticate with Newspapers.com"
    )
    
    newspapers_cookies = ""
    if auth_method == "Manual cookies":
        newspapers_cookies = st.sidebar.text_area(
            "Session Cookies",
            help="Paste your Newspapers.com session cookies here if auto-detection fails"
        )
    
    # Initialize/refresh authentication
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.sidebar.button("🔄 Initialize Auth"):
            initialize_newspapers_authentication(auth_method, newspapers_cookies)
    
    with col2:
        if st.sidebar.button("🧪 Test Auth"):
            test_newspapers_authentication()
    
    # Storage configuration
    st.sidebar.subheader("☁️ Storage Settings")
    bucket_name = st.sidebar.text_input(
        "Replit Storage Bucket Name", 
        value="newspaper-clippings",
        help="Name of the Replit Object Storage bucket to upload images to"
    )
    
    project_name = st.sidebar.text_input(
        "Project Name",
        value="default",
        help="Name of the project folder to organize images in storage"
    )
    
    # Processing configuration
    st.sidebar.subheader("⚙️ Batch Processing")
    max_workers = st.sidebar.slider("Concurrent Workers", 1, 5, 3, help="Number of URLs to process simultaneously")
    delay_between_requests = st.sidebar.slider("Delay Between Requests (sec)", 0.5, 5.0, 1.0, 0.5, help="Delay between requests to be respectful to servers")
    
    # Newspapers.com specific settings
    st.sidebar.subheader("📰 Newspapers.com Settings")
    enable_advanced_processing = st.sidebar.checkbox(
        "Enable Advanced Image Processing",
        value=True,
        help="Use advanced OCR and image processing for newspaper clippings"
    )
    
    player_name = st.sidebar.text_input(
        "Player Name (for filtering)",
        help="Filter articles for specific player mentions"
    )
    
    date_range = st.sidebar.selectbox(
        "Date Range Filter",
        ["Any", "2020-2025", "2010-2019", "2000-2009", "1990-1999", "1980-1989"],
        help="Filter articles by date range"
    )
    
    # Debug controls
    st.sidebar.divider()
    st.sidebar.subheader("🛠️ Debug Options")
    
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
    st.sidebar.subheader("🧪 Storage Test")
    if st.sidebar.button("Test Storage Connection"):
        test_storage_connection(bucket_name, project_name)
    
    return {
        'auth_method': auth_method,
        'newspapers_cookies': newspapers_cookies,
        'bucket_name': bucket_name,
        'project_name': project_name,
        'max_workers': max_workers,
        'delay_between_requests': delay_between_requests,
        'enable_advanced_processing': enable_advanced_processing,
        'player_name': player_name,
        'date_range': date_range if date_range != "Any" else None
    }

def initialize_newspapers_authentication(auth_method, manual_cookies=""):
    """Initialize Newspapers.com authentication"""
    logger.info(f"Initializing Newspapers.com authentication: {auth_method}")
    
    with st.spinner("Initializing Newspapers.com authentication..."):
        try:
            if auth_method == "Auto-detect cookies":
                extractor = NewspapersComExtractor(auto_auth=True)
                success = extractor.initialize()
            elif auth_method == "Manual cookies":
                extractor = NewspapersComExtractor(auto_auth=False)
                # Set manual cookies here if needed
                success = extractor.initialize()
            else:
                extractor = NewspapersComExtractor(auto_auth=False)
                success = extractor.initialize()
            
            st.session_state.newspapers_extractor = extractor
            st.session_state.authentication_status = extractor.get_authentication_status()
            
            if success:
                st.success("✅ Newspapers.com authentication successful!")
                logger.info("Authentication initialized successfully")
            else:
                st.warning("⚠️ Authentication initialized but may have limited access")
                logger.warning("Authentication partially successful")
                
        except Exception as e:
            logger.error(f"Authentication initialization failed: {str(e)}")
            st.error(f"❌ Authentication failed: {str(e)}")

def test_newspapers_authentication():
    """Test current Newspapers.com authentication"""
    if not st.session_state.newspapers_extractor:
        st.warning("Please initialize authentication first")
        return
    
    with st.spinner("Testing authentication..."):
        try:
            status = st.session_state.newspapers_extractor.get_authentication_status()
            st.session_state.authentication_status = status
            
            if status.get('authenticated'):
                st.success("✅ Authentication test successful!")
            else:
                st.warning("⚠️ Authentication test failed - limited access")
                
        except Exception as e:
            logger.error(f"Authentication test failed: {str(e)}")
            st.error(f"❌ Authentication test failed: {str(e)}")

def display_authentication_status():
    """Display current authentication status"""
    st.write("### 🔐 Authentication Status")
    
    status = st.session_state.authentication_status
    
    if not status:
        st.info("Click 'Initialize Auth' in the sidebar to set up Newspapers.com authentication")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if status.get('initialized'):
            st.success("✅ Initialized")
        else:
            st.error("❌ Not Initialized")
    
    with col2:
        if status.get('authenticated'):
            st.success("✅ Authenticated")
        else:
            st.warning("⚠️ Limited Access")
    
    with col3:
        cookies_count = status.get('cookies_count', 0)
        st.metric("Cookies", cookies_count)
    
    with col4:
        last_extraction = status.get('last_extraction')
        if last_extraction:
            try:
                if isinstance(last_extraction, str):
                    last_time = datetime.fromisoformat(last_extraction)
                else:
                    last_time = last_extraction
                time_ago = datetime.now() - last_time
                if time_ago.total_seconds() < 3600:
                    st.success(f"🕐 {int(time_ago.total_seconds()/60)}m ago")
                else:
                    st.warning(f"🕐 {int(time_ago.total_seconds()/3600)}h ago")
            except:
                st.info("🕐 Recently")
        else:
            st.info("🕐 Never")

def display_enhanced_workflow():
    """Display enhanced workflow visualization"""
    logger.info("Rendering enhanced workflow visualization")
    st.write("## 🔄 Enhanced Workflow")
    cols = st.columns(6)
    workflow_steps = [
        "1. Auth Setup",
        "2. Upload Doc",
        "3. Extract URLs", 
        "4. Batch Process",
        "5. Generate Images",
        "6. Upload Storage"
    ]
    
    for i, (col, step) in enumerate(zip(cols, workflow_steps)):
        with col:
            st.info(step)

def handle_newspapers_search(config):
    """Handle direct Newspapers.com search functionality"""
    st.write("## 🔍 Direct Newspapers.com Search")
    
    if not st.session_state.newspapers_extractor:
        st.warning("Please initialize Newspapers.com authentication first in the sidebar")
        return
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        search_query = st.text_input(
            "Search Query",
            placeholder="e.g., Tom Brady, Michael Jordan, Yankees 1995",
            help="Enter search terms to find articles on Newspapers.com"
        )
    
    with col2:
        max_results = st.number_input("Max Results", min_value=1, max_value=50, value=10)
    
    if st.button("🔍 Search Newspapers.com", disabled=not search_query):
        with st.spinner(f"Searching for '{search_query}' on Newspapers.com..."):
            try:
                articles = st.session_state.newspapers_extractor.search_articles(
                    query=search_query,
                    date_range=config.get('date_range'),
                    limit=max_results
                )
                
                if articles:
                    st.session_state.search_results = articles
                    st.success(f"✅ Found {len(articles)} articles!")
                else:
                    st.warning("No articles found for this search query")
                    
            except Exception as e:
                logger.error(f"Search failed: {str(e)}")
                st.error(f"Search failed: {str(e)}")
    
    # Display search results
    if st.session_state.search_results:
        st.write("### Search Results")
        
        results_df = pd.DataFrame(st.session_state.search_results)
        st.dataframe(results_df, use_container_width=True)
        
        # Select articles for processing
        st.write("### Select Articles to Process")
        selected_indices = st.multiselect(
            "Choose articles to add to batch processing:",
            range(len(st.session_state.search_results)),
            format_func=lambda i: f"{i+1}. {st.session_state.search_results[i]['title']}"
        )
        
        if st.button("Add Selected to URL List") and selected_indices:
            selected_urls = [st.session_state.search_results[i]['url'] for i in selected_indices]
            st.session_state.extracted_urls.extend(selected_urls)
            st.success(f"Added {len(selected_urls)} URLs to the processing list!")
            st.rerun()

def handle_document_upload(config):
    """Enhanced document upload handling"""
    logger.info("Setting up enhanced document upload area")
    
    st.write("## 📄 Step 1: Upload Word Document")
    
    uploaded_file = st.file_uploader(
        "Choose a Word document (.docx) containing URLs",
        type=['docx'],
        help="Upload a Word document that contains URLs to articles you want to process"
    )
    
    if uploaded_file is not None:
        logger.info(f"File uploaded: {uploaded_file.name}")
        
        if not validate_document_format(uploaded_file.name):
            st.error("Please upload a valid Word document (.docx)")
            return
        
        st.success(f"✅ Uploaded: {uploaded_file.name} ({uploaded_file.size:,} bytes)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📋 Extract URLs from Document", type="primary"):
                extract_urls_from_document(uploaded_file)
        
        with col2:
            if st.button("🗑️ Clear Extracted URLs"):
                clear_extracted_data()

def extract_urls_from_document(uploaded_file):
    """Extract URLs from uploaded document"""
    logger.info("Starting URL extraction from document")
    
    with st.spinner("Extracting URLs from document..."):
        try:
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

def clear_extracted_data():
    """Clear all extracted data"""
    st.session_state.extracted_urls = []
    st.session_state.batch_results = None
    st.session_state.search_results = []
    logger.info("Cleared all extracted data")
    st.success("Cleared all extracted data")

def display_extracted_urls(config):
    """Enhanced display of extracted URLs"""
    logger.info("Displaying extracted URLs with enhanced features")
    
    st.write("## 📋 Step 2: Review and Manage URLs")
    
    urls = st.session_state.extracted_urls
    st.write(f"**Total URLs: {len(urls)}**")
    
    # Enhanced URL display with domain analysis
    if urls:
        url_df = pd.DataFrame({
            'Index': range(1, len(urls) + 1),
            'URL': urls,
            'Domain': [url.split('/')[2] if len(url.split('/')) > 2 else 'Unknown' for url in urls],
            'Type': ['Newspapers.com' if 'newspapers.com' in url else 'Other' for url in urls]
        })
        
        # Show domain statistics
        domain_counts = url_df['Domain'].value_counts()
        st.write("**Domain Distribution:**")
        for domain, count in domain_counts.head(5).items():
            st.write(f"• {domain}: {count} URLs")
        
        st.dataframe(url_df, use_container_width=True)
        
        # Enhanced URL management
        manage_urls(config)
        
        # Start processing section
        start_enhanced_processing(config)

def manage_urls(config):
    """Enhanced URL management interface"""
    col1, col2, col3 = st.columns(3)
    
    with col1:
        manual_url = st.text_input("Add URL manually:")
        if st.button("➕ Add URL") and manual_url:
            if manual_url not in st.session_state.extracted_urls:
                st.session_state.extracted_urls.append(manual_url)
                logger.info(f"Manually added URL: {manual_url}")
                st.rerun()
    
    with col2:
        if st.session_state.extracted_urls:
            url_to_remove = st.selectbox("Remove URL:", ["Select URL to remove..."] + st.session_state.extracted_urls)
            if st.button("➖ Remove URL") and url_to_remove != "Select URL to remove...":
                st.session_state.extracted_urls.remove(url_to_remove)
                logger.info(f"Removed URL: {url_to_remove}")
                st.rerun()
    
    with col3:
        st.write("**Processing Settings:**")
        st.write(f"🔧 Workers: {config['max_workers']}")
        st.write(f"⏱️ Delay: {config['delay_between_requests']}s")
        if config.get('player_name'):
            st.write(f"🏃 Player: {config['player_name']}")

def start_enhanced_processing(config):
    """Enhanced batch processing with advanced features"""
    st.write("## 🚀 Step 3: Start Enhanced Batch Processing")
    
    urls = st.session_state.extracted_urls
    newspapers_urls = [url for url in urls if 'newspapers.com' in url]
    other_urls = [url for url in urls if 'newspapers.com' not in url]
    
    # Show processing breakdown
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total URLs", len(urls))
    with col2:
        st.metric("Newspapers.com", len(newspapers_urls))
    with col3:
        st.metric("Other Sites", len(other_urls))
    
    if newspapers_urls and not st.session_state.authentication_status.get('initialized'):
        st.warning("⚠️ You have Newspapers.com URLs but authentication is not set up. Initialize authentication in the sidebar for better results.")
    
    if not st.session_state.processing_active:
        if st.button("🚀 Start Enhanced Batch Processing", type="primary", disabled=len(urls) == 0):
            start_enhanced_batch_processing(config)
    else:
        st.warning("⏳ Enhanced batch processing is currently active...")
        if st.button("🛑 Stop Processing"):
            st.session_state.processing_active = False
            st.rerun()

def start_enhanced_batch_processing(config):
    """Start enhanced batch processing with auto-authentication"""
    logger.info("Starting enhanced batch processing")
    
    st.session_state.processing_active = True
    urls = st.session_state.extracted_urls
    
    # Initialize enhanced storage manager and batch processor
    storage_manager = StorageManager(bucket_name=config['bucket_name'], project_name=config['project_name'])
    batch_processor = BatchProcessor(
        storage_manager=storage_manager, 
        max_workers=config['max_workers'],
        newspapers_cookies=config.get('newspapers_cookies', ''),
        newspapers_extractor=st.session_state.newspapers_extractor
    )
    
    # Enhanced progress tracking
    progress_bar = st.progress(0)
    status_text = st.empty()
    results_container = st.container()
    
    def enhanced_progress_callback(processed, total, result):
        """Enhanced callback with more detailed progress"""
        progress = processed / total
        progress_bar.progress(progress)
        
        status_text.text(f"Processing: {processed}/{total} URLs completed ({progress*100:.1f}%)")
        
        # Show detailed results
        with results_container:
            if 'success' in result and result['success']:
                st.success(f"✅ {result['url'][:50]}... - {result.get('headline', 'Success')}")
            else:
                st.error(f"❌ {result['url'][:50]}... - {result.get('error', 'Failed')}")
    try:
        with st.spinner("Processing URLs with enhanced authentication..."):
            results = batch_processor.process_urls_batch(
                urls=urls,
                progress_callback=enhanced_progress_callback,
                delay_between_requests=config['delay_between_requests'],
                player_name=config.get('player_name'),
                enable_advanced_processing=config.get('enable_advanced_processing', True)
            )
        
        # Store enhanced results
        st.session_state.batch_results = results
        st.session_state.processing_active = False
        
        # Update uploaded images list
        if results['successful'] > 0:
            storage_list = storage_manager.list_uploaded_images()
            if storage_list['success']:
                st.session_state.uploaded_images = storage_list['images']
        
        progress_bar.progress(1.0)
        status_text.text("✅ Enhanced batch processing completed!")
        
        logger.info(f"Enhanced batch processing completed: {results['successful']}/{results['processed']} successful")
        
        # Enhanced completion message
        if results['successful'] > 0:
            st.success(f"🎉 Successfully processed {results['successful']} out of {results['processed']} URLs with enhanced authentication!")
            st.balloons()
        else:
            st.warning("No URLs were successfully processed. Check authentication and logs for details.")
            
    except Exception as e:
        logger.error(f"Enhanced batch processing error: {str(e)}")
        st.error(f"Enhanced batch processing error: {str(e)}")
        st.session_state.processing_active = False

def test_storage_connection(bucket_name, project_name):
    """Test storage connection with enhanced feedback"""
    logger.info("Testing enhanced storage connection")
    try:
        storage_manager = StorageManager(bucket_name=bucket_name, project_name=project_name)
        result = storage_manager.list_uploaded_images()
        
        if result['success']:
            st.sidebar.success(f"✅ Storage connected! Found {result['count']} images in project '{project_name}'.")
            if result.get('note'):
                st.sidebar.info(result['note'])
        else:
            st.sidebar.error(f"❌ Storage test failed: {result['error']}")
    except Exception as e:
        logger.error(f"Enhanced storage test error: {str(e)}")
        st.sidebar.error(f"❌ Enhanced storage test error: {str(e)}")

def display_batch_results():
    """Enhanced display of batch processing results"""
    if not st.session_state.batch_results:
        st.info("No batch processing results yet. Process some URLs to see results here.")
        return
    
    logger.info("Displaying enhanced batch results")
    
    results = st.session_state.batch_results
    
    st.write("## 📊 Enhanced Batch Processing Results")
    
    # Enhanced summary metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total URLs", results['total_urls'])
    with col2:
        st.metric("Successful", results['successful'], delta=results['successful'] - results['failed'])
    with col3:
        st.metric("Failed", results['failed'])
    with col4:
        st.metric("Processing Time", f"{results['processing_time_seconds']:.1f}s")
    with col5:
        if results['processed'] > 0:
            success_rate = (results['successful'] / results['processed']) * 100
            st.metric("Success Rate", f"{success_rate:.1f}%")
    
    # Enhanced progress visualization
    if results['processed'] > 0:
        success_rate = (results['successful'] / results['processed']) * 100
        st.progress(success_rate / 100)
        
        # Color-coded success rate
        if success_rate >= 80:
            st.success(f"**Excellent Success Rate: {success_rate:.1f}%**")
        elif success_rate >= 60:
            st.warning(f"**Good Success Rate: {success_rate:.1f}%**")
        else:
            st.error(f"**Low Success Rate: {success_rate:.1f}%** - Check authentication and URLs")
    
    # Enhanced detailed results with tabs
    if results['results'] or results['errors']:
        tab1, tab2 = st.tabs(["✅ Successful Extractions", "❌ Failed Extractions"])
        
        with tab1:
            if results['results']:
                success_df = pd.DataFrame([
                    {
                        'Headline': r.get('headline', 'Unknown')[:50] + ('...' if len(r.get('headline', '')) > 50 else ''),
                        'Source': r.get('source', 'Unknown'),
                        'URL': r['url'][:50] + ('...' if len(r['url']) > 50 else ''),
                        'Upload Status': '✅ Uploaded' if r.get('upload_result', {}).get('success') else '❌ Upload Failed',
                        'Processing Time': f"{r['processing_time_seconds']:.2f}s",
                        'Auth Method': r.get('metadata', {}).get('extraction_method', 'Unknown')
                    }
                    for r in results['results']
                ])
                st.dataframe(success_df, use_container_width=True)
            else:
                st.info("No successful extractions in this batch.")
        
        with tab2:
            if results['errors']:
                error_df = pd.DataFrame([
                    {
                        'URL': e['url'][:50] + ('...' if len(e['url']) > 50 else ''),
                        'Error': e.get('error', 'Unknown error')[:100] + ('...' if len(e.get('error', '')) > 100 else ''),
                        'Processing Time': f"{e['processing_time_seconds']:.2f}s"
                    }
                    for e in results['errors']
                ])
                st.dataframe(error_df, use_container_width=True)
            else:
                st.success("No failed extractions in this batch!")

def display_images_gallery(config):
    """Enhanced image gallery with preview capabilities"""
    logger.info("Displaying enhanced images gallery")
    
    st.write("## 🖼️ Enhanced Images Gallery")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.button("🔄 Refresh Images"):
            refresh_images_gallery(config)
    
    with col2:
        st.write(f"**Total Images: {len(st.session_state.uploaded_images)}**")
    
    with col3:
        if st.session_state.uploaded_images:
            if st.button("📥 Download All"):
                st.info("Download all functionality would be implemented here")
    
    if st.session_state.uploaded_images:
        # Enhanced image display with filtering
        images = st.session_state.uploaded_images
        
        # Filter options
        st.write("### Filter Options")
        col1, col2 = st.columns(2)
        
        with col1:
            name_filter = st.text_input("Filter by name:", placeholder="Enter text to filter...")
        
        with col2:
            sort_option = st.selectbox("Sort by:", ["Name", "Date Created", "Size"])
        
        # Apply filters
        filtered_images = images
        if name_filter:
            filtered_images = [img for img in images if name_filter.lower() in img['name'].lower()]
        
        # Sort images
        if sort_option == "Date Created":
            filtered_images.sort(key=lambda x: x.get('created', ''), reverse=True)
        elif sort_option == "Size":
            filtered_images.sort(key=lambda x: x.get('size', 0), reverse=True)
        else:  # Name
            filtered_images.sort(key=lambda x: x.get('name', ''))
        
        st.write(f"Showing {len(filtered_images)} of {len(images)} images")
        
        # Enhanced grid layout
        cols_per_row = 3
        for i in range(0, len(filtered_images), cols_per_row):
            cols = st.columns(cols_per_row)
            for j, col in enumerate(cols):
                if i + j < len(filtered_images):
                    display_image_card(filtered_images[i + j], config, i + j)
    else:
        st.info("📸 No images uploaded yet. Process some URLs to generate newspaper clippings!")

def refresh_images_gallery(config):
    """Refresh the images gallery"""
    storage_manager = StorageManager(bucket_name=config['bucket_name'], project_name=config['project_name'])
    result = storage_manager.list_uploaded_images()
    if result['success']:
        st.session_state.uploaded_images = result['images']
        st.success(f"🔄 Refreshed! Found {len(result['images'])} images in project '{config['project_name']}'")
    else:
        st.error(f"❌ Failed to refresh images: {result['error']}")

def display_image_card(img, config, index):
    """Display an enhanced image card"""
    with st.container():
        st.write(f"**{img['name'][:25]}{'...' if len(img['name']) > 25 else ''}**")
        
        # Image metadata
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"📏 {img['size']:,} bytes")
        with col2:
            created_display = img['created']
            if created_display != 'Unknown' and 'T' in created_display:
                try:
                    created_dt = datetime.fromisoformat(created_display.replace('Z', '+00:00'))
                    created_display = created_dt.strftime('%m/%d %H:%M')
                except:
                    created_display = created_display[:10]
            st.write(f"📅 {created_display}")
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Preview", key=f"preview_{index}"):
                show_enhanced_image_preview(img, config)
        
        with col2:
            if st.button("📥 Download", key=f"download_{index}"):
                download_image(img, config)
        
        # Thumbnail for local images
        if 'local_path' in img:
            try:
                st.image(img['local_path'], use_container_width=True)
            except Exception as e:
                st.error(f"Could not load: {str(e)[:30]}...")
        else:
            st.info("Cloud stored")

def show_enhanced_image_preview(img, config):
    """Show enhanced image preview with metadata"""
    logger.info(f"Showing enhanced preview for image: {img['name']}")
    
    storage_manager = StorageManager(bucket_name=config['bucket_name'], project_name=config['project_name'])
    
    object_name = img.get('full_path', img['name'])
    if 'local_path' not in img and not object_name.startswith(config['project_name'] + '/'):
        object_name = f"{config['project_name']}/{img['name']}"
    
    with st.spinner(f"Loading enhanced preview for {img['name']}..."):
        try:
            if 'local_path' in img:
                st.image(img['local_path'], caption=img['name'], use_container_width=True)
                st.success(f"✅ Local image preview loaded")
                
                # Show local file metadata
                with st.expander("📋 Image Metadata"):
                    st.json({
                        "name": img['name'],
                        "size": f"{img['size']:,} bytes",
                        "local_path": img['local_path'],
                        "created": img.get('created', 'Unknown')
                    })
            else:
                preview_result = storage_manager.get_image_preview(object_name)
                
                if preview_result['success']:
                    st.image(preview_result['data'], caption=img['name'], use_container_width=True)
                    st.success(f"✅ Cloud image preview loaded ({preview_result['size']:,} bytes)")
                    
                    # Show cloud metadata
                    with st.expander("☁️ Cloud Metadata"):
                        st.json({
                            "name": img['name'],
                            "size": f"{img['size']:,} bytes",
                            "object_name": object_name,
                            "created": img.get('created', 'Unknown'),
                            "bucket": config['bucket_name'],
                            "project": config['project_name']
                        })
                else:
                    st.error(f"❌ Failed to load preview: {preview_result['error']}")
                    
        except Exception as e:
            logger.error(f"Error showing enhanced image preview: {str(e)}")
            st.error(f"Error loading preview: {str(e)}")

def download_image(img, config):
    """Download image functionality"""
    st.info(f"Download functionality for {img['name']} would be implemented here")

def display_enhanced_footer():
    """Display enhanced footer with more information"""
    logger.info("Rendering enhanced footer")
    st.write("---")
    st.write("### 🚀 About This Enhanced Application")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **Best of AI Agent - Enhanced Batch Document Processor**
        
        🔥 **New Features:**
        - 🔐 Auto-cookie authentication for Newspapers.com
        - 🧠 Advanced image processing and OCR
        - 🎯 Smart content filtering and analysis
        - 📊 Enhanced progress tracking and results
        - 🔍 Direct Newspapers.com search
        """)
    
    with col2:
        st.info("""
        **Enhanced Workflow:**
        1. 🔐 Automatic browser cookie detection
        2. 📄 Word document URL extraction
        3. 🔍 Direct newspaper search capability
        4. ⚡ Concurrent batch processing
        5. 🖼️ Advanced newspaper clipping generation
        6. ☁️ Seamless cloud storage integration
        """)
    
    # Technical details
    with st.expander("🔧 Technical Details"):
        st.write("""
        **Enhanced Authentication:**
        - Automatic cookie extraction from Chrome, Firefox, Edge, Safari
        - Session management and authentication testing
        - Fallback to manual cookie input
        
        **Advanced Image Processing:**
        - Computer vision for article boundary detection
        - Enhanced OCR with confidence scoring
        - Smart content analysis and filtering
        
        **Improved Performance:**
        - Concurrent processing with rate limiting
        - Progress tracking with detailed feedback
        - Error handling and retry mechanisms
        """)
    
    logger.debug("Enhanced footer rendered")

def handle_article_test(config):
    """Handle testing of individual Newspapers.com article links"""
    st.write("## 🔬 Test Individual Article")
    
    if not st.session_state.newspapers_extractor:
        st.warning("Please initialize Newspapers.com authentication first in the sidebar")
        return
    
    # Article URL input
    article_url = st.text_input(
        "Article URL",
        placeholder="https://www.newspapers.com/article/...",
        help="Enter a Newspapers.com article URL to test extraction"
    )
    
    # Player name filter (optional)
    player_name = st.text_input(
        "Player Name (optional)",
        placeholder="e.g., Tom Brady",
        help="Filter article content for specific player mentions"
    )
    
    if st.button("🔬 Test Article Extraction", disabled=not article_url):
        with st.spinner("Testing article extraction..."):
            try:
                result = st.session_state.newspapers_extractor.extract_from_url(
                    url=article_url,
                    player_name=player_name if player_name else None
                )
                
                if result['success']:
                    st.success("✅ Article extraction successful!")
                    
                    # Display results in columns
                    col1, col2 = st.columns([1, 1])
                    
                    with col1:
                        st.write("### 📰 Article Details")
                        st.write(f"**Headline:** {result.get('headline', 'N/A')}")
                        st.write(f"**Source:** {result.get('source', 'N/A')}")
                        st.write(f"**Date:** {result.get('date', 'N/A')}")
                        
                        if result.get('metadata'):
                            st.write("### 📊 Analysis")
                            st.write(f"**Sentiment Score:** {result['metadata'].get('sentiment_score', 'N/A')}")
                            st.write(f"**Player Mentions:** {', '.join(result['metadata'].get('player_mentions', []))}")
                            st.write(f"**Confidence:** {result['metadata'].get('confidence', 'N/A')}")
                    
                    with col2:
                        if result.get('image_data'):
                            st.write("### 🖼️ Extracted Image")
                            st.image(result['image_data'], caption="Extracted Article Image")
                        
                        if result.get('content'):
                            st.write("### 📝 Content Preview")
                            st.text_area("Article Content", result['content'], height=200)
                    
                    # Add to batch processing option
                    if st.button("➕ Add to Batch Processing"):
                        if article_url not in st.session_state.extracted_urls:
                            st.session_state.extracted_urls.append(article_url)
                            st.success("Added to batch processing list!")
                            st.rerun()
                
                else:
                    st.error(f"❌ Article extraction failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                logger.error(f"Article test failed: {str(e)}")
                st.error(f"Article test failed: {str(e)}")

if __name__ == "__main__":
    try:
        logger.info("Enhanced application starting...")
        main()
    except Exception as e:
        logger.critical(f"Critical enhanced application error: {str(e)}", exc_info=True)
        st.error(f"A critical error occurred: {str(e)}")