#!/bin/bash
# Quick Setup Script for Emotional TTS
# Run this to set up emotional voice features in 5 minutes

echo "🎙️  Mental Health Chatbot - Emotional TTS Setup"
echo "============================================="
echo ""

# Step 1: Install dependencies
echo "📦 Step 1: Installing dependencies..."
pip install google-cloud-texttospeech==2.14.1 pyttsx3==2.90 librosa==0.10.0
echo "✅ Dependencies installed!"
echo ""

# Step 2: Create .env file
echo "📝 Step 2: Setting up .env file..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ .env file created from .env.example"
else
    echo "⚠️  .env file already exists"
fi
echo ""

# Step 3: Information about Google Cloud setup
echo "🔑 Step 3: Google Cloud Credentials Setup"
echo "=========================================="
echo ""
echo "To use emotional voices, you need Google Cloud Text-to-Speech credentials:"
echo ""
echo "1. Go to Google Cloud Console: https://console.cloud.google.com/"
echo "2. Create a NEW project"
echo "3. Enable Text-to-Speech API"
echo "4. Create a Service Account with 'Cloud Text-to-Speech Client' role"
echo "5. Download the JSON key file"
echo "6. Update .env with: GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json"
echo ""
echo "OR set the environment variable:"
echo "   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json"
echo ""

# Step 4: Verify setup
echo "✅ Step 4: Verification"
echo "======================="
echo ""

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $python_version"

# Check if packages are installed
echo ""
echo "Checking installed packages:"
python -c "import google.cloud.texttospeech; print('✅ google-cloud-texttospeech installed')" 2>/dev/null || echo "❌ google-cloud-texttospeech NOT installed"
python -c "import pyttsx3; print('✅ pyttsx3 installed')" 2>/dev/null || echo "❌ pyttsx3 NOT installed"
python -c "import librosa; print('✅ librosa installed')" 2>/dev/null || echo "⚠️  librosa optional (audio processing)"

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "Next steps:"
echo "1. Update .env with your Google Cloud credentials"
echo "2. Run your Flask app: python app.py"
echo "3. Go to http://localhost:5000/chat"
echo "4. Send a message and click the 'Listen' button"
echo ""
echo "For detailed documentation, see EMOTIONAL_TTS_GUIDE.md"
echo ""
