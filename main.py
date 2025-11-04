import os
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import create_document, get_documents, db
from schemas import SensorEvent, InsightRequest, InsightResponse

app = FastAPI(title="TwinEdge Safety Lab API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "TwinEdge Safety Lab Backend Running"}


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": [],
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, "name") else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"

    return response


# ----------------------------
# Sensor ingestion & retrieval
# ----------------------------

@app.post("/api/sensors/ingest")
def ingest_sensor_event(event: SensorEvent):
    """Ingest a single sensor reading and persist to MongoDB."""
    try:
        inserted_id = create_document("sensorevent", event)
        return {"ok": True, "id": inserted_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class RecentResponse(BaseModel):
    items: list[SensorEvent]


@app.get("/api/sensors/recent", response_model=RecentResponse)
def get_recent_readings(limit: int = 20):
    """Fetch recent sensor readings (most recent first)."""
    try:
        docs = get_documents("sensorevent", {}, limit=limit)
        # Sort by created_at if exists, else timestamp
        def key_fn(d):
            return d.get("created_at") or d.get("timestamp") or datetime.now(timezone.utc)
        docs_sorted = sorted(docs, key=key_fn, reverse=True)
        # Convert _id and datetime to pydantic-friendly
        items = []
        for d in docs_sorted:
            d.pop("_id", None)
            # ensure timestamp is datetime
            if isinstance(d.get("timestamp"), str):
                try:
                    d["timestamp"] = datetime.fromisoformat(d["timestamp"])  # may fail if Z
                except Exception:
                    pass
            items.append(SensorEvent(**d))
        return {"items": items}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------
# AI-style risk assessment
# ----------------------------

@app.post("/api/insights/assess", response_model=InsightResponse)
def assess_risk(payload: InsightRequest):
    """Simple heuristic risk scoring. Replace with real ML later."""
    # Base score from normalized features
    t = payload.temperature_c
    g = payload.gas_ppm
    a = payload.aqi

    # Heuristic weighting
    score = 0.0
    score += max(0.0, (t - 25)) * 1.2  # temp above comfortable range
    score += (g / 12)  # gas ppm scaled
    score += (a / 3)   # AQI scaled

    # Clamp to 0-100
    score = max(0.0, min(100.0, score))

    if score >= 70 or g > 800 or a > 150:
        level = "High risk"
        tips = [
            "Evacuate non-essential personnel",
            "Engage ventilation and gas suppression systems",
            "Activate incident command protocol",
        ]
    elif score >= 45 or g > 600 or a > 100:
        level = "Elevated"
        tips = [
            "Increase monitoring frequency",
            "Prepare PPE and standby team",
            "Verify sensor calibration",
        ]
    else:
        level = "Normal"
        tips = [
            "Continue routine monitoring",
            "Maintain clear egress routes",
        ]

    return InsightResponse(score=round(score, 1), level=level, tips=tips)


# ----------------------------
# Schema exposure (optional viewer support)
# ----------------------------

@app.get("/schema")
def get_schema():
    # Minimal schema metadata for integrators/viewers
    return {
        "collections": [
            {
                "name": "sensorevent",
                "model": "SensorEvent",
                "fields": [
                    "timestamp: datetime",
                    "temperature_c: float",
                    "gas_ppm: int",
                    "aqi: int",
                    "location.lat: float",
                    "location.lng: float",
                    "notes: str?",
                    "source: str",
                ],
            }
        ]
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
