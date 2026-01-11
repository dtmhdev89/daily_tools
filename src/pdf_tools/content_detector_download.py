import os
import asyncio
import argparse
from pathlib import Path
from urllib.parse import urlparse, unquote
from datetime import datetime
from playwright.async_api import async_playwright
import requests

class NetworkPDFInterceptor:
    def __init__(self, download_folder="intercepted_pdfs"):
        """
        Initialize the network PDF interceptor.
        
        Args:
            download_folder (str): Folder to save intercepted PDFs
        """
        self.download_folder = download_folder
        self.intercepted_urls = []
        self.downloaded_files = []
        self._create_download_folder()
    
    def _create_download_folder(self):
        """Create download folder if it doesn't exist."""
        Path(self.download_folder).mkdir(parents=True, exist_ok=True)
        print(f"📁 Download folder: {os.path.abspath(self.download_folder)}")
    
    def get_filename_from_url(self, url, content_disposition=None):
        """
        Extract filename from URL or Content-Disposition header.
        
        Args:
            url (str): The URL
            content_disposition (str): Content-Disposition header value
            
        Returns:
            str: Filename for the PDF
        """
        filename = None
        
        # Try to get filename from Content-Disposition header
        if content_disposition and 'filename=' in content_disposition:
            filename = content_disposition.split('filename=')[1].strip('"\'')
        
        # If no filename from header, extract from URL
        if not filename:
            parsed_url = urlparse(url)
            filename = os.path.basename(unquote(parsed_url.path))
        
        # Ensure filename has .pdf extension
        if not filename or filename == '':
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f'intercepted_{timestamp}.pdf'
        elif not filename.lower().endswith('.pdf'):
            filename += '.pdf'
        
        return filename
    
    def download_pdf(self, url, headers=None):
        """
        Download PDF from intercepted URL.
        
        Args:
            url (str): URL of the PDF
            headers (dict): Optional headers to include in download request
            
        Returns:
            str: Path to downloaded file or None if failed
        """
        try:
            print(f"\n📥 Downloading PDF from: {url}")
            
            # Prepare headers
            request_headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            if headers:
                request_headers.update(headers)
            
            # Download the PDF
            response = requests.get(url, headers=request_headers, stream=True, timeout=30)
            response.raise_for_status()
            
            # Get filename
            content_disposition = response.headers.get('Content-Disposition')
            filename = self.get_filename_from_url(url, content_disposition)
            
            # Full path for saving
            filepath = os.path.join(self.download_folder, filename)
            
            # Handle duplicate filenames
            counter = 1
            original_filepath = filepath
            while os.path.exists(filepath):
                name, ext = os.path.splitext(original_filepath)
                filepath = f"{name}_{counter}{ext}"
                counter += 1
            
            # Save the PDF
            total_size = 0
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    total_size += len(chunk)
            
            size_mb = total_size / (1024 * 1024)
            print(f"✅ Downloaded: {filename} ({size_mb:.2f} MB)")
            print(f"   Saved to: {os.path.abspath(filepath)}")
            
            self.downloaded_files.append(filepath)
            return filepath
            
        except Exception as e:
            print(f"❌ Error downloading PDF: {e}")
            return None
    
    async def save_blob_as_pdf(self, page, blob_url, index=1):
        """
        Extract and save blob URL content as PDF.
        
        Args:
            page: Playwright page object
            blob_url (str): Blob URL to extract
            index (int): Index for filename
            
        Returns:
            str: Path to saved file or None
        """
        try:
            print(f"\n💾 Extracting blob data...")
            
            # Use JavaScript to fetch blob data and convert to base64
            blob_data = await page.evaluate(f"""
                async () => {{
                    const response = await fetch('{blob_url}');
                    const blob = await response.blob();
                    return new Promise((resolve) => {{
                        const reader = new FileReader();
                        reader.onloadend = () => resolve({{
                            data: reader.result.split(',')[1],
                            type: blob.type,
                            size: blob.size
                        }});
                        reader.readAsDataURL(blob);
                    }});
                }}
            """)
            
            if blob_data and blob_data['data']:
                # Generate filename
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f'blob_pdf_{timestamp}_{index}.pdf'
                filepath = os.path.join(self.download_folder, filename)
                
                # Decode base64 and save
                import base64
                pdf_bytes = base64.b64decode(blob_data['data'])
                
                with open(filepath, 'wb') as f:
                    f.write(pdf_bytes)
                
                size_mb = blob_data['size'] / (1024 * 1024)
                print(f"✅ Blob saved: {filename} ({size_mb:.2f} MB)")
                print(f"   Type: {blob_data['type']}")
                print(f"   Saved to: {os.path.abspath(filepath)}")
                
                self.downloaded_files.append(filepath)
                return filepath
            
        except Exception as e:
            print(f"❌ Error extracting blob: {e}")
        
        return None
    
    async def intercept_website(self, url, wait_time=10, headless=True):
        """
        Open a website and intercept all network requests to detect PDFs.
        
        Args:
            url (str): Website URL to visit
            wait_time (int): Time to wait for requests in seconds
            headless (bool): Run browser in headless mode
        """
        print(f"\n{'='*70}")
        print(f"🌐 Intercepting network requests from: {url}")
        print(f"{'='*70}\n")
        
        blob_urls = []
        
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            # Setup request interception
            async def handle_request(request):
                req_url = request.url
                
                # Detect blob URLs
                if req_url.startswith('blob:'):
                    print(f"🔵 Blob URL detected: {req_url}")
                    if req_url not in blob_urls:
                        blob_urls.append(req_url)
                else:
                    print(f"🔍 Request: {request.method} {req_url[:100]}...")
            
            async def handle_response(response):
                content_type = response.headers.get('content-type', '').lower()
                resp_url = response.url
                
                # Check if response is a PDF
                if 'application/pdf' in content_type:
                    print(f"\n{'🎯 PDF DETECTED!':-^70}")
                    print(f"   URL: {resp_url}")
                    print(f"   Content-Type: {content_type}")
                    print(f"   Status: {response.status}")
                    
                    if resp_url not in self.intercepted_urls:
                        self.intercepted_urls.append(resp_url)
                        
                        # Get request headers for download
                        headers = {}
                        if 'authorization' in response.request.headers:
                            headers['Authorization'] = response.request.headers['authorization']
                        if 'cookie' in response.request.headers:
                            headers['Cookie'] = response.request.headers['cookie']
                        
                        # Download the PDF
                        self.download_pdf(resp_url, headers)
                else:
                    # Show other requests (optional, for debugging)
                    if content_type:
                        print(f"   Type: {content_type.split(';')[0]}")
            
            # Attach listeners
            page.on('request', handle_request)
            page.on('response', handle_response)
            
            try:
                # Navigate to the website
                print(f"🚀 Loading website...\n")
                await page.goto(url, wait_until='networkidle', timeout=60000)
                
                print(f"\n⏳ Waiting {wait_time} seconds for additional requests...")
                print(f"   (The browser window will stay open - interact with the page if needed)\n")
                
                # Wait for the specified time to catch lazy-loaded requests
                await asyncio.sleep(wait_time)
                
                # Process any blob URLs found
                if blob_urls:
                    print(f"\n{'='*70}")
                    print(f"🔵 Processing {len(blob_urls)} blob URL(s)...")
                    print(f"{'='*70}")
                    
                    for i, blob_url in enumerate(blob_urls, 1):
                        await self.save_blob_as_pdf(page, blob_url, i)
                
            except Exception as e:
                print(f"❌ Error loading page: {e}")
            
            finally:
                await browser.close()
        
        # Summary
        print(f"\n{'='*70}")
        print(f"📊 SUMMARY")
        print(f"{'='*70}")
        print(f"PDFs detected: {len(self.intercepted_urls)}")
        print(f"PDFs downloaded: {len(self.downloaded_files)}")
        
        if self.intercepted_urls:
            print(f"\n📋 Intercepted PDF URLs:")
            for i, pdf_url in enumerate(self.intercepted_urls, 1):
                print(f"   {i}. {pdf_url}")
        
        if self.downloaded_files:
            print(f"\n📂 Downloaded files:")
            for i, filepath in enumerate(self.downloaded_files, 1):
                print(f"   {i}. {filepath}")
        
        print(f"{'='*70}\n")
        
        return self.downloaded_files


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Network PDF Interceptor - Automatically detect and download PDFs from websites',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python script.py --url https://example.com
  python script.py --url https://example.com --wait 30 --headless
  python script.py --url https://example.com --folder my_pdfs --wait 20
        """
    )
    
    parser.add_argument(
        '--url',
        type=str,
        required=True,
        help='Target website URL to monitor for PDFs'
    )
    
    parser.add_argument(
        '--folder',
        type=str,
        default='intercepted_pdfs',
        help='Folder to save downloaded PDFs (default: intercepted_pdfs)'
    )
    
    parser.add_argument(
        '--wait',
        type=int,
        default=15,
        help='Time to wait for requests in seconds (default: 15)'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (no UI)'
    )
    
    return parser.parse_args()


async def main():
    """Main function with command line argument support."""
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Validate URL
    if not args.url.startswith(('http://', 'https://')):
        print("❌ Error: URL must start with http:// or https://")
        return
    
    # Create interceptor instance
    interceptor = NetworkPDFInterceptor(download_folder=args.folder)
    
    print(f"🎯 Target URL: {args.url}")
    print(f"⏱️  Wait time: {args.wait} seconds")
    print(f"👁️  Headless mode: {args.headless}")
    print()
    
    # Start interception
    await interceptor.intercept_website(
        url=args.url,
        wait_time=args.wait,
        headless=args.headless
    )


# Run the interceptor
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════╗
║         Network PDF Interceptor & Auto-Downloader               ║
║                                                                  ║
║  This tool intercepts all network requests from a website and    ║
║  automatically downloads any PDFs detected (XHR, fetch, etc.)    ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())
