$ErrorActionPreference = "Stop"

Write-Host "Setting up project..." -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python is not installed. Please install Python first." -ForegroundColor Red
    exit 1
}

Write-Host "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

Write-Host "Creating MySQL database..."
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS my_app_db;"

Write-Host "Creating tables..."
python .\backend\dbreset.py

Write-Host "Setting up RAG System..."
python .\ai\rag-semantic-layer\ingest.py --standards
python .\ai\rag-semantic-layer\ingest.py --audits
python .\ai\rag-semantic-layer\seed.py
python .\ai\rag-semantic-layer\ingest.py --intel
python .\ai\rag-semantic-layer\scraprun.py
python .\ai\rag-semantic-layer\totalcount.py

Write-Host "Python, MySQL, and RAG Setup complete!" -ForegroundColor Green