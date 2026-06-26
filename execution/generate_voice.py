import os
import sys
import argparse
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

def generate_voice(name: str, output_path: str):
    """
    Calls the ElevenLabs Text-to-Speech API to generate the personalized voice greeting.
    """
    if not ELEVENLABS_API_KEY or ELEVENLABS_API_KEY == "your_elevenlabs_api_key_here":
        print("⚠️ ElevenLabs API Key missing or default. Skipping voice greeting generation (will use original Becca video audio).")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except:
                pass
        return
        
    if not ELEVENLABS_VOICE_ID or ELEVENLABS_VOICE_ID == "your_elevenlabs_voice_id_here":
        raise ValueError("Missing ELEVENLABS_VOICE_ID in .env file")
        
    print(f"🎙️ Generating voice greeting for '{name}'...")
    
    # Ensure output directory exists
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVENLABS_API_KEY
    }
    
    # We generate "Hey [Name]," which takes about 1.5 seconds.
    data = {
        "text": f"Hey {name},",
        "model_id": "eleven_monolingual_v1",  # Standard fast model
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    response = requests.post(url, json=data, headers=headers, stream=True)
    
    if response.status_code != 200:
        error_msg = response.text
        try:
            error_json = response.json()
            error_msg = error_json.get("detail", {}).get("message", response.text)
        except:
            pass
        raise RuntimeError(f"ElevenLabs API Error (HTTP {response.status_code}): {error_msg}")
        
    with open(output_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                
    print(f"✅ Voice greeting saved to {output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate personalized greeting using ElevenLabs API.")
    parser.add_argument("name", help="Name to personalize (e.g. Tyler)")
    parser.add_argument("output_path", help="Path to save the generated audio (e.g. voice.mp3)")
    
    args = parser.parse_args()
    
    try:
        generate_voice(args.name, args.output_path)
    except Exception as e:
        print(f"❌ Failed to generate voice: {e}")
        sys.exit(1)
