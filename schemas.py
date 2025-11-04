"""
Database Schemas for TwinEdge Safety Lab

Each Pydantic model represents a MongoDB collection. The collection name is the lowercase
of the class name. For example: SensorEvent -> "sensorevent".
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class Location(BaseModel):
    lat: float = Field(..., description="Latitude")
    lng: float = Field(..., description="Longitude")

class SensorEvent(BaseModel):
    """Structured reading from edge sensors (e.g., Raspberry Pi)."""
    timestamp: datetime = Field(..., description="Reading timestamp (ISO 8601)")
    temperature_c: float = Field(..., description="Temperature in Celsius")
    gas_ppm: int = Field(..., ge=0, description="Gas sensor reading (ppm)")
    aqi: int = Field(..., ge=0, description="Air Quality Index")
    location: Optional[Location] = Field(None, description="Approximate location of device")
    notes: Optional[str] = Field(None, description="Optional notes or tags for the event")
    source: str = Field("raspi", description="Source identifier of the reading")

class InsightRequest(BaseModel):
    temperature_c: float
    gas_ppm: int
    aqi: int

class InsightResponse(BaseModel):
    score: float = Field(..., ge=0, le=100, description="0-100 risk score")
    level: str = Field(..., description="Normal | Elevated | High risk")
    tips: list[str] = Field(default_factory=list)
