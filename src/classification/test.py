from dotenv import load_dotenv
load_dotenv("/Users/asolod/work/Hackathons/mistral_26/mistral-monitor/.env")  # adjust path to your .env

from mistralai import Mistral
import os
import requests

api_key = os.getenv("MISTRAL_API_KEY")
resp = requests.post(
    "https://api.mistral.ai/v1/fine_tuning/jobs",
    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
    json={
        "model": "open-mistral-nemo",
        "training_files": [{"file_id": "72280167-462e-4fdf-b0a2-c125db1be15c", "weight": 1}],
        "validation_files": ["951a691b-1b20-47b5-8023-d35b44bc135c"],
        "hyperparameters": {"training_steps": 100, "learning_rate": 0.0001},
    }
)
print(resp.status_code)
print(resp.json())