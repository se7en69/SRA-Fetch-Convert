import streamlit as st
import os
import subprocess
import time
import hashlib

# App Name and Description
st.sidebar.title("🧬 **SRA Fetch & Convert**")
st.sidebar.markdown(""" Welcome to **SRA Fetch & Convert**, a powerful tool to download and convert SRA data into FASTQ format effortlessly. Simply provide the SRA accession numbers, and let the tool handle the rest! """)

# Adding workflow for downloading and converting SRA data
st.title("🔧 **Workflow**")
st.image("workflow.png", use_container_width=True)

# Adding sra toolkit
os.system("setup.sh")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Get project directory
SRA_TOOLKIT_PATH = os.path.join(BASE_DIR, "sratoolkit/bin")  # Path to binaries
PREFETCH_PATH = os.path.join(SRA_TOOLKIT_PATH, "prefetch")  # No .exe
FASTERQ_DUMP_PATH = os.path.join(SRA_TOOLKIT_PATH, "fasterq-dump")  # No .exe

# Input for SRA accession numbers
st.sidebar.header("Input Options")
sra_accession = st.sidebar.text_input("Enter SRA Accession Number(s), separated by commas:")

# File uploader for multiple accession numbers
uploaded_file = st.sidebar.file_uploader("Or upload a file with accession numbers (one per line):", type=["txt"])

# Output directory selection
output_dir = st.sidebar.text_input("Enter output directory (default: 'sra_downloads'):", "sra_downloads")

# Checkbox for automatic FASTQ conversion
auto_convert = st.sidebar.checkbox("Automatically convert to FASTQ", value=True)

# Button to trigger download
if st.sidebar.button("Download SRA Data"):
    accession_list = []
    if sra_accession:
        accession_list = [acc.strip() for acc in sra_accession.split(",")]
    elif uploaded_file:
        accession_list = uploaded_file.read().decode("utf-8").splitlines()
    
    if not accession_list:
        st.warning("Please enter at least one SRA accession number or upload a file.")
    else:
        st.write(f"**Downloading data for:** {', '.join(accession_list)}")
        os.makedirs(output_dir, exist_ok=True)

        # Progress bar and status text
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Initialize download status summary
        download_summary = []

        # Function to update progress
        def update_progress(progress):
            progress_bar.progress(progress)
            time.sleep(0.1)  # Simulate delay for visual effect

        # Function to calculate MD5 checksum
        def calculate_md5(file_path):
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()

        # Download each accession
        for i, acc in enumerate(accession_list):
            st.write(f"**Processing accession:** {acc}")
            try:
                # Step 1: Use prefetch to download the SRA file
                status_text.text(f"Downloading {acc}...")
                prefetch_command = [PREFETCH_PATH, acc]

                # Check if the file already exists (partial download)
                sra_file_path = os.path.join(output_dir, f"{acc}.sra")
                if os.path.exists(sra_file_path):
                    st.write(f"Resuming download for {acc}...")
                
                # Run the actual prefetch command
                subprocess.run(prefetch_command, check=True)

                # Simulate progress while downloading
                for percent in range(0, 101, 10):
                    update_progress(percent / 100)
                    time.sleep(0.5)  # Simulate download time
                
                # Run the actual prefetch command
                subprocess.run(prefetch_command, check=True)
                
                # Step 2: Use fasterq-dump to convert to FASTQ (if enabled)
                if auto_convert:
                    status_text.text(f"Converting {acc} to FASTQ...")
                    fasterq_dump_command = [FASTERQ_DUMP_PATH, "--outdir", output_dir, acc]
                                        
                    # Simulate progress while converting
                    for percent in range(0, 101, 10):
                        update_progress(percent / 100)
                        time.sleep(0.5)  # Simulate conversion time
                    
                    # Run the actual fasterq-dump command
                    subprocess.run(fasterq_dump_command, check=True)
                
                # Get the output file path
                output_files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(acc)]
                output_files_str = ", ".join(output_files)
                
                # Calculate MD5 checksum for the first output file
                md5_checksum = calculate_md5(output_files[0]) if output_files else "N/A"
                
                # Add to download summary
                download_summary.append({
                    "Accession": acc,
                    "Status": "Success",
                    "Output File": output_files_str,
                    "MD5 Checksum": md5_checksum
                })
                
                st.success(f"**Successfully processed:** {acc}")
            except subprocess.CalledProcessError as e:
                # Add to download summary with failure status
                download_summary.append({
                    "Accession": acc,
                    "Status": "Failure",
                    "Output File": "N/A",
                    "MD5 Checksum": "N/A"
                })
                st.error(f"**Failed to process:** {acc} - {e}")
        
        # Final message
        progress_bar.progress(1.0)  # Fill the progress bar completely
        status_text.text("All downloads and conversions completed!")
        st.balloons()

        # Display download status summary
        st.subheader("Download Status Summary")
        st.table(download_summary)