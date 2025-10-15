"""
Fragrantica perfume scraper.
Extracts perfume data from Fragrantica.com for educational purposes.
"""

import requests
from bs4 import BeautifulSoup
import time
import json
import os
from typing import List, Dict, Any, Optional
import re
import random


class FragranticaScraper:
    """
    Scraper for Fragrantica.com perfume database.
    Respects rate limiting and handles errors gracefully.
    """
    
    def __init__(self, delay: float = 5.0):
        """
        Initialize the scraper.
        
        Args:
            delay: Minimum delay between requests in seconds (default 5.0)
        """
        self.delay = delay
        self.max_retries = 5
        self.retry_delay = 30  # Initial retry delay for 429 errors
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.fragrantica.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'max-age=0'
        })
        self.base_url = "https://www.fragrantica.com"
    
    def _get_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        Fetch and parse a web page with retry logic for rate limiting.
        
        Args:
            url: URL to fetch
            
        Returns:
            BeautifulSoup object or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                print(f"📡 Fetching: {url}")
                response = self.session.get(url, timeout=15)
                
                # Handle rate limiting (429 Too Many Requests)
                if response.status_code == 429:
                    retry_delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"⚠️  Rate limited (429). Waiting {retry_delay} seconds before retry {attempt + 1}/{self.max_retries}...")
                    time.sleep(retry_delay)
                    continue
                
                response.raise_for_status()
                
                # Add random delay to appear more human-like (delay ± 50%)
                actual_delay = self.delay + random.uniform(-self.delay * 0.5, self.delay * 0.5)
                actual_delay = max(2.0, actual_delay)  # Ensure minimum 2 seconds
                print(f"⏳ Waiting {actual_delay:.1f} seconds...")
                time.sleep(actual_delay)
                
                # Use response.text to let requests handle encoding/decompression
                return BeautifulSoup(response.text, 'html.parser')
                
            except requests.exceptions.HTTPError as e:
                if response.status_code == 429 and attempt < self.max_retries - 1:
                    # Already handled above, continue to next attempt
                    continue
                print(f"❌ HTTP Error fetching {url}: {str(e)}")
                return None
            except Exception as e:
                print(f"❌ Error fetching {url}: {str(e)}")
                if attempt < self.max_retries - 1:
                    print(f"🔄 Retrying in {self.delay} seconds...")
                    time.sleep(self.delay)
                    continue
                return None
        
        print(f"❌ Failed to fetch {url} after {self.max_retries} attempts")
        return None
    
    def get_popular_perfumes_urls(self, limit: int = 1000) -> List[str]:
        """
        Get URLs of popular perfumes from search page.
        
        Args:
            limit: Maximum number of perfume URLs to retrieve
            
        Returns:
            List of perfume URLs
        """
        perfume_urls = []
        page = 1
        
        print(f"🔍 Searching for up to {limit} popular perfumes...")
        
        while len(perfume_urls) < limit:
            # Fragrantica search URL for most popular perfumes
            search_url = f"{self.base_url}/search/"
            
            if page > 1:
                search_url = f"{self.base_url}/search/?page={page}"
            
            soup = self._get_page(search_url)
            if not soup:
                break
            
            # Find all perfume links with pattern /perfume/Brand/Name-ID.html
            # This pattern matches actual perfume detail pages
            perfume_links = soup.find_all('a', href=re.compile(r'/perfume/[^/]+/[^/]+\.html'))
            
            if not perfume_links:
                print(f"⚠️  No more perfumes found on page {page}")
                break
            
            found_on_page = 0
            for link in perfume_links:
                perfume_url = link.get('href', '')
                
                # Skip if not a valid perfume URL
                if not perfume_url or '/perfume/' not in perfume_url:
                    continue
                
                # Convert to full URL if needed
                if not perfume_url.startswith('http'):
                    perfume_url = self.base_url + perfume_url
                
                # Add if not already in list
                if perfume_url not in perfume_urls:
                    perfume_urls.append(perfume_url)
                    found_on_page += 1
                    print(f"  Found perfume {len(perfume_urls)}: {perfume_url}")
                    
                    if len(perfume_urls) >= limit:
                        break
            
            # If no new perfumes found on this page, stop
            if found_on_page == 0:
                print(f"⚠️  No new perfumes found on page {page}")
                break
            
            page += 1
            
            # Safety limit: don't scrape more than 50 pages
            if page > 50:
                print("⚠️  Reached page limit (50)")
                break
        
        print(f"✅ Found {len(perfume_urls)} perfume URLs")
        return perfume_urls[:limit]
    
    def get_brand_perfumes_urls(self, brand_name: str, limit: int = 100) -> List[str]:
        """
        Get URLs of perfumes from a specific brand.
        
        Args:
            brand_name: Name of the brand (e.g., "Jean Paul Gaultier", "Xerjoff")
            limit: Maximum number of perfume URLs to retrieve
            
        Returns:
            List of perfume URLs for the specified brand
        """
        perfume_urls = []
        page = 1
        
        # Format brand name for URL: replace spaces with hyphens, keep other characters
        # Examples: "Jean Paul Gaultier" -> "Jean-Paul-Gaultier"
        #           "Xerjoff" -> "Xerjoff"
        formatted_brand = brand_name.replace(' ', '-')
        
        print(f"🔍 Searching for perfumes by {brand_name} (up to {limit})...")
        
        while len(perfume_urls) < limit:
            # Fragrantica brand page URL pattern: /designers/{Brand}.html
            # Pagination: appends #page{N} for pages 2+
            if page == 1:
                brand_url = f"{self.base_url}/designers/{formatted_brand}.html"
            else:
                brand_url = f"{self.base_url}/designers/{formatted_brand}.html#page{page}"
            
            soup = self._get_page(brand_url)
            if not soup:
                break
            
            # Find all perfume links with pattern /perfume/Brand/Name-ID.html
            perfume_links = soup.find_all('a', href=re.compile(r'/perfume/[^/]+/[^/]+\.html'))
            
            if not perfume_links:
                print(f"⚠️  No more perfumes found on page {page}")
                break
            
            found_on_page = 0
            for link in perfume_links:
                perfume_url = link.get('href', '')
                
                # Skip if not a valid perfume URL
                if not perfume_url or '/perfume/' not in perfume_url:
                    continue
                
                # Convert to full URL if needed
                if not perfume_url.startswith('http'):
                    perfume_url = self.base_url + perfume_url
                
                # Add if not already in list
                if perfume_url not in perfume_urls:
                    perfume_urls.append(perfume_url)
                    found_on_page += 1
                    print(f"  Found perfume {len(perfume_urls)}: {perfume_url}")
                    
                    if len(perfume_urls) >= limit:
                        break
            
            # If no new perfumes found on this page, stop
            if found_on_page == 0:
                print(f"⚠️  No new perfumes found on page {page}")
                break
            
            page += 1
            
            # Safety limit: don't scrape more than 50 pages
            if page > 50:
                print("⚠️  Reached page limit (50)")
                break
        
        print(f"✅ Found {len(perfume_urls)} perfume URLs for {brand_name}")
        return perfume_urls[:limit]
    
    def extract_perfume_details(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract detailed information from a perfume page.
        
        Args:
            url: Perfume detail page URL
            
        Returns:
            Dictionary with perfume data or None if failed
        """
        soup = self._get_page(url)
        if not soup:
            return None
        
        try:
            perfume_data = {
                'perfume_url': url,
                'name': None,
                'brand': None,
                'release_year': None,
                'gender': None,
                'notes_top': [],
                'notes_middle': [],
                'notes_base': [],
                'rating': None,
                'votes': None,
                'description': None,
                'longevity': None,
                'sillage': None,
                'image_url': None
            }
            
            # Extract name and gender from h1 title
            name_tag = soup.find('h1', itemprop='name')
            if name_tag:
                full_title = name_tag.get_text(strip=True)
                
                # Extract gender from title
                if 'for women and men' in full_title.lower():
                    perfume_data['gender'] = 'Unisex'
                    clean_name = re.sub(r'\s*for women and men\s*', '', full_title, flags=re.IGNORECASE)
                elif 'for women' in full_title.lower():
                    perfume_data['gender'] = 'Women'
                    clean_name = re.sub(r'\s*for women\s*', '', full_title, flags=re.IGNORECASE)
                elif 'for men' in full_title.lower():
                    perfume_data['gender'] = 'Men'
                    clean_name = re.sub(r'\s*for men\s*', '', full_title, flags=re.IGNORECASE)
                elif 'for unisex' in full_title.lower():
                    perfume_data['gender'] = 'Unisex'
                    clean_name = re.sub(r'\s*for unisex\s*', '', full_title, flags=re.IGNORECASE)
                elif 'for her' in full_title.lower():
                    perfume_data['gender'] = 'Women'
                    clean_name = re.sub(r'\s*for her\s*', '', full_title, flags=re.IGNORECASE)
                elif 'for him' in full_title.lower():
                    perfume_data['gender'] = 'Men'
                    clean_name = re.sub(r'\s*for him\s*', '', full_title, flags=re.IGNORECASE)
                else:
                    clean_name = full_title
                
                # Clean up the name (remove extra spaces and fix spacing issues)
                clean_name = re.sub(r'\s+', ' ', clean_name.strip())
                perfume_data['name'] = clean_name
            
            # Extract brand
            brand_tag = soup.find('span', itemprop='name')
            if not brand_tag:
                brand_tag = soup.find('a', class_='brand')
            if brand_tag:
                perfume_data['brand'] = brand_tag.get_text(strip=True)
            
            # Extract release year
            year_info = soup.find('div', text=re.compile(r'^\d{4}$'))
            if not year_info:
                # Look in the main info section
                main_info = soup.find('div', class_='main-info')
                if main_info:
                    year_match = re.search(r'\b(19|20)\d{2}\b', main_info.get_text())
                    if year_match:
                        perfume_data['release_year'] = int(year_match.group())
                
                # If still not found, search in description for launch patterns
                if not perfume_data['release_year']:
                    desc_tag = soup.find('div', itemprop='description')
                    if not desc_tag:
                        desc_tag = soup.find('div', class_='text-description')
                    if desc_tag:
                        desc_text = desc_tag.get_text()
                        # Look for patterns like "launched in 2022", "released in 2022", "was 2022"
                        launch_patterns = [
                            r'launched in (\d{4})',
                            r'released in (\d{4})', 
                            r'was launched in (\d{4})',
                            r'was released in (\d{4})',
                            r'\bwas (\d{4})\b'
                        ]
                        for pattern in launch_patterns:
                            match = re.search(pattern, desc_text, re.IGNORECASE)
                            if match:
                                year = int(match.group(1))
                                if 1900 <= year <= 2030:  # Reasonable year range
                                    perfume_data['release_year'] = year
                                    break
            else:
                try:
                    perfume_data['release_year'] = int(year_info.get_text(strip=True))
                except ValueError:
                    pass
            
            # Gender already extracted from h1 title above, fallback check if not found
            if not perfume_data['gender']:
                gender_tag = soup.find('p', style=re.compile(r'text-align'))
                if gender_tag:
                    gender_text = gender_tag.get_text(strip=True).lower()
                    if 'for women and men' in gender_text or 'unisex' in gender_text or 'for unisex' in gender_text:
                        perfume_data['gender'] = 'Unisex'
                    elif 'for women' in gender_text or 'for her' in gender_text:
                        perfume_data['gender'] = 'Women'
                    elif 'for men' in gender_text or 'for him' in gender_text:
                        perfume_data['gender'] = 'Men'
            
            # Extract notes pyramid using h4 headers (primary method)
            # Top notes
            top_notes_header = soup.find('h4', string=re.compile(r'Top Notes', re.I))
            if top_notes_header:
                # Find the next div after the header that contains the notes
                notes_container = top_notes_header.find_next_sibling('div')
                if notes_container:
                    # Extract note names from links within the container
                    note_links = notes_container.find_all('a', href=re.compile(r'/notes/'))
                    notes = []
                    for link in note_links:
                        note_text = link.get_text(strip=True)
                        if note_text:
                            notes.append(note_text)
                    perfume_data['notes_top'] = notes
            
            # Middle notes
            middle_notes_header = soup.find('h4', string=re.compile(r'Middle Notes', re.I))
            if middle_notes_header:
                notes_container = middle_notes_header.find_next_sibling('div')
                if notes_container:
                    note_links = notes_container.find_all('a', href=re.compile(r'/notes/'))
                    notes = []
                    for link in note_links:
                        note_text = link.get_text(strip=True)
                        if note_text:
                            notes.append(note_text)
                    perfume_data['notes_middle'] = notes
            
            # Base notes
            base_notes_header = soup.find('h4', string=re.compile(r'Base Notes', re.I))
            if base_notes_header:
                notes_container = base_notes_header.find_next_sibling('div')
                if notes_container:
                    note_links = notes_container.find_all('a', href=re.compile(r'/notes/'))
                    notes = []
                    for link in note_links:
                        note_text = link.get_text(strip=True)
                        if note_text:
                            notes.append(note_text)
                    perfume_data['notes_base'] = notes
            
            # Fallback: Extract notes from description text if primary method failed
            if not perfume_data['notes_top'] and not perfume_data['notes_middle'] and not perfume_data['notes_base']:
                desc_tag = soup.find('div', itemprop='description')
                if not desc_tag:
                    desc_tag = soup.find('div', class_='text-description')
                if desc_tag:
                    desc_text = desc_tag.get_text()
                    
                    # Extract top notes
                    top_match = re.search(r'Top notes are ([^;]+)', desc_text, re.IGNORECASE)
                    if top_match:
                        top_notes_text = top_match.group(1)
                        # Split on commas and handle "and" connections
                        notes = re.split(r',|\s+and\s+', top_notes_text)
                        perfume_data['notes_top'] = [note.strip() for note in notes if note.strip()]
                    
                    # Extract middle notes
                    middle_match = re.search(r'middle notes are ([^;]+)', desc_text, re.IGNORECASE)
                    if middle_match:
                        middle_notes_text = middle_match.group(1)
                        notes = re.split(r',|\s+and\s+', middle_notes_text)
                        perfume_data['notes_middle'] = [note.strip() for note in notes if note.strip()]
                        
                    # Extract base notes
                    base_match = re.search(r'base notes are ([^.;]+)', desc_text, re.IGNORECASE)
                    if base_match:
                        base_notes_text = base_match.group(1)
                        notes = re.split(r',|\s+and\s+', base_notes_text)
                        perfume_data['notes_base'] = [note.strip() for note in notes if note.strip()]
            
            # Extract rating and votes
            rating_tag = soup.find('span', itemprop='ratingValue')
            if rating_tag:
                try:
                    perfume_data['rating'] = float(rating_tag.get_text(strip=True))
                except ValueError:
                    pass
            
            votes_tag = soup.find('span', itemprop='ratingCount')
            if votes_tag:
                try:
                    perfume_data['votes'] = int(votes_tag.get_text(strip=True).replace(',', ''))
                except ValueError:
                    pass
            
            # Extract description
            desc_tag = soup.find('div', itemprop='description')
            if not desc_tag:
                desc_tag = soup.find('div', class_='text-description')
            if desc_tag:
                perfume_data['description'] = desc_tag.get_text(strip=True)[:1000]  # Limit length
            
            # Extract longevity rating (0-10 scale)
            # Look for: <p style="color: #83a6c4;">Perfume longevity:<span>2.86</span> out of<span>5</span>.</p>
            blue_p_tags = soup.find_all('p', style=re.compile(r'color:\s*#83a6c4'))
            for p_tag in blue_p_tags:
                p_text = p_tag.get_text()
                if 'perfume longevity:' in p_text.lower():
                    spans = p_tag.find_all('span')
                    if len(spans) >= 2:
                        try:
                            longevity_value = float(spans[0].get_text(strip=True))
                            max_value = float(spans[1].get_text(strip=True))
                            # Convert to 0-10 scale
                            if max_value > 0:
                                perfume_data['longevity'] = round((longevity_value / max_value) * 10, 1)
                        except (ValueError, ZeroDivisionError):
                            pass
                    break
            
            # Extract sillage rating (0-10 scale)  
            # Look for: <p style="color: #83a6c4;">Perfume sillage:<span>2.38</span> out of<span>4</span>.</p>
            for p_tag in blue_p_tags:
                p_text = p_tag.get_text()
                if 'perfume sillage:' in p_text.lower():
                    spans = p_tag.find_all('span')
                    if len(spans) >= 2:
                        try:
                            sillage_value = float(spans[0].get_text(strip=True))
                            max_value = float(spans[1].get_text(strip=True))
                            # Convert to 0-10 scale
                            if max_value > 0:
                                perfume_data['sillage'] = round((sillage_value / max_value) * 10, 1)
                        except (ValueError, ZeroDivisionError):
                            pass
                    break
            
            # Extract image URL
            img_tag = soup.find('img', itemprop='image')
            if img_tag and 'src' in img_tag.attrs:
                perfume_data['image_url'] = img_tag['src']
            
            print(f"✅ Extracted: {perfume_data.get('name', 'Unknown')} by {perfume_data.get('brand', 'Unknown')}")
            return perfume_data
            
        except Exception as e:
            print(f"❌ Error extracting perfume data from {url}: {str(e)}")
            return None
    
    def scrape_perfumes(self, limit: int = 2, save_to_file: bool = True) -> List[Dict[str, Any]]:
        """
        Main scraping function: get perfume URLs and extract details.
        
        Args:
            limit: Number of perfumes to scrape (default 2 for testing)
            save_to_file: Whether to save results to data.json
            
        Returns:
            List of perfume dictionaries
        """
        print(f"🚀 Starting scrape for {limit} perfumes...")
        
        # Visit homepage first to establish session and get cookies
        print("🌐 Establishing session with Fragrantica...")
        try:
            self.session.get(self.base_url, timeout=15)
            time.sleep(3)  # Brief pause after initial connection
        except Exception as e:
            print(f"⚠️  Warning: Could not establish initial session: {e}")
        
        # Get perfume URLs
        urls = self.get_popular_perfumes_urls(limit)
        
        if not urls:
            print("❌ No perfume URLs found")
            return []
        
        # Extract details for each perfume
        perfumes = []
        for i, url in enumerate(urls, 1):
            print(f"\n📋 Processing perfume {i}/{len(urls)}")
            perfume_data = self.extract_perfume_details(url)
            
            if perfume_data and perfume_data.get('name'):
                perfumes.append(perfume_data)
            else:
                print(f"⚠️  Skipped perfume (incomplete data)")
        
        print(f"\n✅ Successfully scraped {len(perfumes)}/{len(urls)} perfumes")
        
        # Save to file
        if save_to_file and perfumes:
            self.save_to_json(perfumes)
        
        return perfumes
    
    def scrape_by_brand(self, brand_name: str, limit: int = 100, save_to_file: bool = True) -> List[Dict[str, Any]]:
        """
        Scrape perfumes from a specific brand.
        
        Args:
            brand_name: Name of the brand (e.g., "Jean Paul Gaultier")
            limit: Number of perfumes to scrape from this brand (default 100)
            save_to_file: Whether to save results to data.json
            
        Returns:
            List of perfume dictionaries
        """
        print(f"🚀 Starting scrape for {brand_name} (up to {limit} perfumes)...")
        
        # Visit homepage first to establish session and get cookies
        print("🌐 Establishing session with Fragrantica...")
        try:
            self.session.get(self.base_url, timeout=15)
            time.sleep(3)  # Brief pause after initial connection
        except Exception as e:
            print(f"⚠️  Warning: Could not establish initial session: {e}")
        
        # Get perfume URLs for this brand
        urls = self.get_brand_perfumes_urls(brand_name, limit)
        
        if not urls:
            print(f"❌ No perfume URLs found for {brand_name}")
            return []
        
        # Extract details for each perfume
        perfumes = []
        for i, url in enumerate(urls, 1):
            print(f"\n📋 Processing perfume {i}/{len(urls)}")
            perfume_data = self.extract_perfume_details(url)
            
            if perfume_data and perfume_data.get('name'):
                perfumes.append(perfume_data)
            else:
                print(f"⚠️  Skipped perfume (incomplete data)")
        
        print(f"\n✅ Successfully scraped {len(perfumes)}/{len(urls)} perfumes from {brand_name}")
        
        # Save to file
        if save_to_file and perfumes:
            self.save_to_json(perfumes)
        
        return perfumes
    
    def scrape_multiple_brands(self, brands: List[str], limit_per_brand: int = 100, save_to_file: bool = True) -> List[Dict[str, Any]]:
        """
        Scrape perfumes from multiple brands.
        
        Args:
            brands: List of brand names (e.g., ["Jean Paul Gaultier", "Xerjoff", "Creed"])
            limit_per_brand: Number of perfumes to scrape per brand (default 100)
            save_to_file: Whether to save combined results to data.json
            
        Returns:
            Combined list of perfume dictionaries from all brands
        """
        print(f"🚀 Starting multi-brand scrape for {len(brands)} brands...")
        print(f"📋 Brands: {', '.join(brands)}")
        
        all_perfumes = []
        
        for i, brand_name in enumerate(brands, 1):
            print(f"\n{'='*80}")
            print(f"🎯 Brand {i}/{len(brands)}: {brand_name}")
            print(f"{'='*80}")
            
            # Scrape this brand (don't save individually)
            brand_perfumes = self.scrape_by_brand(brand_name, limit_per_brand, save_to_file=False)
            all_perfumes.extend(brand_perfumes)
            
            print(f"\n📊 Progress: {len(all_perfumes)} total perfumes scraped so far")
        
        print(f"\n{'='*80}")
        print(f"✅ Completed scraping {len(all_perfumes)} perfumes from {len(brands)} brands")
        print(f"{'='*80}")
        
        # Save all results to file
        if save_to_file and all_perfumes:
            self.save_to_json(all_perfumes)
        
        return all_perfumes
    
    def save_to_json(self, perfumes: List[Dict[str, Any]], filename: str = "data/data.json"):
        """
        Save perfume data to JSON file.
        
        Args:
            perfumes: List of perfume dictionaries
            filename: Output file path
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(perfumes, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Saved {len(perfumes)} perfumes to {filename}")
        except Exception as e:
            print(f"❌ Error saving to file: {str(e)}")


def scrape_fragrantica(limit: int = 2) -> List[Dict[str, Any]]:
    """
    Convenience function to scrape Fragrantica perfumes.
    
    Args:
        limit: Number of perfumes to scrape
        
    Returns:
        List of perfume dictionaries
    """
    # Use longer delay for reliability (5-10 seconds between requests)
    scraper = FragranticaScraper(delay=7.0)
    return scraper.scrape_perfumes(limit=limit, save_to_file=True)


def scrape_fragrantica_by_brand(brand_name: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Convenience function to scrape perfumes from a specific brand.
    
    Args:
        brand_name: Name of the brand (e.g., "Jean Paul Gaultier")
        limit: Number of perfumes to scrape from this brand
        
    Returns:
        List of perfume dictionaries
    """
    scraper = FragranticaScraper(delay=7.0)
    return scraper.scrape_by_brand(brand_name, limit=limit, save_to_file=True)


def scrape_fragrantica_brands(brands: List[str], limit_per_brand: int = 100) -> List[Dict[str, Any]]:
    """
    Convenience function to scrape perfumes from multiple brands.
    
    Args:
        brands: List of brand names (e.g., ["Jean Paul Gaultier", "Xerjoff", "Creed"])
        limit_per_brand: Number of perfumes to scrape per brand
        
    Returns:
        Combined list of perfume dictionaries from all brands
    """
    scraper = FragranticaScraper(delay=7.0)
    return scraper.scrape_multiple_brands(brands, limit_per_brand=limit_per_brand, save_to_file=True)


if __name__ == "__main__":
    # Example 1: Test the scraper with 2 popular perfumes
    print("🧪 Running scraper test...")
    print("\n" + "="*80)
    print("Example 1: Scraping popular perfumes")
    print("="*80)
    perfumes = scrape_fragrantica(limit=2)
    print(f"\n📊 Results: {len(perfumes)} perfumes scraped")
    
    if perfumes:
        print("\n📋 Sample perfume:")
        print(json.dumps(perfumes[0], indent=2))
    
    # Example 2: Scrape perfumes from a single brand
    # Uncomment to test:
    # print("\n" + "="*80)
    # print("Example 2: Scraping from a single brand (Jean Paul Gaultier)")
    # print("="*80)
    # brand_perfumes = scrape_fragrantica_by_brand("Jean Paul Gaultier", limit=5)
    # print(f"\n📊 Results: {len(brand_perfumes)} perfumes scraped")
    
    # Example 3: Scrape perfumes from multiple brands
    # Uncomment to test:
    # print("\n" + "="*80)
    # print("Example 3: Scraping from multiple brands")
    # print("="*80)
    # brands = ["Jean Paul Gaultier", "Xerjoff", "Creed"]
    # multi_brand_perfumes = scrape_fragrantica_brands(brands, limit_per_brand=5)
    # print(f"\n📊 Results: {len(multi_brand_perfumes)} perfumes scraped from {len(brands)} brands")

