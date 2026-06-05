import asyncio
import json
import os
import sys

# Fix protobuf compatibility with Python 3.14 by forcing ImportError
sys.modules['google._upb._message'] = None
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from dotenv import load_dotenv

from evaluation.runner import EvaluationRunner
from utils.gemini_client import GeminiClient
from utils.cost_tracker import CostTracker
from storage.database import init_db
from utils.logger import setup_logging

async def main():
    load_dotenv()
    setup_logging()
    await init_db()
    
    api_key = os.getenv("GEMINI_API_KEY", "")
    client = GeminiClient(api_key=api_key)
    tracker = CostTracker()
    runner = EvaluationRunner(client=client, tracker=tracker)
    
    async def progress_cb(event: dict):
        print(f"Progress: {event['type']} - {event.get('status')} - {event.get('test_name', '')}")
        
    print("Running evaluations...")
    results = await runner.run_all(progress_cb)
    
    print("\n--- RESULTS ---")
    print(json.dumps({k: v for k, v in results.items() if k != 'results'}, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
