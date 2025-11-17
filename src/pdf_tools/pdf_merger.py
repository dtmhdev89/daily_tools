from PyPDF2._page import PageObject
import PyPDF2
import os
from pathlib import Path
import argparse

def is_page_blank(page, threshold=100):
    """
    Check if a PDF page is blank by analyzing text content.
    
    Args:
        page: PyPDF2 page object
        threshold (int): Minimum character count to consider page non-blank
    
    Returns:
        bool: True if page is blank, False otherwise
    """
    try:
        text = page.extract_text().strip()
        # Remove whitespace and check if meaningful content exists
        text_no_space = ''.join(text.split())
        return len(text_no_space) < threshold
    except:
        # If extraction fails, assume page is not blank to be safe
        return False


def remove_blank_pages_from_reader(reader, threshold=100):
    """
    Remove blank pages from a PDF reader and return a writer with clean pages.
    
    Args:
        reader: PyPDF2.PdfReader object
        threshold (int): Character threshold for blank detection
    
    Returns:
        tuple: (PdfWriter with clean pages, removed_count)
    """
    writer = PyPDF2.PdfWriter()
    removed_count = 0
    
    for i, page in enumerate(reader.pages):
        if is_page_blank(page, threshold):
            print(f"  - Removing blank page {i + 1}")
            removed_count += 1
        else:
            writer.add_page(page)
    
    return writer, removed_count


def merge_pdfs_remove_blanks(
    pdf_files,
    output_filename="merged_output.pdf", 
    remove_blanks=True,
    threshold=100
):
    """
    Merge multiple PDF files after removing blank pages.
    
    Args:
        pdf_files (list): List of PDF file paths in desired merge order
        output_filename (str): Name of the output merged PDF file
        remove_blanks (bool): Whether to remove blank pages before merging
        threshold (int): Character threshold for blank page detection
    
    Returns:
        str: Path to the merged PDF file or None if error
    """
    final_writer = PyPDF2.PdfWriter()
    total_removed = 0
    total_kept = 0
    
    try:
        print(f"{'='*60}")
        print(f"Starting PDF merge process...")
        print(f"Remove blanks: {remove_blanks}")
        print(f"Blank threshold: {threshold} characters")
        print(f"Total input files: {len(pdf_files)}")
        print(f"{'='*60}\n")
        
        # Debug: Show all input files
        print("Input files:")
        for i, pdf in enumerate(pdf_files, 1):
            print(f"  {i}. {pdf}")
        print()
        
        # Process each PDF file
        for idx, pdf_file in enumerate(pdf_files, 1):
            if not os.path.exists(pdf_file):
                print(f"Warning: File not found - {pdf_file}")
                continue
            
            if not pdf_file.lower().endswith('.pdf'):
                print(f"Warning: Not a PDF file - {pdf_file}")
                continue
            
            print(f"[{idx}/{len(pdf_files)}] Processing: {os.path.basename(pdf_file)}")
            
            # Read the PDF
            reader = PyPDF2.PdfReader(pdf_file)
            total_pages = len(reader.pages)
            print(f"  Total pages: {total_pages}")
            
            if remove_blanks:
                # Remove blank pages and get clean pages
                clean_writer, removed = remove_blank_pages_from_reader(reader, threshold)
                kept_pages = len(clean_writer.pages)
                
                # Debug: Show what's being added
                print(f"  → Adding {kept_pages} pages to final document")
                print(f"  → Current total pages before adding: {len(final_writer.pages)}")
                
                # Add clean pages to final writer
                for page_num, page in enumerate(clean_writer.pages, 1):
                    final_writer.add_page(page)
                    print(f"    Added page {page_num}/{kept_pages}")
                
                print(f"  → Current total pages after adding: {len(final_writer.pages)}")
                
                total_removed += removed
                total_kept += kept_pages
                print(f"  ✓ Kept {kept_pages} pages, removed {removed} blank pages\n")
            else:
                # Add all pages without checking for blanks
                for page in reader.pages:
                    final_writer.add_page(page)
                total_kept += total_pages
                print(f"  ✓ Added all {total_pages} pages\n")
        
        # Write the final merged PDF
        if len(final_writer.pages) > 0:
            with open(output_filename, 'wb') as f:
                final_writer.write(f)
            
            print(f"{'='*60}")
            print(f"✓ SUCCESS!")
            print(f"{'='*60}")
            print(f"Output file: {output_filename}")
            print(f"Total pages in merged PDF: {len(final_writer.pages)}")
            print(f"Total blank pages removed: {total_removed}")
            print(f"Total pages kept: {total_kept}")
            print(f"{'='*60}")
            
            return output_filename
        else:
            print("Error: No pages to merge")
            return None
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
        return None


def list_files_from_folder(folder_path):
    """Get sorted list of PDF files from a folder."""
    pdf_files = sorted(
        [
            os.path.join(folder_path, f)
            for f in os.listdir(folder_path)
            if f.lower().endswith('.pdf')
        ]
    )
    return pdf_files


# Example usage:
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF Merger")
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--folder-path",
        type=str,
        help="Folder contains pdf files"
    )
    input_group.add_argument(
        "--pdf-files",
        type=list,
        help="Ordered pdf files: file1.pdf file2.pdf"
    )

    parser.add_argument(
        "-o", "--output",
        type=str,
        default="merged_document.pdf"
        help="Output filename (default: merged_document.pdf)"
    )

    parser.add_argument(
        "--no-remove-blanks",
        action="store_true",
        help="Keep blank pages (don't remove them)"
    )

    parser.add_argument(
        "--threshold",
        type=int,
        default=100,
        help="Character threshold for blank page detection (default: 100)"
    )

    args = parser.parse_args()

    if args.folder_path:
        folder_path = Path(args.folder_path)
        if not folder_path.exists():
            print(f"Error: Folder not found: {folder_path}")
            exit(1)
        if not folder_path.is_dir():
            print(f"Error: Not a directory: {folder_path}")
            exit(1)
        
        pdf_list = list_files_from_folder(folder_path=str(folder_path))

        if not pdf_list:
            print(f"Error: No PDF files found in {folder_path}")
            exit(1)
        
        if not os.path.isabs(args.output):
            args.output = str(folder_path / args.output)

    elif args.pdf_files:
        pdf_list = args.pdf_files

        for pdf in pdf_list:
            if not os.path.exists(pdf):
                print(f"Error: File not found {pdf}")
                exit(1)
    
    print(f"Found {len(pdf_list)} PDF files:")
    for i, pdf in enumerate(pdf_list, 1):
        print(f"  {i}. {os.path.basename(pdf)}")
    print()
    
    # Merge PDFs with blank page removal
    merge_pdfs_remove_blanks(
        pdf_files=pdf_list,
        output_filename=str(folder_path / "merged_document.pdf"),
        remove_blanks=not args.no_remove_blanks,
        threshold=args.threshold
    )
