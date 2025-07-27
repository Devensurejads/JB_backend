#!/bin/bash
# run.sh - Development startup script

echo "🚀 Starting Job Management System..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
    # Windows
    source venv/Scripts/activate
else
    # Linux/Mac
    source venv/bin/activate
fi

# Check if requirements are installed
echo "📋 Checking dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs
mkdir -p uploads
mkdir -p data

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating environment file..."
    cp .env.example .env
    echo "⚠️  Please edit .env file with your configuration before running!"
    echo "⚠️  At minimum, change SECRET_KEY and JWT_SECRET_KEY"
fi

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=development

echo "🌟 Starting Flask application..."
echo "📍 Application will be available at: http://127.0.0.1:5000"
echo "👤 Default admin credentials:"
echo "   Username: admin"
echo "   Password: Admin123!"
echo "   Email: admin@jobmanagement.com"
echo ""
echo "🔗 API Documentation:"
echo "   Health Check: GET http://127.0.0.1:5000/"
echo "   User Registration: POST http://127.0.0.1:5000/api/v1/auth/register"
echo "   User Login: POST http://127.0.0.1:5000/api/v1/auth/login"
echo ""
echo "Press Ctrl+C to stop the server"
echo "================================"

# Run the Flask application
python app.py