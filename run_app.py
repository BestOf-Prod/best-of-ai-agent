#!/usr/bin/env python3
"""
Wrapper script to run Streamlit app with proper environment setup for Replit
"""

import os
import sys

# Ensure we're not in a numpy source directory by changing the working directory if needed
if 'numpy' in os.getcwd().lower():
    print("WARNING: Current directory contains 'numpy' - this may cause import issues")

# Set environment variables to avoid numpy import issues
os.environ['PYTHONNOUSERSITE'] = '1'  # Avoid user site packages that might conflict

# Add current directory to path properly
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

print(f"Starting Streamlit app from directory: {current_dir}")
print(f"Python path: {sys.path[:3]}...")  # Show first 3 paths

try:
    # Test imports before starting Streamlit
    print("Testing imports...")
    import numpy
    print(f"✅ NumPy {numpy.__version__}")
    
    import pandas
    print(f"✅ Pandas {pandas.__version__}")
    
    import streamlit as st
    print("✅ Streamlit imported successfully")
    
    # Import our app module
    import app
    print("✅ App module imported successfully")
    
    print("\n🚀 All imports successful - starting Streamlit...")
    
    # Run the Streamlit app
    os.system("streamlit run app.py --server.port 8501 --server.address 0.0.0.0")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nTrying alternative solution...")
    
    # Alternative: Run from a temporary directory
    import tempfile
    import shutil
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        print(f"Copying app to temporary directory: {tmp_dir}")
        
        # Copy necessary files
        for item in ['app.py', 'extractors', 'utils', 'document_capsules', 'lapl_cookies.json']:
            src = os.path.join(current_dir, item)
            if os.path.exists(src):
                if os.path.isdir(src):
                    shutil.copytree(src, os.path.join(tmp_dir, item))
                else:
                    shutil.copy2(src, tmp_dir)
        
        # Change to temp directory and run
        os.chdir(tmp_dir)
        os.system("streamlit run app.py --server.port 8501 --server.address 0.0.0.0")

except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()