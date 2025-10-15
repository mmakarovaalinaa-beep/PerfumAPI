"""
Database utilities for Supabase integration.
Handles table creation, migrations, and CRUD operations for perfumes.
"""

import os
from typing import List, Optional, Dict, Any
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


async def run_migration():
    """
    Auto-migration: Creates the perfumes table if it doesn't exist.
    This runs on application startup.
    """
    try:
        # SQL to create the perfumes table
        migration_sql = """
        CREATE TABLE IF NOT EXISTS perfumes (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            name TEXT NOT NULL,
            brand TEXT,
            release_year INTEGER,
            gender TEXT,
            notes_top TEXT[],
            notes_middle TEXT[],
            notes_base TEXT[],
            rating REAL,
            votes INTEGER,
            description TEXT,
            longevity TEXT,
            sillage TEXT,
            image_url TEXT,
            perfume_url TEXT UNIQUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
        );
        
        -- Create index on perfume_url for faster lookups
        CREATE INDEX IF NOT EXISTS idx_perfumes_url ON perfumes(perfume_url);
        
        -- Create index on brand for filtering
        CREATE INDEX IF NOT EXISTS idx_perfumes_brand ON perfumes(brand);
        """
        
        # Execute migration using raw SQL
        response = supabase.rpc('exec_sql', {'sql': migration_sql}).execute()
        print("✅ Database migration completed successfully")
        return True
        
    except Exception as e:
        # Table might already exist or we're using a different approach
        print(f"⚠️  Migration note: {str(e)}")
        print("💡 If table doesn't exist, create it manually in Supabase SQL Editor with:")
        print("""
        CREATE TABLE IF NOT EXISTS perfumes (
            id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            name TEXT NOT NULL,
            brand TEXT,
            release_year INTEGER,
            gender TEXT,
            notes_top TEXT[],
            notes_middle TEXT[],
            notes_base TEXT[],
            rating REAL,
            votes INTEGER,
            description TEXT,
            longevity TEXT,
            sillage TEXT,
            image_url TEXT,
            perfume_url TEXT UNIQUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
        );
        """)
        return False


async def insert_perfume(perfume_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Insert a single perfume into the database.
    
    Args:
        perfume_data: Dictionary containing perfume information
        
    Returns:
        Inserted perfume data or None if failed
    """
    try:
        response = supabase.table("perfumes").insert(perfume_data).execute()
        if response.data:
            print(f"✅ Inserted perfume: {perfume_data.get('name', 'Unknown')}")
            return response.data[0]
        return None
    except Exception as e:
        print(f"❌ Error inserting perfume {perfume_data.get('name', 'Unknown')}: {str(e)}")
        return None


async def insert_perfumes_batch(perfumes: List[Dict[str, Any]]) -> int:
    """
    Insert multiple perfumes into the database.
    Uses upsert to avoid duplicates based on perfume_url.
    
    Args:
        perfumes: List of perfume dictionaries
        
    Returns:
        Number of successfully inserted perfumes
    """
    try:
        # Use upsert to handle duplicates gracefully
        response = supabase.table("perfumes").upsert(
            perfumes,
            on_conflict="perfume_url"
        ).execute()
        
        count = len(response.data) if response.data else 0
        print(f"✅ Inserted/updated {count} perfumes")
        return count
        
    except Exception as e:
        print(f"❌ Error batch inserting perfumes: {str(e)}")
        # Try inserting one by one as fallback
        success_count = 0
        for perfume in perfumes:
            result = await insert_perfume(perfume)
            if result:
                success_count += 1
        return success_count


async def get_all_perfumes(limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
    """
    Retrieve all perfumes from the database with pagination.
    
    Args:
        limit: Maximum number of perfumes to return (default 100)
        offset: Number of perfumes to skip (default 0)
        
    Returns:
        List of perfume dictionaries
    """
    try:
        response = supabase.table("perfumes")\
            .select("*")\
            .order("created_at", desc=True)\
            .range(offset, offset + limit - 1)\
            .execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        print(f"❌ Error fetching perfumes: {str(e)}")
        return []


async def get_perfume_by_id(perfume_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single perfume by its ID.
    
    Args:
        perfume_id: UUID of the perfume
        
    Returns:
        Perfume dictionary or None if not found
    """
    try:
        response = supabase.table("perfumes")\
            .select("*")\
            .eq("id", perfume_id)\
            .execute()
        
        if response.data and len(response.data) > 0:
            return response.data[0]
        return None
        
    except Exception as e:
        print(f"❌ Error fetching perfume {perfume_id}: {str(e)}")
        return None


async def search_perfumes(query: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Search perfumes by name or brand.
    
    Args:
        query: Search query string
        limit: Maximum number of results
        
    Returns:
        List of matching perfume dictionaries
    """
    try:
        response = supabase.table("perfumes")\
            .select("*")\
            .or_(f"name.ilike.%{query}%,brand.ilike.%{query}%")\
            .limit(limit)\
            .execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        print(f"❌ Error searching perfumes: {str(e)}")
        return []


async def get_perfume_count() -> int:
    """
    Get total count of perfumes in database.
    
    Returns:
        Total number of perfumes
    """
    try:
        response = supabase.table("perfumes")\
            .select("id", count="exact")\
            .execute()
        
        return response.count if hasattr(response, 'count') else 0
        
    except Exception as e:
        print(f"❌ Error counting perfumes: {str(e)}")
        return 0


def get_supabase_client() -> Client:
    """
    Get the Supabase client instance.
    
    Returns:
        Supabase client
    """
    return supabase

