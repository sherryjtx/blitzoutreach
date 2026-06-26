import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/presentations',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/calendar'
]

def get_creds():
    """Shows basic usage of the Drive v3 API.
    Prints the names and ids of the first 10 files the user has access to.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    # Search for token.json in multiple locations
    token_path = 'token.json'
    script_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_dir = os.path.dirname(script_dir)
    if not os.path.exists(token_path):
        parent_token = os.path.join(workspace_dir, 'token.json')
        if os.path.exists(parent_token):
            token_path = parent_token
        elif os.path.exists('/root/token.json'):
            token_path = '/root/token.json'
            
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            import time
            from google.auth.exceptions import TransportError
            for attempt in range(4):
                try:
                    creds.refresh(Request())
                    break
                except (TransportError, Exception) as e:
                    if attempt < 3:
                        wait_time = 5 * (attempt + 1)
                        print(f"   [AUTH RETRY] Token refresh failed ({e}). Retrying in {wait_time}s... (attempt {attempt+1}/4)")
                        time.sleep(wait_time)
                    else:
                        raise e
        else:
            creds_path = 'credentials.json'
            if not os.path.exists(creds_path):
                parent_creds = os.path.join(workspace_dir, 'credentials.json')
                if os.path.exists(parent_creds):
                    creds_path = parent_creds
                elif os.path.exists('/root/credentials.json'):
                    creds_path = '/root/credentials.json'
                else:
                    raise FileNotFoundError("credentials.json not found in workspace.")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                creds_path, SCOPES)
            creds = flow.run_local_server(port=0, access_type='offline', prompt='consent')
        # Save the credentials for the next run
        try:
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        except Exception as e:
            print(f"Warning: Could not save token.json (Read-only fs?): {e}")
    
    return creds

if __name__ == '__main__':
    try:
        get_creds()
        print("Authentication successful.")
    except Exception as e:
        print(f"Authentication failed: {e}")
