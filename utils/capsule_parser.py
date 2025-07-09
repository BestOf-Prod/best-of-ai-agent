"""
Capsule Parser Module

This module parses document capsules that contain typography specifications
for different newspaper elements based on word count ranges.
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from docx import Document
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class TypographySpec:
    """Typography specification for a newspaper element"""
    element_type: str
    font_family: str
    font_weight: str
    font_size: int
    leading: int
    tracking: int
    indent: float = 0.0
    skew: float = 0.0

@dataclass
class DocumentCapsule:
    """Document capsule containing all typography specifications for a word count range"""
    capsule_id: int
    word_count_range: Tuple[int, int]
    category: str  # 'newspaper' or 'web'
    typography_specs: Dict[str, TypographySpec]

class CapsuleParser:
    """Parser for document capsules containing typography specifications"""
    
    def __init__(self, capsule_file_path: str):
        """
        Initialize the capsule parser
        
        Args:
            capsule_file_path: Path to the document capsules file
        """
        self.capsule_file_path = Path(capsule_file_path)
        self.capsules: List[DocumentCapsule] = []
        self._load_capsules()
    
    def _load_capsules(self):
        """Load and parse capsules from the document file"""
        try:
            doc = Document(self.capsule_file_path)
            logger.info(f"Loading capsules from {self.capsule_file_path}")
            
            current_capsule = None
            current_category = "newspaper"  # Default category
            
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if not text:
                    continue
                
                # Check for category headers
                if text.upper() == "WEB TEMPLATES":
                    current_category = "web"
                    continue
                
                # Check for capsule headers
                capsule_match = re.match(r'CAPSULE (\d+)\s*\((\d+)-(\d+)\)', text)
                if capsule_match:
                    # Save previous capsule if exists
                    if current_capsule:
                        self.capsules.append(current_capsule)
                    
                    # Create new capsule
                    capsule_id = int(capsule_match.group(1))
                    min_words = int(capsule_match.group(2))
                    max_words = int(capsule_match.group(3))
                    
                    current_capsule = DocumentCapsule(
                        capsule_id=capsule_id,
                        word_count_range=(min_words, max_words),
                        category=current_category,
                        typography_specs={}
                    )
                    logger.debug(f"Found capsule {capsule_id} for {min_words}-{max_words} words ({current_category})")
                    continue
                
                # Parse typography specifications
                if current_capsule and ':' in text:
                    spec = self._parse_typography_spec(text)
                    if spec:
                        current_capsule.typography_specs[spec.element_type.lower()] = spec
            
            # Add the last capsule
            if current_capsule:
                self.capsules.append(current_capsule)
            
            logger.info(f"Successfully loaded {len(self.capsules)} capsules")
            
        except Exception as e:
            logger.error(f"Error loading capsules: {str(e)}")
            raise
    
    def _parse_typography_spec(self, text: str) -> Optional[TypographySpec]:
        """
        Parse a typography specification line
        
        Args:
            text: Line of text containing typography specification
            
        Returns:
            TypographySpec object or None if parsing fails
        """
        try:
            # Split by colon to get element type and specs
            if ':' not in text:
                return None
            
            element_type, specs = text.split(':', 1)
            element_type = element_type.strip()
            specs = specs.strip()
            
            # Parse font family and weight
            font_match = re.match(r'([^-]+?)\s+(BOLD|Bold|Regular|Italic|regular)\s*-', specs)
            if not font_match:
                logger.warning(f"Could not parse font from: {specs}")
                return None
            
            font_family = font_match.group(1).strip()
            font_weight = font_match.group(2).strip()
            
            # Parse font size
            size_match = re.search(r'(\d+)\s*pt', specs)
            font_size = int(size_match.group(1)) if size_match else 12
            
            # Parse leading
            leading_match = re.search(r'leading\s+(\d+(?:\.\d+)?)\s*pt', specs)
            leading = float(leading_match.group(1)) if leading_match else font_size
            
            # Parse tracking
            tracking_match = re.search(r'tracking\s+(-?\d+)', specs)
            tracking = int(tracking_match.group(1)) if tracking_match else 0
            
            # Parse indent
            indent_match = re.search(r'indent\s+(\d+(?:\.\d+)?)\s*in', specs)
            indent = float(indent_match.group(1)) if indent_match else 0.0
            
            # Parse skew
            skew_match = re.search(r'skew\s+(\d+(?:\.\d+)?)º', specs)
            skew = float(skew_match.group(1)) if skew_match else 0.0
            
            return TypographySpec(
                element_type=element_type,
                font_family=font_family,
                font_weight=font_weight,
                font_size=font_size,
                leading=int(leading),
                tracking=tracking,
                indent=indent,
                skew=skew
            )
            
        except Exception as e:
            logger.warning(f"Error parsing typography spec '{text}': {str(e)}")
            return None
    
    def get_capsule_for_word_count(self, word_count: int, prefer_web: bool = False) -> Optional[DocumentCapsule]:
        """
        Get the appropriate capsule for a given word count
        
        Args:
            word_count: Number of words in the article
            prefer_web: Whether to prefer web templates over newspaper templates
            
        Returns:
            DocumentCapsule object or None if no suitable capsule found
        """
        # First, find all capsules that match the word count
        matching_capsules = []
        
        for capsule in self.capsules:
            min_words, max_words = capsule.word_count_range
            if min_words <= word_count <= max_words:
                matching_capsules.append(capsule)
        
        if not matching_capsules:
            logger.warning(f"No capsule found for word count {word_count}")
            return None
        
        # If we have multiple matches, prefer based on category
        if len(matching_capsules) > 1:
            if prefer_web:
                web_capsules = [c for c in matching_capsules if c.category == "web"]
                if web_capsules:
                    return web_capsules[0]
            else:
                newspaper_capsules = [c for c in matching_capsules if c.category == "newspaper"]
                if newspaper_capsules:
                    return newspaper_capsules[0]
        
        # Return the first matching capsule
        return matching_capsules[0]
    
    def get_available_capsules(self) -> List[DocumentCapsule]:
        """Get all available capsules"""
        return self.capsules.copy()
    
    def get_capsules_by_category(self, category: str) -> List[DocumentCapsule]:
        """Get capsules by category (newspaper or web)"""
        return [c for c in self.capsules if c.category == category]
    
    def get_word_count_ranges(self) -> List[Tuple[int, int]]:
        """Get all word count ranges covered by capsules"""
        return [c.word_count_range for c in self.capsules]
    
    def get_typography_spec(self, word_count: int, element_type: str, prefer_web: bool = False) -> Optional[TypographySpec]:
        """
        Get typography specification for a specific element and word count
        
        Args:
            word_count: Number of words in the article
            element_type: Type of element (headline, body, etc.)
            prefer_web: Whether to prefer web templates
            
        Returns:
            TypographySpec object or None if not found
        """
        capsule = self.get_capsule_for_word_count(word_count, prefer_web)
        if not capsule:
            return None
        
        return capsule.typography_specs.get(element_type.lower())

# Global instance for easy access
_capsule_parser = None

def get_capsule_parser() -> CapsuleParser:
    """Get the global capsule parser instance"""
    global _capsule_parser
    if _capsule_parser is None:
        # Default path to capsules file
        capsule_file = Path(__file__).parent.parent / "document_capsules" / "NEWSPAPER ELEMENTS.docx"
        _capsule_parser = CapsuleParser(str(capsule_file))
    return _capsule_parser

def get_typography_for_article(word_count: int, source_url: str = "") -> Optional[DocumentCapsule]:
    """
    Get typography specifications for an article based on word count and source
    
    Args:
        word_count: Number of words in the article
        source_url: Source URL to determine if it's a web or newspaper source
        
    Returns:
        DocumentCapsule object or None if not found
    """
    parser = get_capsule_parser()
    
    # Import font matrix from newspaper converter
    try:
        from utils.newspaper_converter import FONT_MATRIX
    except ImportError:
        logger.warning("Could not import FONT_MATRIX from newspaper_converter")
        # Fallback to web capsules as default
        return parser.get_capsule_for_word_count(word_count, prefer_web=True)
    
    # Determine if we should prefer web templates based on source using font matrix
    prefer_web = True  # Default to web capsules when determination isn't possible
    
    if source_url:
        from urllib.parse import urlparse
        domain = urlparse(source_url).netloc.replace('www.', '').lower()
        
        # Check if it's a newspaper site based on font matrix
        newspaper_domains = FONT_MATRIX.get('newspaper_sites', {}).get('domains', [])
        if any(news_domain in domain for news_domain in newspaper_domains):
            prefer_web = False
            logger.debug(f"Detected newspaper site from domain {domain}, using newspaper capsules")
        
        # Check if it's a web news site based on font matrix
        web_domains = FONT_MATRIX.get('web_news_sites', {}).get('domains', [])
        if any(web_domain in domain for web_domain in web_domains):
            prefer_web = True
            logger.debug(f"Detected web news site from domain {domain}, using web capsules")
        
        # If domain is not found in either category, default to web capsules
        if not any(news_domain in domain for news_domain in newspaper_domains) and \
           not any(web_domain in domain for web_domain in web_domains):
            prefer_web = True
            logger.debug(f"Domain {domain} not found in font matrix, defaulting to web capsules")
    else:
        # No URL provided, default to web capsules
        logger.debug("No source URL provided, defaulting to web capsules")
    
    return parser.get_capsule_for_word_count(word_count, prefer_web)