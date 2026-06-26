import os
import sys
import argparse
import subprocess

# Local path configuration
PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")

def generate_thumbnail(video_path: str, output_path: str):
    """
    Generates a highly-clickable, lightweight animated GIF thumbnail from the first 3 seconds
    of the finished outreach video, overlaying a play button in the center.
    """
    play_button = os.path.join(ASSETS_DIR, "play_button.png")
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Missing source video file at: {video_path}")
        
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    print(f"🖼️ Generating animated GIF thumbnail for {os.path.basename(video_path)}...")
    
    # If the user hasn't provided a custom play button, we will check if it exists in assets.
    # If it doesn't, we can render the GIF without the play button overlay to avoid crashing.
    has_play_button = os.path.exists(play_button)
    
    if has_play_button:
        # Scale to 480px width, set to 10 FPS, overlay play button in center, and apply optimized GIF palette.
        filter_str = (
            "[0:v]fps=10,scale=480:-1:flags=lanczos[v]; "
            "[v][1:v]overlay=(W-w)/2:(H-h)/2:shortest=1,split[a][b]; "
            "[a]palettegen=stats_mode=single[p]; "
            "[b][p]paletteuse=new=1"
        )
        cmd = [
            "ffmpeg", "-y",
            "-ss", "0.0",
            "-t", "3.0",
            "-i", video_path,
            "-i", play_button,
            "-filter_complex", filter_str,
            output_path
        ]
    else:
        print("⚠️ Warning: play_button.png not found in assets. Generating GIF without play button overlay.")
        filter_str = (
            "[0:v]fps=10,scale=480:-1:flags=lanczos,split[a][b]; "
            "[a]palettegen=stats_mode=single[p]; "
            "[b][p]paletteuse=new=1"
        )
        cmd = [
            "ffmpeg", "-y",
            "-ss", "0.0",
            "-t", "3.0",
            "-i", video_path,
            "-filter_complex", filter_str,
            output_path
        ]
        
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"✅ Animated GIF saved to {output_path} (Size: {os.path.getsize(output_path)/1024:.1f} KB)")
    except Exception as e:
        raise RuntimeError(f"FFmpeg GIF generation failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate animated GIF thumbnail with play button from MP4 video.")
    parser.add_argument("video_path", help="Path to the source outreach video")
    parser.add_argument("output_path", help="Destination path for the final GIF thumbnail")
    
    args = parser.parse_args()
    
    try:
        generate_thumbnail(args.video_path, args.output_path)
    except Exception as e:
        print(f"❌ Failed to generate thumbnail: {e}")
        sys.exit(1)
