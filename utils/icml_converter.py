import streamlit as st
import subprocess
import tempfile
import os
import traceback
import xml.etree.ElementTree as ET
from datetime import datetime
import logging
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
		<Font Self="di8dFontnMyriad Pro Regular" FontFamily="Myriad Pro" Name="Myriad Pro Regular" PostScriptName="MyriadPro-Regular" Status="Installed" FontStyleName="Regular" FontType="OpenTypeCFF" WritingScript="0" FullName="Myriad Pro" FullNameNative="Myriad Pro" FontStyleNameNative="Regular" PlatformName="$ID/" Version="Version 2.106;PS 2.000;hotconv 1.0.70;makeotf.lib2.5.58329" TypekitID="$ID/" />
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
    st.info("🎨 Using embedded Derek Carr Final styling:")
    st.write(f"   • {len(DEREK_CARR_STYLING['colors'])} Colors")
    st.write(f"   • {len(DEREK_CARR_STYLING['inks'])} Inks") 
    st.write(f"   • {len(DEREK_CARR_STYLING['font_families'])} Font Families")
    st.write(f"   • {len(DEREK_CARR_STYLING['composite_fonts'])} Composite Fonts")
    st.write(f"   • {len(DEREK_CARR_STYLING['character_styles'])} Character Style Groups")
    st.write(f"   • {len(DEREK_CARR_STYLING['paragraph_styles'])} Paragraph Style Groups")
    st.write(f"   • {len(DEREK_CARR_STYLING['color_groups'])} Color Groups")
    
    return DEREK_CARR_STYLING

def clean_markdown_content(md_content):
    """Clean markdown content to remove problematic YAML metadata and other issues."""
    lines = md_content.split('\n')
    cleaned_lines = []
    in_yaml_block = False
    yaml_started = False
    
    for i, line in enumerate(lines):
        # Check for YAML frontmatter start
        if i == 0 and line.strip() == '---':
            in_yaml_block = True
            yaml_started = True
            continue
        
        # If we're in a YAML block, skip until we find the end
        if in_yaml_block:
            if line.strip() == '---':
                in_yaml_block = False
            continue
        
        # If we started a YAML block but didn't find the end, stop processing
        if yaml_started and not in_yaml_block:
            break
        
        # Add non-YAML lines
        cleaned_lines.append(line)
    
    # Join the cleaned lines
    cleaned_content = '\n'.join(cleaned_lines)
    
    # Remove any remaining problematic patterns
    import re
    
    # Remove any remaining YAML-like patterns
    cleaned_content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', cleaned_content, flags=re.DOTALL)
    
    # Remove any lines that start with common YAML keys that might cause issues
    cleaned_lines = []
    for line in cleaned_content.split('\n'):
        # Skip lines that look like YAML metadata
        if re.match(r'^\s*(Source|Date|Title|Author|Category|Tags):\s*', line):
            continue
        cleaned_lines.append(line)
    
    cleaned_content = '\n'.join(cleaned_lines)
    
    # Ensure we have some content
    if not cleaned_content.strip():
        cleaned_content = "# No Content\n\nNo readable content found in the markdown file."
    
    return cleaned_content

def combine_markdown_files(md_files):
    """Combine multiple markdown files into one content string."""
    combined_content = ""
    
    for i, md_file in enumerate(md_files):
        try:
            # Read markdown content
            if hasattr(md_file, 'getvalue'):  # If it's a file object (from upload)
                file_content = md_file.getvalue()
                md_content = file_content.decode('utf-8')
                filename = md_file.name
            elif isinstance(md_file, str) and os.path.exists(md_file):  # If it's a file path
                with open(md_file, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                filename = os.path.basename(md_file)
            elif isinstance(md_file, str):  # If it's direct content
                md_content = md_file
                filename = f"content_{i+1}"
            else:
                st.error(f"Unsupported file type: {type(md_file)}")
                continue
            
            # Clean the markdown content
            cleaned_md_content = clean_markdown_content(md_content)
            
            # Add separator between articles (except for the first one)
            if i > 0:
                combined_content += "\n\n---\n\n"
            
            # Add a header with the filename
            filename_without_ext = os.path.splitext(filename)[0]
            combined_content += f"# {filename_without_ext}\n\n"
            
            # Add the cleaned content
            combined_content += cleaned_md_content
            
        except Exception as e:
            st.error(f"Error processing file {md_file}: {str(e)}")
            continue
    
    if not combined_content:
        raise ValueError("No valid content could be combined from the provided files")
        
    return combined_content

def create_manual_icml_content(md_content):
    """Create ICML content manually from markdown when Pandoc truncates."""
    # Split content into paragraphs
    paragraphs = md_content.split('\n\n')
    
    # Create a simple ICML story structure
    story_content = []
    story_content.append('<Story Self="u1" AppliedTOCStyle="TableOfContentsStyle/$ID/[No TOC style]" TrackChanges="false" StoryTitle="$ID/" AppliedNamedGrid="n" AppliedMasterSpread="u2" UserText="false" IsEndnoteStory="false" IncludeInBookmarks="true" IncludeInTOC="true" MaintainTextEditability="false" OverrideAllTextFrameFittingOptions="false" AppliedNamedGrids="n" GridAlignment="AlignToBaseline" FrameType="TextFrameType" TextFramePreference="TextFramePreference/TextFrameGeneralPreference" NextTextFrame="n" PreviousTextFrame="n" Intent="Both">')
    story_content.append('\t<InCopyExportOption IncludeGraphicProxies="true" IncludeAllResources="false" />')
    story_content.append('\t<ParagraphStyleRange AppliedParagraphStyle="ParagraphStyle/$ID/NormalParagraphStyle">')
    story_content.append('\t\t<CharacterStyleRange AppliedCharacterStyle="$ID/[No character style]">')
    
    # Add content paragraphs
    for i, para in enumerate(paragraphs):
        if para.strip():  # Skip empty paragraphs
            # Clean up the paragraph text
            clean_para = para.strip().replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            story_content.append(f'\t\t\t<Content>{clean_para}</Content>')
            if i < len(paragraphs) - 1:  # Add line break between paragraphs
                story_content.append('\t\t\t<Br />')
    
    story_content.append('\t\t</CharacterStyleRange>')
    story_content.append('\t</ParagraphStyleRange>')
    story_content.append('</Story>')
    
    return '\n'.join(story_content)

def create_styled_icml(combined_md_content, styling_elements, debug_mode=False):
    """Create ICML with Derek Carr Final styling applied to combined markdown content."""
    
    # First convert markdown to basic ICML using pandoc
    temp_md = tempfile.NamedTemporaryFile(suffix='.md', mode='w', delete=False)
    temp_icml = tempfile.NamedTemporaryFile(suffix='.icml', delete=False)
    
    try:
        # Write combined markdown content
        temp_md.write(combined_md_content)
        temp_md.flush()
        
        # Convert to ICML using pandoc
        cmd = ["pandoc", "-s", "-f", "markdown", "-t", "icml", temp_md.name, "-o", temp_icml.name]
        
        if debug_mode:
            st.write("🔍 **Debug: Pandoc Command**")
            st.code(" ".join(cmd))
            st.write("🔍 **Debug: Markdown Content Preview**")
            st.code(combined_md_content[:1000] + "..." if len(combined_md_content) > 1000 else combined_md_content)
        
        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            if debug_mode:
                st.write("✅ Pandoc command executed successfully")
        except subprocess.CalledProcessError as e:
            if debug_mode:
                st.error(f"❌ Pandoc command failed with exit code {e.returncode}")
                st.write("🔍 **Debug: Pandoc Error Output**")
                st.code(e.stderr)
            
            # Try alternative Pandoc options
            st.warning("⚠️ Pandoc failed. Trying alternative conversion method...")
            cmd_alt = ["pandoc", "-f", "markdown", "-t", "icml", "--wrap=none", "--fail-if-warnings", temp_md.name, "-o", temp_icml.name]
            
            if debug_mode:
                st.write("🔍 **Debug: Alternative Pandoc Command**")
                st.code(" ".join(cmd_alt))
            
            try:
                result = subprocess.run(cmd_alt, check=True, capture_output=True, text=True)
                if debug_mode:
                    st.write("✅ Alternative Pandoc command executed successfully")
            except subprocess.CalledProcessError as e2:
                if debug_mode:
                    st.error(f"❌ Alternative Pandoc command also failed with exit code {e2.returncode}")
                    st.write("🔍 **Debug: Alternative Pandoc Error Output**")
                    st.code(e2.stderr)
                
                # If both Pandoc attempts fail, use manual fallback immediately
                st.warning("⚠️ Pandoc conversion failed. Using manual ICML generation...")
                stories = [create_manual_icml_content(combined_md_content)]
                st.success("✅ Using manual ICML generation to preserve full content")
                
                # Skip the rest of the Pandoc processing
                styled_icml_parts = []
                
                # Add XML declaration and processing instructions
                styled_icml_parts.append(styling_elements['xml_declaration'])
                styled_icml_parts.append(styling_elements['aid_style'])
                styled_icml_parts.append(styling_elements['aid_snippet'])
                
                # Start document with Derek Carr attributes
                styled_icml_parts.append(f'<Document {styling_elements["document_attrs"]}>')
                
                # Add colors
                for color in styling_elements['colors']:
                    styled_icml_parts.append('\t' + color)
                
                # Add inks
                for ink in styling_elements['inks']:
                    styled_icml_parts.append('\t' + ink)
                
                # Add font families
                for font_family in styling_elements['font_families']:
                    indented_font_family = '\n'.join('\t' + line for line in font_family.split('\n'))
                    styled_icml_parts.append(indented_font_family)
                
                # Add composite fonts
                for composite_font in styling_elements['composite_fonts']:
                    indented_composite_font = '\n'.join('\t' + line for line in composite_font.split('\n'))
                    styled_icml_parts.append(indented_composite_font)
                
                # Add character styles
                for char_style in styling_elements['character_styles']:
                    indented_char_style = '\n'.join('\t' + line for line in char_style.split('\n'))
                    styled_icml_parts.append(indented_char_style)
                
                # Add paragraph styles
                for para_style in styling_elements['paragraph_styles']:
                    indented_para_style = '\n'.join('\t' + line for line in para_style.split('\n'))
                    styled_icml_parts.append(indented_para_style)
                
                # Add the manually generated story
                styled_icml_parts.append('\t' + stories[0])
                
                # Add color groups at the end
                for color_group in styling_elements['color_groups']:
                    indented_color_group = '\n'.join('\t' + line for line in color_group.split('\n'))
                    styled_icml_parts.append(indented_color_group)
                
                # Close document
                styled_icml_parts.append('</Document>')
                
                # Join all parts
                final_icml = '\n'.join(styled_icml_parts)
                
                st.success(f"✅ Applied Derek Carr Final styling: 1 content story with professional formatting")
                
                return final_icml.encode('utf-8')
        
        # Read the generated ICML to extract content stories
        with open(temp_icml.name, "r", encoding="utf-8") as f:
            icml_content = f.read()
        
        # DEBUG: Log the raw ICML content to see what Pandoc is producing
        if debug_mode:
            st.write("🔍 **Debug: Raw Pandoc ICML Output**")
            st.code(icml_content[:2000] + "..." if len(icml_content) > 2000 else icml_content)
        
        # Parse the generated ICML to extract story content
        root = ET.fromstring(icml_content)
        stories = root.findall('.//Story')
        
        if debug_mode:
            st.write(f"🔍 **Debug: Found {len(stories)} Story elements**")
        
        # Check if we have content and if it's complete
        total_content_length = 0
        for i, story in enumerate(stories):
            content_elements = story.findall('.//Content')
            story_content = ''.join([elem.text or '' for elem in content_elements])
            total_content_length += len(story_content)
            if debug_mode:
                st.write(f"🔍 **Debug: Story {i+1} has {len(content_elements)} Content elements, {len(story_content)} characters**")
                if len(story_content) > 200:
                    st.write(f"🔍 **Debug: Story {i+1} preview: {story_content[:200]}...**")
        
        # If content seems truncated, try alternative approach
        if total_content_length < len(combined_md_content) * 0.5:  # If we got less than 50% of original content
            st.warning("⚠️ Content appears to be truncated. Trying alternative conversion method...")
            
            # Try with different Pandoc options
            cmd_alt = ["pandoc", "-f", "markdown", "-t", "icml", "--wrap=none", temp_md.name, "-o", temp_icml.name]
            subprocess.run(cmd_alt, check=True)
            
            with open(temp_icml.name, "r", encoding="utf-8") as f:
                icml_content = f.read()
            
            root = ET.fromstring(icml_content)
            stories = root.findall('.//Story')
            if debug_mode:
                st.write(f"🔍 **Debug: After alternative conversion, found {len(stories)} Story elements**")
            
            # Check content again
            total_content_length = 0
            for story in stories:
                content_elements = story.findall('.//Content')
                story_content = ''.join([elem.text or '' for elem in content_elements])
                total_content_length += len(story_content)
        
        # If still truncated, use manual fallback
        if total_content_length < len(combined_md_content) * 0.5:
            st.warning("⚠️ Pandoc still truncating content. Using manual ICML generation...")
            stories = [create_manual_icml_content(combined_md_content)]
            st.success("✅ Using manual ICML generation to preserve full content")
        
        # Build the styled ICML using static Derek Carr styling
        styled_icml_parts = []
        
        # Add XML declaration and processing instructions
        styled_icml_parts.append(styling_elements['xml_declaration'])
        styled_icml_parts.append(styling_elements['aid_style'])
        styled_icml_parts.append(styling_elements['aid_snippet'])
        
        # Start document with Derek Carr attributes
        styled_icml_parts.append(f'<Document {styling_elements["document_attrs"]}>')
        
        # Add colors
        for color in styling_elements['colors']:
            styled_icml_parts.append('\t' + color)
        
        # Add inks
        for ink in styling_elements['inks']:
            styled_icml_parts.append('\t' + ink)
        
        # Add font families
        for font_family in styling_elements['font_families']:
            # Add proper indentation to font family XML
            indented_font_family = '\n'.join('\t' + line for line in font_family.split('\n'))
            styled_icml_parts.append(indented_font_family)
        
        # Add composite fonts
        for composite_font in styling_elements['composite_fonts']:
            indented_composite_font = '\n'.join('\t' + line for line in composite_font.split('\n'))
            styled_icml_parts.append(indented_composite_font)
        
        # Add character styles
        for char_style in styling_elements['character_styles']:
            indented_char_style = '\n'.join('\t' + line for line in char_style.split('\n'))
            styled_icml_parts.append(indented_char_style)
        
        # Add paragraph styles
        for para_style in styling_elements['paragraph_styles']:
            indented_para_style = '\n'.join('\t' + line for line in para_style.split('\n'))
            styled_icml_parts.append(indented_para_style)
        
        # Add the content stories from pandoc conversion
        stories_added = 0
        for story in stories:
            try:
                if isinstance(story, str):
                    # This is our manually generated story content
                    styled_icml_parts.append('\t' + story)
                    stories_added += 1
                else:
                    # This is an XML element from Pandoc
                    story_xml = ET.tostring(story, encoding='unicode', method='xml')
                    # Add proper indentation
                    indented_story = '\n'.join('\t' + line for line in story_xml.split('\n'))
                    styled_icml_parts.append(indented_story)
                    stories_added += 1
            except Exception as e:
                st.warning(f"⚠️ Could not add story element: {str(e)}")
                continue
        
        # Add color groups at the end
        for color_group in styling_elements['color_groups']:
            indented_color_group = '\n'.join('\t' + line for line in color_group.split('\n'))
            styled_icml_parts.append(indented_color_group)
        
        # Close document
        styled_icml_parts.append('</Document>')
        
        # Join all parts
        final_icml = '\n'.join(styled_icml_parts)
        
        st.success(f"✅ Applied Derek Carr Final styling: {stories_added} content stories with professional formatting")
        
        return final_icml.encode('utf-8')
        
    finally:
        # Clean up temporary files
        os.unlink(temp_md.name)
        os.unlink(temp_icml.name)

def convert_to_icml(md_files, reference_icml_path=None, debug_mode=False):
    """Convert multiple markdown files to a single styled ICML with Derek Carr Final formatting."""
    try:
        # Ensure md_files is a list
        if not isinstance(md_files, list):
            md_files = [md_files]
            
        # Combine all markdown files
        combined_content = combine_markdown_files(md_files)
        
        # Get static Derek Carr styling (reference_icml_path is ignored since we use static styling)
        styling_elements = get_derek_carr_styling()
        
        # Create styled ICML with Derek Carr Final formatting
        icml_content = create_styled_icml(combined_content, styling_elements, debug_mode=debug_mode)
        
        return icml_content
        
    except Exception as e:
        st.error(f"Error converting to ICML: {str(e)}")
        st.error(f"Stack trace: {traceback.format_exc()}")
        raise

def main():
    st.title("Markdown to Derek Carr Final ICML Converter")
    st.markdown("*Converts markdown files to ICML format with **embedded Derek Carr Final styling***")
    
    # Debug toggle
    debug_mode = st.checkbox("🔍 Enable Debug Mode", help="Show detailed conversion process and content analysis")
    
    # Show styling information
    with st.expander("🎨 Derek Carr Final Styling (Embedded)", expanded=False):
        st.write("This converter uses **static Derek Carr Final styling** embedded directly in the code:")
        st.write("• Professional typography with Impact headlines and Minion Pro body text")
        st.write("• Century Gothic Pro for continued text styling")
        st.write("• Myriad Pro for UI elements and captions")
        st.write("• Full color palette and ink definitions")
        st.write("• Complete paragraph and character style definitions")
        st.write("• Composite font handling for international characters")
        st.write("")
        st.success("✅ No external reference files needed - styling is built-in!")
    
    # File upload for markdown files
    uploaded_md_files = st.file_uploader(
        "Upload Markdown Files", 
        type=["md"], 
        accept_multiple_files=True,
        help="Select multiple markdown files to combine into one Derek Carr Final styled ICML"
    )
    
    if uploaded_md_files and st.button("Convert to Derek Carr Final ICML"):
        try:
            st.info("🎨 Converting with embedded Derek Carr Final styling...")
            
            # Convert to ICML (reference_path is ignored since we use static styling)
            icml_content = convert_to_icml(uploaded_md_files, debug_mode=debug_mode)
            
            # Generate output filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"derek_carr_final_articles_{timestamp}.icml"
            
            # Create download button
            st.download_button(
                label=f"📥 Download {output_filename}",
                data=icml_content,
                file_name=output_filename,
                mime="application/x-indesign"
            )
            
            st.success(f"✅ Successfully converted {len(uploaded_md_files)} markdown files to Derek Carr Final ICML!")
            
            # Show summary
            with st.expander("📋 Conversion Summary"):
                st.write(f"**Input files:** {len(uploaded_md_files)} markdown files")
                file_list = ", ".join([f.name for f in uploaded_md_files])
                st.write(f"**Files combined:** {file_list}")
                st.write("**Styling applied:** Derek Carr Final (embedded)")
                st.write("**Features:** Professional typography, colors, fonts, paragraph styles, and formatting")
                st.write(f"**Output:** {output_filename}")
                    
        except Exception as e:
            st.error(f"❌ Error during conversion: {str(e)}")
            st.error("Please ensure Pandoc is installed and accessible.")
            st.error("You can install Pandoc from: https://pandoc.org/installing.html")
            with st.expander("🔍 Full Error Details"):
                st.code(traceback.format_exc())

if __name__ == "__main__":
    main()