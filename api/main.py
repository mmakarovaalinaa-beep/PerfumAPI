"""
FastAPI application for Perfume Data API.
Serves scraped perfume data from Supabase with authentication.
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import os
import sys

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
from utils.auth import get_current_user, verify_admin
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
# Allow frontend URL from environment variable
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
allowed_origins = [
    frontend_url,
    "http://localhost:5173",  # Local development
    "http://localhost:3000",  # Alternative local port
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
    perfume_url: str = Field(..., description="Direct URL to a Fragrantica perfume page (e.g., 'https://www.fragrantica.com/perfume/Xerjoff/White-On-White-Three-76333.html')")


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


# Health check endpoint
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
            "scrape": "/scrape (auth required)",
            "scrape_brand": "/scrape/brand (auth required)",
            "scrape_brands": "/scrape/brands (auth required)",
            "scrape_url": "/scrape/url (auth required)"
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


# Public endpoints (no authentication required)
@app.get("/perfumes", response_model=PerfumeListResponse, tags=["Perfumes"])
async def list_perfumes(
    limit: int = Query(default=100, ge=1, le=500, description="Number of perfumes to return"),
    offset: int = Query(default=0, ge=0, description="Number of perfumes to skip")
):
    """
    Get list of all perfumes with pagination.
    
    - **limit**: Maximum number of perfumes to return (1-500)
    - **offset**: Number of perfumes to skip for pagination
    """
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
    """
    Get a specific perfume by ID.
    
    - **perfume_id**: UUID of the perfume
    """
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
    """
    Search perfumes by name or brand.
    
    - **query**: Search term (searches in name and brand)
    - **limit**: Maximum number of results to return
    """
    try:
        perfumes = await search_perfumes(query, limit=limit)
        return perfumes
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching perfumes: {str(e)}")


# Protected endpoints (authentication required)
@app.post("/perfumes", response_model=PerfumeResponse, tags=["Perfumes (Auth Required)"])
async def create_perfume(
    perfume: PerfumeCreate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new perfume entry manually.
    
    **Requires authentication**: Include `Authorization: Bearer <token>` header.
    """
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


@app.post("/scrape", response_model=ScrapeResponse, tags=["Scraper (Auth Required)"])
async def scrape_perfumes(
    scrape_request: ScrapeRequest,
    current_user: Dict[str, Any] = Depends(verify_admin)
):
    """
    Trigger perfume scraping from Fragrantica.
    
    **Requires authentication**: Include `Authorization: Bearer <token>` header.
    
    - **limit**: Number of perfumes to scrape (default: 2, max: 1000)
    
    This endpoint will:
    1. Scrape perfume data from Fragrantica
    2. Save the data to data.json
    3. Insert the data into Supabase database
    
    ⚠️ **Warning**: Scraping large numbers may take time. Start with small limits for testing.
    """
    try:
        limit = scrape_request.limit
        
        print(f"🔍 Starting scrape for {limit} perfumes (requested by user {current_user.get('id', 'unknown')})")
        
        # Run the scraper
        perfumes = scrape_fragrantica(limit=limit)
        
        if not perfumes:
            return {
                "status": "warning",
                "message": "No perfumes were scraped",
                "scraped_count": 0,
                "inserted_count": 0,
                "perfumes": []
            }
        
        # Insert into database
        inserted_count = await insert_perfumes_batch(perfumes)
        
        return {
            "status": "success",
            "message": f"Successfully scraped and stored perfumes",
            "scraped_count": len(perfumes),
            "inserted_count": inserted_count,
            "perfumes": perfumes[:5]  # Return first 5 as preview
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during scraping: {str(e)}"
        )


@app.post("/scrape/brand", response_model=ScrapeResponse, tags=["Scraper (Auth Required)"])
async def scrape_brand(
    scrape_request: ScrapeBrandRequest,
    current_user: Dict[str, Any] = Depends(verify_admin)
):
    """
    Scrape perfumes from a specific brand on Fragrantica.
    
    **Requires authentication**: Include `Authorization: Bearer <token>` header.
    
    - **brand_name**: Name of the brand (e.g., "Jean Paul Gaultier", "Xerjoff", "Creed")
    - **limit**: Number of perfumes to scrape from this brand (default: 10, max: 500)
    
    This endpoint will:
    1. Scrape perfume data for the specified brand from Fragrantica
    2. Save the data to data.json
    3. Insert the data into Supabase database
    
    ⚠️ **Warning**: Scraping may take time depending on the limit. Start with small limits for testing.
    """
    try:
        brand_name = scrape_request.brand_name
        limit = scrape_request.limit
        
        print(f"🔍 Starting brand scrape for '{brand_name}' with limit {limit} (requested by user {current_user.get('id', 'unknown')})")
        
        # Run the brand scraper
        perfumes = scrape_fragrantica_by_brand(brand_name, limit=limit)
        
        if not perfumes:
            return {
                "status": "warning",
                "message": f"No perfumes were scraped for brand '{brand_name}'",
                "scraped_count": 0,
                "inserted_count": 0,
                "perfumes": []
            }
        
        # Insert into database
        inserted_count = await insert_perfumes_batch(perfumes)
        
        return {
            "status": "success",
            "message": f"Successfully scraped {len(perfumes)} perfumes from '{brand_name}'",
            "scraped_count": len(perfumes),
            "inserted_count": inserted_count,
            "perfumes": perfumes[:5]  # Return first 5 as preview
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during brand scraping: {str(e)}"
        )


@app.post("/scrape/brands", response_model=ScrapeResponse, tags=["Scraper (Auth Required)"])
async def scrape_multiple_brands(
    scrape_request: ScrapeBrandsRequest,
    current_user: Dict[str, Any] = Depends(verify_admin)
):
    """
    Scrape perfumes from multiple brands on Fragrantica.
    
    **Requires authentication**: Include `Authorization: Bearer <token>` header.
    
    - **brands**: List of brand names (e.g., ["Jean Paul Gaultier", "Xerjoff", "Creed"])
    - **limit_per_brand**: Number of perfumes to scrape per brand (default: 10, max: 200)
    
    This endpoint will:
    1. Scrape perfume data for all specified brands from Fragrantica
    2. Save the combined data to data.json
    3. Insert all data into Supabase database
    
    ⚠️ **Warning**: Scraping multiple brands may take significant time. 
    The total scraping time = (number of brands) × (limit per brand) × (time per perfume).
    """
    try:
        brands = scrape_request.brands
        limit_per_brand = scrape_request.limit_per_brand
        
        if not brands:
            return {
                "status": "error",
                "message": "No brands provided",
                "scraped_count": 0,
                "inserted_count": 0,
                "perfumes": []
            }
        
        print(f"🔍 Starting multi-brand scrape for {len(brands)} brands with {limit_per_brand} perfumes each (requested by user {current_user.get('id', 'unknown')})")
        print(f"📋 Brands: {', '.join(brands)}")
        
        # Run the multi-brand scraper
        perfumes = scrape_fragrantica_brands(brands, limit_per_brand=limit_per_brand)
        
        if not perfumes:
            return {
                "status": "warning",
                "message": f"No perfumes were scraped from the specified brands",
                "scraped_count": 0,
                "inserted_count": 0,
                "perfumes": []
            }
        
        # Insert into database
        inserted_count = await insert_perfumes_batch(perfumes)
        
        return {
            "status": "success",
            "message": f"Successfully scraped {len(perfumes)} perfumes from {len(brands)} brands",
            "scraped_count": len(perfumes),
            "inserted_count": inserted_count,
            "perfumes": perfumes[:5]  # Return first 5 as preview
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during multi-brand scraping: {str(e)}"
        )


@app.post("/scrape/url", response_model=ScrapeResponse, tags=["Scraper (Auth Required)"])
async def scrape_by_url(
    scrape_request: ScrapeUrlRequest,
    current_user: Dict[str, Any] = Depends(verify_admin)
):
    """
    Scrape a specific perfume by its direct Fragrantica URL.
    
    **Requires authentication**: Include `Authorization: Bearer <token>` header.
    
    - **perfume_url**: Direct URL to a Fragrantica perfume page 
      (e.g., "https://www.fragrantica.com/perfume/Xerjoff/White-On-White-Three-76333.html")
    
    This endpoint will:
    1. Scrape perfume data from the specified URL
    2. Save the data to data.json
    3. Insert the data into Supabase database
    
    ⚠️ **Note**: This is the fastest scraping method as it only fetches one perfume page.
    """
    try:
        perfume_url = scrape_request.perfume_url
        
        # Validate URL
        if not perfume_url or 'fragrantica.com/perfume/' not in perfume_url:
            return {
                "status": "error",
                "message": f"Invalid Fragrantica perfume URL: {perfume_url}",
                "scraped_count": 0,
                "inserted_count": 0,
                "perfumes": []
            }
        
        print(f"🔍 Starting URL scrape for '{perfume_url}' (requested by user {current_user.get('id', 'unknown')})")
        
        # Run the URL scraper
        perfume = scrape_fragrantica_by_url(perfume_url)
        
        if not perfume:
            return {
                "status": "error",
                "message": f"Failed to scrape perfume from URL: {perfume_url}",
                "scraped_count": 0,
                "inserted_count": 0,
                "perfumes": []
            }
        
        # Insert into database
        inserted_count = await insert_perfumes_batch([perfume])
        
        return {
            "status": "success",
            "message": f"Successfully scraped '{perfume.get('name', 'Unknown')}' by {perfume.get('brand', 'Unknown')}",
            "scraped_count": 1,
            "inserted_count": inserted_count,
            "perfumes": [perfume]  # Return the scraped perfume
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error during URL scraping: {str(e)}"
        )


# Statistics endpoint (public)
@app.get("/stats", tags=["Statistics"])
async def get_stats():
    """
    Get database statistics.
    """
    try:
        total_perfumes = await get_perfume_count()
        
        return {
            "total_perfumes": total_perfumes,
            "database": "Supabase PostgreSQL",
            "source": "Fragrantica.com"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching stats: {str(e)}")


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return {
        "error": "Not Found",
        "message": "The requested resource was not found",
        "path": str(request.url)
    }


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    return {
        "error": "Internal Server Error",
        "message": "An unexpected error occurred",
        "path": str(request.url)
    }


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    port = int(os.getenv("PORT", 9000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

