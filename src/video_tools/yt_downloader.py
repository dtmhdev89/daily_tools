"""
YouTube Video Downloader
Download videos from YouTube at specific resolutions.

Requirements:
    pip install yt-dlp

Usage:
    python yt_downloader.py --url "https://youtube.com/watch?v=..." --resolution 1080p
    python yt_downloader.py -u "VIDEO_URL" -r 720p -o "my_video.mp4"
"""

import argparse
import os
import sys
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    print("Error: yt-dlp is not installed")
    print("Install it with: pip install yt-dlp")
    sys.exit(1)


def download_video(url, resolution="best", output_path=None, audio_only=False, list_formats=False):
    """
    Download a YouTube video at specified resolution.
    
    Args:
        url (str): YouTube video URL
        resolution (str): Desired resolution (e.g., '1080p', '720p', '480p', 'best')
        output_path (str): Output file path (optional)
        audio_only (bool): Download only audio
        list_formats (bool): List available formats without downloading
    
    Returns:
        bool: True if successful, False otherwise
    """
    
    # Configure download options
    ydl_opts = {
        'quiet': False,
        'no_warnings': False,
        'extract_flat': False,
    }
    
    # List available formats
    if list_formats:
        ydl_opts['listformats'] = True
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                print(f"\n{'='*60}")
                print(f"Available formats for: {url}")
                print(f"{'='*60}\n")
                ydl.download([url])
            return True
        except Exception as e:
            print(f"Error listing formats: {e}")
            return False
    
    # Audio only download
    if audio_only:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
        if output_path and not output_path.endswith('.mp3'):
            output_path = output_path.rsplit('.', 1)[0] + '.mp3'
    else:
        # Video download with specific resolution
        if resolution.lower() == 'best':
            format_selector = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
        else:
            # Extract resolution number (e.g., '1080' from '1080p')
            res_num = resolution.lower().replace('p', '')
            # Format selector: prefer mp4, try to get exact resolution with audio
            format_selector = f'bestvideo[height<={res_num}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res_num}][ext=mp4]/best'
        
        ydl_opts.update({
            'format': format_selector,
            'merge_output_format': 'mp4',
        })
    
    # Set output path
    if output_path:
        output_dir = os.path.dirname(output_path) or '.'
        output_filename = os.path.basename(output_path)
        # Remove extension for template
        output_template = os.path.join(output_dir, output_filename.rsplit('.', 1)[0])
        ydl_opts['outtmpl'] = output_template + '.%(ext)s'
    else:
        ydl_opts['outtmpl'] = '%(title)s.%(ext)s'
    
    # Download the video
    try:
        print(f"\n{'='*60}")
        print(f"Downloading video...")
        print(f"URL: {url}")
        print(f"Resolution: {resolution}")
        print(f"Audio only: {audio_only}")
        print(f"{'='*60}\n")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            info = ydl.extract_info(url, download=False)
            video_title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            
            print(f"Title: {video_title}")
            print(f"Duration: {duration // 60}:{duration % 60:02d}")
            print(f"\nStarting download...\n")
            
            # Download
            ydl.download([url])
            
        print(f"\n{'='*60}")
        print(f"✓ Download completed successfully!")
        print(f"{'='*60}\n")
        return True
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"✗ Error downloading video: {e}")
        print(f"{'='*60}\n")
        return False


def download_playlist(url, resolution="best", output_dir=None):
    """
    Download all videos from a YouTube playlist.
    
    Args:
        url (str): YouTube playlist URL
        resolution (str): Desired resolution
        output_dir (str): Output directory
    
    Returns:
        bool: True if successful
    """
    if resolution.lower() == 'best':
        format_selector = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    else:
        res_num = resolution.lower().replace('p', '')
        format_selector = f'bestvideo[height<={res_num}][ext=mp4]+bestaudio[ext=m4a]/best[height<={res_num}][ext=mp4]/best'
    
    ydl_opts = {
        'format': format_selector,
        'merge_output_format': 'mp4',
        'outtmpl': os.path.join(output_dir or '.', '%(playlist_index)s - %(title)s.%(ext)s'),
        'quiet': False,
    }
    
    try:
        print(f"\n{'='*60}")
        print(f"Downloading playlist...")
        print(f"URL: {url}")
        print(f"Resolution: {resolution}")
        print(f"Output directory: {output_dir or 'current directory'}")
        print(f"{'='*60}\n")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        print(f"\n{'='*60}")
        print(f"✓ Playlist download completed!")
        print(f"{'='*60}\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Error downloading playlist: {e}\n")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="YouTube Video Downloader - Download videos at specific resolutions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download at best quality
  python yt_downloader.py -u "https://youtube.com/watch?v=dQw4w9WgXcQ"
  
  # Download at 720p
  python yt_downloader.py -u "VIDEO_URL" -r 720p
  
  # Download with custom filename
  python yt_downloader.py -u "VIDEO_URL" -r 1080p -o "my_video.mp4"
  
  # Download audio only
  python yt_downloader.py -u "VIDEO_URL" --audio-only
  
  # List available formats
  python yt_downloader.py -u "VIDEO_URL" --list-formats
  
  # Download playlist
  python yt_downloader.py -u "PLAYLIST_URL" --playlist -r 720p

Common resolutions: 2160p (4K), 1440p (2K), 1080p (Full HD), 720p (HD), 480p, 360p
        """
    )
    
    parser.add_argument(
        "-u", "--url",
        type=str,
        required=True,
        help="YouTube video or playlist URL"
    )
    
    parser.add_argument(
        "-r", "--resolution",
        type=str,
        default="best",
        help="Video resolution (e.g., 1080p, 720p, 480p, 360p, or 'best')"
    )
    
    parser.add_argument(
        "-o", "--output",
        type=str,
        help="Output filename (optional)"
    )
    
    parser.add_argument(
        "--audio-only",
        action="store_true",
        help="Download audio only (MP3 format)"
    )
    
    parser.add_argument(
        "--list-formats",
        action="store_true",
        help="List all available formats without downloading"
    )
    
    parser.add_argument(
        "--playlist",
        action="store_true",
        help="Download entire playlist"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        help="Output directory for playlist downloads"
    )
    
    args = parser.parse_args()
    
    # Validate URL
    if not ("youtube.com" in args.url or "youtu.be" in args.url):
        print("Warning: URL doesn't appear to be a YouTube link")
    
    # Create output directory if specified
    if args.output_dir:
        os.makedirs(args.output_dir, exist_ok=True)
    
    # Download playlist or single video
    if args.playlist:
        success = download_playlist(
            url=args.url,
            resolution=args.resolution,
            output_dir=args.output_dir
        )
    else:
        success = download_video(
            url=args.url,
            resolution=args.resolution,
            output_path=args.output,
            audio_only=args.audio_only,
            list_formats=args.list_formats
        )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
