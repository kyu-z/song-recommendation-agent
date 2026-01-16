#!/bin/bash

# Music AI Agent - Dependency Installation Script
# This script installs the required dependencies for the music_expander module

echo "🎵 Installing Music Expander Dependencies..."

# Core dependencies for music expansion
echo "📦 Installing core dependencies..."
pip install requests
pip install yt-dlp
pip install pathlib

# Optional API clients
echo "🔌 Installing API clients..."
pip install jamendo-api || echo "⚠️ Warning: jamendo-api not available, using direct requests"

# Audio processing dependencies (if not already installed)
echo "🎵 Ensuring audio processing dependencies..."
pip install librosa
pip install numpy
pip install scipy

# Web scraping dependencies (for future extensions)
echo "🕷️ Installing web scraping tools..."
pip install beautifulsoup4
pip install lxml

echo "✅ Installation completed!"
echo ""
echo "📝 Next steps:"
echo "1. Get API keys:"
echo "   - Freesound: https://freesound.org/apiv2/apply/"
echo "   - Jamendo: https://developer.jamendo.com/"
echo ""
echo "2. Update config/music_sources.json with your API keys"
echo ""
echo "3. Test the expander:"
echo "   python tools/music_expander.py --target 5 --genres ambient electronic"
echo ""
echo "4. For YouTube downloads, make sure yt-dlp is working:"
echo "   yt-dlp --version"
