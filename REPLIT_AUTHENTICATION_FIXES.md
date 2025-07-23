# Replit Google Drive Authentication Fixes

## Overview
Updated the `utils/google_drive_manager.py` module to properly handle Google Drive authentication in Replit containers.

## Key Changes Made

### 1. **Fixed Replit URL Format**
- **Before:** `{repl_slug}-{repl_owner}.replit.app` (outdated format)
- **After:** `{repl_slug}.{repl_owner}.replit.co` (current format)

### 2. **Improved Environment Detection**
```python
# Before
IS_REPLIT = bool(os.environ.get('REPL_ID'))

# After  
IS_REPLIT = bool(os.environ.get('REPL_ID') or os.environ.get('REPL_SLUG'))
```

### 3. **Standardized Redirect URI Configuration**
- **Consistent format:** `https://{replit_url}/oauth/callback`
- **Removed duplicate URIs** that were causing confusion
- **Centralized URL generation** using helper method

### 4. **Added Helper Methods**

#### `_get_replit_url()`
- Centralized Replit URL generation
- Added validation for environment variables
- Consistent format across all methods

#### `validate_replit_environment()`
- Comprehensive environment validation
- Diagnostic information for troubleshooting
- Checks for required environment variables

#### `get_replit_setup_instructions()`
- Detailed setup instructions for Google Cloud Console
- Common issues and solutions
- Step-by-step configuration guide

### 5. **Improved Replit Authentication Flow**
- **Removed problematic console auth** that doesn't work in Replit
- **Streamlined manual authentication** as primary method
- **Better error messages** with specific setup instructions
- **Consistent OAuth configuration** across all methods

## Configuration Requirements

### Google Cloud Console Setup
1. Add redirect URI: `https://{your-repl-slug}.{your-username}.replit.co/oauth/callback`
2. Enable Google Drive API in your project
3. Configure OAuth consent screen properly

### Environment Variables
The module now properly detects and validates:
- `REPL_ID` - Replit container ID
- `REPL_SLUG` - Replit project slug  
- `REPL_OWNER` - Replit username

## Usage in Replit

### 1. Upload Credentials
```python
# Upload your credentials.json file to the app
```

### 2. Get Setup Instructions
```python
drive_manager = GoogleDriveManager()
instructions = drive_manager.get_replit_setup_instructions()
```

### 3. Configure Google Cloud Console
Follow the setup steps provided by the instructions method.

### 4. Authenticate
```python
# Get authorization URL
auth_result = drive_manager.get_auth_url()

# Use manual authentication with the provided URL
# Copy the authorization code and use authenticate_with_code()
```

## Testing

Run the test script to verify the changes:
```bash
python test_replit_auth.py
```

## Benefits

1. **Correct URL Format** - Uses current Replit domain format
2. **Better Error Handling** - Clear error messages and diagnostics
3. **Consistent Configuration** - Same redirect URI used everywhere
4. **Improved Validation** - Comprehensive environment checks
5. **Better Documentation** - Clear setup instructions for users

## Backward Compatibility

- All changes are backward compatible with local development
- Local authentication flow remains unchanged
- Only affects Replit-specific functionality

## Files Modified

- `utils/google_drive_manager.py` - Main authentication module
- `test_replit_auth.py` - Test script for verification

## Next Steps

1. Test the authentication flow in an actual Replit environment
2. Verify Google Cloud Console configuration
3. Test the complete OAuth flow end-to-end 