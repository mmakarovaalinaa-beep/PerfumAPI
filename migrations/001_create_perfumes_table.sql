-- Migration: Create perfumes table
-- Run this in Supabase SQL Editor if auto-migration doesn't work

-- Create perfumes table
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

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_perfumes_url ON perfumes(perfume_url);
CREATE INDEX IF NOT EXISTS idx_perfumes_brand ON perfumes(brand);
CREATE INDEX IF NOT EXISTS idx_perfumes_name ON perfumes(name);
CREATE INDEX IF NOT EXISTS idx_perfumes_created_at ON perfumes(created_at DESC);

-- Optional: Enable Row Level Security (RLS)
-- Uncomment if you want to restrict database access through Supabase policies
-- ALTER TABLE perfumes ENABLE ROW LEVEL SECURITY;

-- Create a policy to allow read access to everyone
-- CREATE POLICY "Allow public read access" ON perfumes
--     FOR SELECT
--     USING (true);

-- Create a policy to allow authenticated users to insert
-- CREATE POLICY "Allow authenticated insert" ON perfumes
--     FOR INSERT
--     TO authenticated
--     WITH CHECK (true);

-- Create a policy to allow authenticated users to update
-- CREATE POLICY "Allow authenticated update" ON perfumes
--     FOR UPDATE
--     TO authenticated
--     USING (true);

COMMENT ON TABLE perfumes IS 'Stores perfume data scraped from Fragrantica';
COMMENT ON COLUMN perfumes.notes_top IS 'Array of top notes';
COMMENT ON COLUMN perfumes.notes_middle IS 'Array of middle/heart notes';
COMMENT ON COLUMN perfumes.notes_base IS 'Array of base notes';
COMMENT ON COLUMN perfumes.perfume_url IS 'Original Fragrantica URL (unique)';

