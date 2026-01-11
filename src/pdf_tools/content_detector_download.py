import os
import asyncio
import argparse
import base64
import json
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
        self.blob_urls = []
        self.downloaded_files = []
        self.pdf_links_file = None
        self._create_download_folder()
    
    def _create_download_folder(self):
        """Create download folder if it doesn't exist."""
        Path(self.download_folder).mkdir(parents=True, exist_ok=True)
        print(f"📁 Download folder: {os.path.abspath(self.download_folder)}")
        
        # Create links file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.pdf_links_file = os.path.join(self.download_folder, f"pdf_links_{timestamp}.txt")
    
    def save_pdf_link(self, url, source_type="network"):
        """
        Save PDF link to file.
        
        Args:
            url (str): PDF URL
            source_type (str): Type of source (network, blob, etc.)
        """
        with open(self.pdf_links_file, 'a', encoding='utf-8') as f:
            f.write(f"[{source_type}] {url}\n")
    
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
    
    async def auto_navigate_pagination(self, page, max_pages=10, navigation_method='auto'):
        """
        Automatically navigate through pagination to collect PDF links.
        
        Args:
            page: Playwright page object
            max_pages (int): Maximum number of pages to navigate
            navigation_method (str): 'auto', 'next_button', 'page_numbers', 'arrows', 'keyboard'
            
        Returns:
            int: Number of pages navigated
        """
        print(f"\n{'='*70}")
        print(f"📄 Starting pagination navigation (max {max_pages} pages)...")
        print(f"   Method: {navigation_method}")
        print(f"{'='*70}\n")
        
        pages_visited = 1
        
        for page_num in range(2, max_pages + 1):
            await asyncio.sleep(3)  # Wait for content to load
            
            try:
                navigated = False
                current_url = page.url
                
                # Method 1: Try "Next" button
                if navigation_method in ['auto', 'next_button']:
                    next_selectors = [
                        'button:has-text("Next")',
                        'a:has-text("Next")',
                        'button:has-text("next")',
                        'a:has-text("next")',
                        'button:has-text(">")',
                        'a:has-text(">")',
                        '[aria-label="Next"]',
                        '[aria-label="next page"]',
                        '[aria-label="Go to next page"]',
                        '.next-page',
                        '.pagination-next',
                        'button[class*="next"]',
                        'a[class*="next"]',
                        'li.next > a',
                        'li.next > button'
                    ]
                    
                    for selector in next_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element:
                                is_disabled = await element.get_attribute('disabled')
                                aria_disabled = await element.get_attribute('aria-disabled')
                                class_attr = await element.get_attribute('class') or ''
                                
                                if not is_disabled and aria_disabled != 'true' and 'disabled' not in class_attr.lower():
                                    print(f"🔽 Clicking Next button with selector: {selector}")
                                    await element.click()
                                    await page.wait_for_timeout(2000)
                                    
                                    # Check if URL changed or content loaded
                                    new_url = page.url
                                    if new_url != current_url:
                                        await page.wait_for_load_state('networkidle', timeout=10000)
                                    
                                    navigated = True
                                    break
                        except Exception as e:
                            print(f"   Failed with {selector}: {str(e)[:50]}")
                            continue
                
                # Method 2: Try page numbers
                if not navigated and navigation_method in ['auto', 'page_numbers']:
                    page_selectors = [
                        f'a:has-text("{page_num}")',
                        f'button:has-text("{page_num}")',
                        f'[data-page="{page_num}"]',
                        f'.page-link:has-text("{page_num}")',
                        f'a.page-number:has-text("{page_num}")',
                        f'li:has-text("{page_num}") > a',
                        f'li:has-text("{page_num}") > button'
                    ]
                    
                    for selector in page_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element:
                                print(f"🔢 Clicking page number {page_num} with selector: {selector}")
                                await element.click()
                                await page.wait_for_timeout(2000)
                                
                                new_url = page.url
                                if new_url != current_url:
                                    await page.wait_for_load_state('networkidle', timeout=10000)
                                
                                navigated = True
                                break
                        except Exception as e:
                            print(f"   Failed with {selector}: {str(e)[:50]}")
                            continue
                
                # Method 3: Try arrow/chevron icons
                if not navigated and navigation_method in ['auto', 'arrows']:
                    arrow_selectors = [
                        '[aria-label="Next page"]',
                        'button[class*="arrow-right"]',
                        'button[class*="chevron-right"]',
                        'a[class*="arrow-right"]',
                        'a[class*="chevron-right"]',
                        '.arrow-right',
                        '.chevron-right',
                        'svg[class*="arrow-right"]',
                        'i[class*="arrow-right"]',
                        'i.fa-arrow-right',
                        'i.fa-chevron-right'
                    ]
                    
                    for selector in arrow_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element:
                                print(f"➡️ Clicking arrow with selector: {selector}")
                                await element.click()
                                await page.wait_for_timeout(2000)
                                
                                new_url = page.url
                                if new_url != current_url:
                                    await page.wait_for_load_state('networkidle', timeout=10000)
                                
                                navigated = True
                                break
                        except Exception as e:
                            print(f"   Failed with {selector}: {str(e)[:50]}")
                            continue
                
                # Method 4: Try keyboard navigation (Arrow keys or Page Down)
                if not navigated and navigation_method in ['auto', 'keyboard']:
                    try:
                        print(f"⌨️ Trying keyboard navigation (Arrow Right)...")
                        await page.keyboard.press('ArrowRight')
                        await page.wait_for_timeout(2000)
                        
                        new_url = page.url
                        if new_url != current_url:
                            await page.wait_for_load_state('networkidle', timeout=10000)
                            navigated = True
                    except Exception as e:
                        print(f"   Keyboard navigation failed: {str(e)[:50]}")
                
                if navigated:
                    pages_visited += 1
                    print(f"✅ Successfully navigated to page {page_num}")
                    print(f"   Current URL: {page.url}\n")
                else:
                    print(f"⚠️ Could not find navigation element. Stopping at page {pages_visited}")
                    print(f"   You may need to specify a custom selector or use manual navigation\n")
                    break
                    
            except Exception as e:
                print(f"❌ Navigation error on page {page_num}: {e}")
                break
        
        print(f"\n✅ Pagination complete: Visited {pages_visited} pages\n")
        return pages_visited
    
    async def intercept_website(self, url, wait_time=10, headless=True, 
                                auto_paginate=False, max_pages=10, 
                                download_now=True, navigation_method='auto'):
        """
        Open a website and intercept all network requests to detect PDFs.
        
        Args:
            url (str): Website URL to visit
            wait_time (int): Time to wait for requests in seconds
            headless (bool): Run browser in headless mode
            auto_paginate (bool): Automatically navigate pagination
            max_pages (int): Maximum pages to navigate
            download_now (bool): Download PDFs immediately or just save links
            navigation_method (str): Method for pagination navigation
        """
        print(f"\n{'='*70}")
        print(f"🌐 Intercepting network requests from: {url}")
        print(f"📝 PDF links will be saved to: {self.pdf_links_file}")
        print(f"{'='*70}\n")
        
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
                    if req_url not in self.blob_urls:
                        self.blob_urls.append(req_url)
                        self.save_pdf_link(req_url, "blob")
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
                        self.save_pdf_link(resp_url, "network")
                        
                        if download_now:
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
                
                print(f"\n⏳ Waiting {wait_time} seconds for initial requests...")
                await asyncio.sleep(wait_time)
                
                # Auto-navigate pagination if enabled
                if auto_paginate:
                    await self.auto_navigate_pagination(page, max_pages, navigation_method)
                    print(f"\n⏳ Waiting {wait_time} seconds after pagination...")
                    await asyncio.sleep(wait_time)
                
                # Process any blob URLs found
                if self.blob_urls and download_now:
                    print(f"\n{'='*70}")
                    print(f"🔵 Processing {len(self.blob_urls)} blob URL(s)...")
                    print(f"{'='*70}")
                    
                    for i, blob_url in enumerate(self.blob_urls, 1):
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
        print(f"Blob URLs detected: {len(self.blob_urls)}")
        print(f"PDFs downloaded: {len(self.downloaded_files)}")
        print(f"Links saved to: {self.pdf_links_file}")
        
        if self.intercepted_urls or self.blob_urls:
            print(f"\n📋 All PDF links:")
            for i, pdf_url in enumerate(self.intercepted_urls + self.blob_urls, 1):
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
  # Basic usage
  python script.py --url "https://example.com"
  
  # With pagination (auto-navigate up to 5 pages)
  python script.py --url "https://example.com" --paginate --max-pages 5
  
  # Just collect links, don't download
  python script.py --url "https://example.com" --paginate --no-download
  
  # Full control
  python script.py --url "https://example.com" --folder my_pdfs --wait 20 --paginate --max-pages 10 --headless
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
    
    parser.add_argument(
        '--paginate',
        action='store_true',
        help='Automatically navigate through pagination'
    )
    
    parser.add_argument(
        '--max-pages',
        type=int,
        default=10,
        help='Maximum pages to navigate (default: 10)'
    )
    
    parser.add_argument(
        '--no-download',
        action='store_true',
        help='Only collect PDF links, do not download them'
    )
    
    parser.add_argument(
        '--nav-method',
        type=str,
        choices=['auto', 'next_button', 'page_numbers', 'arrows', 'keyboard'],
        default='auto',
        help='Navigation method for pagination (default: auto)'
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
    print(f"📄 Auto-paginate: {args.paginate}")
    if args.paginate:
        print(f"📊 Max pages: {args.max_pages}")
        print(f"🔄 Navigation method: {args.nav_method}")
    print(f"💾 Download now: {not args.no_download}")
    print()
    
    # Start interception
    await interceptor.intercept_website(
        url=args.url,
        wait_time=args.wait,
        headless=args.headless,
        auto_paginate=args.paginate,
        max_pages=args.max_pages,
        download_now=not args.no_download,
        navigation_method=args.nav_method
    )


# Run the interceptor
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════════╗
║    Advanced Network PDF Interceptor & Auto-Downloader           ║
║                                                                  ║
║  Features:                                                       ║
║  • Intercepts all network requests (XHR, fetch, etc.)            ║
║  • Detects blob URLs and extracts PDF content                   ║
║  • Auto-navigates pagination to collect all PDFs                ║
║  • Saves all PDF links to a text file                           ║
║  • Downloads PDFs automatically (optional)                       ║
╚══════════════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())
