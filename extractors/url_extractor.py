# Enhanced Dynamic Newspaper Article Generator
import requests
from bs4 import BeautifulSoup
import re
import logging
from utils.logger import setup_logging
import time
from urllib.parse import urlparse
from PIL import Image, ImageDraw, ImageFont
import io
import textwrap
import os
from datetime import datetime
import math
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional

# Setup logging
logger = setup_logging(__name__)

class LayoutType(Enum):
    SINGLE_COLUMN = 1
    TWO_COLUMN = 2
    THREE_COLUMN = 3

@dataclass
class LayoutConfig:
    columns: int
    width: int
    height: int
    margin: int
    column_gap: int
    header_height: int

class NewspaperLayoutEngine:
    """Advanced newspaper layout engine with dynamic column support"""
    
    def __init__(self):
        self.layouts = {
            LayoutType.SINGLE_COLUMN: LayoutConfig(
                columns=1, width=800, height=1200, margin=60, 
                column_gap=0, header_height=200
            ),
            LayoutType.TWO_COLUMN: LayoutConfig(
                columns=2, width=1000, height=1400, margin=60, 
                column_gap=40, header_height=220
            ),
            LayoutType.THREE_COLUMN: LayoutConfig(
                columns=3, width=1200, height=1600, margin=60, 
                column_gap=30, header_height=240
            )
        }
        
        # Font configurations for different elements
        self.font_configs = {
            'headline': {'size_range': (32, 48), 'weight': 'Bold', 'family': 'Georgia'},
            'subhead': {'size_range': (20, 28), 'weight': 'Regular', 'family': 'Georgia'},
            'byline': {'size_range': (16, 20), 'weight': 'Italic', 'family': 'Georgia'},
            'date': {'size_range': (14, 18), 'weight': 'Regular', 'family': 'Arial'},
            'body': {'size_range': (12, 16), 'weight': 'Regular', 'family': 'Georgia'},
            'caption': {'size_range': (10, 12), 'weight': 'Italic', 'family': 'Arial'}
        }

    def determine_layout(self, article_data: dict) -> LayoutType:
        """Intelligently determine the best layout based on article characteristics"""
        content_length = len(article_data.get('text', ''))
        headline_length = len(article_data.get('headline', ''))
        has_image = bool(article_data.get('image_url'))
        
        # Decision logic for layout selection
        if content_length < 500:
            return LayoutType.SINGLE_COLUMN
        elif content_length < 1200:
            return LayoutType.TWO_COLUMN
        else:
            return LayoutType.THREE_COLUMN
    
    def load_fonts(self, layout_type: LayoutType):
        """Load appropriate fonts based on layout size"""
        config = self.layouts[layout_type]
        fonts = {}
        
        # Scale fonts based on layout size
        scale_factor = min(config.width / 1000, config.height / 1400)
        
        for element, font_config in self.font_configs.items():
            base_size = int(font_config['size_range'][1] * scale_factor)
            
            try:
                # Try to load system fonts
                font_name = f"{font_config['family']} {font_config['weight']}"
                fonts[element] = ImageFont.truetype(font_name, base_size)
            except:
                try:
                    # Fallback to basic font files
                    if font_config['weight'] == 'Bold':
                        fonts[element] = ImageFont.truetype("arial-bold.ttf", base_size)
                    elif font_config['weight'] == 'Italic':
                        fonts[element] = ImageFont.truetype("arial-italic.ttf", base_size)
                    else:
                        fonts[element] = ImageFont.truetype("arial.ttf", base_size)
                except:
                    # Final fallback to default font
                    fonts[element] = ImageFont.load_default()
        
        return fonts

    def wrap_text_to_width(self, text: str, font: ImageFont, max_width: int, draw: ImageDraw) -> List[str]:
        """Advanced text wrapping with proper word breaking"""
        if not text.strip():
            return []
            
        lines = []
        paragraphs = text.split('\n')
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                lines.append('')
                continue
                
            words = paragraph.split()
            current_line = ''
            
            for word in words:
                test_line = f"{current_line} {word}".strip()
                bbox = draw.textbbox((0, 0), test_line, font=font)
                line_width = bbox[2] - bbox[0]
                
                if line_width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                        current_line = word
                    else:
                        # Handle very long words
                        lines.append(word)
                        current_line = ''
            
            if current_line:
                lines.append(current_line)
                
        return lines

    def distribute_text_across_columns(self, lines: List[str], column_count: int, 
                                     column_height: int, font: ImageFont, 
                                     draw: ImageDraw) -> List[List[str]]:
        """Distribute text lines across multiple columns evenly"""
        if column_count == 1:
            return [lines]
        
        # Calculate how many lines fit in each column
        line_height = draw.textbbox((0, 0), "Ag", font=font)[3] + 4
        lines_per_column = column_height // line_height
        
        columns = [[] for _ in range(column_count)]
        total_lines = len(lines)
        
        # Distribute lines as evenly as possible
        lines_per_col = total_lines // column_count
        extra_lines = total_lines % column_count
        
        start_idx = 0
        for col_idx in range(column_count):
            col_lines = lines_per_col + (1 if col_idx < extra_lines else 0)
            end_idx = start_idx + col_lines
            columns[col_idx] = lines[start_idx:end_idx]
            start_idx = end_idx
            
        return columns

    def draw_newspaper_header(self, draw: ImageDraw, fonts: dict, config: LayoutConfig, 
                            article_data: dict) -> int:
        """Draw the newspaper header with classic styling"""
        y_pos = config.margin
        
        # Draw top rule
        draw.rectangle([
            (config.margin, y_pos), 
            (config.width - config.margin, y_pos + 2)
        ], fill='black')
        y_pos += 15
        
        # Draw headline with proper newspaper styling
        headline = article_data.get('headline', 'Unknown Headline')
        max_width = config.width - (2 * config.margin)
        
        # Make headline bold and large
        headline_lines = self.wrap_text_to_width(headline, fonts['headline'], max_width, draw)
        
        for line in headline_lines:
            bbox = draw.textbbox((0, 0), line, font=fonts['headline'])
            line_width = bbox[2] - bbox[0]
            x_center = (config.width - line_width) // 2
            
            draw.text((x_center, y_pos), line, fill='black', font=fonts['headline'])
            y_pos += bbox[3] + 8
        
        y_pos += 10
        
        # Draw subtitle rule
        rule_width = min(max_width // 2, 300)
        rule_x = (config.width - rule_width) // 2
        draw.rectangle([
            (rule_x, y_pos), 
            (rule_x + rule_width, y_pos + 1)
        ], fill='black')
        y_pos += 20
        
        # Draw byline and date
        author = article_data.get('author', 'Staff Reporter')
        date = article_data.get('date', 'Unknown Date')
        source = article_data.get('source', 'News Source')
        
        byline_text = f"By {author}"
        date_text = f"{date} | {source}"
        
        # Center the byline
        bbox = draw.textbbox((0, 0), byline_text, font=fonts['byline'])
        line_width = bbox[2] - bbox[0]
        x_center = (config.width - line_width) // 2
        draw.text((x_center, y_pos), byline_text, fill='#333333', font=fonts['byline'])
        y_pos += bbox[3] + 8
        
        # Center the date
        bbox = draw.textbbox((0, 0), date_text, font=fonts['date'])
        line_width = bbox[2] - bbox[0]
        x_center = (config.width - line_width) // 2
        draw.text((x_center, y_pos), date_text, fill='#666666', font=fonts['date'])
        y_pos += bbox[3] + 20
        
        # Draw bottom rule under header
        draw.rectangle([
            (config.margin, y_pos), 
            (config.width - config.margin, y_pos + 2)
        ], fill='black')
        
        return y_pos + 25

    def draw_columns(self, draw: ImageDraw, fonts: dict, config: LayoutConfig, 
                    article_data: dict, start_y: int) -> None:
        """Draw article content in columns with proper newspaper formatting"""
        content = article_data.get('text', '')
        if not content:
            return
        
        # Calculate column dimensions
        total_width = config.width - (2 * config.margin)
        column_width = (total_width - (config.column_gap * (config.columns - 1))) // config.columns
        column_height = config.height - start_y - config.margin
        
        # Wrap text to column width
        content_lines = self.wrap_text_to_width(content, fonts['body'], column_width, draw)
        
        # Distribute across columns
        column_data = self.distribute_text_across_columns(
            content_lines, config.columns, column_height, fonts['body'], draw
        )
        
        # Draw each column
        line_height = draw.textbbox((0, 0), "Ag", font=fonts['body'])[3] + 4
        
        for col_idx, column_lines in enumerate(column_data):
            x_pos = config.margin + col_idx * (column_width + config.column_gap)
            y_pos = start_y
            
            # Draw column separator (except for first column)
            if col_idx > 0:
                separator_x = x_pos - config.column_gap // 2
                draw.line([
                    (separator_x, start_y), 
                    (separator_x, config.height - config.margin)
                ], fill='#cccccc', width=1)
            
            # Draw text in column
            for line in column_lines:
                if y_pos + line_height > config.height - config.margin:
                    break  # Don't overflow the page
                    
                draw.text((x_pos, y_pos), line, fill='black', font=fonts['body'])
                y_pos += line_height

    def create_newspaper_clipping(self, article_data: dict) -> Optional[bytes]:
        """Create a dynamic newspaper clipping with appropriate layout"""
        logger.info("Creating enhanced newspaper clipping")
        
        try:
            # Determine the best layout for this article
            layout_type = self.determine_layout(article_data)
            config = self.layouts[layout_type]
            
            logger.info(f"Using {layout_type.name} layout ({config.columns} columns)")
            
            # Create image with calculated dimensions
            image = Image.new('RGB', (config.width, config.height), '#fafafa')
            draw = ImageDraw.Draw(image)
            
            # Load appropriate fonts
            fonts = self.load_fonts(layout_type)
            
            # Add newspaper aging effect
            self._add_aging_effect(draw, config)
            
            # Draw the header section
            content_start_y = self.draw_newspaper_header(draw, fonts, config, article_data)
            
            # Draw the main content in columns
            self.draw_columns(draw, fonts, config, article_data, content_start_y)
            
            # Add final touches
            self._add_final_touches(draw, config)
            
            # Convert to bytes
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG', quality=95, optimize=True)
            
            logger.info(f"Successfully created {layout_type.name} newspaper clipping")
            return img_byte_arr.getvalue()
            
        except Exception as e:
            logger.error(f"Error creating enhanced newspaper clipping: {str(e)}")
            return None

    def _add_aging_effect(self, draw: ImageDraw, config: LayoutConfig):
        """Add subtle aging effects to make it look like a real newspaper clipping"""
        # Add slight shadow/border effect
        shadow_offset = 5
        draw.rectangle([
            (shadow_offset, shadow_offset), 
            (config.width, config.height)
        ], fill='#e0e0e0')
        
        # Main newspaper background
        draw.rectangle([
            (0, 0), 
            (config.width - shadow_offset, config.height - shadow_offset)
        ], fill='#fefefe', outline='#d0d0d0', width=1)

    def _add_final_touches(self, draw: ImageDraw, config: LayoutConfig):
        """Add final decorative touches"""
        # Add corner decorations
        corner_size = 20
        
        # Top corners
        draw.line([
            (config.margin, config.margin), 
            (config.margin + corner_size, config.margin)
        ], fill='black', width=2)
        draw.line([
            (config.margin, config.margin), 
            (config.margin, config.margin + corner_size)
        ], fill='black', width=2)
        
        draw.line([
            (config.width - config.margin - corner_size, config.margin), 
            (config.width - config.margin, config.margin)
        ], fill='black', width=2)
        draw.line([
            (config.width - config.margin, config.margin), 
            (config.width - config.margin, config.margin + corner_size)
        ], fill='black', width=2)

# Create global instance
layout_engine = NewspaperLayoutEngine()

def create_newspaper_clipping(article_data):
    """
    Enhanced newspaper clipping creation with dynamic layouts
    
    Args:
        article_data (dict): The extracted article data
        
    Returns:
        bytes: The image data in bytes format, or None if creation failed
    """
    return layout_engine.create_newspaper_clipping(article_data)

def wrap_text(text, font, max_width, draw):
    """Legacy function maintained for backward compatibility"""
    return layout_engine.wrap_text_to_width(text, font, max_width, draw)

# Rest of the extraction code remains the same...
def extract_from_url(url):
    """
    Extract article content from a given URL
    
    Args:
        url (str): The URL of the article to extract
        
    Returns:
        dict: A dictionary containing the extracted article data or error information
    """
    logger.info(f"Starting extraction from URL: {url}")
    
    try:
        # Configure request headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        logger.debug(f"Sending HTTP request to: {url}")
        start_time = time.time()
        response = requests.get(url, headers=headers, timeout=10)
        request_time = time.time() - start_time
        logger.debug(f"Request completed in {request_time:.2f} seconds")
        
        # Check for HTTP errors
        response.raise_for_status()
        logger.info(f"Request successful: HTTP {response.status_code}")
        
        # Parse the HTML content
        logger.debug("Parsing HTML content with BeautifulSoup")
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract headline - try multiple selectors
        logger.debug("Extracting headline")
        headline = None
        headline_selectors = [
            'h1', 
            'article h1',
            '.article-header h1', 
            '.article-headline',
            '.headline',
            '.story-headline',
            'header h1'
        ]
        
        for selector in headline_selectors:
            headline_elem = soup.select_one(selector)
            if headline_elem:
                headline = headline_elem.text.strip()
                logger.debug(f"Found headline using selector '{selector}': {headline}")
                break
                
        if not headline:
            logger.warning("Could not find headline with standard selectors")
            # Fallback: Try to find any large text that might be a headline
            h_tags = soup.find_all(['h1', 'h2'])
            for h in h_tags:
                if len(h.text.strip()) > 10:  # Likely a headline, not a section title
                    headline = h.text.strip()
                    logger.debug(f"Using fallback headline: {headline}")
                    break
                    
        headline_text = headline if headline else "Unknown Headline"
        logger.info(f"Extracted headline: {headline_text}")
        
        # Extract date - Multiple formats possible
        logger.debug("Extracting date")
        date_text = "Unknown Date"
        date_selectors = [
            'span.timestamp', 
            '.article-meta', 
            '.pub-date',
            '.article-date',
            'time',
            '.date',
            '.published-date',
            'meta[property="article:published_time"]'
        ]
        
        for selector in date_selectors:
            date_element = soup.select_one(selector)
            if date_element:
                # Handle both content and meta tags
                if date_element.name == 'meta':
                    date_text = date_element.get('content', '').strip()
                else:
                    date_text = date_element.text.strip()
                
                logger.debug(f"Found date using selector '{selector}': {date_text}")
                
                # Try to extract just the date part with regex
                date_match = re.search(r'\w+\s+\d+,\s+\d{4}', date_text)
                if date_match:
                    date_text = date_match.group(0)
                    logger.debug(f"Extracted date format: {date_text}")
                break
                
        logger.info(f"Extracted date: {date_text}")
        
        # Extract author
        logger.debug("Extracting author")
        author = "Unknown Author"
        author_selectors = [
            '.author', 
            '.byline',
            '.author-name',
            '.article-meta .name',
            '.writer',
            'meta[name="author"]',
            '.contributor'
        ]
        
        for selector in author_selectors:
            author_element = soup.select_one(selector)
            if author_element:
                # Handle both content and meta tags
                if author_element.name == 'meta':
                    author = author_element.get('content', '').strip()
                else:
                    author = author_element.text.strip()
                
                # Clean up common prefixes
                author = re.sub(r'^By\s+', '', author, flags=re.IGNORECASE)
                logger.debug(f"Found author using selector '{selector}': {author}")
                break
                
        logger.info(f"Extracted author: {author}")
        
        # Extract article content
        logger.debug("Extracting article content")
        content = ""
        
        # Try multiple selectors for article body
        content_selectors = [
            '.article-body',
            '#story-body',
            '.story-content',
            '[data-article-id]',
            '.article__content',
            'article',
            '.post-content',
            '.entry-content',
            '.content'
        ]
        
        article_body = None
        for selector in content_selectors:
            article_body = soup.select_one(selector)
            if article_body:
                logger.debug(f"Found article body using selector '{selector}'")
                break
        
        if article_body:
            # Extract all paragraphs
            paragraphs = article_body.find_all('p')
            logger.debug(f"Found {len(paragraphs)} paragraphs in article body")
            
            # Join paragraphs, removing any that seem like non-content
            filtered_paragraphs = []
            for p in paragraphs:
                text = p.text.strip()
                # Skip very short paragraphs or known ad/promo text
                if len(text) > 20 and not any(skip in text.lower() for skip in ['advertisement', 'subscribe', 'privacy policy', 'cookie policy', 'terms of use']):
                    filtered_paragraphs.append(text)
            
            content = "\n\n".join(filtered_paragraphs)
            logger.debug(f"Extracted content length: {len(content)} characters")
        else:
            # Last resort - try to get any paragraphs that seem to be content
            logger.warning("No article body container found, trying fallback extraction")
            all_paragraphs = soup.find_all('p')
            
            # Filter out very short paragraphs that are likely not main content
            content_paragraphs = [p.text.strip() for p in all_paragraphs if len(p.text.strip()) > 40]
            content = "\n\n".join(content_paragraphs)
            logger.debug(f"Fallback extraction found {len(content_paragraphs)} paragraphs")
        
        # Verify we have meaningful content
        if len(content) < 100:
            logger.warning(f"Extracted content is suspiciously short: {len(content)} chars")
        else:
            logger.info(f"Successfully extracted {len(content)} chars of content")
        
        # Extract main image if available
        logger.debug("Extracting featured image")
        image_url = None
        image_selectors = [
            'picture img',
            '.article-featured-image img',
            '.main-image img',
            'article img',
            '.article img',
            '.featured-image img',
            'meta[property="og:image"]',
            'meta[name="twitter:image"]'
        ]
        
        for selector in image_selectors:
            image_tags = soup.select(selector)
            for img in image_tags:
                # Handle both img tags and meta tags
                if img.name == 'meta':
                    image_url = img.get('content')
                else:
                    image_url = img.get('src')
                
                if image_url and not any(skip in image_url.lower() for skip in ['spacer', 'pixel', 'advertisement']):
                    # Filter out small icons or tracking pixels
                    if img.get('width') and img.get('height'):
                        try:
                            width = int(img['width'])
                            height = int(img['height'])
                            if width < 100 or height < 100:
                                continue  # Skip small images
                        except (ValueError, TypeError):
                            pass  # Can't determine size, continue

                    # Fix relative URLs
                    if image_url.startswith('/'):
                        parsed_url = urlparse(url)
                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        image_url = base_url + image_url
                    logger.debug(f"Found image URL: {image_url}")
                    break
            
            if image_url:
                break
                
        if image_url:
            logger.info(f"Extracted image URL: {image_url}")
        else:
            logger.info("No suitable image found")
        
        # Get the source domain
        parsed_url = urlparse(url)
        source = parsed_url.netloc.replace('www.', '')
        
        logger.info("Article extraction completed successfully")
        
        # After successful extraction, create the newspaper clipping
        article_data = {
            "success": True,
            "headline": headline_text,
            "date": date_text,
            "author": author,
            "text": content,
            "source": source,
            "url": url,
            "image_url": image_url,
        }
        
        # Generate the enhanced newspaper clipping
        clipping_image = create_newspaper_clipping(article_data)
        if clipping_image:
            article_data["clipping_image"] = clipping_image
            
        return article_data
        
    except requests.RequestException as e:
        # Handle network-related errors
        logger.error(f"Network error during extraction: {str(e)}")
        return {"success": False, "error": f"Network error: {str(e)}"}
        
    except Exception as e:
        # Handle all other errors
        logger.exception(f"Unexpected error during extraction: {str(e)}")
        return {"success": False, "error": f"Extraction error: {str(e)}"}