#!/usr/bin/env python3
"""
Demo script for YouTube Download Tool

This script demonstrates the YouTube downloader tool functionality.
Run this to test the tool without using the full agent system.

Usage:
    python demo_youtube_download.py [--url URL] [--quality QUALITY]

Examples:
    # Download a video in medium quality (default)
    python demo_youtube_download.py --url "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    
    # Download in low quality
    python demo_youtube_download.py --url "https://youtu.be/jNQXAC9IVRw" --quality low
    
    # Extract audio only
    python demo_youtube_download.py --url "https://www.youtube.com/watch?v=jNQXAC9IVRw" --quality audio_only
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from icpy.agent.tools.youtube_download_tool import YouTubeDownloadTool, YT_DLP_AVAILABLE


async def demo_download(url: str, quality: str = 'medium'):
    """Demo the YouTube download tool"""
    
    if not YT_DLP_AVAILABLE:
        print("❌ yt-dlp is not installed. Please run: uv add yt-dlp")
        return
    
    print(f"\n{'='*70}")
    print("  YouTube Download Tool - Demo")
    print(f"{'='*70}\n")
    
    # Create tool instance
    tool = YouTubeDownloadTool()
    
    print(f"📹 URL: {url}")
    print(f"🎬 Quality: {quality}")
    print(f"{'='*70}\n")
    
    # Extract video ID (for display)
    video_id = tool._extract_video_id(url)
    if not video_id:
        print("❌ Invalid YouTube URL")
        return
    
    print(f"🔍 Video ID: {video_id}")
    print(f"\n⏳ Fetching video metadata...")
    
    # Get video info first
    success, metadata, error = await tool._get_video_info(url, video_id)
    
    if not success:
        print(f"❌ Failed to get video info: {error}")
        return
    
    print(f"\n📊 Video Information:")
    print(f"   Title: {metadata.get('title', 'Unknown')}")
    print(f"   Uploader: {metadata.get('uploader', 'Unknown')}")
    print(f"   Duration: {metadata.get('duration_string', 'Unknown')}")
    print(f"   Views: {metadata.get('view_count', 0):,}")
    
    # Confirm download
    print(f"\n{'='*70}")
    print("⚠️  This will download the video to your workspace/videos/ directory.")
    
    if quality == 'high':
        print("⚠️  High quality can be 50-200MB. Consider using 'medium' or 'low'.")
    
    response = input("\nProceed with download? [y/N]: ")
    
    if response.lower() != 'y':
        print("❌ Download cancelled.")
        return
    
    print("\n⏳ Starting download...")
    print(f"{'='*70}\n")
    
    # Execute download
    result = await tool.execute(url=url, quality=quality)
    
    if result.success:
        print(f"\n{'='*70}")
        print(f"✅ Download Complete!")
        print(f"{'='*70}")
        print(result.error)  # Contains success message
        print(f"\n📁 File details:")
        print(f"   Path: {result.data['file_path']}")
        print(f"   Size: {result.data['file_size_mb']} MB")
        print(f"   Format: {result.data['format']}")
        print(f"{'='*70}\n")
    else:
        print("\n❌ Download Failed!")
        print(f"{'='*70}")
        print(f"Error: {result.error}")
        print(f"{'='*70}\n")


async def demo_tool_info():
    """Display tool information"""
    tool = YouTubeDownloadTool()
    
    print(f"\n{'='*70}")
    print("  YouTube Download Tool - Information")
    print(f"{'='*70}\n")
    
    print(f"Tool Name: {tool.name}")
    print("\nDescription:")
    print(f"  {tool.description}\n")
    
    print("Parameters:")
    for param, details in tool.parameters['properties'].items():
        required = "✓" if param in tool.parameters.get('required', []) else " "
        print(f"  [{required}] {param}")
        print(f"      Type: {details.get('type', 'unknown')}")
        if 'enum' in details:
            print(f"      Options: {', '.join(details['enum'])}")
        desc_lines = details.get('description', '').split('\n')
        for line in desc_lines:
            if line.strip():
                print(f"      {line.strip()}")
        print()
    
    print("Quality Presets:")
    from icpy.agent.tools.youtube_download_tool import QUALITY_PRESETS
    for quality, preset in QUALITY_PRESETS.items():
        print(f"  • {quality}: {preset['description']}")
    
    print(f"\n{'='*70}\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="YouTube Download Tool Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        '--url',
        type=str,
        help='YouTube video URL to download'
    )
    
    parser.add_argument(
        '--quality',
        type=str,
        choices=['low', 'medium', 'high', 'audio_only'],
        default='medium',
        help='Download quality (default: medium)'
    )
    
    parser.add_argument(
        '--info',
        action='store_true',
        help='Show tool information and exit'
    )
    
    args = parser.parse_args()
    
    if args.info:
        asyncio.run(demo_tool_info())
        return
    
    if not args.url:
        parser.print_help()
        print("\n❌ Error: --url is required (or use --info to see tool details)\n")
        print("Example:")
        print("  python demo_youtube_download.py --url 'https://www.youtube.com/watch?v=jNQXAC9IVRw' --quality low")
        sys.exit(1)
    
    # Run demo
    asyncio.run(demo_download(args.url, args.quality))


if __name__ == '__main__':
    main()
