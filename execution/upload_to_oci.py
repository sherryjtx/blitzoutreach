import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

OCI_CONFIG_PROFILE = os.getenv("OCI_CONFIG_PROFILE", "DEFAULT")
OCI_NAMESPACE = os.getenv("OCI_NAMESPACE")
OCI_BUCKET_NAME = os.getenv("OCI_BUCKET_NAME")

# Try to import OCI, but don't crash if it's not installed yet (allows local development/testing)
OCI_AVAILABLE = False
try:
    import oci
    OCI_AVAILABLE = True
except ImportError:
    pass

def upload_to_oci(local_file_path: str, object_name: str) -> str:
    """
    Uploads a local file to Oracle Cloud Infrastructure (OCI) Object Storage
    and returns its public URL.
    """
    if not os.path.exists(local_file_path):
        raise FileNotFoundError(f"Local file not found: {local_file_path}")
        
    print(f"☁️ Uploading {os.path.basename(local_file_path)} to OCI Object Storage...")
    
    # 1. Fallback for Local Development (If OCI is not configured or missing)
    if not OCI_AVAILABLE or not OCI_NAMESPACE or OCI_NAMESPACE == "your_oci_object_storage_namespace_here":
        mock_url = f"https://mock-oci-storage.local/{OCI_BUCKET_NAME}/{object_name}"
        print(f"⚠️ Warning: OCI SDK not configured. Returning local mock URL: {mock_url}")
        return mock_url
        
    try:
        # Load OCI config from default location (typically ~/.oci/config on Linux/Windows)
        # In production on OCI, we can also use Instance Principals (auth without keys)
        config = oci.config.from_file(profile_name=OCI_CONFIG_PROFILE)
        region = config.get("region", "us-ashburn-1")
        
        # Initialize Object Storage client
        object_storage_client = oci.object_storage.ObjectStorageClient(config)
        
        # Open file and upload
        with open(local_file_path, "rb") as f:
            object_storage_client.put_object(
                namespace_name=OCI_NAMESPACE,
                bucket_name=OCI_BUCKET_NAME,
                object_name=object_name,
                put_object_body=f
            )
            
        # Build public URL
        # Note: Bucket must be configured as Public in OCI Console for this URL to be accessible.
        public_url = f"https://objectstorage.{region}.oraclecloud.com/n/{OCI_NAMESPACE}/b/{OCI_BUCKET_NAME}/o/{object_name}"
        print(f"✅ Uploaded successfully. Public URL: {public_url}")
        return public_url
        
    except Exception as e:
        raise RuntimeError(f"OCI Upload Failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload file to OCI Object Storage.")
    parser.add_argument("local_path", help="Path to the local file to upload")
    parser.add_argument("object_name", help="Name of the object in the bucket (e.g. videos/test.mp4)")
    
    args = parser.parse_args()
    
    try:
        url = upload_to_oci(args.local_path, args.object_name)
        # Print output URL so calling processes can capture it
        print(f"OUTPUT_URL:{url}")
    except Exception as e:
        print(f"❌ Upload failed: {e}")
        sys.exit(1)
