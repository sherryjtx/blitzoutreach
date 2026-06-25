import os
import sys
import time
from dotenv import load_dotenv
from googleapiclient.discovery import build

# Ensure workspace root is in python path
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, WORKSPACE_DIR)

from execution.auth_google import get_creds

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
TAB_NAME = os.getenv("GOOGLE_SHEET_TAB")

# Load Column Indices
COL_FIRST_NAME = int(os.getenv("COL_FIRST_NAME", "23"))
COL_LAST_NAME = int(os.getenv("COL_LAST_NAME", "30"))
COL_EMAIL = int(os.getenv("COL_EMAIL", "22"))
COL_COMPANY = int(os.getenv("COL_COMPANY", "11"))
COL_WEBSITE = int(os.getenv("COL_WEBSITE", "20"))
COL_LANDING_PAGE = int(os.getenv("COL_LANDING_PAGE", "45"))
COL_GIF_THUMBNAIL = int(os.getenv("COL_GIF_THUMBNAIL", "46"))
COL_STATUS = int(os.getenv("COL_STATUS", "50"))

def col_letter(col_index):
    """Helper to convert 0-based column index to letter (e.g. 0 -> A, 27 -> AB)"""
    result = ""
    while col_index >= 0:
        result = chr(col_index % 26 + ord('A')) + result
        col_index = col_index // 26 - 1
    return result

def get_sheets_service():
    creds = get_creds()
    return build('sheets', 'v4', credentials=creds)

def fetch_leads_batch(start_row: int, end_row: int):
    """
    Fetches lead rows from Google Sheet for the specified row range.
    Returns a list of dictionaries with mapped lead details.
    """
    service = get_sheets_service()
    
    # Calculate the max column letter we need to fetch
    max_col_idx = max(COL_FIRST_NAME, COL_LAST_NAME, COL_EMAIL, COL_COMPANY, COL_WEBSITE, COL_LANDING_PAGE, COL_GIF_THUMBNAIL, COL_STATUS)
    max_col_letter = col_letter(max_col_idx)
    
    range_str = f"{TAB_NAME}!A{start_row}:{max_col_letter}{end_row}"
    print(f"📋 Fetching leads from Google Sheet: {range_str}...")
    
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=range_str
        ).execute()
        
        rows = result.get('values', [])
    except Exception as e:
        raise RuntimeError(f"Failed to fetch Google Sheet data: {e}")
        
    leads = []
    if not rows:
        print("⚠️ No data returned from sheet in this range.")
        return leads
        
    for index, row in enumerate(rows):
        row_num = start_row + index
        
        # Helper safely getting values out of list with default fallback
        def get_val(col_idx, default=""):
            if col_idx < len(row):
                return row[col_idx].strip()
            return default
            
        leads.append({
            "row": row_num,
            "first_name": get_val(COL_FIRST_NAME),
            "last_name": get_val(COL_LAST_NAME),
            "email": get_val(COL_EMAIL),
            "company": get_val(COL_COMPANY),
            "website": get_val(COL_WEBSITE),
            "existing_landing_page": get_val(COL_LANDING_PAGE),
            "existing_gif": get_val(COL_GIF_THUMBNAIL),
            "status": get_val(COL_STATUS)
        })
        
    print(f"✅ Fetched {len(leads)} leads from Google Sheet.")
    return leads

def update_lead_urls(row_num: int, landing_page_url: str, gif_url: str, status_msg: str = "Stitched"):
    """
    Updates a single lead row with the generated landing page and GIF URLs, and marks status.
    """
    service = get_sheets_service()
    
    # Build batch data list to update specific cells
    batch_data = [
        {
            'range': f"{TAB_NAME}!{col_letter(COL_LANDING_PAGE)}{row_num}",
            'values': [[landing_page_url]]
        },
        {
            'range': f"{TAB_NAME}!{col_letter(COL_GIF_THUMBNAIL)}{row_num}",
            'values': [[gif_url]]
        },
        {
            'range': f"{TAB_NAME}!{col_letter(COL_STATUS)}{row_num}",
            'values': [[status_msg]]
        }
    ]
    
    for attempt in range(3):
        try:
            service.spreadsheets().values().batchUpdate(
                spreadsheetId=SHEET_ID,
                body={
                    'valueInputOption': 'USER_ENTERED',
                    'data': batch_data
                }
            ).execute()
            print(f"✅ Stamped row {row_num} with URLs and status.")
            return True
        except Exception as e:
            if attempt < 2:
                wait_time = 3 * (attempt + 1)
                print(f"⚠️ [RETRY] Sheet update for row {row_num} failed: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"❌ [ERROR] Sheet update failed for row {row_num}: {e}")
                return False
