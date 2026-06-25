import os
import sys
import logging
from fastapi import FastAPI, Request, HTTPException
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
load_dotenv(dotenv_path=os.path.join(WORKSPACE_DIR, ".env"))

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

def seed_database_if_empty():
    try:
        leads_res = supabase.table("leads").select("video_id", count="exact").limit(1).execute()
        if not leads_res.data:
            logger.info("🌱 Supabase leads table is empty. Seeding realistic demo data...")
            
            # Realistic leads
            demo_leads = [
                {"video_id": "tyler_dawson", "name": "Tyler Dawson", "company": "ADknown", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/adknown.com", "row_num": 2},
                {"video_id": "sarah_rodriguez", "name": "Sarah Rodriguez", "company": "MarketPro", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/marketpro.io", "row_num": 3},
                {"video_id": "mike_kowalski", "name": "Mike Kowalski", "company": "ScaleOps", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/scaleops.co", "row_num": 4},
                {"video_id": "jessica_lin", "name": "Jessica Lin", "company": "GrowthLab", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/growthlab.ai", "row_num": 5},
                {"video_id": "chris_dymond", "name": "Chris Dymond", "company": "Unfolding", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/unfolding.io", "row_num": 6},
                {"video_id": "alex_hernandez", "name": "Alex Hernandez", "company": "NovaTech", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/novatech.io", "row_num": 7},
                {"video_id": "brian_park", "name": "Brian Park", "company": "Zenith Co", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/zenithco.com", "row_num": 8},
                {"video_id": "priya_sharma", "name": "Priya Sharma", "company": "DataVault", "video_url": "https://www.w3schools.com/html/mov_bbb.mp4", "company_logo": "https://logo.clearbit.com/datavault.dev", "row_num": 9}
            ]
            supabase.table("leads").insert(demo_leads).execute()
            
            # Realistic events
            import datetime
            now = datetime.datetime.now(datetime.timezone.utc)
            
            demo_events = [
                {"video_id": "tyler_dawson", "event_type": "page_view", "timestamp": (now - datetime.timedelta(minutes=2)).isoformat()},
                {"video_id": "tyler_dawson", "event_type": "progress", "time_offset": 66.2, "timestamp": (now - datetime.timedelta(minutes=1)).isoformat()},
                
                {"video_id": "sarah_rodriguez", "event_type": "page_view", "timestamp": (now - datetime.timedelta(minutes=15)).isoformat()},
                {"video_id": "sarah_rodriguez", "event_type": "progress", "time_offset": 72.0, "timestamp": (now - datetime.timedelta(minutes=14)).isoformat()},
                {"video_id": "sarah_rodriguez", "event_type": "booked", "timestamp": (now - datetime.timedelta(minutes=14)).isoformat()},
                
                {"video_id": "jessica_lin", "event_type": "page_view", "timestamp": (now - datetime.timedelta(hours=1)).isoformat()},
                {"video_id": "jessica_lin", "event_type": "progress", "time_offset": 32.4, "timestamp": (now - datetime.timedelta(minutes=58)).isoformat()},
                
                {"video_id": "chris_dymond", "event_type": "page_view", "timestamp": (now - datetime.timedelta(hours=2, minutes=5)).isoformat()},
                {"video_id": "chris_dymond", "event_type": "progress", "time_offset": 56.1, "timestamp": (now - datetime.timedelta(hours=2, minutes=3)).isoformat()},
                {"video_id": "chris_dymond", "event_type": "replied", "timestamp": (now - datetime.timedelta(hours=2)).isoformat()},
                
                {"video_id": "alex_hernandez", "event_type": "page_view", "timestamp": (now - datetime.timedelta(minutes=10)).isoformat()},
                
                {"video_id": "brian_park", "event_type": "page_view", "timestamp": (now - datetime.timedelta(days=1)).isoformat()},
                {"video_id": "brian_park", "event_type": "progress", "time_offset": 48.2, "timestamp": (now - datetime.timedelta(days=1, minutes=5)).isoformat()},
                
                {"video_id": "priya_sharma", "event_type": "page_view", "timestamp": (now - datetime.timedelta(hours=4)).isoformat()},
                {"video_id": "priya_sharma", "event_type": "progress", "time_offset": 39.6, "timestamp": (now - datetime.timedelta(hours=3, minutes=58)).isoformat()},
            ]
            supabase.table("events").insert(demo_events).execute()
            logger.info("🌱 Seeding completed successfully.")
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

# Only mount static directories locally. On Vercel, static files are served directly by the Vercel CDN.
if not os.getenv("VERCEL"):
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
    if not supabase:
        raise HTTPException(
            status_code=500,
            detail="Supabase is not configured. Please add SUPABASE_URL and SUPABASE_ANON_KEY (or SUPABASE_SERVICE_ROLE_KEY) to your Vercel Project Environment Variables."
        )
    try:
        response = supabase.table("leads").select("name, company, video_url, company_logo").eq("video_id", video_id).execute()
        if not response.data:
            raise HTTPException(status_code=404, detail="Video not found")
        
        lead = response.data[0]
        name = lead["name"]
        company = lead["company"]
        video_url = lead["video_url"]
        company_logo = lead["company_logo"]
    except Exception as e:
        logger.error(f"Failed to fetch lead from Supabase: {e}")
        raise HTTPException(status_code=500, detail="Database error")
        
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
    
    # Get clearbit logo fallback if no custom logo provided
    if not company_logo and company:
        clean_company = company.lower().replace(" ", "").replace("ltd", "").replace("inc", "")
        company_logo = f"https://logo.clearbit.com/{clean_company}.com"
        
    return templates.TemplateResponse(
        "watch.html",
        {
            "request": request,
            "name": name,
            "company": company,
            "video_url": video_url,
            "company_logo": company_logo,
            "video_id": video_id
        }
    )

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

class CampaignPayload(BaseModel):
    name: str
    lead_list: str
    template_name: str
    subject: str
    body: str

@app.post("/api/campaigns/create")
async def create_campaign(payload: CampaignPayload):
    try:
        logger.info(f"🚀 Campaign '{payload.name}' launched on list '{payload.lead_list}' using template '{payload.template_name}'!")
        return {"status": "success", "message": f"Campaign '{payload.name}' active."}
    except Exception as e:
        logger.error(f"Failed to create campaign: {e}")
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

class LeadCreatePayload(BaseModel):
    name: str
    company: str
    video_url: str = None
    company_logo: str = None

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
            video_url = "https://www.w3schools.com/html/mov_bbb.mp4"
            
        lead_data = {
            "video_id": video_id,
            "name": payload.name,
            "company": payload.company,
            "video_url": video_url,
            "company_logo": company_logo,
            "row_num": 9999
        }
        
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
