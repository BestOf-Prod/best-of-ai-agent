# NumPy Import Error Fix for Replit

## Error Message
```
ImportError: Unable to import required dependencies: numpy: Error importing numpy: you should not try to import numpy from its source directory; please exit the numpy source tree, and relaunch your python interpreter from there.
```

## Root Cause
This error typically occurs when:
1. NumPy installation is corrupted or incomplete in Replit
2. There are conflicting numpy files in the environment
3. The Python environment needs to be refreshed

## Solutions (Try in Order)

### Solution 1: Force Reinstall NumPy in Replit
In the Replit Shell, run:
```bash
pip uninstall numpy -y
pip install numpy==2.1.3
```

### Solution 2: Clear Python Cache
In the Replit Shell, run:
```bash
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
pip install --force-reinstall numpy==2.1.3
```

### Solution 3: Use Poetry/UV for Clean Install
In the Replit Shell, run:
```bash
uv pip uninstall numpy
uv pip install numpy==2.1.3
```

### Solution 4: Restart Replit Environment
1. Click the "Stop" button in Replit
2. Click "Run" again to restart the environment
3. The dependencies should reinstall automatically

## Code Changes Made

I've added fallback handling to make the app more resilient:

### In `extractors/newspapers_extractor.py`:
```python
# Optional numpy import with fallback
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("NumPy not available. Advanced image processing features will be disabled.")
```

### Fallback Functions:
- **Image enhancement**: Falls back to basic PIL enhancement if numpy unavailable
- **Article region detection**: Returns full image as single region if numpy unavailable
- **App continues to work**: Core functionality preserved even without numpy

## What This Means

### If NumPy Works:
✅ Full advanced image processing capabilities
✅ Precise article region detection
✅ Enhanced OCR preprocessing

### If NumPy Fails:
✅ App still runs without crashes
⚠️ Basic image processing only
⚠️ Simple article region detection
✅ All other features work normally

## Recommended Action

**Try Solution 1 first** (force reinstall) as this usually resolves the issue in Replit. The fallback code ensures your app won't crash even if numpy issues persist.

## Testing
After trying any solution, test with:
```python
import numpy as np
print("NumPy version:", np.__version__)
print("NumPy working!")
```

If this runs without error, your app should work properly with full image processing capabilities.