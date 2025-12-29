"""
Google Elevation API Mock Server.

Returns deterministic elevation data based on latitude ranges:
- Lat < 0.5 -> Low altitude (600m)
- Lat 0.5-1.0 -> Medium altitude (1000m)
- Lat > 1.0 -> High altitude (1400m)

This allows predictable testing of altitude band assignment in Plantation Model.
"""

from fastapi import FastAPI, Query
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="Google Elevation API Mock")


class ElevationResult(BaseModel):
    """Single elevation result."""
    elevation: float
    location: dict
    resolution: float


class ElevationResponse(BaseModel):
    """Google Elevation API response format."""
    results: list[ElevationResult]
    status: str


def get_elevation_for_lat(lat: float) -> float:
    """
    Return deterministic elevation based on latitude.

    Altitude bands match Plantation Model expectations:
    - Low: <800m
    - Medium: 800-1200m
    - High: >1200m
    """
    if lat < 0.5:
        return 600.0  # Low altitude
    elif lat < 1.0:
        return 1000.0  # Medium altitude
    else:
        return 1400.0  # High altitude


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/maps/api/elevation/json")
async def get_elevation(
    locations: str = Query(..., description="Pipe-separated lat,lng pairs"),
    key: str = Query("mock", description="API key (ignored in mock)"),
):
    """
    Mock Google Elevation API endpoint.

    Matches the real API format:
    GET /maps/api/elevation/json?locations=lat,lng|lat,lng&key=API_KEY
    """
    results = []

    # Parse locations (format: "lat,lng|lat,lng")
    for location_str in locations.split("|"):
        parts = location_str.strip().split(",")
        if len(parts) >= 2:
            try:
                lat = float(parts[0])
                lng = float(parts[1])
                elevation = get_elevation_for_lat(lat)

                results.append(ElevationResult(
                    elevation=elevation,
                    location={"lat": lat, "lng": lng},
                    resolution=30.0,  # Mock resolution
                ))
            except ValueError:
                continue

    return ElevationResponse(
        results=results,
        status="OK" if results else "ZERO_RESULTS",
    )


@app.post("/maps/api/elevation/json")
async def post_elevation(
    locations: str = Query(..., description="Pipe-separated lat,lng pairs"),
    key: str = Query("mock", description="API key (ignored in mock)"),
):
    """POST endpoint for elevation (same as GET)."""
    return await get_elevation(locations=locations, key=key)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
