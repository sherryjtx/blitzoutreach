import os
import glob
from dotenv import load_dotenv
from execution.upload_to_oci import upload_to_oci

def main():
    # Load env
    load_dotenv(dotenv_path="/home/ubuntu/BlitzOutreach/.env")
    
    # Grab all screenshots
    screenshots = glob.glob("/home/ubuntu/BlitzOutreach/server/static/output_screenshots/*.png")
    print(f"Found {len(screenshots)} screenshots to upload.")
    
    for ss in screenshots:
        filename = os.path.basename(ss)
        obj_name = f"posters/{filename}"
        try:
            upload_to_oci(ss, obj_name)
            print(f"✅ Uploaded to OCI: {obj_name}")
        except Exception as e:
            print(f"❌ Failed to upload {filename}: {e}")

if __name__ == "__main__":
    main()
