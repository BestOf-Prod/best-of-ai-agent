import streamlit as st
import subprocess
import tempfile
import os
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime
import logging
import re
import zipfile
import requests
from urllib.parse import urljoin, urlparse
from pathlib import Path
import shutil
from utils.logger import setup_logging

# Set up logging using the existing logger
logger = setup_logging(__name__, log_level=logging.INFO)

# Static Derek Carr Final styling - embedded from Derek Carr Final-Continued.icml
DEREK_CARR_STYLING = {
    'xml_declaration': '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
    'aid_style': '<?aid style="50" type="snippet" readerVersion="6.0" featureSet="257" product="20.3(73)" ?>',
    'aid_snippet': '<?aid SnippetType="InCopyInterchange"?>',
    'document_attrs': 'DOMVersion="20.3" Self="d"',
    
    'colors': [
        '<Color Self="Color/Paper" Model="Process" Space="CMYK" ColorValue="0 0 0 0" ColorOverride="Specialpaper" ConvertToHsb="false" AlternateSpace="NoAlternateColor" AlternateColorValue="" Name="Paper" ColorEditable="true" ColorRemovable="false" Visible="true" SwatchCreatorID="7937" SwatchColorGroupReference="u12ColorGroupSwatch2" />'
    ],
    
    'inks': [
        '<Ink Self="Ink/$ID/Process Cyan" Name="$ID/Process Cyan" Angle="45" ConvertToProcess="false" Frequency="60" NeutralDensity="0.61" PrintInk="true" TrapOrder="1" InkType="Normal" />',
        '<Ink Self="Ink/$ID/Process Magenta" Name="$ID/Process Magenta" Angle="45" ConvertToProcess="false" Frequency="60" NeutralDensity="0.76" PrintInk="true" TrapOrder="2" InkType="Normal" />',
        '<Ink Self="Ink/$ID/Process Yellow" Name="$ID/Process Yellow" Angle="45" ConvertToProcess="false" Frequency="60" NeutralDensity="0.16" PrintInk="true" TrapOrder="3" InkType="Normal" />',
        '<Ink Self="Ink/$ID/Process Black" Name="$ID/Process Black" Angle="45" ConvertToProcess="false" Frequency="60" NeutralDensity="1.7" PrintInk="true" TrapOrder="4" InkType="Normal" />'
    ],
    
    'font_families': [
        # Minion Pro family (condensed for brevity - contains all variants)
        '''<FontFamily Self="di39" Name="Minion Pro">
		<Font Self="di39FontnMinion Pro Regular" FontFamily="Minion Pro" Name="Minion Pro Regular" PostScriptName="MinionPro-Regular" Status="Installed" FontStyleName="Regular" FontType="OpenTypeCFF" WritingScript="0" FullName="Minion Pro" FullNameNative="Minion Pro" FontStyleNameNative="Regular" PlatformName="$ID/" Version="Version 2.112;PS 2.000;hotconv 1.0.70;makeotf.lib2.5.5900" TypekitID="$ID/" />
		<Font Self="di39FontnMinion Pro Bold" FontFamily="Minion Pro" Name="Minion Pro Bold" PostScriptName="MinionPro-Bold" Status="Substituted" FontStyleName="Bold" FontType="OpenTypeCFF" WritingScript="0" FullName="Minion Pro Bold" FullNameNative="Minion Pro Bold" FontStyleNameNative="Bold" PlatformName="$ID/" Version="Version 2.108;PS 2.000;hotconv 1.0.67;makeotf.lib2.5.33168" TypekitID="$ID/" />
	</FontFamily>''',
        
        # Myriad Pro family
        '''<FontFamily Self="di8d" Name="Myriad Pro">
		<Font Self="di8dFontnMyriad Pro Regular" FontFamily="Myriad Pro" Name="Myriad Pro Regular" PostScriptName="MyriadPro-Regular" Status="Installed" FontStyle="Regular" FontType="OpenTypeCFF" WritingScript="0" FullName="Myriad Pro" FullNameNative="Myriad Pro" FontStyleNameNative="Regular" PlatformName="$ID/" Version="Version 2.106;PS 2.000;hotconv 1.0.70;makeotf.lib2.5.58329" TypekitID="$ID/" />
		<Font Self="di8dFontnMyriad Pro Bold" FontFamily="Myriad Pro" Name="Myriad Pro Bold" PostScriptName="MyriadPro-Bold" Status="Installed" FontStyleName="Bold" FontType="OpenTypeCFF" WritingScript="0" FullName="Myriad Pro Bold" FullNameNative="Myriad Pro Bold" FontStyleNameNative="Bold" PlatformName="$ID/" Version="Version 2.106;PS 2.000;hotconv 1.0.70;makeotf.lib2.5.58329" TypekitID="$ID/" />
	</FontFamily>''',
        
        # Century Gothic Pro family
        '''<FontFamily Self="die9" Name="Century Gothic Pro">
		<Font Self="die9FontnCentury Gothic Pro Regular" FontFamily="Century Gothic Pro" Name="Century Gothic Pro Regular" PostScriptName="CenturyGothicPro" Status="Substituted" FontStyleName="Regular" FontType="OpenTypeCFF" WritingScript="0" FullName="Century Gothic Pro" FullNameNative="Century Gothic Pro" FontStyleNameNative="Regular" PlatformName="$ID/" Version="Version 1.003;PS 001.000;Core 1.0.38;makeotf.lib1.6.5960" TypekitID="TkD-39203-da5a18a0a3e9a1a0efa53bcd47e4cee2987ee709" />
		<Font Self="die9FontnCentury Gothic Pro Bold" FontFamily="Century Gothic Pro" Name="Century Gothic Pro Bold" PostScriptName="CenturyGothicPro-Bold" Status="Substituted" FontStyleName="Bold" FontType="OpenTypeCFF" WritingScript="0" FullName="Century Gothic Pro Bold" FullNameNative="Century Gothic Pro Bold" FontStyleNameNative="Bold" PlatformName="$ID/" Version="Version 1.004;PS 001.000;Core 1.0.38;makeotf.lib1.6.5960" TypekitID="TkD-39200-f51764797754788dad1694fca46df7f9c138ccf3" />
	</FontFamily>''',
        
        # Impact family
        '''<FontFamily Self="didf" Name="Impact">
		<Font Self="didfFontnImpact Regular" FontFamily="Impact" Name="Impact Regular" PostScriptName="Impact" Status="Installed" FontStyleName="Regular" FontType="OpenTypeTT" WritingScript="0" FullName="Impact" FullNameNative="Impact" FontStyleNameNative="Regular" PlatformName="$ID/" Version="Version 5.00x" TypekitID="$ID/" />
	</FontFamily>'''
    ],
    
    'composite_fonts': [
        '''<CompositeFont Self="CompositeFont/$ID/[No composite font]" Name="$ID/[No composite font]">
		<CompositeFontEntry Self="u95" Name="$ID/Alphabetic" FontStyle="$ID/Regular" RelativeSize="100" HorizontalScale="100" VerticalScale="100" CustomCharacters=" !&quot;#$%&amp;&apos;()*+,-./:;&lt;=&gt;?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~ ¡¤¥¦©ª«­®¯²³µ·¸¹º»¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿıŒœŠšŸŽžƒˆˇ˘˙˚˛˜˝–‚„•‹›⁄€™∆∏∑≈≤≥◊ﬀﬁﬂﬃﬄﬅﬆ" Locked="true" ScaleOption="false" BaselineShift="0">
			<Properties>
				<AppliedFont type="string">Times New Roman</AppliedFont>
			</Properties>
		</CompositeFontEntry>
	</CompositeFont>'''
    ],
    
    'character_styles': [
        '''<RootCharacterStyleGroup Self="u79">
		<CharacterStyle Self="CharacterStyle/$ID/[No character style]" Imported="false" SplitDocument="false" EmitCss="true" StyleUniqueId="425362ec-6bb4-4e43-8d06-d538537e9e1b" IncludeClass="true" ExtendedKeyboardShortcut="0 0 0" Name="$ID/[No character style]" />
	</RootCharacterStyleGroup>'''
    ],
    
    'paragraph_styles': [
        '''<RootParagraphStyleGroup Self="u78">
		<ParagraphStyle Self="ParagraphStyle/1 Headline" Name="1 Headline" Imported="false" NextStyle="ParagraphStyle/1 Headline" SplitDocument="false" EmitCss="true" StyleUniqueId="599e80da-fdf1-43a8-9939-8fa1df96c99b" IncludeClass="true" ExtendedKeyboardShortcut="0 0 0" EmptyNestedStyles="true" EmptyLineStyles="true" EmptyGrepStyles="true" KeyboardShortcut="0 0" PointSize="60" HorizontalScale="80" VerticalScale="80" Hyphenation="false">
			<Properties>
				<BasedOn type="object">ParagraphStyle/$ID/NormalParagraphStyle</BasedOn>
				<PreviewColor type="enumeration">Nothing</PreviewColor>
				<Leading type="unit">45</Leading>
				<AppliedFont type="string">Impact</AppliedFont>
			</Properties>
		</ParagraphStyle>
		<ParagraphStyle Self="ParagraphStyle/Author" Name="Author" Imported="false" NextStyle="ParagraphStyle/Author" SplitDocument="false" EmitCss="true" StyleUniqueId="599e80da-fdf1-43a8-9939-8fa1df96c99c" IncludeClass="true" ExtendedKeyboardShortcut="0 0 0" EmptyNestedStyles="true" EmptyLineStyles="true" EmptyGrepStyles="true" KeyboardShortcut="0 0" PointSize="12" Hyphenation="false">
			<Properties>
				<BasedOn type="object">ParagraphStyle/$ID/NormalParagraphStyle</BasedOn>
				<PreviewColor type="enumeration">Nothing</PreviewColor>
				<Leading type="unit">14</Leading>
				<AppliedFont type="string">Myriad Pro</AppliedFont>
				<FontStyle type="string">Italic</FontStyle>
			</Properties>
		</ParagraphStyle>
		<ParagraphStyle Self="ParagraphStyle/$ID/NormalParagraphStyle" Name="$ID/NormalParagraphStyle" Imported="false" NextStyle="ParagraphStyle/$ID/NormalParagraphStyle" SplitDocument="false" EmitCss="true" StyleUniqueId="931ede32-19a9-4ed6-be7d-c71e5c60a62e" IncludeClass="true" ExtendedKeyboardShortcut="0 0 0" EmptyNestedStyles="true" EmptyLineStyles="true" EmptyGrepStyles="true" KeyboardShortcut="0 0">
			<Properties>
				<BasedOn type="string">$ID/[No paragraph style]</BasedOn>
				<PreviewColor type="enumeration">Nothing</PreviewColor>
			</Properties>
		</ParagraphStyle>
	</RootParagraphStyleGroup>'''
    ],
    
    'color_groups': [
        '''<ColorGroup Self="ColorGroup/[Root Color Group]" Name="[Root Color Group]" IsRootColorGroup="true">
		<ColorGroupSwatch Self="u12ColorGroupSwatch2" SwatchItemRef="Color/Paper" />
	</ColorGroup>'''
    ]
}

def get_derek_carr_styling():
    """Return the static Derek Carr Final styling elements."""
    return DEREK_CARR_STYLING

def parse_article_content(md_content):
    """Parse markdown content to extract title, author/date, and body separately."""
    lines = md_content.split('\n')
    
    # Initialize variables
    title = ""
    author_date = ""
    body_lines = []
    images = []
    
    # State tracking
    found_title = False
    found_author_date = False
    in_body = False
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Skip empty lines at the beginning
        if not line and not found_title:
            continue
            
        # Extract title (first H1)
        if line.startswith('# ') and not found_title:
            title = line[2:].strip()
            found_title = True
            continue
            
        # Extract author/date (next non-empty line that starts with *)
        if found_title and not found_author_date and line.startswith('*') and line.endswith('*'):
            # Check if next line is also author/date info
            author_parts = [line]
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith('*') and lines[j].strip().endswith('*'):
                author_parts.append(lines[j].strip())
                j += 1
            author_date = '\n'.join(author_parts)
            found_author_date = True
            # Skip the lines we just processed
            i = j - 1
            continue
            
        # Extract images
        if '![' in line and '](' in line:
            # Extract image URL from markdown syntax
            img_pattern = r'!\[([^\]]*)\]\(([^\)]+)\)'
            matches = re.findall(img_pattern, line)
            for alt_text, img_url in matches:
                images.append({'alt': alt_text, 'url': img_url, 'line': line})
            # Don't include image lines in body
            continue
            
        # Everything else goes to body (after we've found title and author)
        if found_title and found_author_date:
            # Skip source footer
            if line.startswith('---') and ('Source:' in line or 'Original URL:' in line):
                break
            if line.startswith('*Source:') or line.startswith('*Original URL:'):
                break
            body_lines.append(line)
    
    # Clean up body content
    body = '\n'.join(body_lines).strip()
    
    # Remove any remaining YAML frontmatter or metadata
    body = re.sub(r'^---\s*\n.*?\n---\s*\n', '', body, flags=re.DOTALL)
    
    return {
        'title': title,
        'author_date': author_date,
        'body': body,
        'images': images
    }

def create_icml_element(content, element_type, styling_elements):
    """Create an ICML file for a specific article element."""
    
    # Determine paragraph style based on element type
    if element_type == 'title':
        paragraph_style = 'ParagraphStyle/1 Headline'
    elif element_type == 'author':
        paragraph_style = 'ParagraphStyle/Author'
    else:
        paragraph_style = 'ParagraphStyle/$ID/NormalParagraphStyle'
    
    # Create story content
    story_content = []
    story_content.append('<Story Self="u1" AppliedTOCStyle="TableOfContentsStyle/$ID/[No TOC style]" TrackChanges="false" StoryTitle="$ID/" AppliedNamedGrid="n" AppliedMasterSpread="u2" UserText="false" IsEndnoteStory="false" IncludeInBookmarks="true" IncludeInTOC="true" MaintainTextEditability="false" OverrideAllTextFrameFittingOptions="false" AppliedNamedGrids="n" GridAlignment="AlignToBaseline" FrameType="TextFrameType" TextFramePreference="TextFramePreference/TextFrameGeneralPreference" NextTextFrame="n" PreviousTextFrame="n" Intent="Both">')
    story_content.append('\t<InCopyExportOption IncludeGraphicProxies="true" IncludeAllResources="false" />')
    story_content.append(f'\t<ParagraphStyleRange AppliedParagraphStyle="{paragraph_style}">')
    story_content.append('\t\t<CharacterStyleRange AppliedCharacterStyle="$ID/[No character style]">')
    
    # Add content
    if content:
        # Split content into paragraphs for body text
        if element_type == 'body':
            paragraphs = content.split('\n\n')
            for i, para in enumerate(paragraphs):
                if para.strip():
                    clean_para = para.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                    story_content.append(f'\t\t\t<Content>{clean_para}</Content>')
                    if i < len(paragraphs) - 1:
                        story_content.append('\t\t\t<Br />')
        else:
            # Single content block for title and author
            clean_content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story_content.append(f'\t\t\t<Content>{clean_content}</Content>')
    else:
        story_content.append('\t\t\t<Content></Content>')
    
    story_content.append('\t\t</CharacterStyleRange>')
    story_content.append('\t</ParagraphStyleRange>')
    story_content.append('</Story>')
    
    # Build the full ICML document
    icml_parts = []
    
    # Add XML declaration and processing instructions
    icml_parts.append(styling_elements['xml_declaration'])
    icml_parts.append(styling_elements['aid_style'])
    icml_parts.append(styling_elements['aid_snippet'])
    
    # Start document
    icml_parts.append(f'<Document {styling_elements["document_attrs"]}>')
    
    # Add styling elements
    for color in styling_elements['colors']:
        icml_parts.append('\t' + color)
    
    for ink in styling_elements['inks']:
        icml_parts.append('\t' + ink)
    
    for font_family in styling_elements['font_families']:
        indented_font_family = '\n'.join('\t' + line for line in font_family.split('\n'))
        icml_parts.append(indented_font_family)
    
    for composite_font in styling_elements['composite_fonts']:
        indented_composite_font = '\n'.join('\t' + line for line in composite_font.split('\n'))
        icml_parts.append(indented_composite_font)
    
    for char_style in styling_elements['character_styles']:
        indented_char_style = '\n'.join('\t' + line for line in char_style.split('\n'))
        icml_parts.append(indented_char_style)
    
    for para_style in styling_elements['paragraph_styles']:
        indented_para_style = '\n'.join('\t' + line for line in para_style.split('\n'))
        icml_parts.append(indented_para_style)
    
    # Add the story content
    icml_parts.append('\t' + '\n\t'.join(story_content))
    
    # Add color groups
    for color_group in styling_elements['color_groups']:
        indented_color_group = '\n'.join('\t' + line for line in color_group.split('\n'))
        icml_parts.append(indented_color_group)
    
    # Close document
    icml_parts.append('</Document>')
    
    return '\n'.join(icml_parts)

def download_image(image_url, base_path, filename):
    """Download an image from URL to local path."""
    try:
        # Handle relative URLs
        if image_url.startswith('../'):
            # This is a relative path to local files
            source_path = os.path.join(base_path, image_url)
            if os.path.exists(source_path):
                dest_path = os.path.join(base_path, 'images', filename)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                shutil.copy2(source_path, dest_path)
                return dest_path
            else:
                logger.warning(f"Local image file not found: {source_path}")
                return None
        
        # Handle HTTP/HTTPS URLs
        elif image_url.startswith(('http://', 'https://')):
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            dest_path = os.path.join(base_path, 'images', filename)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            with open(dest_path, 'wb') as f:
                f.write(response.content)
            
            return dest_path
        
        else:
            logger.warning(f"Unsupported image URL format: {image_url}")
            return None
            
    except Exception as e:
        logger.error(f"Error downloading image {image_url}: {str(e)}")
        return None

def create_modular_icml_package(md_files, debug_mode=False):
    """Create a zip package with individual ICML files for each article element."""
    
    # Create temporary directory for processing
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Get styling elements
        styling_elements = get_derek_carr_styling()
        
        # Process each markdown file
        articles_processed = 0
        
        for md_file in md_files:
            try:
                # Read markdown content
                if hasattr(md_file, 'getvalue'):  # File upload object
                    file_content = md_file.getvalue()
                    md_content = file_content.decode('utf-8')
                    filename = md_file.name
                elif isinstance(md_file, str) and os.path.exists(md_file):  # File path
                    with open(md_file, 'r', encoding='utf-8') as f:
                        md_content = f.read()
                    filename = os.path.basename(md_file)
                elif isinstance(md_file, str):  # Direct content
                    md_content = md_file
                    filename = f"article_{articles_processed + 1}.md"
                else:
                    logger.error(f"Unsupported file type: {type(md_file)}")
                    continue
                
                # Parse article content
                article_data = parse_article_content(md_content)
                
                # Create article directory
                article_name = os.path.splitext(filename)[0]
                article_dir = os.path.join(temp_dir, article_name)
                os.makedirs(article_dir, exist_ok=True)
                
                # Create ICML files for each element
                elements = [
                    ('title', article_data['title']),
                    ('author', article_data['author_date']),
                    ('body', article_data['body'])
                ]
                
                for element_type, content in elements:
                    if content:  # Only create file if content exists
                        icml_content = create_icml_element(content, element_type, styling_elements)
                        icml_filename = f"{article_name}_{element_type}.icml"
                        icml_path = os.path.join(article_dir, icml_filename)
                        
                        with open(icml_path, 'w', encoding='utf-8') as f:
                            f.write(icml_content)
                        
                        if debug_mode:
                            try:
                                st.write(f"✅ Created {icml_filename}")
                            except:
                                logger.info(f"Created {icml_filename}")
                
                # Download images
                if article_data['images']:
                    images_downloaded = 0
                    for i, image_data in enumerate(article_data['images']):
                        image_url = image_data['url']
                        
                        # Generate filename for image
                        parsed_url = urlparse(image_url)
                        if parsed_url.path:
                            image_filename = os.path.basename(parsed_url.path)
                        else:
                            # Extract extension from URL or default to .jpg
                            ext = '.jpg'
                            if '.' in image_url:
                                ext = '.' + image_url.split('.')[-1].split('?')[0]
                            image_filename = f"image_{i+1}{ext}"
                        
                        # Get the base path for relative image URLs
                        base_path = os.path.dirname(md_file) if isinstance(md_file, str) and os.path.exists(md_file) else temp_dir
                        
                        downloaded_path = download_image(image_url, article_dir, image_filename)
                        if downloaded_path:
                            images_downloaded += 1
                            if debug_mode:
                                try:
                                    st.write(f"✅ Downloaded image: {image_filename}")
                                except:
                                    logger.info(f"Downloaded image: {image_filename}")
                    
                    if debug_mode:
                        try:
                            st.write(f"📷 Downloaded {images_downloaded}/{len(article_data['images'])} images for {article_name}")
                        except:
                            logger.info(f"Downloaded {images_downloaded}/{len(article_data['images'])} images for {article_name}")
                
                articles_processed += 1
                
                if debug_mode:
                    try:
                        st.write(f"✅ Processed article: {article_name}")
                    except:
                        logger.info(f"Processed article: {article_name}")
            
            except Exception as e:
                logger.error(f"Error processing {filename}: {str(e)}")
                try:
                    st.error(f"Error processing {filename}: {str(e)}")
                except:
                    pass  # In case Streamlit context is not available
                continue
        
        # Create zip file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"modular_icml_articles_{timestamp}.zip"
        zip_path = os.path.join(temp_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    if file != zip_filename:  # Don't include the zip file itself
                        file_path = os.path.join(root, file)
                        # Create relative path for zip
                        rel_path = os.path.relpath(file_path, temp_dir)
                        zipf.write(file_path, rel_path)
        
        # Read zip file content
        with open(zip_path, 'rb') as f:
            zip_content = f.read()
        
        if debug_mode:
            try:
                st.success(f"✅ Created zip package with {articles_processed} articles")
            except:
                logger.info(f"Created zip package with {articles_processed} articles")
        
        return zip_content, zip_filename
        
    finally:
        # Clean up temporary directory
        shutil.rmtree(temp_dir, ignore_errors=True)

def main():
    st.title("Modular ICML Converter")
    st.markdown("*Converts markdown files to individual ICML files for each article element (title, author, body) with images*")
    
    # Debug toggle
    debug_mode = st.checkbox("🔍 Enable Debug Mode", help="Show detailed conversion process")
    
    # Show information about the new structure
    with st.expander("📁 New Modular Structure", expanded=True):
        st.write("This converter creates a **zip package** with the following structure:")
        st.code("""
article_package.zip
├── article_1/
│   ├── article_1_title.icml
│   ├── article_1_author.icml
│   ├── article_1_body.icml
│   └── images/
│       ├── image_1.jpg
│       └── image_2.png
├── article_2/
│   ├── article_2_title.icml
│   ├── article_2_author.icml
│   ├── article_2_body.icml
│   └── images/
│       └── image_1.jpg
└── ...
        """)
        st.write("**Benefits:**")
        st.write("• Each article element is a separate ICML file for precise InDesign placement")
        st.write("• Images are downloaded and organized by article")
        st.write("• Easy to import individual components into InDesign layouts")
        st.write("• Maintains Derek Carr Final styling for all elements")
    
    # File upload for markdown files
    uploaded_md_files = st.file_uploader(
        "Upload Markdown Files", 
        type=["md"], 
        accept_multiple_files=True,
        help="Select multiple markdown files to convert to modular ICML package"
    )
    
    if uploaded_md_files and st.button("Create Modular ICML Package"):
        try:
            st.info("🎨 Creating modular ICML package with Derek Carr Final styling...")
            
            # Create modular ICML package
            zip_content, zip_filename = create_modular_icml_package(uploaded_md_files, debug_mode=debug_mode)
            
            # Create download button
            st.download_button(
                label=f"📥 Download {zip_filename}",
                data=zip_content,
                file_name=zip_filename,
                mime="application/zip"
            )
            
            st.success(f"✅ Successfully created modular ICML package from {len(uploaded_md_files)} markdown files!")
            
            # Show summary
            with st.expander("📋 Package Summary"):
                st.write(f"**Input files:** {len(uploaded_md_files)} markdown files")
                file_list = ", ".join([f.name for f in uploaded_md_files])
                st.write(f"**Files processed:** {file_list}")
                st.write("**Structure:** Individual ICML files for title, author/date, and body")
                st.write("**Images:** Downloaded and organized by article")
                st.write("**Styling:** Derek Carr Final (embedded)")
                st.write(f"**Output:** {zip_filename}")
                    
        except Exception as e:
            st.error(f"❌ Error during conversion: {str(e)}")
            with st.expander("🔍 Full Error Details"):
                st.code(traceback.format_exc())

if __name__ == "__main__":
    main()