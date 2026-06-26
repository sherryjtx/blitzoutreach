import os
import sys
import logging

# Ensure UTF-8 stdout on Windows to support emojis
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from dotenv import load_dotenv
from supabase import create_client, Client
from starlette.middleware.base import BaseHTTPMiddleware

# Load env variables
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
WORKSPACE_DIR = os.path.dirname(PROJECT_DIR)
try:
    load_dotenv(dotenv_path=os.path.join(WORKSPACE_DIR, ".env"))
except Exception as e:
    pass

app = FastAPI(title="BlitzOutreach Video Portal")

# Subdomain Routing Middleware
class SubdomainRoutingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        host = request.headers.get("host", "").lower()
        path = request.url.path
        
        # If accessing via the video subdomain, redirect dashboard routes
        if "video.sherryautomates.com" in host:
            if path.startswith("/dashboard"):
                return RedirectResponse("https://dashboard.sherryautomates.com" + path)
            if path == "/":
                # Redirect root of video domain to main company page
                return RedirectResponse("https://sherryautomates.com")
                
        # If accessing via the dashboard subdomain, redirect watch portal routes
        elif "dashboard.sherryautomates.com" in host:
            if path.startswith("/v/"):
                return RedirectResponse("https://video.sherryautomates.com" + path)
            if path == "/":
                return RedirectResponse("https://dashboard.sherryautomates.com/dashboard/index.html")
                
        return await call_next(request)

app.add_middleware(SubdomainRoutingMiddleware)

# Configure CORS
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("BlitzOutreachPortal")

# Supabase Initialization
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

supabase = None
if not SUPABASE_URL or not SUPABASE_KEY:
    logger.error("❌ SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY/ANON_KEY must be set in environment variables")
else:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        logger.error(f"❌ Failed to initialize Supabase client: {e}")

# Calendly Configuration
CALENDLY_URL = os.getenv("CALENDLY_URL", "https://calendly.com/sherryjtx9/30min")

def seed_database_if_empty():
    try:
        # 1. Seed campaigns if empty
        camp_res = supabase.table("campaigns").select("id", count="exact").limit(1).execute()
        if not camp_res.data:
            logger.info("🌱 Supabase campaigns table is empty. Seeding mock campaigns...")
            demo_campaigns = [
                {"id": "saas_founder_outbound", "name": "SaaS Founder Outbound", "template_name": "SaaS Growth Audit V2", "status": "Active"},
                {"id": "enterprise_ops", "name": "Enterprise Operations Pitch", "template_name": "AI Operations Audit", "status": "Active"},
                {"id": "ecommerce_scaling", "name": "E-Commerce Scaling", "template_name": "Brand CRO Breakdown", "status": "Paused"},
                {"id": "yc_outbound", "name": "Y Combinator Outbound", "template_name": "Seed Pitch Audit", "status": "Draft"}
            ]
            supabase.table("campaigns").insert(demo_campaigns).execute()

        # 2. Seed leads if empty
        leads_res = supabase.table("leads").select("video_id", count="exact").limit(1).execute()
        if not leads_res.data:
            logger.info("🌱 Supabase leads table is empty. Seeding realistic demo data...")
            demo_leads = [
                {"video_id": "tyler_dawson", "name": "Tyler Dawson", "company": "ADknown", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/adknown.com", "row_num": 2, "campaign_id": "saas_founder_outbound", "batch_id": "Batch 1 (Rows 100-200)", "email": "tyler@adknown.com", "email_status": "Opened"},
                {"video_id": "sarah_rodriguez", "name": "Sarah Rodriguez", "company": "MarketPro", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/marketpro.io", "row_num": 3, "campaign_id": "saas_founder_outbound", "batch_id": "Batch 1 (Rows 100-200)", "email": "sarah@marketpro.io", "email_status": "Opened"},
                {"video_id": "mike_kowalski", "name": "Mike Kowalski", "company": "ScaleOps", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/scaleops.co", "row_num": 4, "campaign_id": "saas_founder_outbound", "batch_id": "Batch 2 (Rows 200-300)", "email": "mike@scaleops.co", "email_status": "Sent"},
                {"video_id": "jessica_lin", "name": "Jessica Lin", "company": "GrowthLab", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/growthlab.ai", "row_num": 5, "campaign_id": "enterprise_ops", "batch_id": "Batch 1 (Rows 1-50)", "email": "jessica@growthlab.ai", "email_status": "Opened"},
                {"video_id": "chris_dymond", "name": "Chris Dymond", "company": "Unfolding", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/unfolding.io", "row_num": 6, "campaign_id": "enterprise_ops", "batch_id": "Batch 1 (Rows 1-50)", "email": "chris@unfolding.io", "email_status": "Opened"},
                {"video_id": "alex_hernandez", "name": "Alex Hernandez", "company": "NovaTech", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/novatech.io", "row_num": 7, "campaign_id": "enterprise_ops", "batch_id": "Batch 1 (Rows 1-50)", "email": "alex@novatech.io", "email_status": "Sent"},
                {"video_id": "brian_park", "name": "Brian Park", "company": "Zenith Co", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/zenithco.com", "row_num": 8, "campaign_id": "ecommerce_scaling", "batch_id": "Batch 1 (Rows 1-50)", "email": "brian@zenithco.com", "email_status": "Opened"},
                {"video_id": "priya_sharma", "name": "Priya Sharma", "company": "DataVault", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/datavault.dev", "row_num": 9, "campaign_id": "ecommerce_scaling", "batch_id": "Batch 1 (Rows 1-50)", "email": "priya@datavault.dev", "email_status": "Opened"}
            ]
            supabase.table("leads").insert(demo_leads).execute()
            
            # Realistic events
            import datetime
            now = datetime.datetime.now(datetime.timezone.utc)
            
            demo_events = [
                {"video_id": "tyler_dawson", "event_type": "page_view", "timestamp": (now - datetime.timedelta(minutes=2)).isoformat()},
                {"video_id": "tyler_dawson", "event_type": "progress_25", "time_offset": 18.0, "timestamp": (now - datetime.timedelta(minutes=1)).isoformat()},
                {"video_id": "tyler_dawson", "event_type": "progress_50", "time_offset": 36.0, "timestamp": (now - datetime.timedelta(minutes=1)).isoformat()},
                {"video_id": "tyler_dawson", "event_type": "progress_75", "time_offset": 54.0, "timestamp": (now - datetime.timedelta(minutes=1)).isoformat()},
                
                {"video_id": "sarah_rodriguez", "event_type": "page_view", "timestamp": (now - datetime.timedelta(minutes=15)).isoformat()},
                {"video_id": "sarah_rodriguez", "event_type": "progress_25", "time_offset": 18.0, "timestamp": (now - datetime.timedelta(minutes=14)).isoformat()},
                {"video_id": "sarah_rodriguez", "event_type": "progress_50", "time_offset": 36.0, "timestamp": (now - datetime.timedelta(minutes=14)).isoformat()},
                {"video_id": "sarah_rodriguez", "event_type": "progress_75", "time_offset": 54.0, "timestamp": (now - datetime.timedelta(minutes=14)).isoformat()},
                {"video_id": "sarah_rodriguez", "event_type": "progress_100", "time_offset": 72.0, "timestamp": (now - datetime.timedelta(minutes=14)).isoformat()},
                {"video_id": "sarah_rodriguez", "event_type": "booked", "timestamp": (now - datetime.timedelta(minutes=14)).isoformat()},
                
                {"video_id": "jessica_lin", "event_type": "page_view", "timestamp": (now - datetime.timedelta(hours=1)).isoformat()},
                {"video_id": "jessica_lin", "event_type": "progress_25", "time_offset": 18.0, "timestamp": (now - datetime.timedelta(minutes=58)).isoformat()},
                
                {"video_id": "chris_dymond", "event_type": "page_view", "timestamp": (now - datetime.timedelta(hours=2, minutes=5)).isoformat()},
                {"video_id": "chris_dymond", "event_type": "progress_25", "time_offset": 18.0, "timestamp": (now - datetime.timedelta(hours=2, minutes=3)).isoformat()},
                {"video_id": "chris_dymond", "event_type": "progress_50", "time_offset": 36.0, "timestamp": (now - datetime.timedelta(hours=2, minutes=3)).isoformat()},
                {"video_id": "chris_dymond", "event_type": "replied", "timestamp": (now - datetime.timedelta(hours=2)).isoformat()},
                
                {"video_id": "alex_hernandez", "event_type": "page_view", "timestamp": (now - datetime.timedelta(minutes=10)).isoformat()},
                
                {"video_id": "brian_park", "event_type": "page_view", "timestamp": (now - datetime.timedelta(days=1)).isoformat()},
                {"video_id": "brian_park", "event_type": "progress_25", "time_offset": 18.0, "timestamp": (now - datetime.timedelta(days=1, minutes=5)).isoformat()},
                {"video_id": "brian_park", "event_type": "progress_50", "time_offset": 36.0, "timestamp": (now - datetime.timedelta(days=1, minutes=5)).isoformat()},
                
                {"video_id": "priya_sharma", "event_type": "page_view", "timestamp": (now - datetime.timedelta(hours=4)).isoformat()},
                {"video_id": "priya_sharma", "event_type": "progress_25", "time_offset": 18.0, "timestamp": (now - datetime.timedelta(hours=3, minutes=58)).isoformat()},
                {"video_id": "priya_sharma", "event_type": "progress_50", "time_offset": 36.0, "timestamp": (now - datetime.timedelta(hours=3, minutes=58)).isoformat()},
            ]
            supabase.table("events").insert(demo_events).execute()
            logger.info("🌱 Seeding completed successfully.")
        else:
            # If leads exist, check if campaign_id is filled
            tyler = supabase.table("leads").select("campaign_id").eq("video_id", "tyler_dawson").execute()
            if tyler.data and not tyler.data[0].get("campaign_id"):
                logger.info("🔧 Linking existing leads to mock campaigns...")
                updates = [
                    {"video_id": "tyler_dawson", "campaign_id": "saas_founder_outbound", "batch_id": "Batch 1 (Rows 100-200)", "email": "tyler@adknown.com", "email_status": "Opened"},
                    {"video_id": "sarah_rodriguez", "campaign_id": "saas_founder_outbound", "batch_id": "Batch 1 (Rows 100-200)", "email": "sarah@marketpro.io", "email_status": "Opened"},
                    {"video_id": "mike_kowalski", "campaign_id": "saas_founder_outbound", "batch_id": "Batch 2 (Rows 200-300)", "email": "mike@scaleops.co", "email_status": "Sent"},
                    {"video_id": "jessica_lin", "campaign_id": "enterprise_ops", "batch_id": "Batch 1 (Rows 1-50)", "email": "jessica@growthlab.ai", "email_status": "Opened"},
                    {"video_id": "chris_dymond", "campaign_id": "enterprise_ops", "batch_id": "Batch 1 (Rows 1-50)", "email": "chris@unfolding.io", "email_status": "Opened"},
                    {"video_id": "alex_hernandez", "campaign_id": "enterprise_ops", "batch_id": "Batch 1 (Rows 1-50)", "email": "alex@novatech.io", "email_status": "Sent"},
                    {"video_id": "brian_park", "campaign_id": "ecommerce_scaling", "batch_id": "Batch 1 (Rows 1-50)", "email": "brian@zenithco.com", "email_status": "Opened"},
                    {"video_id": "priya_sharma", "campaign_id": "ecommerce_scaling", "batch_id": "Batch 1 (Rows 1-50)", "email": "priya@datavault.dev", "email_status": "Opened"}
                ]
                for up in updates:
                    try:
                        supabase.table("leads").update(up).eq("video_id", up["video_id"]).execute()
                    except Exception as e:
                        logger.warning(f"Failed to update lead {up['video_id']}: {e}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to seed database: {e}")

# Run seeding
seed_database_if_empty()

# Root Redirect to Dashboard
@app.get("/")
async def root_redirect():
    return RedirectResponse(url="/dashboard/index.html")

# Templates & Static Files
# Resolve templates directory (check api/templates first for Vercel bundling compatibility)
api_templates_dir = os.path.join(PROJECT_DIR, "api", "templates")
server_templates_dir = os.path.join(BASE_DIR, "templates")

if os.path.exists(api_templates_dir):
    templates = Jinja2Templates(directory=api_templates_dir)
elif os.path.exists(server_templates_dir):
    templates = Jinja2Templates(directory=server_templates_dir)
else:
    templates = Jinja2Templates(directory=server_templates_dir)

# Mount static directories
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/dashboard", StaticFiles(directory=os.path.join(PROJECT_DIR, "dashboard")), name="dashboard")
app.mount("/assets", StaticFiles(directory=os.path.join(PROJECT_DIR, "assets")), name="assets")

# Models for tracking payload
class TrackingPayload(BaseModel):
    video_id: str
    event_type: str
    time_offset: float = 0.0
    metadata: dict = {}

@app.get("/v/{video_id}", response_class=HTMLResponse)
async def watch_video(video_id: str, request: Request):
    """
    Renders the personalized video page for a lead.
    """
    try:
        if not supabase:
            raise Exception("Supabase is not configured. Please add SUPABASE_URL and SUPABASE_ANON_KEY (or SUPABASE_SERVICE_ROLE_KEY) to your Vercel Project Environment Variables.")
        
        try:
            response = supabase.table("leads").select("name, company, video_url, company_logo").eq("video_id", video_id).execute()
            if not response.data:
                raise HTTPException(status_code=404, detail="Video outreach page not found.")
            
            lead = response.data[0]
            name = lead["name"]
            company = lead["company"]
            video_url = lead["video_url"]
            company_logo = lead["company_logo"]
        except HTTPException as http_e:
            raise http_e
        except Exception as db_err:
            raise Exception(f"Failed to fetch lead from Supabase: {db_err}")
            
        # Log page view automatically
        ip = request.client.host if request.client else "unknown"
        ua = request.headers.get("user-agent", "unknown")
        
        try:
            event_data = {
                "video_id": video_id,
                "event_type": "page_view",
                "ip_address": ip,
                "user_agent": ua
            }
            supabase.table("events").insert(event_data).execute()
        except Exception as e:
            logger.warning(f"Failed to log page view event to Supabase: {e}")
            
        logger.info(f"👀 Page view on video '{video_id}' from IP: {ip}")
        
        # Resolve company logos (wordmark & sign icon)
        company_lower = company.lower().strip()
        company_logo_sign = None
        company_logo_wordmark = None
        company_badge_bg = "#111113"
        
        if "github" in company_lower:
            company_logo_sign = "/static/github_icon.svg"
            company_logo_wordmark = "/static/github_wordmark.svg"
            company_badge_bg = "#24292e"
        elif "vimeo" in company_lower:
            company_logo_sign = "/static/vimeo_icon.svg"
            company_logo_wordmark = "/static/vimeo_wordmark.svg"
            company_badge_bg = "#00adef"
        elif "nike" in company_lower:
            company_logo_sign = "/static/nike_icon.svg"
            company_logo_wordmark = "/static/nike_wordmark.svg"
            company_badge_bg = "#000000"
        elif "adknown" in company_lower:
            company_logo_sign = "/static/adknown_logo.svg"
            company_logo_wordmark = "/static/adknown_logo.svg"
            company_badge_bg = "#3da9d7"
        elif "lemieux" in company_lower:
            company_logo_sign = "/static/lemieux_leaf.png"
            company_logo_wordmark = "/static/lemieux_logo_main.svg"
            company_badge_bg = "#58652d"
        else:
            # Fallback to Clearbit logo for general companies
            if not company_logo and company:
                clean_company = company.lower().replace(" ", "").replace("ltd", "").replace("inc", "")
                company_logo = f"https://logo.clearbit.com/{clean_company}.com"
            company_logo_sign = company_logo
            
        return templates.TemplateResponse(
            request=request,
            name="watch.html",
            context={
                "name": name,
                "company": company,
                "video_url": video_url,
                "company_logo": company_logo_sign,
                "company_wordmark": company_logo_wordmark,
                "company_badge_bg": company_badge_bg,
                "video_id": video_id,
                "calendly_url": CALENDLY_URL
            }
        )
    except HTTPException as http_err:
        return HTMLResponse(content=f"<div style='font-family: sans-serif; text-align: center; margin-top: 10%;'><h2>404: Not Found</h2><p>{http_err.detail}</p></div>", status_code=http_err.status_code)
    except Exception as err:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Error in watch_video: {tb}")
        return HTMLResponse(content=f"<pre>Error in watch_video:\n{tb}</pre>", status_code=500)

@app.post("/track")
async def track_event(payload: TrackingPayload, request: Request):
    """
    Logs active events from the video player (play, pause, milestones).
    """
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "unknown")
    
    try:
        event_data = {
            "video_id": payload.video_id,
            "event_type": payload.event_type,
            "time_offset": payload.time_offset,
            "ip_address": ip,
            "user_agent": ua,
            "metadata": payload.metadata
        }
        supabase.table("events").insert(event_data).execute()
        logger.info(f"📊 Event '{payload.event_type}' logged for video '{payload.video_id}' (Time: {payload.time_offset}s)")
        return JSONResponse(content={"status": "logged"})
    except Exception as e:
        logger.error(f"Failed to log event to Supabase: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.post("/track-beacon")
async def track_beacon(request: Request):
    """
    Alternative endpoint to accept navigator.sendBeacon requests when browser tab closes.
    """
    try:
        body = await request.json()
        video_id = body.get("video_id")
        event_type = body.get("event_type")
        metadata = body.get("metadata", {})
        
        ip = request.client.host if request.client else "unknown"
        ua = request.headers.get("user-agent", "unknown")
        
        event_data = {
            "video_id": video_id,
            "event_type": event_type,
            "ip_address": ip,
            "user_agent": ua,
            "metadata": metadata
        }
        supabase.table("events").insert(event_data).execute()
        
        logger.info(f"📊 Beacon '{event_type}' logged for video '{video_id}': {metadata}")
        return JSONResponse(content={"status": "logged"})
    except Exception as e:
        logger.error(f"Beacon logging failed: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=400)

# ═══ Dashboard APIs ═══

@app.get("/api/stats")
async def get_stats():
    try:
        # Query total leads
        leads_res = supabase.table("leads").select("video_id", count="exact").execute()
        total_sent = leads_res.count or 0

        # Query events to calculate open/response rates
        events_res = supabase.table("events").select("event_type, video_id").execute()
        events = events_res.data or []

        # Calculate metrics
        opened_video_ids = set()
        replied_count = 0
        booked_count = 0
        for ev in events:
            etype = ev.get("event_type")
            vid = ev.get("video_id")
            if etype == "page_view":
                opened_video_ids.add(vid)
            elif etype in ["reply", "replied"]:
                replied_count += 1
            elif etype in ["meeting_booked", "booked"]:
                booked_count += 1

        opened_count = len(opened_video_ids)
        
        open_rate = round((opened_count / total_sent * 100), 1) if total_sent > 0 else 0.0
        reply_rate = round((replied_count / total_sent * 100), 1) if total_sent > 0 else 0.0
        booking_rate = round((booked_count / total_sent * 100), 1) if total_sent > 0 else 0.0

        return {
            "total_sent": total_sent,
            "deliverability_rate": 99.8,  # Mock stable outbound deliverability
            "open_rate": open_rate,
            "response_rate": reply_rate,
            "booking_rate": booking_rate,
            "booked_count": booked_count
        }
    except Exception as e:
        logger.error(f"Failed to fetch stats: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.get("/api/leads")
async def get_leads():
    try:
        # Fetch all leads
        leads_res = supabase.table("leads").select("*").order("created_at", desc=True).execute()
        leads = leads_res.data or []

        # Fetch all events to compute status and watch percentage
        events_res = supabase.table("events").select("*").execute()
        events = events_res.data or []

        # Map events to video_id
        lead_events = {}
        for ev in events:
            vid = ev.get("video_id")
            if vid not in lead_events:
                lead_events[vid] = []
            lead_events[vid].append(ev)

        # Build lead response items
        results = []
        for lead in leads:
            vid = lead["video_id"]
            name = lead["name"]
            company = lead["company"]
            video_url = lead["video_url"]
            logo = lead.get("company_logo")
            row = lead.get("row_num")
            created_at = lead.get("created_at")

            # Compute status & watch %
            v_events = lead_events.get(vid, [])
            
            # Default status
            status = "Sent"
            max_watch = 0.0
            has_booked = False
            has_replied = False
            has_viewed = False

            for ev in v_events:
                etype = ev.get("event_type")
                offset = ev.get("time_offset") or 0.0
                if etype == "page_view":
                    has_viewed = True
                elif etype in ["reply", "replied"]:
                    has_replied = True
                elif etype in ["meeting_booked", "booked"]:
                    has_booked = True
                
                # Find max watch progress if it's a progress event
                if offset > max_watch:
                    max_watch = offset

            if has_booked:
                status = "Booked"
            elif has_replied:
                status = "Replied"
            elif has_viewed:
                status = "Viewed"

            # Format watch percent (guess total video length is 72s if not specified)
            watch_pct = f"{int(min(max_watch / 72.0 * 100, 100))}%" if max_watch > 0 else "-"
            if status == "Booked":
                watch_pct = "100%"

            results.append({
                "video_id": vid,
                "name": name,
                "company": company,
                "video_url": video_url,
                "company_logo": logo,
                "row_num": row,
                "status": status,
                "watch_percent": watch_pct,
                "created_at": created_at
            })

        return results
    except Exception as e:
        logger.error(f"Failed to fetch leads list: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.get("/api/events")
async def get_events():
    try:
        # Fetch latest 20 events, join with lead info
        events_res = supabase.table("events").select("*, leads(name, company)").order("timestamp", desc=True).limit(20).execute()
        events = events_res.data or []
        
        results = []
        for ev in events:
            leads_info = ev.get("leads") or {}
            lead_name = leads_info.get("name", "Unknown Lead")
            lead_company = leads_info.get("company", "Unknown Company")
            
            results.append({
                "id": ev["id"],
                "video_id": ev["video_id"],
                "event_type": ev["event_type"],
                "time_offset": ev.get("time_offset"),
                "ip_address": ev.get("ip_address"),
                "user_agent": ev.get("user_agent"),
                "timestamp": ev["timestamp"],
                "name": lead_name,
                "company": lead_company
            })
        return results
    except Exception as e:
        logger.error(f"Failed to fetch events: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.get("/api/videos")
async def get_videos():
    try:
        # Fetch the registered videos in leads table
        response = supabase.table("leads").select("video_id, name, company, video_url, company_logo, created_at").order("created_at", desc=True).execute()
        return response.data or []
    except Exception as e:
        logger.error(f"Failed to fetch videos: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

class CampaignCreatePayload(BaseModel):
    name: str
    template_name: str
    import_method: str  # "manual", "google_sheets", "csv"
    start_row: int = None
    end_row: int = None
    csv_data: str = None
    batch_name: str = None
    sheet_id: str = None
    sheet_tab: str = None

# Background processing handlers
def run_sheets_import_and_video_generation(campaign_id: str, batch_name: str, start_row: int, end_row: int, sheet_id: str = None, sheet_tab: str = None):
    try:
        from execution import sheet_sync
        logger.info(f"Background Sheets Sync: Fetching rows {start_row} to {end_row}")
        leads = sheet_sync.fetch_leads_batch(start_row, end_row, sheet_id=sheet_id, sheet_tab=sheet_tab)
        if not leads:
            logger.info("Background Sheets Sync: No leads found in this range.")
            return
            
        import random
        leads_to_process = []
        for l in leads:
            fname = l.get("first_name", "").strip()
            lname = l.get("last_name", "").strip()
            email = l.get("email", "").strip()
            company = l.get("company", "").strip()
            website = l.get("website", "").strip()
            row_val = l.get("row", 9999)
            
            if not fname:
                continue
                
            clean_name = f"{fname.lower()}{lname.lower()}".replace(" ", "")
            clean_company = company.lower().replace(" ", "")
            video_id = f"{clean_name}_{clean_company}_{random.randint(100, 999)}"
            video_id = "".join(c for c in video_id if c.isalnum() or c == "_")
            
            clean_domain = website if website else (company.lower().replace(" ", "").replace("ltd", "").replace("inc", "") + ".com")
            if not clean_domain.startswith("http"):
                clean_domain = clean_domain.replace("https://", "").replace("http://", "")
            company_logo = f"https://logo.clearbit.com/{clean_domain}"
            
            lead_data = {
                "video_id": video_id,
                "name": f"{fname} {lname}".strip(),
                "company": company,
                "video_url": "pending",
                "company_logo": company_logo,
                "row_num": row_val,
                "campaign_id": campaign_id,
                "batch_id": batch_name,
                "email": email,
                "email_status": "Sent"
            }
            supabase.table("leads").upsert(lead_data, on_conflict="video_id").execute()
            
            lead_dict = {
                "row": row_val,
                "first_name": fname,
                "last_name": lname,
                "email": email,
                "company": company,
                "website": clean_domain,
                "campaign_id": campaign_id,
                "batch_id": batch_name,
                "video_id": video_id,
                "company_logo": company_logo,
                "sheet_id": sheet_id,
                "sheet_tab": sheet_tab
            }
            leads_to_process.append(lead_dict)
            
        logger.info(f"Background Sheets Sync: Registered {len(leads_to_process)} leads in database. Starting background video generation...")
        
        if leads_to_process:
            if PROJECT_DIR not in sys.path:
                sys.path.insert(0, PROJECT_DIR)
            from execution.factory import run_factory_for_leads
            run_factory_for_leads(leads_to_process)
            
    except Exception as e:
        logger.error(f"Error in background sheets sync and generation: {e}")

def run_csv_import_and_video_generation(campaign_id: str, batch_name: str, csv_data: str):
    try:
        logger.info("Background CSV Sync: Parsing CSV and starting video generation...")
        lines = csv_data.strip().split("\n")
        leads_to_process = []
        import random
        
        for idx, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            parts = line.split(",")
            if len(parts) < 2:
                continue
                
            name = parts[0].strip()
            company = parts[1].strip()
            
            name_parts = name.split(" ")
            fname = name_parts[0]
            lname = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
            
            website = parts[2].strip() if len(parts) > 2 else ""
            email = parts[3].strip() if len(parts) > 3 else f"{fname.lower()}@{company.lower().replace(' ', '')}.com"
            
            clean_name = f"{fname.lower()}{lname.lower()}".replace(" ", "")
            clean_company = company.lower().replace(" ", "")
            video_id = f"{clean_name}_{clean_company}_{random.randint(100, 999)}"
            video_id = "".join(c for c in video_id if c.isalnum() or c == "_")
            
            clean_domain = website if website else (company.lower().replace(" ", "").replace("ltd", "").replace("inc", "") + ".com")
            if not clean_domain.startswith("http"):
                clean_domain = clean_domain.replace("https://", "").replace("http://", "")
            company_logo = f"https://logo.clearbit.com/{clean_domain}"
            
            lead_data = {
                "video_id": video_id,
                "name": name,
                "company": company,
                "video_url": "pending",
                "company_logo": company_logo,
                "row_num": 1000 + idx,
                "campaign_id": campaign_id,
                "batch_id": batch_name,
                "email": email,
                "email_status": "Sent"
            }
            supabase.table("leads").upsert(lead_data, on_conflict="video_id").execute()
            
            lead_dict = {
                "row": 1000 + idx,
                "first_name": fname,
                "last_name": lname,
                "email": email,
                "company": company,
                "website": clean_domain,
                "campaign_id": campaign_id,
                "batch_id": batch_name,
                "video_id": video_id,
                "company_logo": company_logo
            }
            leads_to_process.append(lead_dict)
            
        logger.info(f"Background CSV Sync: Registered {len(leads_to_process)} leads in database. Starting background video generation...")
        
        if leads_to_process:
            if PROJECT_DIR not in sys.path:
                sys.path.insert(0, PROJECT_DIR)
            from execution.factory import run_factory_for_leads
            run_factory_for_leads(leads_to_process)
            
    except Exception as e:
        logger.error(f"Error in background CSV sync and generation: {e}")


# Campaign APIs
@app.get("/api/campaigns")
async def get_campaigns():
    try:
        c_res = supabase.table("campaigns").select("*").order("created_at", desc=True).execute()
        campaigns = c_res.data or []
        
        leads_res = supabase.table("leads").select("*").execute()
        leads = leads_res.data or []
        
        events_res = supabase.table("events").select("*").execute()
        events = events_res.data or []
        
        lead_events = {}
        for ev in events:
            vid = ev.get("video_id")
            if vid not in lead_events:
                lead_events[vid] = []
            lead_events[vid].append(ev)
            
        lead_metrics = {}
        for lead in leads:
            vid = lead["video_id"]
            c_id = lead.get("campaign_id")
            b_id = lead.get("batch_id")
            e_status = lead.get("email_status", "Sent")
            
            v_events = lead_events.get(vid, [])
            has_page_view = any(ev.get("event_type") == "page_view" for ev in v_events)
            has_progress = any(ev.get("event_type", "").startswith("progress_") for ev in v_events)
            has_replied = any(ev.get("event_type") in ["replied", "reply"] for ev in v_events) or lead.get("status") == "Replied"
            has_booked = any(ev.get("event_type") in ["booked", "meeting_booked"] for ev in v_events) or lead.get("status") == "Booked"
            
            opened = e_status == "Opened" or has_page_view
            watched = has_progress
            replied = has_replied
            booked = has_booked
            
            lead_metrics[vid] = {
                "campaign_id": c_id,
                "batch_id": b_id,
                "opened": opened,
                "watched": watched,
                "replied": replied,
                "booked": booked
            }
            
        campaign_list = []
        for camp in campaigns:
            cid = camp["id"]
            c_leads = [l for l in leads if l.get("campaign_id") == cid]
            
            batches_map = {}
            for l in c_leads:
                bid = l.get("batch_id") or "Default Batch"
                if bid not in batches_map:
                    batches_map[bid] = []
                batches_map[bid].append(l)
                
            batches_list = []
            for bid, b_leads in batches_map.items():
                b_sent = len(b_leads)
                b_opened = sum(1 for l in b_leads if lead_metrics.get(l["video_id"], {}).get("opened"))
                b_watched = sum(1 for l in b_leads if lead_metrics.get(l["video_id"], {}).get("watched"))
                b_replied = sum(1 for l in b_leads if lead_metrics.get(l["video_id"], {}).get("replied"))
                b_booked = sum(1 for l in b_leads if lead_metrics.get(l["video_id"], {}).get("booked"))
                
                batches_list.append({
                    "batch_id": bid,
                    "total_sent": b_sent,
                    "total_opened": b_opened,
                    "total_watched": b_watched,
                    "total_replied": b_replied,
                    "total_booked": b_booked
                })
                
            c_sent = len(c_leads)
            c_opened = sum(1 for l in c_leads if lead_metrics.get(l["video_id"], {}).get("opened"))
            c_watched = sum(1 for l in c_leads if lead_metrics.get(l["video_id"], {}).get("watched"))
            c_replied = sum(1 for l in c_leads if lead_metrics.get(l["video_id"], {}).get("replied"))
            c_booked = sum(1 for l in c_leads if lead_metrics.get(l["video_id"], {}).get("booked"))
            
            c_pending = sum(1 for l in c_leads if l.get("video_url") == "pending" or not l.get("video_url"))
            c_processing = sum(1 for l in c_leads if l.get("video_url") == "processing")
            c_failed = sum(1 for l in c_leads if l.get("video_url") == "failed")
            c_generated = c_sent - c_pending - c_processing - c_failed
            
            campaign_list.append({
                "id": cid,
                "name": camp["name"],
                "template_name": camp.get("template_name"),
                "status": camp.get("status", "Active"),
                "created_at": camp.get("created_at"),
                "total_sent": c_sent,
                "total_opened": c_opened,
                "total_watched": c_watched,
                "total_replied": c_replied,
                "total_booked": c_booked,
                "total_leads": c_sent,
                "total_pending": c_pending,
                "total_processing": c_processing,
                "total_failed": c_failed,
                "total_generated": c_generated,
                "batches": batches_list
            })
            
        return campaign_list
    except Exception as e:
        logger.error(f"Failed to fetch campaigns: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.get("/api/campaigns/{campaign_id}/batches/{batch_id}/leads")
async def get_campaign_batch_leads(campaign_id: str, batch_id: str):
    try:
        leads_res = supabase.table("leads").select("*").eq("campaign_id", campaign_id).eq("batch_id", batch_id).execute()
        leads = leads_res.data or []
        
        events_res = supabase.table("events").select("*").execute()
        events = events_res.data or []
        
        lead_events = {}
        for ev in events:
            vid = ev.get("video_id")
            if vid not in lead_events:
                lead_events[vid] = []
            lead_events[vid].append(ev)
            
        results = []
        for lead in leads:
            vid = lead["video_id"]
            name = lead["name"]
            company = lead["company"]
            video_url = lead["video_url"]
            logo = lead.get("company_logo")
            row = lead.get("row_num")
            created_at = lead.get("created_at")
            email = lead.get("email") or ""
            email_status = lead.get("email_status", "Sent")
            
            v_events = lead_events.get(vid, [])
            
            # Simple milestones watch percent
            has_25 = any(ev.get("event_type") == "progress_25" for ev in v_events)
            has_50 = any(ev.get("event_type") == "progress_50" for ev in v_events)
            has_75 = any(ev.get("event_type") == "progress_75" for ev in v_events)
            has_100 = any(ev.get("event_type") == "progress_100" for ev in v_events)
            
            watch_pct = "-"
            if has_100: watch_pct = "100%"
            elif has_75: watch_pct = "75%"
            elif has_50: watch_pct = "50%"
            elif has_25: watch_pct = "25%"
            
            has_page_view = any(ev.get("event_type") == "page_view" for ev in v_events)
            has_replied = any(ev.get("event_type") in ["replied", "reply"] for ev in v_events) or lead.get("status") == "Replied"
            has_booked = any(ev.get("event_type") in ["booked", "meeting_booked"] for ev in v_events) or lead.get("status") == "Booked"
            
            status = "Sent"
            if has_booked:
                status = "Booked"
                watch_pct = "100%"
            elif has_replied:
                status = "Replied"
            elif has_page_view:
                status = "Viewed"
                
            # Get last activity timestamp
            last_activity = created_at
            if v_events:
                sorted_events = sorted(v_events, key=lambda e: e.get("timestamp", ""))
                last_activity = sorted_events[-1].get("timestamp")
                
            results.append({
                "video_id": vid,
                "name": name,
                "company": company,
                "video_url": video_url,
                "company_logo": logo,
                "row_num": row,
                "status": status,
                "watch_percent": watch_pct,
                "email": email,
                "email_status": email_status,
                "last_activity": last_activity,
                "created_at": created_at
            })
            
        return results
    except Exception as e:
        logger.error(f"Failed to fetch batch leads: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.post("/api/campaigns/create")
async def create_campaign(payload: CampaignCreatePayload, background_tasks: BackgroundTasks):
    try:
        import re
        import random
        
        # Generate slugified ID
        slug = re.sub(r'[^a-zA-Z0-9]+', '_', payload.name.lower()).strip('_')
        campaign_id = f"{slug}_{random.randint(100, 999)}"
        
        camp_data = {
            "id": campaign_id,
            "name": payload.name,
            "template_name": payload.template_name,
            "status": "Active"
        }
        supabase.table("campaigns").insert(camp_data).execute()
        
        batch_name = campaign_id
        
        if payload.import_method == "google_sheets":
            if not payload.start_row or not payload.end_row:
                raise HTTPException(status_code=400, detail="start_row and end_row are required for google_sheets import.")
            background_tasks.add_task(
                run_sheets_import_and_video_generation,
                campaign_id,
                batch_name,
                payload.start_row,
                payload.end_row,
                payload.sheet_id,
                payload.sheet_tab
            )
            return {"status": "success", "campaign_id": campaign_id, "message": "Campaign created! Importing leads and generating videos in background."}
            
        elif payload.import_method == "csv":
            if not payload.csv_data:
                raise HTTPException(status_code=400, detail="csv_data is required for csv import.")
            background_tasks.add_task(
                run_csv_import_and_video_generation,
                campaign_id,
                batch_name,
                payload.csv_data
            )
            return {"status": "success", "campaign_id": campaign_id, "message": "Campaign created! Parsing CSV and generating videos in background."}
            
        else:
            return {"status": "success", "campaign_id": campaign_id, "message": "Campaign created manually."}
            
    except Exception as e:
        logger.error(f"Failed to create campaign: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

class SyncPayload(BaseModel):
    start_row: int
    end_row: int
    campaign_id: str = None
    batch_id: str = None
    sheet_id: str = None
    sheet_tab: str = None

@app.post("/api/leads/sync")
async def sync_leads(payload: SyncPayload):
    try:
        if PROJECT_DIR not in sys.path:
            sys.path.insert(0, PROJECT_DIR)
        from execution import sheet_sync
        
        leads = sheet_sync.fetch_leads_batch(payload.start_row, payload.end_row, sheet_id=payload.sheet_id, sheet_tab=payload.sheet_tab)
        if not leads:
            return {"status": "success", "imported": 0, "message": "No leads found in range."}
            
        import random
        imported_count = 0
        campaign_id = payload.campaign_id
        batch_id = payload.batch_id
        
        for l in leads:
            fname = l.get("first_name", "").strip()
            lname = l.get("last_name", "").strip()
            email = l.get("email", "").strip()
            company = l.get("company", "").strip()
            website = l.get("website", "").strip()
            row_val = l.get("row", 9999)
            
            if not fname or not email:
                continue
                
            # Create a unique video_id
            clean_name = f"{fname.lower()}{lname.lower()}".replace(" ", "")
            clean_company = company.lower().replace(" ", "")
            video_id = f"{clean_name}_{clean_company}"
            video_id = "".join(c for c in video_id if c.isalnum() or c == "_")
            video_id += f"_{random.randint(100, 999)}"
            
            # Find logo fallback
            clean_domain = website if website else (company.lower().replace(" ", "").replace("ltd", "").replace("inc", "") + ".com")
            if not clean_domain.startswith("http"):
                clean_domain = clean_domain.replace("https://", "").replace("http://", "")
            
            company_logo = f"https://logo.clearbit.com/{clean_domain}"
            
            lead_data = {
                "video_id": video_id,
                "name": f"{fname} {lname}".strip(),
                "company": company,
                "video_url": "pending",
                "company_logo": company_logo,
                "row_num": row_val,
                "email": email,
                "email_status": "Sent"
            }
            if campaign_id:
                lead_data["campaign_id"] = campaign_id
            if batch_id:
                lead_data["batch_id"] = batch_id
            
            # Upsert in Supabase
            supabase.table("leads").upsert(lead_data, on_conflict="video_id").execute()
            imported_count += 1
            
        return {"status": "success", "imported": imported_count, "message": f"Successfully synced {imported_count} leads."}
    except Exception as e:
        logger.error(f"Failed to sync leads: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


class LeadCreatePayload(BaseModel):
    name: str
    company: str
    video_url: str = None
    company_logo: str = None
    campaign_id: str = None
    batch_id: str = None

@app.post("/api/leads/create")
async def create_lead(payload: LeadCreatePayload):
    try:
        import random
        # Generate video ID
        clean_name = payload.name.lower().replace(" ", "")
        clean_company = payload.company.lower().replace(" ", "")
        video_id = f"{clean_name}_{clean_company}"
        video_id = "".join(c for c in video_id if c.isalnum() or c == "_")
        video_id += f"_{random.randint(100, 999)}"
        
        company_logo = payload.company_logo
        if not company_logo:
            clean_company_domain = payload.company.lower().replace(" ", "").replace("ltd", "").replace("inc", "")
            company_logo = f"https://logo.clearbit.com/{clean_company_domain}.com"
            
        video_url = payload.video_url
        if not video_url:
            video_url = "pending"
            
        lead_data = {
            "video_id": video_id,
            "name": payload.name,
            "company": payload.company,
            "video_url": video_url,
            "company_logo": company_logo,
            "row_num": 9999,
            "email_status": "Sent"
        }
        if payload.campaign_id:
            lead_data["campaign_id"] = payload.campaign_id
        if payload.batch_id:
            lead_data["batch_id"] = payload.batch_id
            
        response = supabase.table("leads").insert(lead_data).execute()
        return {"status": "success", "lead": response.data[0]}
    except Exception as e:
        logger.error(f"Failed to create lead: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

@app.delete("/api/leads/{video_id}")
async def delete_lead(video_id: str):
    try:
        supabase.table("events").delete().eq("video_id", video_id).execute()
        response = supabase.table("leads").delete().eq("video_id", video_id).execute()
        return {"status": "success", "message": f"Lead {video_id} deleted."}
    except Exception as e:
        logger.error(f"Failed to delete lead: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
