#!/bin/bash
# MapR1 Frontend Start Script
# This script starts the frontend development server

echo "🚀 Starting MapR1 Frontend..."
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
    echo ""
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚙️  Creating .env file..."
    cp .env.example .env
    echo "✅ Created .env file"
    echo ""
fi

# Display backend connection info
echo "🔗 Backend Configuration:"
echo "   API URL: http://localhost:8000/api"
echo "   Make sure your backend is running!"
echo ""

# Start the dev server
echo "🌐 Starting development server..."
echo "   Frontend will be available at: http://localhost:5173"
echo ""

npm run dev
