
# NumPy Import Error Analysis and Fix Plan

## Problem Summary
The application is failing to start due to a numpy import error:
```
ImportError: Unable to import required dependencies:
numpy: Error importing numpy: you should not try to import numpy from
        its source directory; please exit the numpy source tree, and relaunch
        your python interpreter from there.
```

## Deep Codebase Analysis

### Files Using NumPy
Based on my analysis of the codebase, numpy is used in the following locations:

1. **`extractors/newspapers_extractor.py`** - Uses numpy for advanced image processing
2. **`app.py`** - Imports pandas which depends on numpy
3. **`pyproject.toml`** - Lists pandas>=2.2.3 as dependency (which requires numpy)

### Current Fallback Implementation
The codebase already has some fallback handling in `extractors/newspapers_extractor.py`:

```python
# Optional numpy import with fallback
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    logger.warning("NumPy not available. Advanced image processing features will be disabled.")
```

However, the main issue is that **pandas** (imported in `app.py`) has a hard dependency on numpy and fails completely when numpy can't be imported.

## Root Cause Analysis

### Primary Issues:
1. **Corrupted NumPy Installation**: The error suggests numpy files are present but corrupted or in an inconsistent state
2. **Environment Contamination**: Previous installation attempts may have left conflicting files
3. **Cache Issues**: Python cache files may be referencing old/corrupted numpy files
4. **Dependency Chain Failure**: pandas → numpy dependency chain is breaking the entire app

### Why Previous Fixes Didn't Work:
1. **Partial Cleanup**: Previous `pip uninstall/install` commands didn't fully clean the environment
2. **Cache Persistence**: Python bytecode cache wasn't cleared
3. **Environment Not Reset**: Replit environment may need a complete refresh

## Comprehensive Fix Plan

### Phase 1: Complete Environment Cleanup
1. **Clear All Python Cache Files**
   ```bash
   find . -name "*.pyc" -delete
   find . -name "__pycache__" -type d -exec rm -rf {} +
   find . -name "*.pyo" -delete
   ```

2. **Remove All Numpy/Pandas Related Files**
   ```bash
   rm -rf .pythonlibs/lib/python3.12/site-packages/numpy*
   rm -rf .pythonlibs/lib/python3.12/site-packages/pandas*
   rm -rf .pythonlibs/lib/python3.12/site-packages/*numpy*
   rm -rf .pythonlibs/lib/python3.12/site-packages/*pandas*
   ```

3. **Clear pip cache**
   ```bash
   pip cache purge
   ```

### Phase 2: Fresh Installation Strategy
1. **Use pip with explicit version pinning**
   ```bash
   pip install --no-cache-dir --force-reinstall numpy==2.1.3
   pip install --no-cache-dir --force-reinstall pandas==2.2.3
   ```

2. **Alternative: Use uv for clean installation**
   ```bash
   uv pip uninstall numpy pandas
   uv pip install --no-cache numpy==2.1.3 pandas==2.2.3
   ```

### Phase 3: Fallback Implementation Enhancement
Enhance the application to gracefully handle numpy unavailability:

#### 3.1 Create Robust Import Handler
Create a new utility file to handle numpy imports safely:

```python
# utils/numpy_handler.py
import logging
from utils.logger import setup_logging

logger = setup_logging(__name__)

# Safe numpy import with detailed error reporting
def safe_numpy_import():
    try:
        import numpy as np
        logger.info(f"NumPy successfully imported, version: {np.__version__}")
        return np, True
    except ImportError as e:
        logger.error(f"NumPy import failed: {str(e)}")
        return None, False
    except Exception as e:
        logger.error(f"Unexpected error importing NumPy: {str(e)}")
        return None, False

# Safe pandas import with fallback
def safe_pandas_import():
    try:
        import pandas as pd
        logger.info(f"Pandas successfully imported, version: {pd.__version__}")
        return pd, True
    except ImportError as e:
        logger.error(f"Pandas import failed: {str(e)}")
        # Create minimal pandas-like interface for basic functionality
        return create_minimal_pandas_interface(), False
    except Exception as e:
        logger.error(f"Unexpected error importing Pandas: {str(e)}")
        return create_minimal_pandas_interface(), False

def create_minimal_pandas_interface():
    """Create a minimal pandas-like interface for basic operations"""
    class MinimalDataFrame:
        def __init__(self, data=None):
            self.data = data or []
        
        def __len__(self):
            return len(self.data)
        
        def head(self, n=5):
            return self.data[:n]
    
    class MinimalPandas:
        DataFrame = MinimalDataFrame
    
    return MinimalPandas()

# Initialize at module level
np, NUMPY_AVAILABLE = safe_numpy_import()
pd, PANDAS_AVAILABLE = safe_pandas_import()
```

#### 3.2 Update Main Application
Modify `app.py` to use safe imports:

```python
# Replace the pandas import in app.py
# FROM: import pandas as pd
# TO: from utils.numpy_handler import pd, PANDAS_AVAILABLE
```

#### 3.3 Add Graceful Degradation
Add user-friendly messages when numpy/pandas features are unavailable:

```python
def display_dependency_status():
    """Display dependency status to users"""
    if not PANDAS_AVAILABLE:
        st.warning("⚠️ Advanced data processing unavailable. Basic functionality preserved.")
    
    if not NUMPY_AVAILABLE:
        st.info("ℹ️ Advanced image processing disabled. Using basic image handling.")
```

### Phase 4: Environment Reset Option
If all else fails, provide instructions for complete environment reset:

1. **Fork the repl** to create a clean copy
2. **Delete and recreate** the current repl
3. **Use Replit's package manager** instead of pip:
   ```bash
   upm add numpy==2.1.3
   uvm add pandas==2.2.3
   ```

## Implementation Priority

### High Priority (Fix Immediately)
1. Complete environment cleanup (Phase 1)
2. Fresh installation using multiple strategies (Phase 2)
3. Test application startup

### Medium Priority (Implement as Backup)
1. Enhanced fallback implementation (Phase 3)
2. Safe import handlers
3. Graceful degradation UI

### Low Priority (Last Resort)
1. Environment reset instructions (Phase 4)
2. Alternative package manager usage

## Testing Strategy

### 1. Verification Commands
After each fix attempt, run these tests:
```bash
# Test numpy import
python -c "import numpy as np; print(f'NumPy version: {np.__version__}')"

# Test pandas import
python -c "import pandas as pd; print(f'Pandas version: {pd.__version__}')"

# Test application startup
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

### 2. Functionality Tests
1. **Basic App Load**: Verify Streamlit interface loads
2. **Document Upload**: Test file upload functionality
3. **URL Processing**: Test URL extraction
4. **Image Gallery**: Verify image display works

## Expected Outcomes

### Best Case Scenario
- NumPy and pandas install cleanly
- Full application functionality restored
- All advanced features work

### Acceptable Scenario
- NumPy fails but pandas works with basic features
- Application runs with limited image processing
- Core functionality preserved

### Fallback Scenario
- Both numpy and pandas fail
- Application runs with minimal data processing
- Basic document processing still works

## Monitoring and Maintenance

### 1. Dependency Health Check
Add a system status page showing:
- NumPy availability and version
- Pandas availability and version
- Feature availability matrix

### 2. Proactive Error Handling
- Log all import attempts
- Monitor for recurring issues
- Provide user-friendly error messages

### 3. Alternative Dependencies
Consider lighter alternatives if issues persist:
- Use built-in CSV handling instead of pandas
- Use PIL/Pillow instead of numpy for images
- Implement basic data structures manually

## Conclusion

This comprehensive plan addresses the numpy import error from multiple angles:
1. **Immediate fix** through environment cleanup and reinstallation
2. **Resilient design** through fallback implementations
3. **User experience** through graceful degradation
4. **Long-term stability** through proper error handling

The layered approach ensures the application can function even if numpy/pandas issues persist, while providing multiple pathways to full functionality restoration.
