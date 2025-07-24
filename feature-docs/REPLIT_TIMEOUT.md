2025-07-09 13:35:22.45
94fa9914
User
2025-07-09 18:35:22,457 - INFO - extractors.newspapers_extractor - Authentication verified: window.ncom.statsiguser.custom.isloggedin is true.
2025-07-09 13:35:22.46
94fa9914
User
2025-07-09 18:35:22,461 - INFO - extractors.newspapers_extractor - Authentication is current and valid.
2025-07-09 13:35:22.46
94fa9914
User
2025-07-09 18:35:22,461 - INFO - extractors.newspapers_extractor - Newspapers.com URL detected. Forcing content fetch via Selenium for URL: https://www.newspapers.com/image/1015223323/
2025-07-09 13:35:22.83
94fa9914
User
2025-07-09 18:35:22,834 - INFO - extractors.newspapers_extractor - Re-using existing Selenium driver for page content capture.
2025-07-09 13:35:22.83
94fa9914
User
2025-07-09 18:35:22,837 - INFO - extractors.newspapers_extractor - Loading target page with Selenium: https://www.newspapers.com/image/1015223323/
2025-07-09 13:36:07.12
94fa9914
User
2025-07-09 18:36:07,121 - INFO - extractors.newspapers_extractor - Debug HTML saved to debug_html/debug_page_20250709_183607_0b13a6c7.html
2025-07-09 13:36:07.13
94fa9914
User
2025-07-09 18:36:07,138 - INFO - extractors.newspapers_extractor - Debug summary saved to debug_html/debug_summary_20250709_183607_0b13a6c7.txt
2025-07-09 13:36:07.13
94fa9914
User
2025-07-09 18:36:07,139 - INFO - extractors.newspapers_extractor - Selenium successfully captured HTML content: 76295 bytes.
2025-07-09 13:36:07.13
94fa9914
User
2025-07-09 18:36:07,139 - INFO - extractors.newspapers_extractor - Parsing HTML for image metadata...
2025-07-09 13:36:07.14
94fa9914
User
2025-07-09 18:36:07,140 - INFO - extractors.newspapers_extractor - Found image ID: 1015223323
2025-07-09 13:36:07.14
94fa9914
User
2025-07-09 18:36:07,141 - INFO - extractors.newspapers_extractor - Found base image URL: https://img.newspapers.com
2025-07-09 13:36:07.14
94fa9914
User
2025-07-09 18:36:07,142 - INFO - extractors.newspapers_extractor - Successfully extracted image metadata: {'image_id': 1015223323, 'date': '2016-03-21', 'publication_title': 'The Hamilton Spectator', 'location': 'Hamilton, Ontario, Canada', 'title': '34', 'width': 3276, 'height': 0, 'wfm_image_path': '8eec6d3f-dca0-4bf5-bc85-f708d80b1aae/25f27278-5833-4249-8574-97490703c156/HAM_259_20160321-20160630_01/0035', 'base_image_url': 'https://img.newspapers.com'}
2025-07-09 13:36:07.14
94fa9914
User
2025-07-09 18:36:07,142 - INFO - extractors.newspapers_extractor - Extracted image metadata: {'image_id': 1015223323, 'date': '2016-03-21', 'publication_title': 'The Hamilton Spectator', 'location': 'Hamilton, Ontario, Canada', 'title': '34', 'width': 3276, 'height': 0, 'wfm_image_path': '8eec6d3f-dca0-4bf5-bc85-f708d80b1aae/25f27278-5833-4249-8574-97490703c156/HAM_259_20160321-20160630_01/0035', 'base_image_url': 'https://img.newspapers.com', 'url': 'https://www.newspapers.com/image/1015223323/'}
2025-07-09 13:36:07.14
94fa9914
User
2025-07-09 18:36:07,143 - INFO - extractors.newspapers_extractor - Searching for genuine multi-page article indicators...
2025-07-09 13:36:07.14
94fa9914
User
2025-07-09 18:36:07,143 - INFO - extractors.newspapers_extractor - Searching for multi-page images related to base image 1015223323.
2025-07-09 13:36:07.15
94fa9914
User
2025-07-09 18:36:07,152 - INFO - extractors.newspapers_extractor - No genuine multi-page article indicators found - treating as single page.
2025-07-09 13:36:07.15
94fa9914
User
2025-07-09 18:36:07,152 - INFO - extractors.newspapers_extractor - No genuine multi-page article found - processing as single page with multiple regions.
2025-07-09 13:36:07.15
94fa9914
User
2025-07-09 18:36:07,153 - INFO - extractors.newspapers_extractor - Downloading main newspaper image...
2025-07-09 13:36:07.15
94fa9914
User
2025-07-09 18:36:07,153 - INFO - extractors.newspapers_extractor - Downloading newspaper article via screenshot...
2025-07-09 13:36:09.38
94fa9914
User
2025-07-09 18:36:09,386 - INFO - extractors.newspapers_extractor - Loading main site to set cookies for Selenium image download...
2025-07-09 13:36:59.89
94fa9914
User
2025-07-09 18:36:59,889 - INFO - extractors.newspapers_extractor - Loading target page for article extraction: https://www.newspapers.com/image/1015223323/
2025-07-09 13:39:00.34
94fa9914
User
2025-07-09 18:38:59,995 - ERROR - extractors.newspapers_extractor - Article extraction failed: HTTPConnectionPool(host='localhost', port=52289): Read timed out. (read timeout=120)