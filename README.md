# Perfume Data API

A complete FastAPI application that scrapes perfume data from Fragrantica, stores it in Supabase (PostgreSQL), and serves it through a REST API. Designed for free hosting on Render.com. For testing and educational purposes. One love Fragrantica.com <3.

## Features

- **Web Scraper**: Extracts perfume data from Fragrantica.com
  - General popular perfumes scraping
  - Brand-specific scraping (e.g., Jean Paul Gaultier, Xerjoff, Creed)
  - Multi-brand batch scraping
  - Direct URL scraping (fastest - single perfume)
- **Supabase Integration**: PostgreSQL database with auto-migration
- **Authentication**: Supabase JWT-based auth for protected endpoints
- **FastAPI Backend**: Fast, modern REST API with automatic documentation
- **CORS Enabled**: Works with any frontend application

## Project Structure

```
PerfumAPI/
├── api/
│   └── main.py              # FastAPI application with all endpoints
├── scraper/
│   └── scrape.py            # Fragrantica web scraper
├── utils/
│   ├── db.py                # Supabase client and database operations
│   └── auth.py              # Authentication middleware
├── data/
│   └── data.json            # Scraped data cache (auto-generated)
├── requirements.txt         # Python dependencies
├── Procfile                 # Render deployment configuration
├── env.example              # Environment variables template
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Database Schema

The `perfumes` table includes:

- `id` (UUID) - Primary key
- `name` (TEXT) - Perfume name
- `brand` (TEXT) - Brand/designer name
- `release_year` (INTEGER) - Year of release
- `gender` (TEXT) - Target gender (Men/Women/Unisex)
- `notes_top` (TEXT[]) - Top notes array
- `notes_middle` (TEXT[]) - Middle/heart notes array
- `notes_base` (TEXT[]) - Base notes array
- `rating` (REAL) - Average rating
- `votes` (INTEGER) - Number of votes
- `description` (TEXT) - Perfume description
- `longevity` (TEXT) - Longevity rating
- `sillage` (TEXT) - Sillage/projection rating
- `image_url` (TEXT) - Perfume image URL
- `perfume_url` (TEXT) - Source URL (unique)
- `created_at` (TIMESTAMP) - Creation timestamp

## Quick Start (Local Development)

### Prerequisites

- Python 3.9 or higher
- Supabase account (free tier)
- Git

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd PerfumAPI
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Set Up Supabase

1. Go to [supabase.com](https://supabase.com) and create a free account
2. Create a new project
3. Wait for the database to be provisioned
4. Go to **Project Settings** → **API**
5. Copy your:
   - `Project URL` (SUPABASE_URL)
   - `anon public` key (SUPABASE_KEY)
   - `service_role` key (SUPABASE_SERVICE_KEY) - keep this secret!

### 4. Configure Environment Variables

```bash
# Copy the example env file
cp env.example .env

# Edit .env and add your Supabase credentials
nano .env  # or use any text editor
```

Your `.env` file should look like:

```env
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
DEBUG=True
```

### 5. Create Database Table

The application will attempt to auto-create the table on startup. If that doesn't work, manually create it:

1. Go to your Supabase project
2. Click **SQL Editor**
3. Run this SQL:

```sql
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

CREATE INDEX IF NOT EXISTS idx_perfumes_url ON perfumes(perfume_url);
CREATE INDEX IF NOT EXISTS idx_perfumes_brand ON perfumes(brand);
```

### 6. Run the API

```bash
# From the project root directory
uvicorn api.main:app --reload --port 9000
```

The API will be available at:
- 🌐 **API**: http://localhost:9000
- 📚 **Interactive Docs**: http://localhost:9000/docs
- 📖 **ReDoc**: http://localhost:9000/redoc

## Authentication Setup

To use protected endpoints (scraping, creating perfumes), you need to authenticate:

### Option 1: Create a User in Supabase Dashboard

1. Go to **Authentication** → **Users** in Supabase
2. Click **Add User**
3. Enter email and password
4. Click **Create User**

### Option 2: Use Supabase Auth API

```bash
curl -X POST 'https://YOUR-PROJECT.supabase.co/auth/v1/signup' \
-H "apikey: YOUR-ANON-KEY" \
-H "Content-Type: application/json" \
-d '{
  "email": "user@example.com",
  "password": "your-password"
}'
```

### Get Authentication Token

```bash
curl -X POST 'https://YOUR-PROJECT.supabase.co/auth/v1/token?grant_type=password' \
-H "apikey: YOUR-ANON-KEY" \
-H "Content-Type: application/json" \
-d '{
  "email": "user@example.com",
  "password": "your-password"
}'
```

Copy the `access_token` from the response.

## API Endpoints

### Public Endpoints (No Auth Required)

#### Get All Perfumes
```bash
GET /perfumes?limit=100&offset=0
```

#### Get Perfume by ID
```bash
GET /perfumes/{perfume_id}
```

#### Search Perfumes
```bash
GET /perfumes/search/{query}?limit=50
```

#### Get Statistics
```bash
GET /stats
```

### Protected Endpoints (Auth Required)

Include the auth token in headers:
```
Authorization: Bearer YOUR_ACCESS_TOKEN
```

#### Trigger Scraping (General)
```bash
POST /scrape
Content-Type: application/json

{
  "limit": 2
}
```

Example with curl:
```bash
curl -X POST http://localhost:9000/scrape \
-H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d '{"limit": 2}'
```

#### Scrape by Brand
Scrape perfumes from a specific brand:
```bash
POST /scrape/brand
Content-Type: application/json

{
  "brand_name": "Jean Paul Gaultier",
  "limit": 10
}
```

Example with curl:
```bash
curl -X POST http://localhost:9000/scrape/brand \
-H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d '{"brand_name": "Jean Paul Gaultier", "limit": 10}'
```

#### Scrape Multiple Brands
Scrape perfumes from multiple brands at once:
```bash
POST /scrape/brands
Content-Type: application/json

{
  "brands": ["Jean Paul Gaultier", "Xerjoff", "Creed"],
  "limit_per_brand": 10
}
```

Example with curl:
```bash
curl -X POST http://localhost:9000/scrape/brands \
-H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d '{"brands": ["Jean Paul Gaultier", "Xerjoff", "Creed"], "limit_per_brand": 10}'
```

#### Scrape by URL
Scrape a specific perfume by its direct Fragrantica URL:
```bash
POST /scrape/url
Content-Type: application/json

{
  "perfume_url": "https://www.fragrantica.com/perfume/Xerjoff/White-On-White-Three-76333.html"
}
```

Example with curl:
```bash
curl -X POST http://localhost:9000/scrape/url \
-H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
-H "Content-Type: application/json" \
-d '{"perfume_url": "https://www.fragrantica.com/perfume/Xerjoff/White-On-White-Three-76333.html"}'
```

**Benefits:**
- Fastest scraping method (only 1 request)
- Get data for a specific perfume you already know
- No need to search through lists or brands
- Perfect for updating existing perfume data

#### Create Perfume Manually
```bash
POST /perfumes
Content-Type: application/json

{
  "name": "Bleu de Chanel",
  "brand": "Chanel",
  "release_year": 2010,
  "gender": "Men",
  "notes_top": ["Lemon", "Mint", "Pink Pepper"],
  "notes_middle": ["Ginger", "Jasmine", "Melon"],
  "notes_base": ["Cedar", "Sandalwood", "Amber"]
}
```
## Testing the Scraper

### Test with 2 Perfumes (Safe)
```bash
curl -X POST http://localhost:9000/scrape \
-H "Authorization: Bearer YOUR_TOKEN" \
-H "Content-Type: application/json" \
-d '{"limit": 2}'
```

### Scrape More Perfumes
```bash
# Scrape 10 perfumes
curl -X POST http://localhost:9000/scrape \
-H "Authorization: Bearer YOUR_TOKEN" \
-H "Content-Type: application/json" \
-d '{"limit": 10}'

# Scrape 100 perfumes (will take time)
curl -X POST http://localhost:9000/scrape \
-H "Authorization: Bearer YOUR_TOKEN" \
-H "Content-Type: application/json" \
-d '{"limit": 100}'
```

### Verify Data
```bash
# Check how many perfumes are in the database
curl http://localhost:9000/stats

# List all perfumes
curl http://localhost:9000/perfumes?limit=10
```

## Usage Examples

### JavaScript/Fetch
```javascript
// Get all perfumes
const response = await fetch('https://your-api.onrender.com/perfumes?limit=50');
const data = await response.json();
console.log(data.perfumes);

// Trigger scraping (requires auth)
const scrapeResponse = await fetch('https://your-api.onrender.com/scrape', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ limit: 5 })
});
const scrapeData = await scrapeResponse.json();
```

### Python/Requests
```python
import requests

# Get perfumes
response = requests.get('https://your-api.onrender.com/perfumes')
perfumes = response.json()

# Scrape with auth
headers = {'Authorization': 'Bearer YOUR_TOKEN'}
scrape_response = requests.post(
    'https://your-api.onrender.com/scrape',
    headers=headers,
    json={'limit': 5}
)
print(scrape_response.json())
```

## Important Notes

### Ethical Scraping
- This scraper is for **educational purposes only**
- Respects rate limiting (2-second delay between requests)
- Scrapes publicly available data only
- Does not overwhelm the target website
- Always check `robots.txt` and terms of service

### Rate Limiting
The scraper includes built-in delays to be respectful:
- 2 seconds between page requests
- Handles errors gracefully
- Stops if too many failures occur

### Data Privacy
- Do not scrape personal information
- Respect copyright and intellectual property
- Only use data for personal/educational projects

## Troubleshooting

### "SUPABASE_URL and SUPABASE_KEY must be set"
- Ensure `.env` file exists in project root
- Check that environment variables are set correctly
- Restart the application after changing `.env`

### "Table 'perfumes' does not exist"
- Run the SQL migration manually in Supabase SQL Editor
- Check database connection in Supabase dashboard

### Authentication Issues
- Verify your token is not expired
- Ensure you're using the correct token format: `Bearer <token>`
- Create a new user if needed

### Scraping Failures
- Check internet connection
- Fragrantica might have changed their HTML structure
- Reduce the limit and try again
- Check console logs for specific errors

### Render Deployment Issues
- Verify all environment variables are set in Render dashboard
- Check build logs for errors
- Ensure `Procfile` and `requirements.txt` are in the repo root

## 🔧 Development

### Run Tests
```bash
# Test the scraper directly
python scraper/scrape.py

# Test API health
curl http://localhost:9000/health
```

### View Logs
```bash
# Local development logs appear in terminal

# Render logs: Dashboard → Logs tab
```

### Database Inspection
Use Supabase dashboard:
1. Go to **Table Editor**
2. Select `perfumes` table
3. View, edit, or delete records

## 📚 Tech Stack

- **Backend**: FastAPI 0.104+
- **Database**: Supabase (PostgreSQL)
- **Scraper**: BeautifulSoup4, Requests
- **Auth**: Supabase JWT
- **Hosting**: Render.com (free tier)
- **Language**: Python 3.9+

## 🤝 Contributing

This is an educational project. Feel free to fork and modify for your own learning!

## 📄 License

This project is for educational purposes. Please respect Fragrantica's terms of service and use responsibly.

## 🆘 Support

For issues:
1. Check the troubleshooting section above
2. Review Supabase and Render documentation
3. Check console/logs for error messages


---



