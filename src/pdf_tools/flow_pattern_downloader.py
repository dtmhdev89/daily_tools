import os
import re
import argparse
from pathlib import Path
from urllib.parse import urlparse
import requests
from tqdm import tqdm

class FlowPatternPDFDownloader:
    def __init__(self, save_path=None):
        """
        Initialize the downloader.
        
        Args:
            save_path (str): Directory where downloaded PDFs will be saved.
        """
        self.save_path = save_path or os.getcwd()
        self.session = requests.Session()
        
        # Configure standard headers to look like a real browser
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
        # Ensure save directory exists
        Path(self.save_path).mkdir(parents=True, exist_ok=True)

    def extract_config(self, main_url):
        """
        Fetch the HTML of the main page and extract the PDF Reader configuration.
        """
        print("🌐 Step 1: Initializing session & fetching viewer page...")
        try:
            res = self.session.get(main_url, timeout=30)
            res.raise_for_status()
        except requests.RequestException as e:
            print(f"❌ Failed to load viewer page: {e}")
            return None

        html = res.text

        # Extract pdfReaderConfig using regex
        pdf_id_match = re.search(r'pdfId:\s*(\d+)', html)
        total_pages_match = re.search(r'totalPages:\s*(\d+)', html)
        mode_match = re.search(r'mode:\s*"([^"]+)"', html)

        if not pdf_id_match or not total_pages_match:
            print("❌ Error: Could not extract PDF reader configuration from the page.")
            print("Please check if the URL is correct and public.")
            return None

        config = {
            'pdf_id': int(pdf_id_match.group(1)),
            'total_pages': int(total_pages_match.group(1)),
            'mode': mode_match.group(1) if mode_match else "standard"
        }
        
        print(f"✅ Configuration extracted:")
        print(f"   • PDF ID: {config['pdf_id']}")
        print(f"   • Total Pages: {config['total_pages']}")
        print(f"   • Reader Mode: {config['mode']}")
        return config

    def simulate_progress(self, pdf_id, total_pages):
        """
        Simulate page-by-page progress updates to the progress API.
        """
        print(f"\n📊 Step 2: Simulating page progress updates (1 to {total_pages})...")
        progress_url = f"https://tutorial.aivietnam.edu.vn/api/progress/{pdf_id}"
        
        # Track simulated progress bar
        with tqdm(total=total_pages, desc="Sending progress", unit="page") as pbar:
            for page in range(1, total_pages + 1):
                percent = round((page / total_pages) * 100)
                payload = {
                    "current_page": page,
                    "progress_percentage": percent
                }
                try:
                    res = self.session.post(progress_url, json=payload, timeout=10)
                    if res.status_code != 200:
                        print(f"\n⚠️ Page {page} progress update returned status {res.status_code}: {res.text.strip()}")
                except requests.RequestException as e:
                    print(f"\n⚠️ Connection error on page {page} progress: {e}")
                pbar.update(1)
        print("✅ Progress updates successfully sent to API.")

    def get_token(self, pdf_id, main_url):
        """
        Request PDF access token from the API.
        """
        token_url = f"https://tutorial.aivietnam.edu.vn/api/pdf/{pdf_id}/token"
        
        # Configure headers specifically for API calls
        self.session.headers.update({
            'Referer': main_url,
            'Origin': 'https://tutorial.aivietnam.edu.vn',
            'Accept': '*/*',
            'Content-Type': 'application/json',
        })
        
        try:
            res = self.session.post(token_url, json=None, timeout=15)
            if res.status_code == 200:
                data = res.json()
                token = data.get('token')
                if token:
                    return token
            print(f"❌ Token request failed: Status {res.status_code} - {res.text}")
        except Exception as e:
            print(f"❌ Error requesting token: {e}")
            
        return None

    def download_file(self, token, pdf_id, custom_filename=None):
        """
        Download the PDF using the retrieved access token.
        """
        serve_url = f"https://tutorial.aivietnam.edu.vn/api/pdf/serve/{token}?from=reader"
        print(f"\n📥 Step 3: Downloading PDF document...")
        
        try:
            response = self.session.get(serve_url, stream=True, timeout=60)
            response.raise_for_status()
            
            # Determine filename from headers or default
            filename = custom_filename
            if not filename:
                content_disposition = response.headers.get('Content-Disposition', '')
                if 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[1].strip('"\'')
                else:
                    filename = f"aivietnam_pdf_{pdf_id}.pdf"
            
            # Sanitize and build full path
            filename = os.path.basename(filename)
            file_path = os.path.join(self.save_path, filename)
            
            # Get total file size
            total_size = int(response.headers.get('content-length', 0))
            
            # Download chunks and track with progress bar
            with open(file_path, 'wb') as f:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc=filename, leave=True) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))
                            
            print(f"\n🎉 Download Complete!")
            print(f"   • Saved location: {os.path.abspath(file_path)}")
            print(f"   • File size: {os.path.getsize(file_path) / (1024 * 1024):.2f} MB")
            return True
            
        except Exception as e:
            print(f"❌ Error downloading file: {e}")
            return False

    def run(self, main_url, simulate_progress=False, filename=None):
        """
        Execute the entire download workflow.
        """
        print("="*65)
        print("     TUTORIAL PDF DOWNLOADER")
        print("="*65)
        print(f"Target URL: {main_url}\n")
        
        config = self.extract_config(main_url)
        if not config:
            return False

        # Attempt to get the token directly first
        print("\n🔑 Requesting token directly...")
        token = self.get_token(config['pdf_id'], main_url)
        
        if not token or simulate_progress:
            if not token:
                print("⚠️ Token request unsuccessful. Simulating progress to unlock document...")
            else:
                print("📊 Force-simulating progress updates as requested...")
            self.simulate_progress(config['pdf_id'], config['total_pages'])
            
            # Re-request token
            print("\n🔑 Requesting token after progress simulation...")
            token = self.get_token(config['pdf_id'], main_url)
            
        if not token:
            print("❌ Unable to retrieve access token even after sending progress updates.")
            return False
            
        print(f"✅ Token obtained successfully!")
        
        # Download the actual file
        return self.download_file(token, config['pdf_id'], filename)


def main():
    parser = argparse.ArgumentParser(
        description="Download PDF files from tutorial.aivietnam.edu.vn by simulating reading progress and obtaining access tokens.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download a PDF file (extracts name from website headers)
  python src/pdf_tools/aivietnam_downloader.py --url "https://tutorial.aivietnam.edu.vn/pdf/62?fbclid=..."
  
  # Download to a specific directory
  python src/pdf_tools/aivietnam_downloader.py --url "https://tutorial.aivietnam.edu.vn/pdf/62?fbclid=..." --save-path "./my_pdfs"
  
  # Force simulation of progress updates page-by-page
  python src/pdf_tools/aivietnam_downloader.py --url "https://tutorial.aivietnam.edu.vn/pdf/62?fbclid=..." --simulate-progress
        """
    )
    
    parser.add_argument(
        '--url',
        required=True,
        help='The URL of the PDF viewer page (e.g. https://tutorial.aivietnam.edu.vn/pdf/62)'
    )
    
    parser.add_argument(
        '-s', '--save-path',
        default=os.getcwd(),
        help='Directory to save downloaded PDF (default: current directory)'
    )
    
    parser.add_argument(
        '--simulate-progress',
        action='store_true',
        help='Force simulate reading progress updates page-by-page'
    )
    
    parser.add_argument(
        '-o', '--output',
        default=None,
        help='Custom filename for the saved PDF'
    )
    
    args = parser.parse_args()
    
    downloader = AIVietnamPDFDownloader(save_path=args.save_path)
    downloader.run(args.url, simulate_progress=args.simulate_progress, filename=args.output)


if __name__ == "__main__":
    main()
