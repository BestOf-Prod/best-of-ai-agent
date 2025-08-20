#!/usr/bin/env python3
"""
Wrapper script to run Streamlit app with proper environment setup for Replit
"""

import os
import sys
import subprocess
import tempfile
import shutil

# Define current_dir at module level to avoid scope issues
current_dir = os.path.dirname(os.path.abspath(__file__))

def clear_python_cache():
    """Clear Python cache files that might cause import issues"""
    print("Clearing Python cache...")
    cache_dirs = ['__pycache__', '.pytest_cache']
    for root, dirs, files in os.walk(current_dir):
        for cache_dir in cache_dirs:
            if cache_dir in dirs:
                cache_path = os.path.join(root, cache_dir)
                try:
                    shutil.rmtree(cache_path)
                    print(f"Removed cache: {cache_path}")
                except Exception as e:
                    print(f"Could not remove cache {cache_path}: {e}")

def fix_numpy_environment():
    """Fix NumPy environment issues common in Replit"""
    print("Attempting NumPy fixes...")
    
    # Clear environment variables that might interfere
    env_vars_to_clear = ['PYTHONPATH']
    for var in env_vars_to_clear:
        if var in os.environ:
            print(f"Cleared environment variable: {var}")
            del os.environ[var]
    
    # Set environment variables to avoid numpy import issues
    os.environ['PYTHONNOUSERSITE'] = '1'
    os.environ['NUMPY_EXPERIMENTAL_ARRAY_FUNCTION'] = '0'
    
    clear_python_cache()
    
    # Try to force reinstall numpy if needed
    try:
        print("Force reinstalling NumPy...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--force-reinstall', '--no-cache-dir', 'numpy'], 
                      capture_output=True, check=False)
        print("NumPy fix attempts completed")
    except Exception as e:
        print(f"NumPy reinstall failed: {e}")

def install_dependencies():
    """Ensure all dependencies are installed"""
    print("Installing dependencies from pyproject.toml...")
    try:
        # Install using uv if available, otherwise pip
        if shutil.which('uv'):
            result = subprocess.run(['uv', 'pip', 'install', '-e', '.'], 
                                  cwd=current_dir, capture_output=True, text=True)
        else:
            result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-e', '.'], 
                                  cwd=current_dir, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Dependencies installed successfully")
        else:
            print(f"⚠️ Dependency installation had issues: {result.stderr}")
            # Try installing streamlit specifically
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'streamlit'], check=False)
    except Exception as e:
        print(f"❌ Failed to install dependencies: {e}")

# Ensure we're not in a numpy source directory
if 'numpy' in os.getcwd().lower():
    print("WARNING: Current directory contains 'numpy' - this may cause import issues")

# Install dependencies first
install_dependencies()

# Apply NumPy fixes
fix_numpy_environment()

# Clean Python path and add current directory properly
sys.path = [p for p in sys.path if 'numpy' not in p.lower() or 'site-packages' in p]
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

print(f"Starting Streamlit app from directory: {current_dir}")
print(f"Cleaned Python path: {sys.path[:3]}...")

try:
    # Test imports before starting Streamlit
    print("Testing imports...")
    
    try:
        import numpy
        print(f"✅ NumPy {numpy.__version__}")
    except ImportError as e:
        print(f"⚠️ NumPy import failed: {e}")
        print("Continuing without NumPy - some features may be limited")
    
    try:
        import pandas
        print(f"✅ Pandas {pandas.__version__}")
    except ImportError as e:
        print(f"⚠️ Pandas import failed: {e}")
        print("Continuing without Pandas - using fallback data handling")
    
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
    with tempfile.TemporaryDirectory() as tmp_dir:
        print(f"Copying app to temporary directory: {tmp_dir}")
        
        # Copy necessary files (current_dir is now defined at module level)
        files_to_copy = ['app.py', 'extractors', 'utils', 'document_capsules']
        optional_files = ['lapl_cookies.json', 'local_storage']
        
        for item in files_to_copy + optional_files:
            src = os.path.join(current_dir, item)
            if os.path.exists(src):
                try:
                    if os.path.isdir(src):
                        shutil.copytree(src, os.path.join(tmp_dir, item))
                    else:
                        shutil.copy2(src, tmp_dir)
                    print(f"Copied: {item}")
                except Exception as copy_error:
                    if item in files_to_copy:
                        print(f"❌ Failed to copy required file {item}: {copy_error}")
                        raise
                    else:
                        print(f"⚠️ Optional file {item} not copied: {copy_error}")
        
        # Change to temp directory and run
        original_dir = os.getcwd()
        try:
            os.chdir(tmp_dir)
            print(f"Changed to temporary directory: {tmp_dir}")
            os.system("streamlit run app.py --server.port 8501 --server.address 0.0.0.0")
        finally:
            os.chdir(original_dir)

except Exception as e:
    print(f"❌ Unexpected error: {e}")
    import traceback
    traceback.print_exc()