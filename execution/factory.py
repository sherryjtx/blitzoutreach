import os
import sys
import datetime
import sqlite3
import argparse
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv

# Ensure workspace root is in python path
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, WORKSPACE_DIR)

# Import local modules
from capture_website import capture_website
from generate_voice import generate_voice
from stitch_video import stitch_video
from generate_thumbnail import generate_thumbnail
from upload_to_oci import upload_to_oci
import sheet_sync

# Load environment variables
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_DIR = os.path.dirname(PROJECT_DIR)
load_dotenv(dotenv_path=os.path.join(WORKSPACE_DIR, ".env"))

LANDING_PAGE_DOMAIN = os.getenv("LANDING_PAGE_DOMAIN", "watch.sherryautomates.com")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
OCI_NAMESPACE = os.getenv("OCI_NAMESPACE")

# DB path for FastAPI portal registry
def is_mock_mode():
    """Returns True if local configurations are using default templates (mock mode)."""
    return (
        not ELEVENLABS_API_KEY 
        or ELEVENLABS_API_KEY == "your_elevenlabs_api_key_here"
        or not OCI_NAMESPACE
        or OCI_NAMESPACE == "your_oci_object_storage_namespace_here"
    )

def register_lead_in_portal(video_id: str, name: str, company: str, video_url: str, logo_url: str, row_num: int):
    """Registers the generated video details inside Supabase for FastAPI to serve."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not url or not key:
        print("⚠️ Supabase credentials not found in env. Skipping registration.")
        return
        
    try:
        from supabase import create_client
        supabase = create_client(url, key)
        
        data = {
            "video_id": video_id,
            "name": name,
            "company": company,
            "video_url": video_url,
            "company_logo": logo_url,
            "row_num": row_num
        }
        
        # Upsert in Supabase
        supabase.table("leads").upsert(data, on_conflict="video_id").execute()
        print(f"✅ Lead '{name}' registered in Supabase portal under ID: {video_id}")
    except Exception as e:
        print(f"❌ Failed to register lead in Supabase: {e}")

def process_lead(lead: dict, paths: dict, today: str, mock: bool):
    """Processes a single lead row end-to-end in a parallel worker thread."""
    row_num = lead["row"]
    fname = lead["first_name"]
    lname = lead["last_name"]
    email = lead["email"]
    company = lead["company"]
    website = lead["website"]
    
    # Safe checks
    if not fname or not email:
        print(f"⚠️ Row {row_num}: Skipping due to missing Name or Email.")
        return False
        
    # Resume Guard: Skip if sheet already has a landing page URL
    if lead.get("existing_landing_page") and lead.get("existing_landing_page").startswith("http"):
        print(f"⏩ Row {row_num}: Skipping (already stitched: {lead['existing_landing_page']})")
        return True
        
    # Sanitize and truncate filename and ID to prevent Windows long path limits
    clean_fname = "".join(c for c in fname if c.isalnum())
    clean_lname = "".join(c for c in lname if c.isalnum())
    clean_company = "".join(c for c in company if c.isalnum())
    
    safe_name = f"{clean_fname}_{clean_lname}"
    if len(safe_name) > 60:
        safe_name = safe_name[:60]
        
    video_id = f"{clean_fname.lower()}_{clean_lname.lower()}_{clean_company.lower()}"
    if len(video_id) > 80:
        video_id = video_id[:80]
    
    # Path settings
    ss_path = os.path.join(paths["ss"], f"{safe_name}.webm")
    voice_path = os.path.join(paths["voice"], f"{safe_name}_voice.mp3")
    video_path = os.path.join(paths["video"], f"{safe_name}_outreach.mp4")
    gif_path = os.path.join(paths["gif"], f"{safe_name}_preview.gif")
    
    # Determine website target URL
    target_url = website if (website and website.startswith("http")) else f"https://{website}" if website else "https://google.com"
    
    print(f"\n🚀 Row {row_num}: Processing '{fname} {lname}' from '{company}'...")
    
    try:
        # Step 1: Capture Website Video Scroll
        screenshot_path = os.path.join(PROJECT_DIR, "server/static/output_screenshots", f"{video_id}.png")
        if mock:
            # Create a mock video background file
            intro_wave = os.path.join(paths["assets"], "intro_wave.mp4")
            if os.path.exists(intro_wave):
                import shutil
                shutil.copy(intro_wave, ss_path)
            else:
                with open(ss_path, "w") as f:
                    f.write("mock video background")
            # Create mock screenshot file
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
            with open(screenshot_path, "w") as f:
                f.write("mock screenshot")
            print(f"   [MOCK] Created mock video background and cover screenshot")
        else:
            capture_website(target_url, ss_path, screenshot_path)
            
        # Step 2: Generate Voice Greeting (ElevenLabs)
        if mock:
            # Copy generic silence/greeting to mock voice path
            # We can create a dummy 0-byte file for testing FFmpeg flow
            with open(voice_path, "w") as f:
                f.write("mock voice")
            print(f"   [MOCK] Created mock voice greeting: {voice_path}")
        else:
            generate_voice(fname, voice_path)
            
        # Step 3: FFmpeg Stitching (Voice + Intro + Body + Video Background Overlay)
        if mock:
            # Create a mock video file by copying assets/intro_wave.mp4 if it exists, or a dummy file
            intro_wave = os.path.join(paths["assets"], "intro_wave.mp4")
            if os.path.exists(intro_wave):
                import shutil
                shutil.copy(intro_wave, video_path)
            else:
                with open(video_path, "w") as f:
                    f.write("mock video")
            print(f"   [MOCK] Created mock video: {video_path}")
        else:
            stitch_video(ss_path, voice_path, video_path)
            
        # Step 4: Generate GIF Thumbnail for Email
        if mock:
            with open(gif_path, "w") as f:
                f.write("mock gif")
            print(f"   [MOCK] Created mock GIF preview: {gif_path}")
        else:
            generate_thumbnail(video_path, gif_path)
            
        # Step 5: Upload Files & Get URLs
        if mock:
            video_url = f"file:///{video_path.replace('\\', '/')}"
            gif_url = f"file:///{gif_path.replace('\\', '/')}"
            print(f"   [MOCK] Storage URLs generated: Video: {video_url}, GIF: {gif_url}")
        else:
            # Upload to Oracle Object Storage
            video_obj_name = f"videos/{today}/{safe_name}_outreach.mp4"
            gif_obj_name = f"thumbnails/{today}/{safe_name}_preview.gif"
            
            video_url = upload_to_oci(video_path, video_obj_name)
            gif_url = upload_to_oci(gif_path, gif_obj_name)
            
        # Step 6: Register Video in Local SQLite database for FastAPI portal
        landing_page_url = f"https://{LANDING_PAGE_DOMAIN}/v/{video_id}"
        register_lead_in_portal(
            video_id=video_id,
            name=fname,
            company=company,
            video_url=video_url,
            logo_url=None, # Will auto-resolve via Clearbit API on page load
            row_num=row_num
        )
        print(f"   Registered video ID '{video_id}' in SQLite portal.")
        
        # Step 7: Update Google Sheet with Output URLs
        if mock:
            print(f"   [MOCK] Would write to Sheet: Landing Page: {landing_page_url}, GIF: {gif_url}")
        else:
            sheet_sync.update_lead_urls(row_num, landing_page_url, gif_url, "Stitched")
            
        print(f"✅ Row {row_num}: Finished processing '{fname}' successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Row {row_num}: Failed to process lead: {e}")
        # Mark as failed in sheet
        if not mock:
            try:
                sheet_sync.update_lead_urls(row_num, "", "", f"ERROR: {str(e)[:30]}")
            except:
                pass
        return False

def run_factory(start_row: int, end_row: int):
    """Initializes workspace folders and runs the batch video generation factory."""
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    
    # Establish folder paths inside output/
    output_base = os.path.join(PROJECT_DIR, "output", today)
    paths = {
        "ss": os.path.join(output_base, "screenshots"),
        "voice": os.path.join(output_base, "voices"),
        "video": os.path.join(output_base, "videos"),
        "gif": os.path.join(output_base, "thumbnails"),
        "assets": os.path.join(PROJECT_DIR, "assets")
    }
    
    for k, p in paths.items():
        os.makedirs(p, exist_ok=True)
        
    mock = is_mock_mode()
    if mock:
        print("\nℹ️  LAUNCHING IN MOCK MODE (Placeholder API keys or storage parameters detected in .env)")
        print("   The script will generate mock visual/audio files locally for verification.")
    else:
        print(f"\n🚀 LAUNCHING PRODUCTION FACTORY FOR ROWS {start_row} TO {end_row}")
        print(f"   Target OCI Bucket: {os.getenv('OCI_BUCKET_NAME')}")
        print(f"   Target Google Sheet: {os.getenv('GOOGLE_SHEET_ID')}")
        
    # 1. Fetch leads range
    try:
        leads = sheet_sync.fetch_leads_batch(start_row, end_row)
    except Exception as e:
        print(f"❌ Failed to fetch lead rows: {e}")
        return
        
    if not leads:
        print("❌ No leads found to process in the specified range. Exiting.")
        return
        
    print(f"\nProcessing {len(leads)} leads using 4 parallel workers...\n")
    
    # 2. Run workers in parallel (4 workers maximum for OCI VM CPU capacity)
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(
            lambda l: process_lead(l, paths, today, mock),
            leads
        ))
        
    success_count = sum(1 for r in results if r)
    print(f"\n{'='*50}")
    print(f"🏁 FACTORY COMPLETE: Processed {success_count}/{len(leads)} leads successfully.")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    # Reconfigure console streams to UTF-8 on Windows to prevent encoding crashes with emojis
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except AttributeError:
            pass # Older Python versions
            
    parser = argparse.ArgumentParser(description="BlitzOutreach Video Generation Factory.")
    parser.add_argument("start_row", type=int, help="Starting row in Google Sheet (inclusive)")
    parser.add_argument("end_row", type=int, help="Ending row in Google Sheet (inclusive)")
    
    args = parser.parse_args()
    
    if args.start_row <= 1:
        print("❌ Starting row must be greater than 1 (Row 1 contains headers).")
        sys.exit(1)
    if args.end_row < args.start_row:
        print("❌ Ending row must be greater than or equal to starting row.")
        sys.exit(1)
        
    run_factory(args.start_row, args.end_row)
