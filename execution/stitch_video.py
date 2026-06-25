import os
import sys
import argparse
import subprocess

# Local path configuration
PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
ASSETS_DIR = os.path.join(PROJECT_DIR, "assets")

def stitch_video(screenshot_path: str, voice_path: str, output_path: str):
    """
    Stitches a personalized outreach video:
    1. Overlays ElevenLabs voice greeting onto the waving intro clip.
    2. Concatenates the voiced intro with the generic pitch body video.
    3. Overlays the resulting webcam video as a bubble on top of the website screenshot background.
    """
    intro_wave = os.path.join(ASSETS_DIR, "intro_wave.mp4")
    pitch_body = os.path.join(ASSETS_DIR, "pitch_body.mp4")
    circle_mask = os.path.join(ASSETS_DIR, "circle_mask_1024.png")
    
    # Validation checks
    for path, label in [(intro_wave, "Intro Waving Clip"), (pitch_body, "Pitch Body Video"), (circle_mask, "Circle Mask Image"), (screenshot_path, "Website Screenshot"), (voice_path, "Personalized Voice")]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing {label} file at: {path}")
            
    temp_dir = os.path.join(PROJECT_DIR, ".tmp")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Filenames for intermediates
    base_name = os.path.splitext(os.path.basename(output_path))[0]
    voiced_intro = os.path.join(temp_dir, f"{base_name}_intro_voiced.mp4")
    full_webcam = os.path.join(temp_dir, f"{base_name}_full_webcam.mp4")
    concat_list_file = os.path.join(temp_dir, f"{base_name}_concat_list.txt")
    
    print(f"🎬 Starting video stitching pipeline for {base_name}...")
    
    try:
        # Step 1: Swap the audio of the 2.5s waving intro clip with the ElevenLabs voice audio
        # Forces a fixed 2.5s duration and transcodes audio to aac
        print("🔗 Step 1: Merging voice greeting onto waving intro...")
        cmd_voice = [
            "ffmpeg", "-y",
            "-i", intro_wave,
            "-i", voice_path,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-t", "2.5",
            voiced_intro
        ]
        subprocess.run(cmd_voice, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # Step 2: Concatenate the voiced intro and the generic pitch body video losslessly
        print("🔗 Step 2: Concatenating intro and pitch body...")
        with open(concat_list_file, "w") as f:
            f.write(f"file '{voiced_intro.replace('\\', '/')}'\n")
            f.write(f"file '{pitch_body.replace('\\', '/')}'\n")
            
        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", concat_list_file,
            "-c", "copy",
            full_webcam
        ]
        subprocess.run(cmd_concat, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        
        # Step 3: Overlay the full webcam bubble video onto the website screenshot background
        print("🔗 Step 3: Rendering webcam bubble overlay onto screenshot background...")
        # Note: Using crf=26 and preset=ultrafast for optimized file size and speed.
        # Background is scaled to 1080p, and webcam is cropped to square, scaled to 280x280, masked, and overlaid.
        cmd_overlay = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", screenshot_path,
            "-i", full_webcam,
            "-i", circle_mask,
            "-filter_complex", (
                "[0:v]scale=trunc(iw/2)*2:trunc(ih/2)*2:in_range=full:out_range=tv:out_color_matrix=bt709,setsar=1[bg]; "
                "[1:v]crop='min(iw,ih)':'min(iw,ih)',scale=280:280:flags=lanczos,format=yuva420p[bub]; "
                "[2:v]scale=280:280:flags=bicubic,format=gray[mask]; "
                "[bub][mask]alphamerge[bub_m]; "
                "[bg][bub_m]overlay=30:H-h-80:shortest=1[outv]"
            ),
            "-map", "[outv]", "-map", "1:a?",
            "-c:v", "libx264", "-crf", "26", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
            "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
            "-c:a", "copy",
            output_path
        ]
        subprocess.run(cmd_overlay, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print(f"✅ Stitched video successfully created: {output_path}")
        
    finally:
        # Cleanup intermediate temp files
        for f in [voiced_intro, full_webcam, concat_list_file]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                except:
                    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stitch personalized outreach video using FFmpeg.")
    parser.add_argument("screenshot_path", help="Path to the website screenshot")
    parser.add_argument("voice_path", help="Path to the personalized voice greeting")
    parser.add_argument("output_path", help="Destination path for the final MP4 video")
    
    args = parser.parse_args()
    
    try:
        stitch_video(args.screenshot_path, args.voice_path, args.output_path)
    except Exception as e:
        print(f"❌ Failed to stitch video: {e}")
        sys.exit(1)
