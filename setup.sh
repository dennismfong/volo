#!/bin/bash
# Setup script for Volo Sports Bot

echo "Setting up Volo Sports Bot..."
echo ""

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "Error: pip3 is not installed. Please install pip3 first."
    exit 1
fi

# Install dependencies
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

# Check if ChromeDriver is installed
if ! command -v chromedriver &> /dev/null; then
    echo ""
    echo "Warning: ChromeDriver is not installed."
    echo "Please install it using one of these methods:"
    echo "  macOS: brew install chromedriver"
    echo "  Or download from: https://chromedriver.chromium.org/downloads"
    echo ""
else
    echo "ChromeDriver found: $(chromedriver --version)"
fi

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env and add your Volo Sports credentials:"
    echo "  VOLO_EMAIL=your_email@example.com"
    echo "  VOLO_PASSWORD=your_password"
    echo ""
else
    echo ".env file already exists"
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your credentials"
echo "2. Test the bot: python3 volo_bot.py"
echo "3. Set up scheduling (see README.md for options)"
