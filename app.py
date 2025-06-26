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
import os
import zipfile
import tempfile
from pathlib import Path

# Import existing modules
from extractors.url_extractor import extract_from_url
from extractors.newspapers_extractor import NewspapersComExtractor, extract_from_newspapers_com
from utils.logger import setup_logging
from utils.processor import process_article
from utils.document_processor import extract_urls_from_docx, validate_document_format
from utils.storage_manager import StorageManager
from utils.batch_processor import BatchProcessor
from utils.icml_converter import convert_to_icml
from utils.modular_icml_converter import create_modular_icml_package
from utils.newspaper_converter import convert_markdown_to_newspaper, convert_multiple_markdown_to_newspaper_zip

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
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["📄 Document Processing", "🔬 Test Article", "🔍 Newspapers.com Search", "📊 Batch Results", "🖼️ Image Gallery", "📑 ICML Export", "📰 Newspaper Clipping"])
    
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
        
    with tab6:
        handle_icml_conversion()
        
    with tab7:
        handle_newspaper_conversion()
    
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
    
    # Get login credentials
    email = st.sidebar.text_input(
        "Newspapers.com Email",
        help="Enter your Newspapers.com account email"
    )
    
    password = st.sidebar.text_input(
        "Newspapers.com Password",
        type="password",
        help="Enter your Newspapers.com account password"
    )

    # Add cookie file upload
    uploaded_cookies = st.sidebar.file_uploader(
        "Upload Cookies (Optional)",
        type=['json'],
        help="Upload a JSON file containing Newspapers.com cookies"
    )
    
    # Initialize/refresh authentication
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.sidebar.button("🔄 Initialize Auth"):
            initialize_newspapers_authentication(email, password, uploaded_cookies)
    
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
    date_range = st.sidebar.selectbox(
        "Date Range",
        ["Any", "2020-2025", "2010-2019", "2000-2009", "1990-1999", "1980-1989"],
        help="Filter articles by date range"
    )
    
    return {
        'bucket_name': bucket_name,
        'project_name': project_name,
        'max_workers': max_workers,
        'delay_between_requests': delay_between_requests,
        'date_range': date_range
    }

def initialize_newspapers_authentication(email: str, password: str, uploaded_cookies=None):
    """Initialize Newspapers.com authentication"""
    logger.info("Initializing Newspapers.com authentication")
    
    with st.spinner("Initializing Newspapers.com authentication..."):
        try:
            # Check if we're in Replit environment
            is_replit = 'REPL_ID' in os.environ or 'REPL_SLUG' in os.environ
            
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
                # Debug: Print available results
                logger.debug(f"Number of results: {len(results['results'])}")
                for idx, r in enumerate(results['results']):
                    logger.debug(f"Result {idx + 1}: {r.get('headline', 'Unknown')} - Markdown path: {r.get('markdown_path', 'Not available')}")
                
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
                        markdown_path = selected_article.get('markdown_path')
                        if markdown_path:
                            logger.debug(f"Attempting to read markdown file: {markdown_path}")
                            try:
                                if os.path.exists(markdown_path):
                                    with open(markdown_path, 'r', encoding='utf-8') as f:
                                        markdown_content = f.read()
                                    logger.debug(f"Successfully read markdown content, length: {len(markdown_content)}")
                                    st.markdown(markdown_content)
                                else:
                                    logger.error(f"Markdown file not found: {markdown_path}")
                                    st.error(f"Markdown file not found at: {markdown_path}")
                            except Exception as e:
                                logger.error(f"Error reading markdown file: {str(e)}")
                                st.error(f"Error reading markdown file: {str(e)}")
                        else:
                            logger.warning("No markdown path available for selected article")
                            st.warning("No markdown file available for preview")
                    
                    with preview_col2:
                        st.write("#### Image Preview")
                        if selected_article.get('image_url'):
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
                            logger.info("No image URL available for this article")
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

def handle_icml_conversion():
    """Handle ICML conversion of processed articles"""
    st.write("## 📑 ICML Export for InDesign")
    
    # Debug toggle for ICML conversion
    icml_debug_mode = st.checkbox("🔍 Enable ICML Debug Mode", help="Show detailed ICML conversion process and content analysis")
    
    if not st.session_state.batch_results or not st.session_state.batch_results.get('results'):
        st.info("Process some articles first to enable ICML export")
        return
    
    # Conversion type selection
    st.write("### Choose Conversion Type")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("""
        **📄 Single File ICML**
        - All articles combined into one ICML file
        - Easy to import as a complete document
        - Traditional workflow
        """)
    
    with col2:
        st.info("""
        **📁 Modular ICML Package**
        - Individual ICML files for each article element
        - Separate files for title, author/date, and body
        - Images downloaded and organized
        - Precise InDesign placement control
        """)
    
    conversion_type = st.radio(
        "Select conversion type:",
        ["Single File ICML", "Modular ICML Package"],
        help="Choose how you want to structure the ICML output"
    )
    
    # Create a temporary directory for markdown files
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Get successful results
    successful_results = st.session_state.batch_results.get('results', [])
    
    if not successful_results:
        st.warning("No successfully processed articles found to convert")
        return
    
    # Create markdown content for each article
    markdown_files = []
    for idx, result in enumerate(successful_results):
        # Get full content - optimized for Replit environment
        article_content = 'No content available'
        
        # Primary: try to get full_content from result (works in Replit)
        if result.get('full_content'):
            article_content = result.get('full_content')
            if icml_debug_mode:
                st.write(f"📝 Using full_content for article {idx + 1}: {len(article_content)} characters")
        
        # Fallback: use the truncated content and warn user
        else:
            article_content = result.get('content', 'No content available')
            if icml_debug_mode:
                st.warning(f"⚠️ Using truncated content for article {idx + 1}: {len(article_content)} characters")
                st.write("💡 **Note**: If content appears truncated, there may be an issue with the batch processing results.")
        
        # Create enhanced markdown content with proper formatting for modular converter
        author_line = f"*By {result.get('source', 'Unknown Source')}*"
        date_line = f"*{result.get('date', 'Unknown Date')}*"
        
        if conversion_type == "Modular ICML Package":
            # Format for modular converter (matches expected structure)
            markdown_content = f"""# {result.get('headline', 'Untitled Article')}

{author_line}
{date_line}

{article_content}

---
*Source: {result.get('source', 'Unknown Source')}*
"""
        else:
            # Original format for single file
            markdown_content = f"""# {result.get('headline', 'Untitled Article')}

Source: {result.get('source', 'Unknown Source')}
Date: {result.get('date', 'Unknown Date')}

{article_content}
"""
        
        # Save markdown file
        md_filename = f"article_{idx + 1}.md"
        md_path = output_dir / md_filename
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        markdown_files.append(str(md_path))  # Convert Path to string
    
    # Show markdown files info
    if icml_debug_mode:
        st.write("### 📋 Debug: Markdown Files Created")
        for i, md_file in enumerate(markdown_files):
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                st.write(f"**File {i+1}:** {os.path.basename(md_file)} ({len(content)} characters)")
                if len(content) > 200:
                    st.write(f"**Preview:** {content[:200]}...")
                else:
                    st.write(f"**Content:** {content}")
            except Exception as e:
                st.error(f"Error reading {md_file}: {str(e)}")
    
    # Convert to ICML
    button_text = "🔄 Create Single ICML File" if conversion_type == "Single File ICML" else "📁 Create Modular ICML Package"
    
    if st.button(button_text):
        conversion_status = st.empty()
        
        if conversion_type == "Single File ICML":
            conversion_status.write("Converting articles to single ICML file...")
            
            with st.spinner("Converting articles to ICML format..."):
                try:
                    # Convert all markdown files to a single ICML with debug mode
                    icml_content = convert_to_icml(markdown_files, debug_mode=icml_debug_mode)
                    
                    # Generate output filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_filename = f"combined_articles_{timestamp}.icml"
                    
                    # Create download button for the ICML file
                    st.download_button(
                        label=f"📥 Download {output_filename}",
                        data=icml_content,
                        file_name=output_filename,
                        mime="application/x-indesign"
                    )
                    
                    st.success(f"✅ Successfully converted {len(markdown_files)} articles to a single ICML file")
                    
                    # Show summary
                    with st.expander("📋 Single File Conversion Summary"):
                        st.write(f"**Input files:** {len(markdown_files)} markdown files")
                        file_list = ", ".join([os.path.basename(f) for f in markdown_files])
                        st.write(f"**Files combined:** {file_list}")
                        st.write(f"**Output:** {output_filename}")
                        st.write("**Debug mode:** " + ("Enabled" if icml_debug_mode else "Disabled"))
                        st.write("**Format:** Single ICML file with all articles combined")
                    
                except Exception as e:
                    st.error(f"ICML conversion error: {str(e)}")
                    logger.error(f"ICML conversion error: {str(e)}")
        
        else:  # Modular ICML Package
            conversion_status.write("Creating modular ICML package...")
            
            with st.spinner("Creating modular ICML package with individual files..."):
                try:
                    # Create modular ICML package
                    zip_content, zip_filename = create_modular_icml_package(markdown_files, debug_mode=icml_debug_mode)
                    
                    # Create download button for the zip file
                    st.download_button(
                        label=f"📥 Download {zip_filename}",
                        data=zip_content,
                        file_name=zip_filename,
                        mime="application/zip"
                    )
                    
                    st.success(f"✅ Successfully created modular ICML package from {len(markdown_files)} articles!")
                    
                    # Show summary
                    with st.expander("📁 Modular Package Summary"):
                        st.write(f"**Input files:** {len(markdown_files)} markdown files")
                        file_list = ", ".join([os.path.basename(f) for f in markdown_files])
                        st.write(f"**Files processed:** {file_list}")
                        st.write(f"**Output:** {zip_filename}")
                        st.write("**Structure:** Individual ICML files for title, author/date, and body")
                        st.write("**Debug mode:** " + ("Enabled" if icml_debug_mode else "Disabled"))
                        st.write("**Format:** Zip package with subdirectories for each article")
                        
                        # Show expected structure
                        st.write("**Package Structure:**")
                        st.code(f"""
{zip_filename.replace('.zip', '')}
├── article_1/
│   ├── article_1_title.icml
│   ├── article_1_author.icml
│   ├── article_1_body.icml
│   └── images/ (if any)
├── article_2/
│   ├── article_2_title.icml
│   ├── article_2_author.icml
│   ├── article_2_body.icml
│   └── images/ (if any)
└── ...
                        """)
                
                except Exception as e:
                    st.error(f"Modular ICML package creation error: {str(e)}")
                    logger.error(f"Modular ICML package creation error: {str(e)}")
        
        # Clean up temporary files
        try:
            for md_file in markdown_files:
                if os.path.exists(md_file):
                    os.unlink(md_file)
        except Exception as e:
            logger.warning(f"Error cleaning up temporary files: {str(e)}")

def handle_newspaper_conversion():
    """Handle newspaper clipping conversion functionality"""
    st.write("## 📰 Newspaper Clipping Converter")
    st.write("Convert markdown content into professional newspaper-style Word documents with dynamic column layouts.")
    
    # Conversion type selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        conversion_source = st.radio(
            "Choose content source:",
            ["Upload Markdown File", "Use Processed Articles"],
            help="Select whether to upload a new markdown file or use articles from batch processing"
        )
    
    with col2:
        st.info("""
        **📰 Layout Rules:**
        - **Short** (<1500 chars): Single column
        - **Long** (1500+ chars): Two columns  
        - **Optimized for 1-page documents**
        """)
    
    if conversion_source == "Upload Markdown File":
        handle_markdown_upload_conversion()
    else:
        handle_processed_articles_conversion()

def handle_markdown_upload_conversion():
    """Handle conversion from uploaded markdown files"""
    st.write("### 📄 Upload Markdown Files")
    
    uploaded_md_files = st.file_uploader(
        "Choose markdown files",
        type=["md", "txt"],
        accept_multiple_files=True,
        help="Upload one or more markdown files to convert to newspaper format"
    )
    
    if uploaded_md_files:
        st.success(f"✅ Uploaded {len(uploaded_md_files)} file(s)")
        
        # Show file details
        for i, uploaded_file in enumerate(uploaded_md_files):
            with st.expander(f"📄 {uploaded_file.name} ({uploaded_file.size:,} bytes)"):
                try:
                    content = uploaded_file.getvalue().decode('utf-8')
                    st.write(f"**Content length:** {len(content)} characters")
                    st.write(f"**Estimated layout:** {determine_layout_display(len(content))}")
                    
                    # Show preview
                    if len(content) > 200:
                        st.write(f"**Preview:** {content[:200]}...")
                    else:
                        st.write(f"**Content:** {content}")
                except Exception as e:
                    st.error(f"Error reading file: {str(e)}")
        
        # Convert button
        if st.button("🔄 Convert to Newspaper Format", type="primary"):
            convert_uploaded_markdown_files(uploaded_md_files)

def handle_processed_articles_conversion():
    """Handle conversion from processed batch results"""
    if not st.session_state.batch_results or not st.session_state.batch_results.get('results'):
        st.info("Process some articles first to enable newspaper conversion")
        return
    
    st.write("### 📊 Use Processed Articles")
    
    successful_results = st.session_state.batch_results.get('results', [])
    st.write(f"**Available articles:** {len(successful_results)}")
    
    # Article selection
    if successful_results:
        selected_articles = st.multiselect(
            "Select articles to convert:",
            range(len(successful_results)),
            default=list(range(min(3, len(successful_results)))),  # Select first 3 by default
            format_func=lambda i: f"{i+1}. {successful_results[i].get('headline', 'Untitled')[:50]}..."
        )
        
        if selected_articles:
            st.write(f"**Selected:** {len(selected_articles)} articles")
            
            # Show layout estimation for combined content
            total_content_length = 0
            for idx in selected_articles:
                article = successful_results[idx]
                content = article.get('full_content') or article.get('content', '')
                total_content_length += len(content)
            
            st.write(f"**Combined content length:** {total_content_length} characters")
            st.write(f"**Estimated layout:** {determine_layout_display(total_content_length)}")
            
            if st.button("🔄 Convert Selected Articles", type="primary"):
                convert_processed_articles(selected_articles, successful_results)

def determine_layout_display(content_length):
    """Return display string for layout type"""
    if content_length < 1500:
        return "Single column (headline above image, body below)"
    else:
        return "Two columns (image on left, text on right)"

def convert_uploaded_markdown_files(uploaded_files):
    """Convert uploaded markdown files to individual newspaper documents in a zip file"""
    with st.spinner("Converting markdown files to individual newspaper documents..."):
        try:
            # Extract content from uploaded files
            markdown_contents = []
            file_names = []
            
            for uploaded_file in uploaded_files:
                content = uploaded_file.getvalue().decode('utf-8')
                markdown_contents.append(content)
                file_names.append(uploaded_file.name)
                logger.info(f"Loaded content from {uploaded_file.name}")
            
            if not markdown_contents:
                st.error("❌ No valid markdown content found")
                return
            
            # Convert to zip file with individual documents
            result = convert_multiple_markdown_to_newspaper_zip(markdown_contents)
            
            if result and result.get('zip_data'):
                st.success(f"✅ Successfully converted {result['document_count']} files to newspaper format!")
                
                # Generate zip filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_filename = f"newspaper_articles_{timestamp}.zip"
                
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
                        st.write(f"  {i+1}. **{doc_info['filename']}** - {doc_info['title'][:50]}{'...' if len(doc_info['title']) > 50 else ''} ({doc_info['size']:,} bytes)")
                    
                    if result.get('image_count', 0) > 0:
                        st.write(f"  📁 **clippings/** directory with {result['image_count']} scraped images")
                    
                    st.write("**Features:**")
                    st.write("• Individual Word documents for each article")
                    st.write("• Filenames based on article titles with hyphens")
                    st.write("• Dynamic column layouts based on content length")
                    st.write("• Images downloaded and inserted automatically")
                    st.write("• Professional newspaper styling")
                    st.write("• Scraped images saved in clippings/ directory")
            else:
                st.error("❌ Failed to create newspaper zip file")
                
        except Exception as e:
            logger.error(f"Markdown conversion error: {str(e)}")
            st.error(f"Conversion error: {str(e)}")

def convert_processed_articles(selected_indices, results):
    """Convert processed articles to individual newspaper documents in a zip file"""
    with st.spinner("Converting processed articles to individual newspaper documents..."):
        try:
            # Create individual markdown content for each selected article
            markdown_contents = []
            
            for idx in selected_indices:
                article = results[idx]
                headline = article.get('headline', 'Untitled Article')
                source = article.get('source', 'Unknown Source')
                date = article.get('date', 'Unknown Date')
                content = article.get('full_content') or article.get('content', 'No content available')
                
                # Create individual markdown content
                article_markdown = f"# {headline}\n\n"
                article_markdown += f"*By {source} - {date}*\n\n"
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
            result = convert_multiple_markdown_to_newspaper_zip(markdown_contents, processed_articles=selected_articles_data)
            
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
                st.error("❌ Failed to create newspaper zip file")
                
        except Exception as e:
            logger.error(f"Article conversion error: {str(e)}")
            st.error(f"Conversion error: {str(e)}")

if __name__ == "__main__":
    try:
        logger.info("Enhanced application starting...")
        main()
    except Exception as e:
        logger.critical(f"Critical enhanced application error: {str(e)}", exc_info=True)
        st.error(f"A critical error occurred: {str(e)}")