"""
FastAPI application for Perfume Data API.
Serves scraped perfume data from Supabase.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import os
import sys
import asyncio

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import (
    run_migration,
    insert_perfume,
    insert_perfumes_batch,
    get_all_perfumes,
    get_perfume_by_id,
    search_perfumes,
    get_perfume_count
)
from scraper.scrape import (
    scrape_fragrantica,
    scrape_fragrantica_by_brand,
    scrape_fragrantica_brands,
    scrape_fragrantica_by_url
)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Perfume Data API",
    description="API for scraping and serving perfume data from Fragrantica",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request/response validation
class PerfumeBase(BaseModel):
    """Base perfume model"""
    name: str
    brand: Optional[str] = None
    release_year: Optional[int] = None
    gender: Optional[str] = None
    notes_top: List[str] = Field(default_factory=list)
    notes_middle: List[str] = Field(default_factory=list)
    notes_base: List[str] = Field(default_factory=list)
    rating: Optional[float] = None
    votes: Optional[int] = None
    description: Optional[str] = None
    longevity: Optional[str] = None
    sillage: Optional[str] = None
    image_url: Optional[str] = None
    perfume_url: Optional[str] = None


class PerfumeCreate(PerfumeBase):
    """Model for creating a new perfume"""
    pass


class PerfumeResponse(PerfumeBase):
    """Model for perfume response"""
    id: str
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class ScrapeRequest(BaseModel):
    """Model for scrape request"""
    limit: int = Field(default=2, ge=1, le=1000, description="Number of perfumes to scrape (1-1000)")


class ScrapeBrandRequest(BaseModel):
    """Model for brand scrape request"""
    brand_name: str = Field(..., description="Brand name (e.g., 'Jean Paul Gaultier')")
    limit: int = Field(default=10, ge=1, le=500, description="Number of perfumes to scrape from this brand (1-500)")


class ScrapeBrandsRequest(BaseModel):
    """Model for multiple brands scrape request"""
    brands: List[str] = Field(..., description="List of brand names")
    limit_per_brand: int = Field(default=10, ge=1, le=200, description="Number of perfumes to scrape per brand (1-200)")


class ScrapeUrlRequest(BaseModel):
    """Model for URL scrape request"""
    perfume_url: str = Field(..., description="Direct URL to a Fragrantica perfume page")


class ScrapeResponse(BaseModel):
    """Model for scrape response"""
    status: str
    message: str
    scraped_count: int
    inserted_count: int
    perfumes: List[Dict[str, Any]] = Field(default_factory=list)


class PerfumeListResponse(BaseModel):
    """Model for paginated perfume list response"""
    total: int
    limit: int
    offset: int
    perfumes: List[PerfumeResponse]


# Startup event
@app.on_event("startup")
async def startup_event():
    """Run database migration on startup"""
    print("🚀 Starting Perfume API...")
    await run_migration()
    print("✅ API ready!")


# Health check endpoints
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Perfume API is running",
        "version": "1.0.0",
        "endpoints": {
            "docs": "/docs",
            "perfumes": "/perfumes",
            "scrape": "/scrape",
            "scrape_brand": "/scrape/brand",
            "scrape_brands": "/scrape/brands",
            "scrape_url": "/scrape/url"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    try:
        count = await get_perfume_count()
        return {
            "status": "healthy",
            "database": "connected",
            "perfumes_count": count
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


# Public endpoints
@app.get("/perfumes", response_model=PerfumeListResponse, tags=["Perfumes"])
async def list_perfumes(
    limit: int = Query(default=100, ge=1, le=500, description="Number of perfumes to return"),
    offset: int = Query(default=0, ge=0, description="Number of perfumes to skip")
):
    """Get list of all perfumes with pagination."""
    try:
        perfumes = await get_all_perfumes(limit=limit, offset=offset)
        total = await get_perfume_count()
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "perfumes": perfumes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching perfumes: {str(e)}")


@app.get("/perfumes/{perfume_id}", response_model=PerfumeResponse, tags=["Perfumes"])
async def get_perfume(perfume_id: str):
    """Get a specific perfume by ID."""
    try:
        perfume = await get_perfume_by_id(perfume_id)
        if not perfume:
            raise HTTPException(status_code=404, detail=f"Perfume with ID {perfume_id} not found")
        return perfume
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching perfume: {str(e)}")


@app.get("/perfumes/search/{query}", response_model=List[PerfumeResponse], tags=["Perfumes"])
async def search_perfumes_endpoint(
    query: str,
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of results")
):
    """Search perfumes by name or brand."""
    try:
        perfumes = await search_perfumes(query, limit=limit)
        return perfumes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching perfumes: {str(e)}")


@app.post("/perfumes", response_model=PerfumeResponse, tags=["Perfumes"])
async def create_perfume(perfume: PerfumeCreate):
    """Create a new perfume entry manually."""
    try:
        perfume_dict = perfume.model_dump()
        result = await insert_perfume(perfume_dict)
        if not result:
            raise HTTPException(status_code=500, detail="Failed to create perfume")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating perfume: {str(e)}")


# Scraper endpoints (no authentication required)
@app.post("/scrape", response_model=ScrapeResponse, tags=["Scraper"])
async def scrape_perfumes(scrape_request: ScrapeRequest):
    """Trigger perfume scraping from Fragrantica."""
    try:
        limit = scrape_request.limit
        print(f"🔍 Starting scrape for {limit} perfumes")
        perfumes = await asyncio.to_thread(scrape_fragrantica, limit=limit)
        if not perfumes:
            return {"status": "warning", "message": "No perfumes were scraped", "scraped_count": 0, "inserted_count": 0, "perfumes": []}
        inserted_count = await insert_perfumes_batch(perfumes)
        return {"status": "success", "message": f"Successfully scraped and stored perfumes", "scraped_count": len(perfumes), "inserted_count": inserted_count, "perfumes": perfumes[:5]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during scraping: {str(e)}")


@app.post("/scrape/brand", response_model=ScrapeResponse, tags=["Scraper"])
async def scrape_brand(scrape_request: ScrapeBrandRequest):
    """Scrape perfumes from a specific brand on Fragrantica."""
    try:
        brand_name = scrape_request.brand_name
        limit = scrape_request.limit
        print(f"🔍 Starting brand scrape for '{brand_name}' with limit {limit}")
        perfumes = await asyncio.to_thread(scrape_fragrantica_by_brand, brand_name, limit=limit)
        if not perfumes:
            return {"status": "warning", "message": f"No perfumes were scraped for brand '{brand_name}'", "scraped_count": 0, "inserted_count": 0, "perfumes": []}
        inserted_count = await insert_perfumes_batch(perfumes)
        return {"status": "success", "message": f"Successfully scraped {len(perfumes)} perfumes from '{brand_name}'", "scraped_count": len(perfumes), "inserted_count": inserted_count, "perfumes": perfumes[:5]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during brand scraping: {str(e)}")


@app.post("/scrape/brands", response_model=ScrapeResponse, tags=["Scraper"])
async def scrape_multiple_brands(scrape_request: ScrapeBrandsRequest):
    """Scrape perfumes from multiple brands on Fragrantica."""
    try:
        brands = scrape_request.brands
        limit_per_brand = scrape_request.limit_per_brand
        if not brands:
            return {"status": "error", "message": "No brands provided", "scraped_count": 0, "inserted_count": 0, "perfumes": []}
        print(f"🔍 Starting multi-brand scrape for {len(brands)} brands with {limit_per_brand} perfumes each")
        print(f"📋 Brands: {', '.join(brands)}")
        perfumes = await asyncio.to_thread(scrape_fragrantica_brands, brands, limit_per_brand=limit_per_brand)
        if not perfumes:
            return {"status": "warning", "message": "No perfumes were scraped from the specified brands", "scraped_count": 0, "inserted_count": 0, "perfumes": []}
        inserted_count = await insert_perfumes_batch(perfumes)
        return {"status": "success", "message": f"Successfully scraped {len(perfumes)} perfumes from {len(brands)} brands", "scraped_count": len(perfumes), "inserted_count": inserted_count, "perfumes": perfumes[:5]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during multi-brand scraping: {str(e)}")


@app.post("/scrape/url", response_model=ScrapeResponse, tags=["Scraper"])
async def scrape_by_url(scrape_request: ScrapeUrlRequest):
    """Scrape a specific perfume by its direct Fragrantica URL."""
    try:
        perfume_url = scrape_request.perfume_url
        if not perfume_url or 'fragrantica.com/perfume/' not in perfume_url:
            return {"status": "error", "message": f"Invalid Fragrantica perfume URL: {perfume_url}", "scraped_count": 0, "inserted_count": 0, "perfumes": []}
        print(f"🔍 Starting URL scrape for '{perfume_url}'")
        perfume = await asyncio.to_thread(scrape_fragrantica_by_url, perfume_url)
        if not perfume:
            return {"status": "error", "message": f"Failed to scrape perfume from URL: {perfume_url}", "scraped_count": 0, "inserted_count": 0, "perfumes": []}
        inserted_count = await insert_perfumes_batch([perfume])
        return {"status": "success", "message": f"Successfully scraped '{perfume.get('name', 'Unknown')}' by {perfume.get('brand', 'Unknown')}", "scraped_count": 1, "inserted_count": inserted_count, "perfumes": [perfume]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error during URL scraping: {str(e)}")


# Statistics endpoint
@app.get("/stats", tags=["Statistics"])
async def get_stats():
    """Get database statistics."""
    try:
        total_perfumes = await get_perfume_count()
        return {
            "total_perfumes": total_perfumes,
            "database": "Supabase PostgreSQL",
            "source": "Fragrantica.com"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")



# ── SUPABASE-BACKED FRAGRANCE ENDPOINTS ──────────────────────────────────────
# These replace the Fragella proxy for browsing — reads from your local DB,
# zero Fragella quota usage. Run import_fragella.py once to populate.

from supabase import create_client as _create_sb_client

def _get_sb():
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        raise HTTPException(status_code=503, detail="Supabase not configured")
    return _create_sb_client(url, key)


@app.get("/sillage/fragrances", tags=["Sillage DB"])
async def sillage_fragrances(
    search: Optional[str] = Query(None, description="Search name or brand"),
    gender: Optional[str] = Query(None, description="men | women | unisex"),
    brand:  Optional[str] = Query(None, description="Exact brand name"),
    limit:  int           = Query(48, ge=1, le=500),
    offset: int           = Query(0, ge=0),
):
    """Browse fragrances from Supabase — fast, no quota."""
    sb = _get_sb()
    q  = sb.table("fragrances").select(
        "id,name,brand,year,gender,rating,longevity,sillage,oil_type,"
        "image_url,purchase_url,accords,accord_pct,notes_top,notes_middle,"
        "notes_base,popularity,country,price,seasons"
    )

    if search:
        # Use RPC function to search across JSONB columns (notes, accords) via cast to text
        rpc_result = sb.rpc("search_fragrances", {"search_term": search}).execute()
        rows = rpc_result.data or []

        # Apply gender/brand filters in Python since we are post-RPC
        if gender:
            rows = [r for r in rows if (r.get("gender") or "").lower() == gender.lower()]
        if brand:
            rows = [r for r in rows if brand.lower() in (r.get("brand") or "").lower()]

        # Sort by rating descending and apply pagination
        rows.sort(key=lambda r: r.get("rating") or 0, reverse=True)
        rows = rows[offset: offset + limit]
    else:
        if gender:
            q = q.eq("gender", gender.lower())
        if brand:
            q = q.ilike("brand", f"%{brand}%")

        q = q.order("rating", desc=True, nullsfirst=False)
        q = q.range(offset, offset + limit - 1)

        result = q.execute()
        rows   = result.data or []

    # Parse JSON strings back to lists/dicts
    import json as _json
    for row in rows:
        for field in ("accords","accord_pct","notes_top","notes_middle","notes_base","seasons"):
            if isinstance(row.get(field), str):
                try: row[field] = _json.loads(row[field])
                except: row[field] = []

    return {"total": len(rows), "offset": offset, "limit": limit, "fragrances": rows}


@app.get("/sillage/fragrances/count", tags=["Sillage DB"])
async def sillage_count():
    """Total fragrances in Supabase."""
    sb = _get_sb()
    r  = sb.table("fragrances").select("id", count="exact").execute()
    return {"count": r.count}


@app.get("/sillage/brands", tags=["Sillage DB"])
async def sillage_brands():
    """All distinct brands in Supabase."""
    sb = _get_sb()
    r  = sb.table("fragrances").select("brand").execute()
    brands = sorted(set(row["brand"] for row in (r.data or []) if row.get("brand")))
    return {"brands": brands, "count": len(brands)}


@app.post("/admin/import", tags=["Admin"])
async def trigger_import(background_tasks: __import__('fastapi').BackgroundTasks):
    """Trigger a background re-import from Fragella into Supabase.
    Only call this when you want to refresh the database."""
    import subprocess, sys
    def run():
        subprocess.run([sys.executable, "import_fragella.py"], check=False)
    background_tasks.add_task(run)
    return {"status": "Import started in background — check Railway logs for progress"}


# ── FRAGELLA PROXY (kept for one-time imports / admin use) ─────────────────
# Forwards requests to Fragella API server-side (avoids browser CORS restrictions)

import httpx

FRAGELLA_BASE = "https://api.fragella.com/api/v1"
FRAGELLA_KEY  = os.getenv("FRAGELLA_KEY", "")


@app.get("/fragella/fragrances", tags=["Fragella Proxy"])
async def fragella_fragrances(
    search: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    limit:  int           = Query(50, ge=1, le=500),
):
    """Proxy: GET /api/v1/fragrances from Fragella."""
    params = {"limit": limit}
    if search: params["search"] = search
    if gender: params["gender"] = gender
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            f"{FRAGELLA_BASE}/fragrances",
            params=params,
            headers={"x-api-key": FRAGELLA_KEY},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()



@app.get("/fragella/brands/{brand_name}", tags=["Fragella Proxy"])
async def fragella_brand(
    brand_name: str,
    limit: int = Query(500, ge=1, le=500),
):
    """Proxy: GET /api/v1/brands/{brandName} — all fragrances for a house."""
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            f"{FRAGELLA_BASE}/brands/{brand_name}",
            params={"limit": limit},
            headers={"x-api-key": FRAGELLA_KEY},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@app.get("/fragella/fragrances/match", tags=["Fragella Proxy"])
async def fragella_match(
    accords: Optional[str] = Query(None),
    top:     Optional[str] = Query(None),
    limit:   int           = Query(20, ge=1, le=100),
):
    """Proxy: GET /api/v1/fragrances/match from Fragella."""
    params = {"limit": limit}
    if accords: params["accords"] = accords
    if top:     params["top"] = top
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            f"{FRAGELLA_BASE}/fragrances/match",
            params=params,
            headers={"x-api-key": FRAGELLA_KEY},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


@app.get("/fragella/fragrances/similar", tags=["Fragella Proxy"])
async def fragella_similar(
    name:  str = Query(...),
    limit: int = Query(6, ge=1, le=50),
):
    """Proxy: GET /api/v1/fragrances/similar from Fragella."""
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(
            f"{FRAGELLA_BASE}/fragrances/similar",
            params={"name": name, "limit": limit},
            headers={"x-api-key": FRAGELLA_KEY},
        )
    if r.status_code != 200:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 9000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
