import streamlit as st
import os
import subprocess
from pathlib import Path

def convert_to_icml(md_file, output_dir):
    """Convert a markdown file to .icml using Pandoc."""
    output_file = Path(output_dir) / f"{Path(md_file.name).stem}.icml"
    cmd = ["pandoc", "-s", "-f", "markdown", "-t", "icml", md_file.name, "-o", str(output_file)]
    subprocess.run(cmd, check=True)
    return output_file

def main():
    st.title("Markdown to ICML Converter")
    uploaded_files = st.file_uploader("Upload Markdown Files", type=["md"], accept_multiple_files=True)
    image_dir = st.file_uploader("Upload Images", type=["jpg", "png"], accept_multiple_files=True)
    
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    if image_dir:
        for img in image_dir:
            with open(output_dir / img.name, "wb") as f:
                f.write(img.read())
    
    if uploaded_files and st.button("Convert"):
        for md_file in uploaded_files:
            with open(md_file.name, "wb") as f:
                f.write(md_file.read())
            icml_file = convert_to_icml(md_file, output_dir)
            with open(icml_file, "rb") as f:
                st.download_button(
                    label=f"Download {icml_file.name}",
                    data=f,
                    file_name=icml_file.name,
                    mime="application/x-indesign"
                )
            os.remove(md_file.name)  # Clean up temporary markdown file

if __name__ == "__main__":
    main()