# app.py
# Enhanced main application with auto-cookie authentication
import streamlit as st
import streamlit.components.v1
import sys

# Fix for Replit numpy import issues
try:
    import pandas as pd
except ImportError as e:
    if "numpy" in str(e).lower():
        st.error("❌ **Environment Issue**: NumPy/Pandas import conflict detected.")
        st.error("**Solution**: In Replit, go to Shell and run: `kill 1` then restart the app.")
        st.info("**Alternative**: Use the `run_app.py` script instead of running `app.py` directly.")
        st.code("python run_app.py", language="bash")
        st.stop()
    else:
        raise e
import logging
from datetime import datetime
import uuid
import time
import io
import json
import os
import zipfile
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Import existing modules
from extractors.url_extractor import extract_from_url
from extractors.newspapers_extractor import NewspapersComExtractor, extract_from_newspapers_com
from utils.logger import setup_logging
from utils.processor import process_article
from utils.document_processor import extract_urls_from_docx, validate_document_format
from utils.storage_manager import StorageManager
from utils.batch_processor import BatchProcessor
from utils.newspaper_converter import convert_markdown_to_newspaper, convert_multiple_markdown_to_newspaper_zip, convert_articles_to_component_zip, create_single_word_document_with_images
from utils.credential_manager import CredentialManager

# Setup logging
logger = setup_logging(__name__, log_level=logging.INFO)

def main():
    """Enhanced main application entry point"""
    logger.info("Starting enhanced application with auto-authentication")
    
    # Configure page
    st.set_page_config(
        page_title="Best of AI Agent - Enhanced Batch Processor", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Ensure credential manager is always available first
    if 'credential_manager' not in st.session_state or st.session_state.credential_manager is None:
        st.session_state.credential_manager = CredentialManager()
        logger.info("Ensured credential manager initialization at startup")
        
        # Disable auto-authentication for both services to prevent loops and provide user control
        # auto_load_newspapers_credentials()
    
    
    # Initialize session state variables
    initialize_session_state()
    
    # Application title
    st.title("📰 Article Extractor")
    st.caption("Upload documents, extract articles, and generate newspaper clippings")
    logger.info("Rendered application header")
    
    # Get configuration from sidebar
    config = streamlined_sidebar_config()
    
    # Main content area with simplified tabs
    tab1, tab2, tab3 = st.tabs(["📄 Process Documents", "📊 Results", "⚙️ Advanced"])
    
    with tab1:
        handle_document_upload(config)
        if st.session_state.extracted_urls:
            display_extracted_urls(config)
    
    with tab2:
        st.subheader("📊 Processing Results")
        display_batch_results(config)
        st.divider()
        st.subheader("📰 Newspaper Format")
        handle_newspaper_conversion()
            
    with tab3:
        st.subheader("🔬 Test Single Article")
        handle_article_test(config)
        st.divider()
        st.subheader("🔍 Newspapers.com Search")
        handle_newspapers_search(config)
    
    logger.info("Application fully rendered")

def initialize_session_state():
    """Initialize all session state variables"""
    defaults = {
        'extracted_urls': [],
        'batch_results': None,
        'processing_active': False,
        'uploaded_images': [],
        'newspapers_extractor': None,
        'lapl_extractor': None,
        'authentication_status': {},
        'search_results': [],
        'selected_articles': [],
        'credential_manager': None
    }
    
    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value
            logger.info(f"Initialized {key} session state")
    
    # Initialize credential manager
    if st.session_state.credential_manager is None:
        st.session_state.credential_manager = CredentialManager()
        logger.info("Initialized credential manager")

def ensure_credential_manager():
    """Ensure credential manager is initialized in session state"""
    if 'credential_manager' not in st.session_state or st.session_state.credential_manager is None:
        st.session_state.credential_manager = CredentialManager()
        logger.info("Ensured credential manager initialization")

def auto_load_newspapers_credentials():
    """Auto-load newspapers.com credentials if available"""
    logger.info("Starting auto-load newspapers.com credentials check")
    
    # Only show loading screen if newspapers extractor is not already initialized
    show_loading = 'newspapers_extractor' not in st.session_state or st.session_state.newspapers_extractor is None
    
    if show_loading:
        with st.spinner("🔐 Loading newspapers.com authentication..."):
            time.sleep(0.1)  # Brief delay to show loading screen
            _perform_newspapers_auth_load()
    else:
        _perform_newspapers_auth_load()

def _perform_newspapers_auth_load():
    """Internal function to perform newspapers.com authentication loading"""
    try:
        ensure_credential_manager()
        cred_manager = st.session_state.credential_manager
        cookies_result = cred_manager.load_newspapers_cookies()
        
        if cookies_result['success']:
            logger.info(f"Auto-loaded newspapers.com cookies: {cookies_result['metadata']['cookie_count']} cookies")
            
            # Initialize extractor with loaded cookies
            extractor = NewspapersComExtractor(auto_auth=True)
            extractor.cookie_manager.cookies = cookies_result['cookies']
            
            # Try to initialize
            success = extractor.initialize()
            
            # Store in session state
            st.session_state.newspapers_extractor = extractor
            st.session_state.authentication_status = extractor.get_authentication_status()
            
            if success:
                logger.info("Auto-initialized newspapers.com authentication from saved cookies")
            else:
                logger.warning("Newspapers.com auto-authentication partially successful")
        else:
            logger.info("No saved newspapers.com cookies found for auto-load")
            
    except Exception as e:
        logger.error(f"Failed to auto-load newspapers.com credentials: {str(e)}")

def streamlined_sidebar_config():
    """Streamlined sidebar configuration"""
    logger.info("Setting up sidebar")
    st.sidebar.header("⚙️ Settings")
    
    # Get credential manager status for UI
    ensure_credential_manager()
    cred_manager = st.session_state.credential_manager
    newspapers_status = cred_manager.get_newspapers_status()
    lapl_status = cred_manager.get_lapl_status()
    
    # Newspapers.com Authentication section (collapsed by default)
    with st.sidebar.expander("🔐 Newspapers.com Authentication", expanded=False):
        # Simple button to use saved credentials
        if st.button("📁 Use Saved Credentials", key="use_saved_newspapers_creds"):
            use_saved_newspapers_credentials()
        
        st.divider()
        st.caption("🔧 Manual Setup (if no saved credentials)")
        
        uploaded_cookies = st.file_uploader("Upload Cookies File", type=['json'], help="Upload your newspapers.com cookies JSON file")
        
        if st.button("Save New Cookies", key="save_cookies"):
            if uploaded_cookies is not None:
                initialize_newspapers_authentication_with_cookies(uploaded_cookies)
            else:
                st.warning("Please upload a cookies file first")
        
        # Show credential management options
        if newspapers_status['has_cookies']:
            st.divider()
            st.caption("🔧 Credential Management")
            if st.button("Clear Saved Cookies", key="clear_cookies", help="Remove saved cookies from persistent storage"):
                clear_result = cred_manager.clear_newspapers_cookies()
                if clear_result['success']:
                    st.success("✅ Cookies cleared!")
                    st.session_state.newspapers_extractor = None
                    st.session_state.authentication_status = {}
                    st.rerun()
                else:
                    st.error(f"❌ {clear_result['error']}")
    
    # LAPL Authentication section (new)
    with st.sidebar.expander("🏛️ LAPL Authentication", expanded=False):
        # Simple button to use saved credentials
        if st.button("📁 Use Saved LAPL Credentials", key="use_saved_lapl_creds"):
            use_saved_lapl_credentials()
        
        st.divider()
        st.caption("🔧 Manual Setup (if no saved credentials)")
        
        uploaded_lapl_cookies = st.file_uploader("Upload LAPL Cookies File", type=['json'], key="lapl_cookies", help="Upload your LAPL cookies JSON file")
        
        if st.button("Save New LAPL Cookies", key="save_lapl_cookies"):
            if uploaded_lapl_cookies is not None:
                initialize_lapl_authentication_with_cookies(uploaded_lapl_cookies)
            else:
                st.warning("Please upload a cookies file first")
        
        # Show credential management options
        if lapl_status['has_cookies']:
            st.divider()
            st.caption("🔧 Credential Management")
            if st.button("Clear Saved LAPL Cookies", key="clear_lapl_cookies", help="Remove saved LAPL cookies from persistent storage"):
                clear_result = cred_manager.clear_lapl_cookies()
                if clear_result['success']:
                    st.success("✅ LAPL Cookies cleared!")
                    st.rerun()
                else:
                    st.error(f"❌ {clear_result['error']}")
        
        # Test LAPL URL access
        st.divider()
        st.caption("🧪 Test LAPL Access")
        test_url = st.text_input("Test URL", value="https://access-newspaperarchive-com.lapl.idm.oclc.org/us/california/marysville/marysville-appeal-democrat/2014/12-12/page-10", key="lapl_test_url")
        if st.button("🔍 Test LAPL URL Access", key="test_lapl_access"):
            test_lapl_url_access(test_url)
    
    
    # Display auth status compactly with persistent credential info
    auth_status = st.session_state.get('authentication_status', {})
    ensure_credential_manager()
    cred_manager = st.session_state.credential_manager
    newspapers_status = cred_manager.get_newspapers_status()
    
    if auth_status.get('authenticated'):
        st.sidebar.success("✅ Logged in")
        if newspapers_status['has_cookies']:
            st.sidebar.caption(f"🍪 {newspapers_status['cookie_count']} cookies saved")
    elif newspapers_status['has_cookies']:
        st.sidebar.info("ℹ️ Cookies saved - Auto-login attempted")
        st.sidebar.caption(f"🍪 {newspapers_status['cookie_count']} cookies from {newspapers_status['saved_at'][:10] if newspapers_status.get('saved_at') else 'unknown date'}")
    else:
        st.sidebar.info("ℹ️ Login for newspapers.com")
        st.sidebar.caption("📋 No saved cookies")
    
    # Return configuration with defaults for Render hosting
    return {
        'project_name': 'default',
        'max_workers': 3,
        'delay_between_requests': 1.0,
        'newspapers_cookies': '',
        'player_name': None,
        'enable_advanced_processing': True,
        'date_range': None
    }

def initialize_newspapers_authentication(email: str, password: str, uploaded_cookies=None):
    """Initialize Newspapers.com authentication"""
    logger.info("Initializing Newspapers.com authentication")
    
    # Check if we're in Replit environment for optimized timeout settings
    is_replit = 'REPL_ID' in os.environ or 'REPL_SLUG' in os.environ
    loading_text = "🔐 Authenticating with newspapers.com..." + (" (Replit - may take longer)" if is_replit else "")
    
    with st.spinner(loading_text):
        try:
            # Initialize extractor with appropriate settings
            extractor = NewspapersComExtractor(auto_auth=True)
            
            # Set login credentials
            extractor.cookie_manager.set_login_credentials(email, password)
            
            # If cookies file is uploaded, load them
            if uploaded_cookies is not None:
                try:
                    cookies_data = json.loads(uploaded_cookies.getvalue().decode())
                    # Convert list of cookie dictionaries to a single dictionary of name-value pairs
                    if isinstance(cookies_data, list):
                        cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies_data}
                        extractor.cookie_manager.cookies = cookies_dict
                    else:
                        extractor.cookie_manager.cookies = cookies_data
                    logger.info("Successfully loaded cookies from uploaded file")
                except Exception as e:
                    logger.error(f"Failed to load cookies from file: {str(e)}")
                    st.warning("Failed to load cookies from file. Will proceed with standard authentication.")
            
            # Try to authenticate
            success = extractor.initialize(email=email, password=password)
            
            # If authentication was successful, save credentials for future use
            if success and extractor.cookie_manager.cookies:
                try:
                    ensure_credential_manager()
                    cred_manager = st.session_state.credential_manager
                    save_result = cred_manager.save_newspapers_cookies(extractor.cookie_manager.cookies)
                    if save_result['success']:
                        logger.info(f"Saved {save_result['cookie_count']} cookies for future sessions")
                except Exception as e:
                    logger.warning(f"Failed to save credentials for future use: {str(e)}")
            
            # Store in session state
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
            return False
            
        return True

def initialize_newspapers_authentication_with_cookies(uploaded_cookies):
    """Initialize Newspapers.com authentication using only cookies"""
    logger.info("Initializing Newspapers.com authentication with cookies only")
    
    # Check if we're in Replit environment for optimized settings
    is_replit = 'REPL_ID' in os.environ or 'REPL_SLUG' in os.environ
    loading_text = "🍪 Loading authentication cookies..." + (" (Replit optimized)" if is_replit else "")
    
    with st.spinner(loading_text):
        try:
            # Initialize extractor with appropriate settings
            extractor = NewspapersComExtractor(auto_auth=True)
            
            # Load cookies from uploaded file
            try:
                cookies_data = json.loads(uploaded_cookies.getvalue().decode())
                
                # Save cookies using credential manager
                ensure_credential_manager()
                cred_manager = st.session_state.credential_manager
                save_result = cred_manager.save_newspapers_cookies(cookies_data)
                
                if save_result['success']:
                    st.success(f"✅ Saved {save_result['cookie_count']} cookies for future sessions!")
                    logger.info(f"Saved cookies to persistent storage: {save_result['cookie_count']} cookies")
                else:
                    st.warning(f"⚠️ Failed to save cookies: {save_result['error']}")
                
                # Convert list of cookie dictionaries to a single dictionary of name-value pairs
                if isinstance(cookies_data, list):
                    cookies_dict = {cookie['name']: cookie['value'] for cookie in cookies_data}
                    extractor.cookie_manager.cookies = cookies_dict
                else:
                    extractor.cookie_manager.cookies = cookies_data
                logger.info("Successfully loaded cookies from uploaded file")
            except Exception as e:
                logger.error(f"Failed to load cookies from file: {str(e)}")
                st.error("Failed to load cookies from file. Please check the file format.")
                return False
            
            # Try to authenticate using only cookies (no email/password)
            success = extractor.initialize()
            
            # Store in session state
            st.session_state.newspapers_extractor = extractor
            st.session_state.authentication_status = extractor.get_authentication_status()
            
            if success:
                st.success("✅ Newspapers.com authentication successful with cookies!")
                logger.info("Authentication initialized successfully with cookies")
            else:
                st.warning("⚠️ Authentication initialized but may have limited access")
                logger.warning("Authentication partially successful with cookies")
                
        except Exception as e:
            logger.error(f"Authentication initialization failed: {str(e)}")
            st.error(f"❌ Authentication failed: {str(e)}")
            return False
            
        return True

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
    if not st.session_state.newspapers_extractor:
        st.warning("🔐 Initialize authentication first in the sidebar")
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
    # Clear article selection state
    if 'select_all_articles' in st.session_state:
        del st.session_state.select_all_articles
    # Clear Word document results
    if 'word_doc_result' in st.session_state:
        del st.session_state.word_doc_result
    if 'word_doc_timestamp' in st.session_state:
        del st.session_state.word_doc_timestamp
    logger.info("Cleared all extracted data")
    st.success("Cleared all extracted data")

def display_extracted_urls(config):
    """Enhanced display of extracted URLs"""
    logger.info("Displaying extracted URLs with enhanced features")
    
    urls = st.session_state.extracted_urls
    st.write(f"📋 **{len(urls)} URLs found:**")
    
    # Enhanced URL display with domain analysis
    if urls:
        url_df = pd.DataFrame({
            'Index': range(1, len(urls) + 1),
            'URL': urls,
            'Domain': [url.split('/')[2] if len(url.split('/')) > 2 else 'Unknown' for url in urls],
            'Type': ['Newspapers.com' if 'newspapers.com' in url else 'Other' for url in urls]
        })
        
        st.dataframe(url_df, use_container_width=True, hide_index=True)
        
        # Processing controls
        col1, col2 = st.columns([2, 1])
        with col1:
            if st.button("⚡ Process All URLs", type="primary", use_container_width=True):
                start_enhanced_batch_processing(config)
        with col2:
            if st.button("🗑️ Clear", use_container_width=True):
                clear_extracted_data()

# Removed - functionality integrated into display_extracted_urls

# Removed - functionality integrated into display_extracted_urls

def start_enhanced_batch_processing(config):
    """Start enhanced batch processing with auto-authentication"""
    logger.info("Starting enhanced batch processing")
    
    st.session_state.processing_active = True
    urls = st.session_state.extracted_urls
    
    # Debug logging for URL order
    logger.info(f"Processing {len(urls)} URLs with Process All button")
    if urls:
        logger.info(f"URLs in session state (first 3): {urls[:3]}")
    
    # Initialize enhanced storage manager and batch processor
    storage_manager = StorageManager(project_name=config['project_name'])
    batch_processor = BatchProcessor(
        storage_manager=storage_manager, 
        max_workers=config['max_workers'],
        newspapers_cookies=config.get('newspapers_cookies', ''),
        newspapers_extractor=st.session_state.newspapers_extractor,
        lapl_extractor=st.session_state.get('lapl_extractor', None)
        # extraction_method parameter removed - using optimized download_clicks only
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
                enable_advanced_processing=config.get('enable_advanced_processing', True),
                project_name=config['project_name']
            )
        
        # Store enhanced results
        st.session_state.batch_results = results
        st.session_state.processing_active = False
        
        # Debug: Show order preservation status to user
        if results.get('successful', 0) > 0 and results.get('results'):
            original_urls = st.session_state.extracted_urls
            result_urls = [r['url'] for r in results['results']]
            
            # Simple order check: see if results appear in the same relative order as original
            logger.info(f"Order check - Original URLs (first 3): {original_urls[:3]}")
            logger.info(f"Order check - Result URLs (first 3): {result_urls[:3]}")
            
            # Show first few URLs to user for manual verification
            if len(result_urls) >= 2:
                st.info(f"📋 Processing order - First result: {result_urls[0][:60]}...")
                if len(result_urls) >= 2:
                    st.info(f"📋 Processing order - Second result: {result_urls[1][:60]}...")
                    
            # Check if order preservation flag is set
            if results.get('statistics', {}).get('order_preserved'):
                st.success("✅ Order preservation enabled in batch processor")
            else:
                st.warning("⚠️ Order preservation status unknown")
        
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

def test_storage_connection(project_name):
    """Test storage connection with enhanced feedback"""
    logger.info("Testing enhanced storage connection")
    try:
        storage_manager = StorageManager(project_name=project_name)
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

def display_batch_results(config):
    """Enhanced display of batch processing results"""
    if not st.session_state.batch_results:
        st.info("📊 No results yet. Process URLs first.")
        return
    
    results = st.session_state.batch_results
    
    # Summary metrics
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
                # Debug: Print available results and check order
                logger.debug(f"Number of results: {len(results['results'])}")
                logger.info("Results display order check:")
                for idx, r in enumerate(results['results']):
                    logger.debug(f"Result {idx + 1}: {r.get('headline', 'Unknown')} - Markdown path: {r.get('markdown_path', 'Not available')}")
                    if idx < 3:  # Log first 3 for order verification
                        logger.info(f"Display position {idx + 1}: URL {r.get('url', 'unknown')[:50]}...")
                
                # Create a DataFrame for the results table
                success_df = pd.DataFrame([
                    {
                        'Headline': r.get('headline', 'Unknown')[:50] + ('...' if len(r.get('headline', '')) > 50 else ''),
                        'Source': r.get('source', 'Unknown'),
                        'URL': r['url'][:50] + ('...' if len(r['url']) > 50 else ''),
                        'Markdown': r.get('markdown_path', 'Not available'),
                        'Image': '✅' if r.get('image_url') else '❌',
                        'Processing Time': f"{r['processing_time_seconds']:.2f}s"
                    }
                    for r in results['results']
                ])
                
                # Display the results table
                st.dataframe(success_df, use_container_width=True)
                
                # Add preview functionality
                st.write("### 📝 Article Previews")
                
                # Create a selectbox for choosing which article to preview
                preview_options = [f"{i+1}. {r.get('headline', 'Unknown')}" for i, r in enumerate(results['results'])]
                selected_preview = st.selectbox("Select an article to preview:", preview_options)
                
                if selected_preview:
                    # Get the index of the selected article
                    selected_idx = int(selected_preview.split('.')[0]) - 1
                    selected_article = results['results'][selected_idx]
                    
                    # Debug: Print selected article details
                    logger.debug(f"Selected article index: {selected_idx}")
                    logger.debug(f"Selected article: {selected_article.get('headline', 'Unknown')}")
                    logger.debug(f"Markdown path: {selected_article.get('markdown_path', 'Not available')}")
                    
                    # Create two columns for the preview
                    preview_col1, preview_col2 = st.columns([2, 1])
                    
                    with preview_col1:
                        st.write("#### Markdown Preview")
                        markdown_content = None
                        
                        # Try to get markdown content from different sources
                        # First try the markdown_path if it exists
                        markdown_path = selected_article.get('markdown_path')
                        if markdown_path:
                            logger.debug(f"Attempting to read markdown file: {markdown_path}")
                            try:
                                if os.path.exists(markdown_path):
                                    with open(markdown_path, 'r', encoding='utf-8') as f:
                                        markdown_content = f.read()
                                    logger.debug(f"Successfully read markdown content from file, length: {len(markdown_content)}")
                                else:
                                    logger.warning(f"Markdown file not found: {markdown_path}")
                            except Exception as e:
                                logger.error(f"Error reading markdown file: {str(e)}")
                        
                        # If no markdown from file, try to construct from article content
                        if not markdown_content:
                            logger.debug("No markdown file found, constructing from article content")
                            try:
                                # Construct markdown from article components
                                markdown_parts = []
                                
                                # Add headline
                                headline = selected_article.get('headline', '')
                                if headline:
                                    markdown_parts.append(f"# {headline}\n")
                                
                                # Add source and date
                                source = selected_article.get('source', '')
                                date = selected_article.get('date', '')
                                if source or date:
                                    metadata_line = f"**Source:** {source}"
                                    if date:
                                        metadata_line += f" | **Date:** {date}"
                                    markdown_parts.append(f"{metadata_line}\n")
                                
                                # Add content
                                content = selected_article.get('content', '')
                                if content:
                                    markdown_parts.append(f"\n{content}")
                                
                                # Add image if available
                                image_url = selected_article.get('image_url', '')
                                if image_url:
                                    markdown_parts.append(f"\n![Article Image]({image_url})")
                                
                                markdown_content = '\n'.join(markdown_parts)
                                logger.debug(f"Constructed markdown content, length: {len(markdown_content)}")
                                
                            except Exception as e:
                                logger.error(f"Error constructing markdown from article: {str(e)}")
                                markdown_content = f"Error constructing markdown preview: {str(e)}"
                        
                        # Display the markdown content
                        if markdown_content:
                            st.markdown(markdown_content)
                        else:
                            st.warning("No content available for preview")
                        
                    
                    with preview_col2:
                        st.write("#### Image Preview")
                        
                        # First check for image_data (in-memory image)
                        if selected_article.get('image_data'):
                            logger.debug("Displaying image from image_data")
                            st.image(selected_article['image_data'], caption="Extracted Article Image")
                        # Then check for image_url and try to find file on disk
                        elif selected_article.get('image_url'):
                            # Try to find the downloaded image
                            image_path = None
                            source = selected_article.get('source', 'unknown')
                            image_dir = os.path.join('extracted_images', source)
                            
                            logger.debug(f"Looking for image in directory: {image_dir}")
                            
                            if os.path.exists(image_dir):
                                # Find the most recent image file
                                image_files = [f for f in os.listdir(image_dir) if f.endswith(('.jpg', '.jpeg', '.png'))]
                                if image_files:
                                    image_path = os.path.join(image_dir, image_files[-1])
                                    logger.debug(f"Found image file: {image_path}")
                            
                            if image_path and os.path.exists(image_path):
                                logger.debug(f"Displaying image from: {image_path}")
                                st.image(image_path, caption="Extracted Article Image")
                            else:
                                logger.warning(f"No image found at path: {image_path}")
                                st.warning("Image not found locally")
                        else:
                            logger.info("No image data or URL available for this article")
                            st.info("No image available for this article")
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


# Removed - footer function not needed

def handle_article_test(config):
    """Handle testing of individual Newspapers.com article links"""
    if not st.session_state.newspapers_extractor:
        st.warning("🔐 Initialize authentication first in the sidebar")
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
                    # extraction_method parameter removed - using optimized download_clicks only
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


def handle_newspaper_conversion():
    """Handle newspaper clipping conversion functionality"""
    st.write("## 📰 Newspaper Clipping Converter")
    st.write("Convert markdown content into professional newspaper-style Word documents with dynamic column layouts.")
    
    # Show layout info
    st.info("""
    **📰 Layout Rules:**
    - **Short** (<1500 chars): Single column
    - **Long** (1500+ chars): Two columns  
    - **Optimized for 1-page documents**
    """)
    
    # Always use processed articles
    handle_processed_articles_conversion()


def handle_processed_articles_conversion():
    """Handle conversion from processed batch results"""
    if not st.session_state.batch_results or not st.session_state.batch_results.get('results'):
        st.info("Process some articles first to enable newspaper conversion")
        return
    
    st.write("### 📊 Use Processed Articles")
    
    successful_results = st.session_state.batch_results.get('results', [])
    
    # Show source breakdown
    source_breakdown = {}
    for article in successful_results:
        source = article.get('source', 'Unknown')
        source_breakdown[source] = source_breakdown.get(source, 0) + 1
    
    st.write(f"**Available articles:** {len(successful_results)} total")
    if source_breakdown:
        breakdown_text = ", ".join([f"{count} from {source}" for source, count in source_breakdown.items()])
        st.write(f"**Sources:** {breakdown_text}")
    
    # Article selection
    if successful_results:
        st.write("### 📄 Select Articles to Convert")
        
        # Add Select All / Select None buttons
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            if st.button("✅ Select All", help="Select all articles"):
                st.session_state.select_all_articles = True
                st.rerun()
        with col2:
            if st.button("❌ Select None", help="Deselect all articles"):
                st.session_state.select_all_articles = False
                st.rerun()
        
        # Determine default selection
        if hasattr(st.session_state, 'select_all_articles'):
            if st.session_state.select_all_articles:
                default_selection = list(range(len(successful_results)))
            else:
                default_selection = []
            # Clear the flag after using it
            del st.session_state.select_all_articles
        else:
            # Default to all articles selected
            default_selection = list(range(len(successful_results)))
        
        selected_articles = st.multiselect(
            "Choose articles to include in your document:",
            range(len(successful_results)),
            default=default_selection,
            format_func=lambda i: f"{i+1}. {successful_results[i].get('headline', 'Untitled')[:50]}... [{successful_results[i].get('source', 'Unknown')}]",
            help=f"All {len(successful_results)} articles from newspapers.com and other sources are available"
        )
        
        if selected_articles:
            # Show selected articles breakdown by source
            selected_breakdown = {}
            for idx in selected_articles:
                source = successful_results[idx].get('source', 'Unknown')
                selected_breakdown[source] = selected_breakdown.get(source, 0) + 1
            
            selected_breakdown_text = ", ".join([f"{count} from {source}" for source, count in selected_breakdown.items()])
            st.write(f"**Selected:** {len(selected_articles)} articles ({selected_breakdown_text})")
            
            # Show layout estimation for combined content
            total_content_length = 0
            for idx in selected_articles:
                article = successful_results[idx]
                content = article.get('full_content') or article.get('content', '')
                total_content_length += len(content)
            
            st.write(f"**Combined content length:** {total_content_length} characters")
            st.write(f"**Estimated layout:** {determine_layout_display(total_content_length)}")
            
            # Single Word Document Option (Featured)
            st.write("### 📄 Download Single Word Document")
            
            st.info("""
            **📄 Enhanced Single Word Document**
            - All articles combined in one professional document
            - Articles in exact original order  
            - Images embedded and exported to separate folder
            - Complete newspaper-style formatting with dropheads
            - Enhanced image naming with article index and source
            - Ready for immediate use
            """)
            
            # Single featured button
            if st.button("📄 Initiate Download", type="primary", use_container_width=True, help="Create one Word document with all articles and export images to a separate folder"):
                convert_to_single_word_document(selected_articles, successful_results)
        
        # Display persistent Word document results if available
        display_persistent_word_doc_results()

def display_persistent_word_doc_results():
    """Display persistent Word document download results that survive page reloads"""
    if 'word_doc_result' not in st.session_state or 'word_doc_timestamp' not in st.session_state:
        return
    
    result = st.session_state.word_doc_result
    timestamp = st.session_state.word_doc_timestamp
    
    st.write("### 📄 Recently Created Word Document")
    
    # Generate download filename
    doc_filename = f"enhanced_articles_{timestamp}.docx"
    
    # Show success message
    with st.container():
        col1, col2 = st.columns([1, 1])
        with col1:
            st.success(f"✅ Enhanced single Word document available!")
        with col2:
            st.info(f"Contains {result['articles_count']} articles with {result['images_count']} images")
    
    # Word document download button
    with st.container():
        # Read the document for download
        if os.path.exists(result['document_path']):
            with open(result['document_path'], 'rb') as f:
                doc_data = f.read()
            
            st.write(f"📄 **{doc_filename}** ({result['document_size']:,} bytes)")
            
            st.download_button(
                label="📥 Download Single Word Document",
                data=doc_data,
                file_name=doc_filename,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                type="primary",
                use_container_width=True
            )
    
    # Show images folder info and download button
    if result['images_count'] > 0:
        st.write("### 📁 Images Folder")
        st.info(f"All {result['images_count']} images have been exported to: **{os.path.basename(result['images_folder'])}**")
        st.write("This folder contains all original images from the articles, organized with descriptive filenames.")
        
        # Create zip file with images for download
        images_zip_path = result['images_folder'] + '.zip'
        try:
            import zipfile
            if not os.path.exists(images_zip_path):
                with zipfile.ZipFile(images_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for img in result['images']:
                        if os.path.exists(img['path']):
                            zipf.write(img['path'], img['filename'])
            
            if os.path.exists(images_zip_path):
                with open(images_zip_path, 'rb') as f:
                    zip_data = f.read()
                
                st.download_button(
                    label="📁 Download Images Folder",
                    data=zip_data,
                    file_name=f"article_images_{timestamp}.zip",
                    mime="application/zip"
                )
        except Exception as e:
            st.warning("Images folder created but zip download failed")
    
    
    # Add clear button
    if st.button("🗑️ Clear Results", help="Clear the Word document results"):
        if 'word_doc_result' in st.session_state:
            del st.session_state.word_doc_result
        if 'word_doc_timestamp' in st.session_state:
            del st.session_state.word_doc_timestamp
        st.rerun()

def determine_layout_display(content_length):
    """Return display string for layout type"""
    if content_length < 1500:
        return "Single column (headline above image, body below)"
    else:
        return "Two columns (image on left, text on right)"


def convert_processed_articles(selected_indices, results):
    """Convert processed articles to individual newspaper documents in a zip file"""
    with st.spinner("Converting processed articles to individual newspaper documents..."):
        try:
            # Get original URL order from session state for order preservation
            original_url_order = st.session_state.get('extracted_urls', [])
            
            # Reorder selected_indices based on original URL order to preserve document order
            if original_url_order:
                # Create URL to result index mapping
                url_to_result_index = {}
                for idx in selected_indices:
                    article_url = results[idx].get('url', '')
                    if article_url:
                        url_to_result_index[article_url] = idx
                
                # Reorder selected indices based on original URL order
                ordered_indices = []
                for url in original_url_order:
                    if url in url_to_result_index:
                        ordered_indices.append(url_to_result_index[url])
                
                # Add any remaining selected indices that weren't in original order
                for idx in selected_indices:
                    if idx not in ordered_indices:
                        ordered_indices.append(idx)
                        logger.info(f"Added selected article not in original order for zip: index {idx}")
                
                selected_indices = ordered_indices
                logger.info(f"Reordered {len(selected_indices)} articles based on original URL order for zip documents")
            
            # Create individual markdown content for each selected article
            markdown_contents = []
            
            for idx in selected_indices:
                article = results[idx]
                headline = article.get('headline', 'Untitled Article')
                source = article.get('source', 'Unknown Source')
                author = article.get('author', '')
                date = article.get('date', 'Unknown Date')
                content = article.get('full_content') or article.get('content', 'No content available')
                
                # Create individual markdown content
                article_markdown = f"# {headline}\n\n"
                if author:
                    article_markdown += f"*By {author}*\n\n"
                article_markdown += f"*{source} - {date}*\n\n"
                article_markdown += f"{content}\n\n"
                
                # Add image if available
                if article.get('image_url'):
                    article_markdown += f"![Article Image]({article['image_url']})\n\n"
                
                markdown_contents.append(article_markdown)
                logger.info(f"Prepared article: {headline}")
            
            if not markdown_contents:
                st.error("❌ No valid articles to convert")
                return
            
            # Convert to zip file with individual documents
            # Pass the selected articles so images can be extracted from image_data
            selected_articles_data = [results[idx] for idx in selected_indices]
            logger.info(f"Converting {len(markdown_contents)} processed articles to newspaper format")
            result = convert_multiple_markdown_to_newspaper_zip(markdown_contents, processed_articles=selected_articles_data)
            
            logger.info(f"Processed articles conversion result: {result is not None}")
            if result:
                logger.info(f"Result keys: {list(result.keys())}")
                logger.info(f"Zip data size: {len(result.get('zip_data', b''))} bytes")
            
            if result and result.get('zip_data'):
                st.success(f"✅ Successfully converted {len(selected_indices)} articles to individual newspaper documents!")
                
                # Generate zip filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_filename = f"processed_articles_{timestamp}.zip"
                
                # Create download button for zip file
                st.write("### 📥 Download Newspaper Documents")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📦 **{zip_filename}** ({result['total_size']:,} bytes)")
                    st.write(f"Contains {result['document_count']} individual Word documents")
                with col2:
                    st.download_button(
                        label="📥 Download Zip",
                        data=result['zip_data'],
                        file_name=zip_filename,
                        mime="application/zip"
                    )
                
                # Show detailed file list
                with st.expander("📋 Files in Zip Package"):
                    st.write(f"**Total documents:** {result['document_count']}")
                    st.write(f"**Total images:** {result.get('image_count', 0)}")
                    st.write(f"**Total size:** {result['total_size']:,} bytes")
                    st.write("**Individual files:**")
                    
                    for i, doc_info in enumerate(result['documents']):
                        original_article = results[selected_indices[i]]
                        st.write(f"  {i+1}. **{doc_info['filename']}** - {original_article.get('source', 'Unknown')} ({doc_info['size']:,} bytes)")
                    
                    if result.get('image_count', 0) > 0:
                        st.write(f"  📁 **clippings/** directory with {result['image_count']} scraped images")
                    
                    st.write("**Features:**")
                    st.write("• Individual Word documents for each processed article")
                    st.write("• Filenames based on article headlines with hyphens")
                    st.write("• Dynamic column layouts based on content length")
                    st.write("• Images from processed articles included")
                    st.write("• Professional newspaper styling")
                    st.write("• Source and date information preserved")
                    st.write("• Scraped images saved in clippings/ directory")
            else:
                if not result:
                    st.error("❌ Failed to create newspaper zip file - conversion returned None")
                    logger.error("Processed articles conversion function returned None")
                elif not result.get('zip_data'):
                    st.error("❌ Failed to create newspaper zip file - no zip data in result")
                    logger.error(f"Processed articles result keys: {list(result.keys()) if result else 'None'}")
                else:
                    st.error("❌ Failed to create newspaper zip file - unknown error")
                    logger.error(f"Processed articles unknown error with result: {result}")
                
        except Exception as e:
            logger.error(f"Article conversion error: {str(e)}")
            st.error(f"Conversion error: {str(e)}")

def convert_processed_articles_to_components(selected_indices, results):
    """Convert processed articles to component documents organized by word count, font, and title"""
    with st.spinner("Converting processed articles to component documents..."):
        try:
            # Get original URL order from session state for order preservation
            original_url_order = st.session_state.get('extracted_urls', [])
            
            # Reorder selected_indices based on original URL order to preserve document order
            if original_url_order:
                # Create URL to result index mapping
                url_to_result_index = {}
                for idx in selected_indices:
                    article_url = results[idx].get('url', '')
                    if article_url:
                        url_to_result_index[article_url] = idx
                
                # Reorder selected indices based on original URL order
                ordered_indices = []
                for url in original_url_order:
                    if url in url_to_result_index:
                        ordered_indices.append(url_to_result_index[url])
                
                # Add any remaining selected indices that weren't in original order
                for idx in selected_indices:
                    if idx not in ordered_indices:
                        ordered_indices.append(idx)
                        logger.info(f"Added selected article not in original order for components: index {idx}")
                
                selected_indices = ordered_indices
                logger.info(f"Reordered {len(selected_indices)} articles based on original URL order for component documents")
            
            # Transform processed articles into the format expected by component converter
            articles_data = []
            
            for idx in selected_indices:
                article = results[idx]
                headline = article.get('headline', 'Untitled Article')
                source = article.get('source', 'Unknown Source')
                date = article.get('date', 'Unknown Date')
                content = article.get('full_content') or article.get('content', 'No content available')
                url = article.get('url', '')
                
                # Create article data in the format expected by component converter
                article_data = {
                    'headline': headline,
                    'text': content,
                    'source': source,
                    'author': article.get('author', ''),
                    'date': date,
                    'url': url,
                    'image_url': article.get('image_url'),  # Pass through the image URL from batch results
                    'image_data': article.get('image_data'),  # Pass through PIL Image from newspapers.com
                    'word_count': article.get('word_count', 0),  # Pass through word count for capsule selection
                    'typography_capsule': article.get('typography_capsule'),  # Pass through capsule data
                    'structured_content': article.get('structured_content', [])  # Pass through structured content
                }
                
                articles_data.append(article_data)
                logger.info(f"Prepared component data for article: {headline}")
            
            if not articles_data:
                st.error("❌ No valid articles to convert")
                return
            
            # Convert to component zip file
            logger.info(f"Converting {len(articles_data)} articles to component format")
            result = convert_articles_to_component_zip(articles_data)
            
            logger.info(f"Component conversion result: {result is not None}")
            if result:
                logger.info(f"Result keys: {list(result.keys())}")
                logger.info(f"Zip data size: {len(result.get('zip_data', b''))} bytes")
            
            if result and result.get('zip_data'):
                st.success(f"✅ Successfully created component documents from {len(selected_indices)} articles!")
                
                # Generate zip filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_filename = f"component_articles_{timestamp}.zip"
                
                # Create download button for zip file
                st.write("### 📥 Download Component Documents")
                
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📦 **{zip_filename}** ({result['total_size']:,} bytes)")
                    st.write(f"Contains {result['document_count']} component documents in {result['article_count']} article directories")
                with col2:
                    st.download_button(
                        label="📥 Download Zip",
                        data=result['zip_data'],
                        file_name=zip_filename,
                        mime="application/zip"
                    )
                
                # Show detailed breakdown
                with st.expander("📋 Component Package Details"):
                    st.write(f"**Total component documents:** {result['document_count']}")
                    st.write(f"**Total images:** {result.get('image_count', 0)}")
                    st.write(f"**Total article directories:** {result['article_count']}")
                    st.write(f"**Total size:** {result['total_size']:,} bytes")
                    
                    # Show component counts
                    st.write("**Component breakdown:**")
                    for component_type, count in result.get('component_counts', {}).items():
                        st.write(f"  • {component_type.title()} documents: {count}")
                    
                    st.write("**Article directories:**")
                    for article_info in result.get('articles', []):
                        st.write(f"  📁 **{article_info['directory']}**")
                        st.write(f"    • Title: {article_info['title']}")
                        st.write(f"    • Word count: {article_info['word_count']} words")
                        st.write(f"    • Font: {article_info['font']}")
                        st.write(f"    • Components: {article_info['components']} documents")
                        st.write(f"    • Images: {article_info['images']} files")
                    
                    st.write("**Package structure:**")
                    st.code(f"""
{zip_filename.replace('.zip', '')}
├── {result['articles'][0]['directory'] if result.get('articles') else 'WORDCOUNT_FONT_TITLE'}/
│   ├── heading.docx
│   ├── body.docx
│   ├── blockquote.docx (if quotes found)
│   ├── images/ (if any)
│   └── article_info.txt
├── [next article directory]/
└── ...
                    """)
                    
                    st.write("**Key Features:**")
                    st.write("• **Organized by metadata**: Each article in its own directory named with word count, font, and title")
                    st.write("• **Separate components**: Individual Word documents for heading, body, and blockquotes")
                    st.write("• **Font selection**: Automatically chooses appropriate fonts based on source domain")
                    st.write("• **Dynamic styling**: Professional newspaper styling for each component")
                    st.write("• **Image handling**: Downloads and organizes images by article")
                    st.write("• **Metadata tracking**: Includes article info file with processing details")
            else:
                if not result:
                    st.error("❌ Failed to create component zip file - conversion returned None")
                    logger.error("Component conversion function returned None")
                elif not result.get('zip_data'):
                    st.error("❌ Failed to create component zip file - no zip data in result")
                    logger.error(f"Component conversion result keys: {list(result.keys()) if result else 'None'}")
                else:
                    st.error("❌ Failed to create component zip file - unknown error")
                    logger.error(f"Component conversion unknown error with result: {result}")
                
        except Exception as e:
            logger.error(f"Component conversion error: {str(e)}")
            st.error(f"Component conversion error: {str(e)}")

def convert_to_single_word_document(selected_indices, results):
    """Convert processed articles to a single Word document with separate images folder"""
    
    # Add progress feedback
    progress_placeholder = st.empty()
    status_text = st.empty()
    
    with st.spinner("Creating enhanced single Word document with all articles and images..."):
        try:
            # Update progress
            status_text.text("📝 Preparing articles for document creation...")
            progress_placeholder.progress(0.1)
            
            # Get original URL order from session state for order preservation
            original_url_order = st.session_state.get('extracted_urls', [])
            
            # Reorder selected_indices based on original URL order to preserve document order
            if original_url_order:
                # Create URL to result index mapping
                url_to_result_index = {}
                for idx in selected_indices:
                    article_url = results[idx].get('url', '')
                    if article_url:
                        url_to_result_index[article_url] = idx
                
                # Reorder selected indices based on original URL order
                ordered_indices = []
                for url in original_url_order:
                    if url in url_to_result_index:
                        ordered_indices.append(url_to_result_index[url])
                
                # Add any remaining selected indices that weren't in original order
                for idx in selected_indices:
                    if idx not in ordered_indices:
                        ordered_indices.append(idx)
                        logger.info(f"Added selected article not in original order: index {idx}")
                
                selected_indices = ordered_indices
                logger.info(f"Reordered {len(selected_indices)} articles based on original URL order for Word document")
            
            # Transform processed articles into the format expected by the converter
            articles_data = []
            
            for idx in selected_indices:
                article = results[idx]
                headline = article.get('headline', 'Untitled Article')
                source = article.get('source', 'Unknown Source')
                author = article.get('author', '')
                date = article.get('date', 'Unknown Date')
                content = article.get('full_content') or article.get('content', 'No content available')
                url = article.get('url', '')
                
                # Create article data for the converter
                article_data = {
                    'headline': headline,
                    'source': source,
                    'author': author,
                    'date': date,
                    'content': content,
                    'full_content': content,
                    'url': url,
                    'image_url': article.get('image_url'),
                    'image_data': article.get('image_data')
                }
                
                articles_data.append(article_data)
                logger.info(f"Prepared article for single document: {headline}")
            
            if not articles_data:
                st.error("❌ No valid articles to convert")
                return
            
            # Update progress
            status_text.text("🔄 Preserving original article order...")
            progress_placeholder.progress(0.3)
            
            # Get original URL order from session state for order preservation
            original_url_order = st.session_state.get('extracted_urls', [])
            
            # Update progress
            status_text.text("📰 Creating enhanced Word document with professional formatting...")
            progress_placeholder.progress(0.5)
            
            # Create single Word document with images and order preservation
            logger.info(f"Converting {len(articles_data)} articles to single Word document with original URL order")
            result = create_single_word_document_with_images(articles_data, original_url_order=original_url_order)
            
            # Update progress
            status_text.text("✅ Document creation completed!")
            progress_placeholder.progress(1.0)
            
            if result:
                # Clear progress elements to prevent UI interference
                progress_placeholder.empty()
                status_text.empty()
                
                # Store result in session state for persistence
                st.session_state.word_doc_result = result
                st.session_state.word_doc_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                
                st.balloons()
                st.success(f"✅ Enhanced single Word document created successfully!")
                st.info(f"Document contains {result['articles_count']} articles with {result['images_count']} images")
                st.info("📥 Download buttons available below!")
                
            else:
                # Clear progress elements even when there's an error
                progress_placeholder.empty()
                status_text.empty()
                st.error("❌ Failed to create single Word document")
                
        except Exception as e:
            # Clear progress elements in case of exception
            progress_placeholder.empty()
            status_text.empty()
            logger.error(f"Single document conversion error: {str(e)}")
            st.error(f"Single document conversion error: {str(e)}")

def use_saved_newspapers_credentials():
    """Use existing newspapers.com cookies to initialize authentication"""
    try:
        with st.spinner("📁 Loading saved newspapers.com credentials..."):
            ensure_credential_manager()
            cred_manager = st.session_state.credential_manager
            cookies_result = cred_manager.load_newspapers_cookies()
            
            if not cookies_result['success']:
                st.error("❌ No saved newspapers.com cookies found. Please upload a cookies file first.")
                st.info("💡 Use the 'Upload Cookies File' section below to save cookies")
                return
            
            # Initialize extractor with loaded cookies
            extractor = NewspapersComExtractor(auto_auth=True)
            extractor.cookie_manager.cookies = cookies_result['cookies']
            
            # Try to initialize
            success = extractor.initialize()
            
            # Store in session state
            st.session_state.newspapers_extractor = extractor
            st.session_state.authentication_status = extractor.get_authentication_status()
            
            if success:
                st.success("✅ Newspapers.com connected successfully using saved cookies!")
                st.balloons()
                logger.info("Newspapers.com initialized successfully with saved cookies")
                
                # Show cookie info
                metadata = cookies_result.get('metadata', {})
                cookie_count = metadata.get('cookie_count', 'unknown')
                saved_at = metadata.get('saved_at', 'unknown date')
                st.info(f"🍪 Using {cookie_count} cookies saved on {saved_at[:10]}")
            else:
                st.warning("⚠️ Cookies loaded but authentication may have limited access")
                st.info("💡 Try uploading fresh cookies if you encounter issues")
                
    except Exception as e:
        logger.error(f"Failed to use saved newspapers.com credentials: {str(e)}")
        st.error(f"❌ Error loading saved credentials: {str(e)}")


def use_saved_lapl_credentials():
    """Use existing LAPL cookies to initialize authentication"""
    try:
        with st.spinner("📁 Loading saved LAPL credentials..."):
            ensure_credential_manager()
            cred_manager = st.session_state.credential_manager
            cookies_result = cred_manager.load_lapl_cookies()
            
            if not cookies_result['success']:
                st.error("❌ No saved LAPL cookies found. Please upload a cookies file first.")
                st.info("💡 Use the 'Upload LAPL Cookies File' section below to save cookies")
                return
            
            # Initialize extractor with loaded cookies
            from extractors.lapl_extractor import LAPLExtractor
            extractor = LAPLExtractor(auto_auth=False)
            extractor.load_cookies_from_data(cookies_result['cookies'])
            
            # Store in session state
            st.session_state.lapl_extractor = extractor
            
            # Test authentication
            auth_test = extractor.test_authentication()
            
            if auth_test['success'] and auth_test['authenticated']:
                st.success("✅ LAPL connected successfully using saved cookies!")
                st.balloons()
                logger.info("LAPL initialized successfully with saved cookies")
                
                # Show cookie info
                metadata = cookies_result.get('metadata', {})
                cookie_count = metadata.get('cookie_count', 'unknown')
                saved_at = metadata.get('saved_at', 'unknown date')
                st.info(f"🍪 Using {cookie_count} cookies saved on {saved_at[:10]}")
            else:
                st.warning("⚠️ LAPL cookies loaded but authentication test failed")
                st.info("💡 Try uploading fresh cookies if you encounter issues")
                st.info(f"Test result: {auth_test.get('message', 'Unknown error')}")
                
    except Exception as e:
        logger.error(f"Failed to use saved LAPL credentials: {str(e)}")
        st.error(f"❌ Error loading saved credentials: {str(e)}")

def initialize_lapl_authentication_with_cookies(uploaded_cookies):
    """Initialize LAPL authentication using only cookies"""
    logger.info("Initializing LAPL authentication with cookies only")
    
    try:
        with st.spinner("🔐 Initializing LAPL authentication..."):
            # Initialize extractor
            from extractors.lapl_extractor import LAPLExtractor
            extractor = LAPLExtractor(auto_auth=False)
            
            # Load cookies from uploaded file
            try:
                cookies_data = json.loads(uploaded_cookies.getvalue().decode())
                
                # Save cookies using credential manager
                ensure_credential_manager()
                cred_manager = st.session_state.credential_manager
                save_result = cred_manager.save_lapl_cookies(cookies_data)
                
                if save_result['success']:
                    st.success(f"✅ Saved {save_result['cookie_count']} cookies for future sessions!")
                    
                    # Load cookies into extractor
                    load_result = extractor.load_cookies_from_data(cookies_data)
                    
                    if load_result['success']:
                        # Store in session state
                        st.session_state.lapl_extractor = extractor
                        
                        # Test authentication
                        auth_test = extractor.test_authentication()
                        
                        if auth_test['success'] and auth_test['authenticated']:
                            st.success("✅ LAPL authentication successful!")
                            st.balloons()
                        else:
                            st.warning("⚠️ LAPL cookies saved but authentication test failed")
                            st.info(f"Test result: {auth_test.get('message', 'Unknown error')}")
                    else:
                        st.error(f"❌ Failed to load cookies: {load_result['error']}")
                else:
                    st.error(f"❌ Failed to save cookies: {save_result['error']}")
                    
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON file. Please upload a valid cookies JSON file.")
            except Exception as e:
                st.error(f"❌ Error processing cookies file: {str(e)}")
                
    except Exception as e:
        logger.error(f"Failed to initialize LAPL authentication: {str(e)}")
        st.error(f"❌ Authentication failed: {str(e)}")

def test_lapl_url_access(test_url: str):
    """Test access to a specific LAPL URL"""
    try:
        # Check if LAPL extractor is available
        if 'lapl_extractor' not in st.session_state or st.session_state.lapl_extractor is None:
            st.error("❌ No LAPL authentication available. Please upload and save cookies first.")
            return
        
        with st.spinner(f"🔍 Testing access to LAPL URL..."):
            extractor = st.session_state.lapl_extractor
            result = extractor.access_specific_url(test_url)
            
            if result['success']:
                st.success("✅ URL access successful!")
                
                # Show detailed results
                st.info(f"Status Code: {result['status_code']}")
                st.info(f"Content Length: {result['content_length']:,} characters")
                st.info(f"Final URL: {result['final_url']}")
                
                if result['has_newspaper_content']:
                    st.success("📰 Newspaper content detected!")
                else:
                    st.warning("⚠️ No clear newspaper content indicators found")
                
                if result['has_errors']:
                    st.error("❌ Error indicators found in content")
                
                # Show content preview
                if result.get('content_preview'):
                    st.text_area("Content Preview (first 500 chars)", result['content_preview'], height=100)
                    
            else:
                st.error(f"❌ URL access failed: {result['message']}")
                if result.get('status_code'):
                    st.info(f"Status Code: {result['status_code']}")
                    
    except Exception as e:
        logger.error(f"Failed to test LAPL URL access: {str(e)}")
        st.error(f"❌ Test failed: {str(e)}")

if __name__ == "__main__":
    try:
        logger.info("Enhanced application starting...")
        main()
    except Exception as e:
        logger.critical(f"Critical enhanced application error: {str(e)}", exc_info=True)
        st.error(f"A critical error occurred: {str(e)}")