import requests
import os
import argparse
from pathlib import Path
from urllib.parse import urlparse
from tqdm import tqdm

def download_pdf(url, save_path=None, filename=None):
    """
    Download a PDF file from a URL, with or without .pdf extension.
    
    Args:
        url (str): The URL of the PDF file
        save_path (str): Directory to save the file (default: current directory)
        filename (str): Custom filename (default: extracted from URL)
    
    Returns:
        bool: True if download successful, False otherwise
    """
    
    try:
        # Ensure URL has proper scheme
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        # Set default save path
        if save_path is None:
            save_path = os.getcwd()
        
        # Create directory if it doesn't exist
        Path(save_path).mkdir(parents=True, exist_ok=True)
        
        # Download with timeout and headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()
        
        # Generate filename if not provided
        if filename is None:
            # Extract filename from URL
            parsed_url = urlparse(url)
            path = parsed_url.path
            filename = os.path.basename(path)
            
            # If no filename or just numbers, create one
            if not filename or filename.endswith('/'):
                filename = 'downloaded_pdf'
            
            # Add .pdf extension if not present
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
        
        # Full file path
        file_path = os.path.join(save_path, filename)
        
        # Get total file size
        total_size = int(response.headers.get('content-length', 0))
        
        # Download and save file with progress bar
        with open(file_path, 'wb') as f:
            with tqdm(total=total_size, unit='B', unit_scale=True, desc=filename, leave=True) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        print(f"✓ PDF downloaded successfully!")
        print(f"  URL: {url}")
        print(f"  Location: {file_path}")
        print(f"  Size: {os.path.getsize(file_path) / 1024:.2f} KB")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"✗ Download failed for {url}: {e}")
        return False
    except IOError as e:
        print(f"✗ File save error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Download one or multiple PDF files from URLs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
        # Download a single PDF
        python script.py --urls https://exampleurl
        
        # Download a single PDF to specific folder
        python script.py --urls https://exampleurl -s ./my_pdfs
        
        # Download multiple PDFs
        python script.py --urls https://exampleurl https://exampleurl2
        
        # Download multiple PDFs to specific folder
        python script.py --urls https://exampleurl https://exampleurl2 -s ./papers
        """
    )
    
    parser.add_argument(
        '--urls',
        nargs='+',
        required=True,
        help='One or more PDF URLs to download'
    )
    
    parser.add_argument(
        '-s', '--save-path',
        default=os.getcwd(),
        help='Directory to save PDFs (default: current directory)'
    )
    
    args = parser.parse_args()
    
    print(f"Saving PDFs to: {os.path.abspath(args.save_path)}\n")
    
    success_count = 0
    failed_count = 0
    
    # Download each URL
    for url in args.urls:
        if download_pdf(url, save_path=args.save_path):
            success_count += 1
        else:
            failed_count += 1
        print()  # Add blank line between downloads
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Download Summary:")
    print(f"  Successful: {success_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total: {len(args.urls)}")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
