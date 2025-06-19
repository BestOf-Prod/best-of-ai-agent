# ICML Converter Update

## Summary

The main app.py has been updated to support both single file and modular ICML conversion options.

## New Features

### 1. Conversion Type Selection
Users can now choose between two ICML conversion types:

#### **📄 Single File ICML** (Original)
- All articles combined into one ICML file
- Easy to import as a complete document
- Traditional workflow
- Uses `utils/icml_converter.py`

#### **📁 Modular ICML Package** (New)
- Individual ICML files for each article element
- Separate files for title, author/date, and body
- Images downloaded and organized
- Precise InDesign placement control
- Uses `utils/modular_icml_converter.py`

### 2. Enhanced UI
- Radio button selection for conversion type
- Clear descriptions of each option
- Dynamic button text based on selection
- Detailed package structure preview
- Separate summary sections for each type

### 3. Improved Markdown Formatting
- Different markdown formats for each conversion type
- Proper author/date formatting for modular converter
- Enhanced content structure for better parsing

## Usage

1. Process articles through the normal workflow
2. Go to the "📑 ICML Export" tab
3. Choose your preferred conversion type
4. Click the appropriate conversion button
5. Download either:
   - `.icml` file (single file option)
   - `.zip` package (modular option)

## File Structure

### Single File Output
```
combined_articles_[timestamp].icml
```

### Modular Package Output
```
modular_icml_articles_[timestamp].zip
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
```

## Implementation Details

### Files Modified
- `app.py`: Updated ICML tab with dual conversion options
- Added import for `utils.modular_icml_converter`

### Files Added
- `utils/modular_icml_converter.py`: New modular conversion functionality

### Backward Compatibility
- Original single file ICML conversion remains unchanged
- Existing functionality is preserved
- No breaking changes to existing workflows

## Benefits

### For Users
- Choose the workflow that best fits their InDesign process
- Modular files allow precise control over element placement
- Single files maintain traditional import workflow

### For InDesign Usage
- **Single File**: Import entire document at once
- **Modular**: Place individual elements (title, author, body) precisely where needed
- Images organized and ready for linking
- Professional Derek Carr Final styling maintained in both formats