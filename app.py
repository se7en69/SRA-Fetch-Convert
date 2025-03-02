import streamlit as st
import os
import subprocess
import time
import hashlib
import logging
import shutil
import gzip
from Bio import Entrez

# Configure logging
logging.basicConfig(
    filename='sra_fetch.log',  # Log file name
    level=logging.INFO,        # Log level (INFO, WARNING, ERROR, etc.)
    format='%(asctime)s - %(levelname)s - %(message)s'  # Log format
)

# Set your email for NCBI API (required by NCBI)
Entrez.email = "hanzo7n@gmail.com"  # Replace with your email

# App Name and Description
st.sidebar.title("🧬 **SRA Fetch & Convert**")
st.sidebar.markdown(""" Welcome to **SRA Fetch & Convert**, a powerful tool to download and convert SRA data into FASTQ format effortlessly. Simply provide the SRA accession numbers, and let the tool handle the rest! """)

# Adding workflow for downloading and converting SRA data
st.title("🔧 **Workflow**")
st.image("workflow.png", use_container_width=True)

# Configuration Section in Sidebar
st.sidebar.header("Configuration")

# Allow users to configure paths to SRA Toolkit executables
sra_toolkit_path = st.sidebar.text_input(
    "Path to SRA Toolkit Bin Directory (e.g., /path/to/sratoolkit/bin):",
    r"C:\Program Files\NCBI\sratoolkit.3.2.0-win64\bin"  # Default path
)

# Allow users to customize prefetch and fasterq-dump commands
prefetch_options = st.sidebar.text_input(
    "Additional Options for prefetch (e.g., --max-size 20G):",
    ""
)

fasterq_dump_options = st.sidebar.text_input(
    "Additional Options for fasterq-dump (e.g., --split-files):",
    ""
)

# Input for SRA accession numbers
st.sidebar.header("Input Options")
sra_accession = st.sidebar.text_input("Enter SRA Accession Number(s), separated by commas:")

# File uploader for multiple accession numbers
uploaded_file = st.sidebar.file_uploader("Or upload a file with accession numbers (one per line):", type=["txt"])

# Output directory selection
output_dir = st.sidebar.text_input("Enter output directory (default: 'sra_downloads'):", "sra_downloads")

# Checkbox for automatic FASTQ conversion
auto_convert = st.sidebar.checkbox("Automatically convert to FASTQ", value=True)

# Checkbox for file compression
compress_files = st.sidebar.checkbox("Compress FASTQ files using gzip", value=True)

# Function to fetch metadata for a given SRA accession
def fetch_metadata(accession):
    try:
        # Fetch metadata from NCBI SRA database
        handle = Entrez.esearch(db="sra", term=accession)
        record = Entrez.read(handle)
        handle.close()

        if not record["IdList"]:
            return {"Accession": accession, "Metadata": "No metadata found"}

        sra_id = record["IdList"][0]
        handle = Entrez.efetch(db="sra", id=sra_id, rettype="docsum", retmode="xml")
        metadata = handle.read()
        handle.close()

        return {"Accession": accession, "Metadata": metadata}
    except Exception as e:
        return {"Accession": accession, "Metadata": f"Error fetching metadata: {str(e)}"}

# Function to calculate MD5 checksum
def calculate_md5(file_path):
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

# Function to check disk space
def check_disk_space(required_space_gb):
    total, used, free = shutil.disk_usage(output_dir)
    free_gb = free // (2**30)  # Convert bytes to GB
    if free_gb < required_space_gb:
        raise RuntimeError(f"Insufficient disk space. Required: {required_space_gb} GB, Available: {free_gb} GB")

# Function to validate accession numbers
def validate_accession(acc):
    if not acc.startswith(("SRR", "ERR", "DRR")):  # Basic validation for SRA accession numbers
        raise ValueError(f"Invalid accession number: {acc}. Must start with SRR, ERR, or DRR.")

# Function to compress a file using gzip
def compress_file(file_path):
    compressed_file_path = file_path + ".gz"
    with open(file_path, 'rb') as f_in:
        with gzip.open(compressed_file_path, 'wb') as f_out:
            f_out.writelines(f_in)
    os.remove(file_path)  # Remove the original uncompressed file
    return compressed_file_path

# Function to process a single accession
def process_accession(acc):
    try:
        # Validate accession number
        validate_accession(acc)
        
        # Create a subdirectory for the accession
        acc_output_dir = os.path.join(output_dir, acc)
        os.makedirs(acc_output_dir, exist_ok=True)
        
        # Step 1: Use prefetch to download the SRA file
        logging.info(f"Downloading {acc}...")
        prefetch_command = [os.path.join(sra_toolkit_path, "prefetch.exe"), acc]
        if prefetch_options:
            prefetch_command.extend(prefetch_options.split())
        
        # Check if the file already exists (partial download)
        sra_file_path = os.path.join(acc_output_dir, f"{acc}.sra")
        if os.path.exists(sra_file_path):
            logging.info(f"Resuming download for {acc}...")
        
        # Run the prefetch command
        subprocess.run(prefetch_command, check=True)
        
        # Step 2: Use fasterq-dump to convert to FASTQ (if enabled)
        if auto_convert:
            logging.info(f"Converting {acc} to FASTQ...")
            fasterq_dump_command = [os.path.join(sra_toolkit_path, "fasterq-dump.exe"), "--outdir", acc_output_dir, acc]
            if fasterq_dump_options:
                fasterq_dump_command.extend(fasterq_dump_options.split())
            subprocess.run(fasterq_dump_command, check=True)
        
        # Get the output file paths
        output_files = [os.path.join(acc_output_dir, f) for f in os.listdir(acc_output_dir) if f.startswith(acc)]
        
        # Compress FASTQ files if enabled
        if auto_convert and compress_files:
            for file_path in output_files:
                if file_path.endswith(".fastq"):
                    compressed_file_path = compress_file(file_path)
                    output_files.remove(file_path)
                    output_files.append(compressed_file_path)
        
        output_files_str = ", ".join(output_files)
        
        # Calculate MD5 checksum for the first output file
        md5_checksum = calculate_md5(output_files[0]) if output_files else "N/A"
        
        return {
            "Accession": acc,
            "Status": "Success",
            "Output File": output_files_str,
            "MD5 Checksum": md5_checksum
        }
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to process {acc}: {e}")
        return {
            "Accession": acc,
            "Status": "Failure",
            "Output File": "N/A",
            "MD5 Checksum": "N/A",
            "Error": str(e)
        }
    except Exception as e:
        logging.error(f"Unexpected error processing {acc}: {e}")
        return {
            "Accession": acc,
            "Status": "Failure",
            "Output File": "N/A",
            "MD5 Checksum": "N/A",
            "Error": str(e)
        }

# Button to trigger metadata fetching
if st.sidebar.button("Fetch Metadata"):
    accession_list = []
    if sra_accession:
        accession_list = [acc.strip() for acc in sra_accession.split(",")]
    elif uploaded_file:
        accession_list = uploaded_file.read().decode("utf-8").splitlines()
    
    if not accession_list:
        st.warning("Please enter at least one SRA accession number or upload a file.")
    else:
        st.write(f"**Fetching metadata for:** {', '.join(accession_list)}")
        
        # Fetch metadata for each accession
        metadata_results = []
        for acc in accession_list:
            metadata = fetch_metadata(acc)
            metadata_results.append(metadata)
        
        # Display metadata results
        st.subheader("Metadata Results")
        for result in metadata_results:
            st.write(f"**Accession:** {result['Accession']}")
            st.write(f"**Metadata:**")
            st.code(result["Metadata"], language="xml")

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
        
        # Check disk space (assuming 10 GB is required)
        try:
            check_disk_space(10)
        except RuntimeError as e:
            st.error(str(e))
            logging.error(str(e))
            st.stop()
        
        # Progress bar and status text
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Initialize download status summary
        download_summary = []
        
        # Process each accession
        for i, acc in enumerate(accession_list):
            st.write(f"**Processing accession:** {acc}")
            result = process_accession(acc)
            download_summary.append(result)
            
            # Update progress bar
            progress = (i + 1) / len(accession_list)
            progress_bar.progress(progress)
            time.sleep(0.1)  # Simulate delay for visual effect
        
        # Final message
        progress_bar.progress(1.0)
        status_text.text("All downloads and conversions completed!")
        st.balloons()
        
        # Display download status summary
        st.subheader("Download Status Summary")
        st.table(download_summary)