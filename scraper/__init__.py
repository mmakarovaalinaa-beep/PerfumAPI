"""Scraper package for Fragrantica perfume data."""

from .scrape import (
    FragranticaScraper,
    scrape_fragrantica,
    scrape_fragrantica_by_brand,
    scrape_fragrantica_brands
)

__all__ = [
    'FragranticaScraper',
    'scrape_fragrantica',
    'scrape_fragrantica_by_brand',
    'scrape_fragrantica_brands'
]
