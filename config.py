import os
from dotenv import load_dotenv

load_dotenv()

VK_TOKEN = os.getenv("VK_API_TOKEN")
VK_GROUP_ID = os.getenv("VK_GROUP_ID")
MY_VK_ID = int(os.getenv("MY_VK_ID", 0))

API_URL = os.getenv("API_URL")
API_USERNAME = os.getenv("API_USERNAME")
API_PASSWORD = os.getenv("API_PASSWORD")
