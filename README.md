# BlitzOutreach — Scaled Video Outreach Engine

BlitzOutreach is a standalone, cloud-native video personalization and outreach pipeline designed to generate and host 500-600 custom video landing pages per day for **$0.00/month** in cloud fees.

It is deployed on Vercel at:
- Dashboard: https://dashboard.sherryautomates.com
- Video Watch Portal: https://video.sherryautomates.com

It is completely independent of the existing `AutoLoom` project.

---

## 🚀 Quick Start (Mock Mode Testing)

You can run the entire factory in **Mock Mode** immediately without setting up any paid API keys or cloud credentials. In Mock Mode, the script fetches lead rows from Google Sheets, generates dummy screenshots/audio files, renders local output folders, and registers them in the local database.

### 1. Install Dependencies
Run in your terminal:
```bash
pip install -r requirements.txt
playwright install
```

### 2. Run the Factory (Mock Mode)
Run the orchestrator for a row range (e.g. rows 38 to 40 in your Google Sheet):
```bash
python execution/factory.py 38 40
```
This will create a daily folder under `output/YYYY-MM-DD/` containing mock screenshots, voice files, videos, and GIF thumbnails.

### 3. Launch the Landing Page Portal
Start the FastAPI server locally:
```bash
python server/app.py
```
Open your browser and navigate to the URLs printed in the console during the factory run (e.g., `http://localhost:8000/v/chris_dymond_unfolding`). You will see the co-branded landing page, player tracking JS scripts active in the console, and the Calendly widget.

---

## 🛠️ Production Mode Configuration

To transition the system to production:

### 1. Fill in Your `.env` File
Open the `.env` file at the root of this folder and fill in your details:
*   `ELEVENLABS_API_KEY`: Your ElevenLabs API key.
*   `ELEVENLABS_VOICE_ID`: Your cloned voice ID.
*   `OCI_NAMESPACE`: Automatically verified and updated to `axv9qsbet8n5`.
*   `OCI_BUCKET_NAME`: Set to `blitz-outreach-videos`.
*   `GOOGLE_SHEET_ID`: Your target Google Sheet ID.
*   `LANDING_PAGE_DOMAIN`: The subdomain pointing to your server (e.g., `watch.sherryautomates.com`).

### 2. Prepare Master Video Assets
Place your one-time recorded assets inside the `assets/` folder:
1.  **`intro_wave.mp4`**: A 2.5-second webcam clip of you smiling, nodding, and waving at the camera **without moving your mouth**.
2.  **`pitch_body.mp4`**: Your 45-60 second generic pitch video.
3.  **`play_button.png`**: A play icon overlay (already auto-generated for you in the assets folder).
4.  **`circle_mask_1024.png`**: A white circle on a black background (copy this from your `AutoLoom/Assets/circle_mask_1024.png` file).

### 3. Run Production
Once the keys are in `.env` and the videos are in `assets/`, running the orchestrator will automatically trigger production mode (Playwright captures, ElevenLabs voice, FFmpeg rendering, and OCI uploads):
```bash
python execution/factory.py 38 40
```
Your Google Sheet will automatically be stamped with the live public URLs.
