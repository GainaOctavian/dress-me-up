import os
from dotenv import load_dotenv

if os.getenv("ENV", "dev") == "dev":
    load_dotenv()