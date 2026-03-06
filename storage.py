import json
import os

STORAGE_FILE = "data.json"

def load_data():
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "channels": [],
        "top_count": 5,
        "hours": 24,
        "schedule_time": None
    }

def save_data(data):
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
