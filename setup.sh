#!/bin/bash
# Setup script for Perfume API
# Run this after cloning the repository

set -e

echo "🌸 Perfume API Setup Script"
echo "=============================="

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.9 or higher."
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "⚠️  Please edit .env and add your Supabase credentials!"
else
    echo "✅ .env file already exists"
fi

# Create data directory
mkdir -p data

echo ""
echo "=============================="
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your Supabase credentials"
echo "2. Run: source venv/bin/activate"
echo "3. Run: uvicorn api.main:app --reload"
echo "4. Open http://localhost:9000/docs"
echo ""
echo "For more information, see README.md"

