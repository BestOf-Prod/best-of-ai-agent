# Best of AI Agent - Batch Document Processor

A Streamlit application that processes Word documents containing multiple URLs, extracts articles, generates newspaper-style clippings, and uploads them to Replit Object Storage.

## Features

- 📄 **Word Document Processing**: Upload `.docx` files containing URLs
- 🔍 **Smart URL Extraction**: Automatically finds URLs in text, hyperlinks, and tables
- 🔄 **Concurrent Batch Processing**: Process multiple URLs simultaneously with configurable concurrency
- 🖼️ **Newspaper Clipping Generation**: Creates beautiful newspaper-style images from articles
- ☁️ **Replit Object Storage Integration**: Automatically uploads generated images to cloud storage
- 📊 **Progress Tracking**: Real-time progress updates and detailed error reporting
- 🛡️ **Error Handling**: Robust error handling with detailed logging and retry mechanisms

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the Application

```bash
streamlit run app.py
```

### 3. Create Sample Document (Optional)

```bash
python sample_urls.py
```

This creates `sample_urls_document.docx` with example URLs for testing.

## Usage

### Step 1: Upload Document
- Upload a Word document (`.docx`) containing URLs
- The document can have URLs in:
  - Plain text paragraphs
  - Hyperlinks
  - Table cells

### Step 2: Review URLs
- Review extracted URLs in the data table
- Add or remove URLs manually as needed
- Check processing settings in the sidebar

### Step 3: Configure Processing
- **Bucket Name**: Set your Replit Object Storage bucket name
- **Concurrent Workers**: Number of URLs to process simultaneously (1-5)
- **Request Delay**: Delay between requests to be respectful to servers

### Step 4: Start Batch Processing
- Click "🚀 Start Batch Processing" to begin
- Monitor progress with real-time updates
- View results as they complete

### Step 5: View Results
- Review processing summary with success/failure metrics
- Browse uploaded images in the gallery
- Check detailed error logs for failed URLs

## Configuration

### Replit Object Storage Setup

1. **Create a Bucket**: Use the Replit Object Storage tool to create a bucket
2. **Configure Access**: Ensure your Replit app has access to the bucket
3. **Set Bucket Name**: Enter the bucket name in the sidebar

### Environment Variables

- `REPLIT_BUCKET_NAME`: Default bucket name for Object Storage

## Architecture

### Core Components

```
├── app.py                      # Main Streamlit application
├── extractors/
│   └── url_extractor.py       # Article extraction and image generation
├── utils/
│   ├── document_processor.py  # Word document and URL processing
│   ├── storage_manager.py     # Replit Object Storage integration
│   ├── batch_processor.py     # Batch processing coordination
│   ├── processor.py           # Article data processing
│   └── logger.py              # Logging configuration
├── requirements.txt           # Python dependencies
└── sample_urls.py            # Sample document generator
```

### Processing Flow

1. **Document Upload** → Word document uploaded via Streamlit
2. **URL Extraction** → Extract URLs from document content
3. **Batch Processing** → Process URLs concurrently with rate limiting
4. **Article Extraction** → Extract content from each URL
5. **Image Generation** → Create newspaper-style clippings
6. **Cloud Upload** → Upload images to Replit Object Storage
7. **Results Display** → Show processing results and image gallery

## Storage Integration

### Replit Object Storage

The application integrates with Replit Object Storage using the official SDK:

```python
from replit_object_storage import Client

# Initialize client
client = Client()

# Upload image with metadata
result = client.upload_file(
    bucket_name="newspaper-clippings",
    object_name="article_clipping.png",
    file_data=image_bytes,
    metadata={
        'source_url': url,
        'headline': headline,
        'extracted_at': timestamp
    }
)
```

### Development Mode

When Replit Object Storage is not available, the application falls back to local storage in the `local_storage/` directory.

## Error Handling

### Robust Processing
- **Network Timeouts**: Configurable request timeouts with retries
- **Invalid URLs**: URL validation and filtering
- **Extraction Failures**: Graceful handling of content extraction errors
- **Upload Failures**: Detailed error reporting for storage issues

### Logging
- **Comprehensive Logging**: All operations logged with appropriate levels
- **Debug Mode**: Enable verbose logging in the sidebar
- **Error Tracking**: Failed operations tracked with detailed error messages

## Rate Limiting

### Respectful Processing
- **Configurable Delays**: Delay between requests to avoid overwhelming servers
- **Concurrent Limits**: Limit simultaneous requests (default: 3 workers)
- **Batch Processing**: Process URLs in batches to manage load

## Image Generation

### Newspaper Clipping Style
- **Professional Layout**: Clean, newspaper-like design
- **Typography**: Multiple font sizes for hierarchy
- **Content Wrapping**: Intelligent text wrapping for readability
- **Metadata Display**: Source, date, and author information
- **Border Effects**: Decorative borders for newspaper aesthetic

## Troubleshooting

### Common Issues

**1. Storage Connection Failed**
- Check bucket name spelling
- Verify Replit app has bucket access
- Test connection using sidebar button

**2. No URLs Extracted**
- Ensure document is `.docx` format
- Check that URLs are properly formatted (http/https)
- Verify URLs are not in images or other non-text elements

**3. Processing Failures**
- Check network connectivity
- Verify URLs are accessible
- Increase request delay for rate-limited sites

**4. Import Errors**
- Install all dependencies: `pip install -r requirements.txt`
- Check Python version compatibility
- Verify Replit Object Storage SDK installation

### Development Mode

If Replit Object Storage is not available:
- Images are saved to `local_storage/` directory
- Gallery displays local images
- All other functionality remains operational

## Dependencies

```
beautifulsoup4==4.12.3    # HTML parsing
pandas==2.2.3             # Data manipulation
requests==2.32.3          # HTTP requests
streamlit==1.40.2         # Web interface
python-docx==1.1.2        # Word document processing
replit-object-storage==1.0.0  # Cloud storage
pillow==10.4.0            # Image processing
google-cloud-storage==2.18.0  # GCS backend
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review the logs in verbose mode
3. Create an issue with detailed error information 