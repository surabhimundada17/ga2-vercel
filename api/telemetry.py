from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import json
from pathlib import Path

app = FastAPI()

# Enable CORS for all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Load telemetry bundle once at startup
DATA_PATH = Path(__file__).resolve().parent.parent / "q-vercel-latency.json"
with open(DATA_PATH, "r") as f:
    telemetry = json.load(f)

@app.post("/")
async def get_latency_metrics(request: Request):
    try:
        payload = await request.json()
        regions = payload.get("regions")
        
        if not regions or not isinstance(regions, list):
            return {"error": "Request must include a 'regions' array"}
        
        threshold = payload.get("threshold_ms", 180)
        response = {}

        for region in regions:
            # Filter records for this region
            region_data = [r for r in telemetry if r["region"] == region]
            if not region_data:
                continue

            latencies = [r["latency_ms"] for r in region_data]
            uptimes = [r["uptime_pct"] for r in region_data]

            avg_latency = float(np.mean(latencies))
            p95_latency = float(np.percentile(latencies, 95))
            avg_uptime = float(np.mean(uptimes))
            breaches = int(sum(l > threshold for l in latencies))

            response[region] = {
                "avg_latency": round(avg_latency, 2),
                "p95_latency": round(p95_latency, 2),
                "avg_uptime": round(avg_uptime, 3),
                "breaches": breaches,
            }

        if not response:
            return {"error": "No data found for the specified regions"}
            
        return response
    except json.JSONDecodeError:
        return {"error": "Invalid JSON in request body"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}
