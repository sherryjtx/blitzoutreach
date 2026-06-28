import os
import sys
import time
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
from supabase import create_client

# Ensure execution and project root are in python path
exec_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(exec_dir)
if exec_dir not in sys.path:
    sys.path.insert(0, exec_dir)
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

# Import factory modules
import factory

# Load environment variables
load_dotenv(dotenv_path=os.path.join(project_dir, ".env"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
MAX_WORKERS = int(os.getenv("MAX_VIDEO_WORKERS", "8"))

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and Keys must be set in environment.")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_paths(today):
    output_base = os.path.join(project_dir, "output", today)
    paths = {
        "ss": os.path.join(output_base, "screenshots"),
        "voice": os.path.join(output_base, "voices"),
        "video": os.path.join(output_base, "videos"),
        "gif": os.path.join(output_base, "thumbnails"),
        "assets": os.path.join(project_dir, "assets")
    }
    for p in paths.values():
        os.makedirs(p, exist_ok=True)
    return paths

def process_single_lead(lead, paths, today, mock):
    """Process a single lead in its own thread. Returns (video_id, name, success)."""
    video_id = lead["video_id"]
    name = lead["name"]
    company = lead["company"]
    email = lead["email"]
    row_num = lead.get("row_num", 9999)
    
    # Split name safely into first/last
    name_parts = name.split(" ")
    first_name = name_parts[0] if name_parts else "Prospect"
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
    
    # Recover website domain from clearbit logo or sanitizing company name
    logo_url = lead.get("company_logo")
    website = ""
    if logo_url and logo_url.startswith("http") and "logo.clearbit.com/" not in logo_url:
        # Direct website URL stored in company_logo
        website = logo_url
    elif logo_url and "logo.clearbit.com/" in logo_url:
        website = logo_url.split("logo.clearbit.com/")[-1]
    else:
        clean_company = company.lower().replace(" ", "").replace("ltd", "").replace("inc", "")
        website = f"{clean_company}.com"
        
    print(f"Processing lead '{name}' (ID: {video_id}) for company '{company}'...")
    
    # Formulate the lead dict expected by process_lead
    lead_dict = {
        "row": row_num,
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "company": company,
        "website": website,
        "video_id": video_id,
        "campaign_id": lead.get("campaign_id"),
        "batch_id": lead.get("batch_id"),
        "company_logo": logo_url,
        "sheet_id": os.getenv("GOOGLE_SHEET_ID"),
        "sheet_tab": os.getenv("GOOGLE_SHEET_TAB")
    }
    
    # Run the generation process
    success = factory.process_lead(lead_dict, paths, today, mock)
    return video_id, name, success

def poll_and_process():
    print(f"[{datetime.datetime.now().isoformat()}] Polling Supabase for pending video generations...")
    try:
        # Atomic work-claiming loop to safely fetch and lock leads one by one
        pending_leads = []
        for _ in range(MAX_WORKERS):
            res = supabase.rpc("claim_next_lead").execute()
            # The RPC returns a list of matching claimed rows (usually 0 or 1 row)
            if res.data and len(res.data) > 0:
                pending_leads.append(res.data[0])
            else:
                break
                
        if not pending_leads:
            return
            
        print(f"Claimed {len(pending_leads)} pending leads to process in parallel.")
        
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        paths = get_paths(today)
        mock = factory.is_mock_mode()
        
        # Process leads in parallel using ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=min(MAX_WORKERS, len(pending_leads))) as executor:
            futures = {
                executor.submit(process_single_lead, lead, paths, today, mock): lead
                for lead in pending_leads
            }
            
            for future in as_completed(futures):
                try:
                    video_id, name, success = future.result()
                    if success:
                        print(f"Lead '{name}' processed successfully.")
                    else:
                        print(f"Lead '{name}' processing failed.")
                except Exception as e:
                    lead = futures[future]
                    print(f"Error processing lead '{lead.get('name', '?')}': {e}")
                
    except Exception as e:
        print(f"Error in poll loop: {e}")

def main():
    print("BlitzOutreach Background Worker Daemon started.")
    print(f"Supabase target: {SUPABASE_URL}")
    print(f"Mode: {'MOCK' if factory.is_mock_mode() else 'PRODUCTION'}")
    print(f"Max parallel workers: {MAX_WORKERS}")
    
    # Enable console encoding setup on Windows
    if sys.platform.startswith("win"):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except:
            pass
            
    while True:
        poll_and_process()
        time.sleep(10)

if __name__ == "__main__":
    main()
