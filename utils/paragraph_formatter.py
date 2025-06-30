"""
Paragraph formatting utility using LLM to add proper paragraph breaks to extracted text.

This module provides functionality to analyze extracted article text that lacks proper
paragraph breaks and uses an LLM to intelligently insert paragraph breaks where appropriate.
"""

import re
import logging
from typing import Optional, Dict, Any
import requests
import json
import os
from utils.logger import setup_logging

# Setup logging
logger = setup_logging(__name__)


class ParagraphFormatter:
    """Service for adding paragraph breaks to extracted text using LLM"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
        """
        Initialize the paragraph formatter
        
        Args:
            api_key: OpenAI API key (if None, will try to get from environment)
            model: LLM model to use for paragraph formatting
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.api_url = "https://api.openai.com/v1/chat/completions"
        
        if not self.api_key:
            logger.warning("No OpenAI API key provided. LLM paragraph formatting will be disabled.")
    
    def _needs_paragraph_formatting(self, text: str) -> bool:
        """
        Determine if text needs paragraph break formatting
        
        Args:
            text: The text to analyze
            
        Returns:
            bool: True if text appears to lack proper paragraph breaks
        """
        if not text or len(text.strip()) < 100:
            return False
        
        # Count existing paragraph breaks
        paragraph_breaks = text.count('\n\n')
        sentence_count = len(re.findall(r'[.!?]+\s+[A-Z]', text))
        
        # If we have very few paragraph breaks relative to sentences, formatting is likely needed
        if sentence_count > 5 and paragraph_breaks < (sentence_count / 10):
            logger.debug(f"Text needs formatting: {sentence_count} sentences, {paragraph_breaks} paragraph breaks")
            return True
        
        # Check for long continuous blocks of text
        lines = text.split('\n')
        for line in lines:
            if len(line.strip()) > 500:  # Very long line suggests lack of paragraph breaks
                logger.debug(f"Found long line ({len(line)} chars), formatting needed")
                return True
        
        return False
    
    def _call_llm_api(self, prompt: str, text: str) -> Optional[str]:
        """
        Call the LLM API to format text with paragraph breaks
        
        Args:
            prompt: The system prompt for the LLM
            text: The text to format
            
        Returns:
            Formatted text with paragraph breaks, or None if API call fails
        """
        if not self.api_key:
            logger.warning("No API key available, skipping LLM formatting")
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.model,
                'messages': [
                    {
                        'role': 'system',
                        'content': prompt
                    },
                    {
                        'role': 'user',
                        'content': text
                    }
                ],
                'max_tokens': min(len(text) + 500, 4000),  # Allow for some expansion
                'temperature': 0.3  # Lower temperature for consistent formatting
            }
            
            logger.debug(f"Calling {self.model} API for paragraph formatting")
            response = requests.post(self.api_url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                formatted_text = result['choices'][0]['message']['content'].strip()
                logger.info(f"Successfully formatted text using {self.model}")
                return formatted_text
            else:
                logger.error("Unexpected API response format")
                return None
                
        except requests.RequestException as e:
            logger.error(f"API request failed: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error calling LLM API: {str(e)}")
            return None
    
    def format_paragraphs(self, text: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Add paragraph breaks to text that lacks proper formatting
        
        Args:
            text: The text to format (should be plain text without paragraph breaks)
            context: Optional context about the article (title, source, etc.)
            
        Returns:
            Text with properly inserted paragraph breaks
        """
        if not text or not text.strip():
            return text
        
        # Check if formatting is needed
        if not self._needs_paragraph_formatting(text):
            logger.debug("Text appears to already have adequate paragraph breaks")
            return text
        
        # Fallback formatting if no LLM is available
        if not self.api_key:
            logger.info("Using fallback paragraph formatting (no LLM available)")
            return self._fallback_paragraph_formatting(text)
        
        # Prepare context for LLM
        context_info = ""
        if context:
            if context.get('headline'):
                context_info += f"Article Title: {context['headline']}\n"
            if context.get('source'):
                context_info += f"Source: {context['source']}\n"
            if context.get('author'):
                context_info += f"Author: {context['author']}\n"
            context_info += "\n"
        
        # Create prompt for LLM
        prompt = f"""You are a text formatting assistant. Your task is to add paragraph breaks to article text that lacks proper paragraph formatting.

{context_info}Please analyze the following text and add paragraph breaks (double newlines \\n\\n) where they would naturally occur in a well-formatted article. Follow these guidelines:

1. Insert paragraph breaks at natural topic transitions
2. Keep related sentences together in the same paragraph
3. Don't break up quotes or dialogue
4. Maintain the original text content exactly - only add paragraph breaks
5. Don't add any additional text, comments, or explanations
6. Return only the formatted text

The text appears to be from a newspaper or magazine article that was extracted using OCR, so it may lack proper paragraph structure."""

        # Call LLM API
        formatted_text = self._call_llm_api(prompt, text)
        
        if formatted_text:
            # Validate that the content is preserved
            if self._validate_formatted_text(text, formatted_text):
                logger.info("Successfully formatted text with LLM")
                return formatted_text
            else:
                logger.warning("LLM formatting validation failed, using fallback")
                return self._fallback_paragraph_formatting(text)
        else:
            logger.info("LLM formatting failed, using fallback method")
            return self._fallback_paragraph_formatting(text)
    
    def _validate_formatted_text(self, original: str, formatted: str) -> bool:
        """
        Validate that formatted text preserves the original content
        
        Args:
            original: Original text
            formatted: Formatted text
            
        Returns:
            bool: True if formatted text appears to preserve original content
        """
        # Remove whitespace and newlines for comparison
        original_clean = re.sub(r'\s+', ' ', original.strip())
        formatted_clean = re.sub(r'\s+', ' ', formatted.strip())
        
        # Check if content length is roughly preserved (allow some variation)
        length_ratio = len(formatted_clean) / len(original_clean) if len(original_clean) > 0 else 0
        
        if length_ratio < 0.8 or length_ratio > 1.2:
            logger.warning(f"Text length changed significantly: {length_ratio:.2f} ratio")
            return False
        
        # Check if most words are preserved
        original_words = set(original_clean.lower().split())
        formatted_words = set(formatted_clean.lower().split())
        
        if len(original_words) > 0:
            word_preservation = len(original_words & formatted_words) / len(original_words)
            if word_preservation < 0.9:
                logger.warning(f"Word preservation too low: {word_preservation:.2f}")
                return False
        
        return True
    
    def _fallback_paragraph_formatting(self, text: str) -> str:
        """
        Fallback method to add paragraph breaks using heuristics
        
        Args:
            text: Text to format
            
        Returns:
            Text with basic paragraph formatting applied
        """
        logger.debug("Applying fallback paragraph formatting")
        
        # Start with the original text
        formatted = text.strip()
        
        # Replace single newlines with spaces (in case text has random line breaks)
        formatted = re.sub(r'(?<!\n)\n(?!\n)', ' ', formatted)
        
        # Fix multiple spaces
        formatted = re.sub(r' +', ' ', formatted)
        
        # Add paragraph breaks at common patterns
        patterns = [
            # After sentences that end with periods followed by capital letters
            (r'([.!?])\s+([A-Z][a-z])', r'\1\n\n\2'),
            
            # Before common transition words/phrases at sentence start
            (r'\s+(However|Meanwhile|Furthermore|Additionally|Moreover|Nevertheless|Therefore|Consequently|In contrast|On the other hand|For example|For instance|In conclusion|Finally),\s+', r'\n\n\1, '),
            
            # Before quoted speech
            (r'\s+(["""])', r'\n\n\1'),
            
            # After quoted speech ends
            (r'(["""][.!?])\s+([A-Z])', r'\1\n\n\2'),
            
            # Before numbers that might start new sections
            (r'\s+(\d+\.\s+[A-Z])', r'\n\n\1'),
            
            # After long sentences (over 150 chars) followed by capital letters
            (r'([.!?])\s+([A-Z][^.!?]{0,149}[.!?])\s+([A-Z])', r'\1\n\n\2\n\n\3'),
        ]
        
        for pattern, replacement in patterns:
            formatted = re.sub(pattern, replacement, formatted)
        
        # Clean up excessive paragraph breaks
        formatted = re.sub(r'\n{3,}', '\n\n', formatted)
        
        # Ensure we don't start or end with paragraph breaks
        formatted = formatted.strip()
        
        logger.debug("Applied fallback paragraph formatting")
        return formatted


# Global instance for easy access
_paragraph_formatter = ParagraphFormatter()


def format_article_paragraphs(text: str, context: Optional[Dict[str, Any]] = None) -> str:
    """
    Convenience function to format article paragraphs using the global formatter instance
    
    Args:
        text: The text to format
        context: Optional context about the article
        
    Returns:
        Formatted text with paragraph breaks
    """
    return _paragraph_formatter.format_paragraphs(text, context)


def configure_paragraph_formatter(api_key: Optional[str] = None, model: str = "gpt-3.5-turbo"):
    """
    Configure the global paragraph formatter instance
    
    Args:
        api_key: OpenAI API key
        model: LLM model to use
    """
    global _paragraph_formatter
    _paragraph_formatter = ParagraphFormatter(api_key=api_key, model=model)
    logger.info(f"Configured paragraph formatter with model: {model}")