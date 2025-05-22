# Main application
import streamlit as st
import pandas as pd
import logging
from datetime import datetime
import uuid
import time

# Import modules
from extractors.url_extractor import extract_from_url
from utils.logger import setup_logging
from utils.processor import process_article

# Setup logging
logger = setup_logging(__name__, log_level=logging.INFO)

def main():
    """Main application entry point"""
    logger.info("Starting application")
    
    # Configure page
    st.set_page_config(
        page_title="Best of AI Agent", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    logger.info("Page config set")
    
    # Initialize session state variables
    if 'extracted_articles' not in st.session_state:
        st.session_state.extracted_articles = []
        logger.info("Initialized extracted_articles session state")
        
    if 'current_extraction' not in st.session_state:
        st.session_state.current_extraction = None
        logger.info("Initialized current_extraction session state")
    
    # Application title
    st.title("Best of AI Agent")
    st.subheader("Demonstration of automated article extraction")
    logger.info("Rendered application header")
    
    # Get extraction method and delay from sidebar
    extraction_method, delay = sidebar_config()
    
    # Display workflow visualization
    display_workflow()
    
    # Main content area based on selected method
    handle_extraction_input(extraction_method, delay)
    
    # Display current extraction if available
    if st.session_state.current_extraction:
        display_current_extraction()
    
    # Display saved articles
    if st.session_state.extracted_articles:
        display_saved_articles()
    
    # Footer
    display_footer()
    logger.info("Application fully rendered")

def sidebar_config():
    """Configure the sidebar controls"""
    logger.info("Setting up sidebar")
    st.sidebar.header("Extraction Options")
    
    extraction_method = st.sidebar.radio(
        "Select extraction method",
        ["URL Input", "Sample ESPN Article"],
        key="extraction_method_radio"
    )
    logger.info(f"Extraction method selected: {extraction_method}")
    
    # Add debug controls in sidebar
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
    
    # Add artificial delay slider for testing responsiveness
    delay = st.sidebar.slider("Simulate Processing Delay (sec)", 0, 5, 0)
    if delay > 0:
        logger.debug(f"Using artificial delay of {delay} seconds")
    
    return extraction_method, delay

def display_workflow():
    """Display the workflow visualization"""
    logger.info("Rendering workflow visualization")
    st.write("## Workflow")
    cols = st.columns(4)
    with cols[0]:
        st.info("1. Source Selection")
    with cols[1]:
        st.info("2. Content Extraction")
    with cols[2]:
        st.info("3. Metadata Processing")
    with cols[3]:
        st.info("4. Export & Storage")
    logger.debug("Workflow visualization complete")

def handle_extraction_input(extraction_method, delay):
    """Handle user input for extraction"""
    logger.info("Setting up extraction input area")
    
    if extraction_method == "URL Input":
        url = st.text_input(
            "Enter ESPN article URL:", 
            value="https://www.espn.com/nfl/story/_/id/38786845/nfl-week-11-takeaways-2023-what-learned-big-questions-every-game-future-team-outlooks"
        )
        logger.debug(f"URL input: {url}")
        
        if st.button("Extract Article"):
            logger.info(f"Extract button clicked for URL: {url}")
            with st.spinner("Extracting article content..."):
                if delay > 0:  # Artificial delay for testing
                    logger.debug(f"Applying artificial delay of {delay} seconds")
                    time.sleep(delay)
                
                try:
                    logger.info("Starting ESPN extraction")
                    article_data = extract_from_url(url)
                    logger.debug(f"Extraction result: success={article_data['success']}")
                    
                    if article_data["success"]:
                        logger.info("Processing extracted article")
                        processed_article = process_article(article_data)
                        st.session_state.current_extraction = processed_article
                        logger.info("Article extraction successful")
                        st.success("Article extracted successfully!")
                    else:
                        error_msg = article_data.get('error', 'Unknown error')
                        logger.error(f"Extraction failed: {error_msg}")
                        st.error(f"Extraction failed: {error_msg}")
                except Exception as e:
                    logger.exception(f"Unexpected error during extraction: {str(e)}")
                    st.error(f"An unexpected error occurred: {str(e)}")
                
    else:  # Sample Article
        if st.button("Load Sample ESPN Article"):
            logger.info("Load sample article button clicked")
            with st.spinner("Loading sample ESPN article..."):
                if delay > 0:  # Artificial delay for testing
                    logger.debug(f"Applying artificial delay of {delay} seconds")
                    time.sleep(delay)
                    
                try:
                    # Extract from a known good ESPN article
                    sample_url = "https://www.espn.com/nfl/story/_/id/38786845/nfl-week-11-takeaways-2023-what-learned-big-questions-every-game-future-team-outlooks"
                    logger.info(f"Using sample URL: {sample_url}")
                    article_data = extract_from_url(sample_url)
                    logger.debug(f"Sample extraction result: success={article_data['success']}")
                    
                    if article_data["success"]:
                        logger.info("Processing sample article")
                        processed_article = process_article(article_data)
                        st.session_state.current_extraction = processed_article
                        logger.info("Sample article loaded successfully")
                        st.success("Sample article loaded!")
                    else:
                        error_msg = article_data.get('error', 'Unknown error')
                        logger.error(f"Sample extraction failed: {error_msg}")
                        st.error(f"Sample extraction failed: {error_msg}")
                except Exception as e:
                    logger.exception(f"Unexpected error during sample extraction: {str(e)}")
                    st.error(f"An unexpected error occurred: {str(e)}")

def display_current_extraction():
    """Display the currently extracted article"""
    logger.info("Displaying current extraction")
    article = st.session_state.current_extraction
    
    st.write("## Extracted Article Preview")
    
    # Display the newspaper clipping at the top if available
    if article.get("clipping_image"):
        st.write("### Newspaper Clipping")
        st.image(article["clipping_image"], use_column_width=True)
        logger.debug("Newspaper clipping displayed")
        st.write("---")  # Add a separator after the clipping
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.write("### Metadata")
        try:
            metadata_df = pd.DataFrame({
                "Field": ["Filename", "Source", "Date", "Author", "URL"],
                "Value": [
                    article["filename"], 
                    article["source"], 
                    article["date"],
                    article["author"],
                    article["source_url"]
                ]
            })
            st.table(metadata_df)
            logger.debug("Metadata table displayed")
        except Exception as e:
            logger.error(f"Error displaying metadata: {str(e)}")
            st.error(f"Error displaying metadata: {str(e)}")
        
        if article.get("image_url"):
            st.write("### Featured Image")
            try:
                st.image(article["image_url"], use_column_width=True)
                logger.debug("Featured image displayed")
            except Exception as e:
                logger.error(f"Error displaying image: {str(e)}")
                st.error("Could not load image")
        
        if st.button("Save Article"):
            logger.info("Save article button clicked")
            st.session_state.extracted_articles.append(article)
            logger.info(f"Article saved. Total articles: {len(st.session_state.extracted_articles)}")
            st.success(f"Article saved! Total articles: {len(st.session_state.extracted_articles)}")
    
    with col2:
        st.write("### Content")
        st.subheader(article["headline"])
        st.write(f"*{article['source']} - {article['date']} - By {article['author']}*")
        
        # Show original HTML vs cleaned content
        tabs = st.tabs(["Cleaned Content", "Raw HTML"])
        with tabs[0]:
            st.write(article["content"])
            logger.debug("Content tab rendered")
        with tabs[1]:
            st.code(f"Original HTML source would be displayed here (truncated for demo)")
            logger.debug("Raw HTML tab rendered")

def display_saved_articles():
    """Display the saved articles table"""
    logger.info("Displaying saved articles")
    st.write("## Saved Articles")
    
    try:
        # Create dataframe of saved articles
        articles_df = pd.DataFrame([
            {
                "Headline": a["headline"],
                "Date": a["date"],
                "Source": a["source"],
                "ID": a["id"]
            } for a in st.session_state.extracted_articles
        ])
        
        st.dataframe(articles_df)
        logger.debug("Saved articles dataframe displayed")
        
        # Export options
        st.write("### Export Options")
        export_format = st.selectbox("Select export format", ["CSV", "JSON", "Folder Structure"])
        logger.debug(f"Export format selected: {export_format}")
        
        if st.button("Export Data"):
            logger.info(f"Export data requested in {export_format} format")
            st.success(f"Articles would be exported as {export_format} (not implemented in demo)")
    except Exception as e:
        logger.error(f"Error displaying saved articles: {str(e)}")
        st.error(f"Error displaying saved articles: {str(e)}")

def display_footer():
    """Display the footer with next steps"""
    logger.info("Rendering footer")
    st.write("---")
    st.write("### Next Steps")
    st.info("""
    #### Immediate Developments:
    - Add support for Newspapers.com (requiring pre-authentication)
    - Implement batch processing for multiple articles
    - Create export to folder structure matching client requirements

    #### Future Phases:
    - Integrate OCR for scanned newspaper content
    - Develop automated layout templates
    - Build PDF generation capability
    """)
    logger.debug("Footer rendered")

if __name__ == "__main__":
    try:
        logger.info("Application starting...")
        main()
    except Exception as e:
        logger.critical(f"Critical application error: {str(e)}", exc_info=True)
        st.error(f"A critical error occurred: {str(e)}")