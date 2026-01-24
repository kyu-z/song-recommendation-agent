#!/bin/bash

# Next.js Frontend Startup Script

echo "🎵 Starting Next.js Music Agent Frontend..."

# Check if we're in the frontend directory
if [ ! -f "package.json" ]; then
    echo "❌ Error: package.json not found. Make sure you're in the frontend directory."
    exit 1
fi

# Install dependencies if node_modules doesn't exist
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start the development server
echo "🚀 Starting Next.js development server on http://localhost:3000"
echo "📚 Make sure your FastAPI backend is running on http://localhost:8000"
echo "🛑 Press Ctrl+C to stop the server"
echo ""

npm run dev
