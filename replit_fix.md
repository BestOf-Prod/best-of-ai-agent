# Replit NumPy Import Fix

## The Problem
You're getting this error:
```
ImportError: Unable to import required dependencies: numpy: Error importing numpy: you should not try to import numpy from its source directory
```

## Quick Solutions (try in order):

### 1. **Restart Replit Environment** (Most Common Fix)
In the Replit Shell, run:
```bash
kill 1
```
Then restart your app.

### 2. **Use the Wrapper Script**
Instead of running `app.py` directly, use:
```bash
python run_app.py
```

### 3. **Clear Python Cache**
In the Shell:
```bash
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
python -c "import sys; print('Cleared cache')"
```

### 4. **Alternative Streamlit Command**
```bash
cd /tmp
cp -r /home/runner/workspace/* .
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

## Why This Happens
- Replit sometimes has cached Python modules that conflict
- The working directory might contain cached numpy files
- Environment variables might be set incorrectly

## Prevention
- Use the `run_app.py` script provided
- Avoid creating files named `numpy.py` or directories named `numpy`
- Restart the Replit environment periodically