import os
from dotenv import load_dotenv

load_dotenv()

VK_TOKEN = os.getenv("VK_API_TOKEN", "").strip()
API_URL = os.getenv("API_URL", "").strip()
