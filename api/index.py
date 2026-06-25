import os
import sys

# Add project root to sys.path for Vercel imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.app import app
