# 🎙️ Emotional Text-to-Speech Setup Guide

## Overview

Your Mental Health Chatbot now has **emotional speech synthesis** using Google Cloud Text-to-Speech. This provides warm, empathetic voices that are perfect for mental health support conversations.

## Available Emotions

The TTS system supports 5 emotional voice profiles:

| Emotion | Description | Use Case | Voice Profile |
|---------|-------------|----------|---------------|
| **empathetic** | Warm, understanding, caring tone | Default for mental health responses | Female, slower pace |
| **calm** | Soothing, slow, peaceful | For relaxation/grounding techniques | Male, slower, lower pitch |
| **encouraging** | Energetic, positive, uplifting | For motivation/affirmations | Female, faster, higher pitch |
| **supportive** | Attentive, caring, focused | For validation and acknowledgment | Female, moderate pace |
| **neutral** | Professional, standard | For general information | Male, normal pace |

## Setup Instructions

### 1. **Google Cloud Text-to-Speech (Recommended)**

The chatbot comes pre-configured to use Google Cloud TTS, which provides the best emotional expression.

#### Steps:

1. **Create a Google Cloud Project:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable the "Text-to-Speech API"

2. **Create a Service Account:**
   - In Google Cloud Console, go to "Service Accounts"
   - Create a new service account
   - Grant it the "Cloud Text-to-Speech Client" role
   - Create and download a JSON key file

3. **Configure Your App:**
   ```bash
   # Copy the example env file
   cp .env.example .env
   
   # Set the path to your Google credentials
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/credentials.json
   ```

4. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### 2. **Fallback Options**

If Google Cloud TTS is unavailable, the app automatically falls back to:

- **pyttsx3**: Offline text-to-speech (included, no API keys needed)
- **Hugging Face TTS**: Free online TTS (requires HF_API_TOKEN)

## Usage

### In Chat Mode

1. Send a message to the chatbot
2. The AI responds with text
3. Click the **"Listen"** button below the response
4. The message is synthesized with emotional tone and played back

### Programmatically

```python
from tts_service import synthesize_with_emotion

# Simple usage
success, message, audio_bytes = synthesize_with_emotion(
    text="Hello! I'm here to listen. How are you feeling today?",
    emotion="empathetic",
    output_path="output.mp3"  # Optional
)

if success:
    print("Audio generated successfully!")
```

### API Endpoint

```bash
POST /api/synthesize
Authorization: Bearer <auth_token>

{
    "text": "Your message here",
    "emotion": "empathetic"  # Optional
}

# Response:
{
    "success": true,
    "audio": "base64-encoded-audio",
    "audio_format": "audio/mpeg",
    "emotion": "empathetic",
    "text_length": 35
}
```

## Emotion Selection Guide

### For Mental Health Responses:

```
User says "I'm feeling sad" 
→ Use "empathetic" + "calm"

User asks for motivation
→ Use "encouraging"

User shares anxiety
→ Use "supportive" + "calm"

Providing resources/information
→ Use "neutral"
```

### Voice Characteristics (Google Cloud Neural2):

- **en-US-Neural2-C** (Empathetic/Supportive): Warm female voice
- **en-US-Neural2-D** (Calm): Warm male voice
- **en-US-Neural2-E** (Encouraging): Bright female voice
- **en-US-Neural2-B** (Neutral): Professional male voice

## Advanced Configuration

### Change Default Emotion

In `app.py`, modify the `synthesize_with_emotion` call:

```python
# In the /api/synthesize endpoint
emotion = data.get("emotion", "empathetic").lower()  # Change "empathetic" to default
```

### Adjust Voice Parameters

Edit `tts_service.py` - `_get_emotional_voice_config()` method:

```python
"empathetic": {
    "voice_name": "en-US-Neural2-C",
    "gender": texttospeech.SsmlVoiceGender.FEMALE,
    "speaking_rate": 0.95,  # Adjust speed (0.25 to 4.0)
    "pitch": 0.0  # Adjust pitch (-20 to +20)
}
```

## Troubleshooting

### Issue: "Google TTS not available"
- **Solution**: Install `google-cloud-texttospeech`
  ```bash
  pip install google-cloud-texttospeech==2.14.1
  ```

### Issue: "GOOGLE_APPLICATION_CREDENTIALS not set"
- **Solution**: Set the environment variable
  ```bash
  export GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
  ```

### Issue: "Unknown TTS error" in frontend
- Check browser console for error details
- Ensure you're logged in
- Verify API token is valid

### Issue: Audio not playing
- Check if browser allows audio playback
- Try a different browser
- Verify TTS endpoint returns valid audio

### Issue: Robotic sounding voice
- Your fallback system is using pyttsx3
- Set up Google Cloud TTS for better quality
- Adjust `speaking_rate` and `pitch` parameters

## Free Tier Limitations

**Google Cloud Text-to-Speech Free Tier:**
- 1 million characters per month
- Sufficient for most chatbot usage

**Hugging Face Free Tier:**
- API calls limited per month
- Good backup option

## Cost Estimation

- Google Cloud: $0-15/month for typical usage
- Hugging Face: Free tier available
- pyttsx3: Free (offline)

## Technical Details

### Supported Features

✅ Multiple emotional voices  
✅ Real-time synthesis  
✅ Audio format: MP3 (compatible with all browsers)  
✅ Base64 encoding for easy transmission  
✅ Fallback system (automatic or manual)  
✅ Sentiment-aware emotion selection (future)  

### Not Supported

❌ SSML markup (custom prosody)  
❌ Voice cloning  
❌ Real-time streaming  

## Best Practices for Mental Health Chatbots

1. **Always use "empathetic" by default** - Builds trust
2. **Match emotion to sentiment** - Use calm for anxious users
3. **Test voice quality** - Have stakeholders listen first
4. **Keep audio short** - <30 seconds is ideal
5. **Offer text alternative** - Not everyone needs voice
6. **Monitor audio usage** - Track cost and quota usage

## Future Enhancements

- [ ] Sentiment-aware emotion selection
- [ ] Custom voice cloning from recordings
- [ ] SSML support for advanced prosody
- [ ] Voice quality metrics
- [ ] Multi-language support
- [ ] Streaming audio for faster playback

## Support & Resources

- [Google Cloud Text-to-Speech Documentation](https://cloud.google.com/text-to-speech/docs)
- [Mozilla TTS (Alternative)](https://github.com/mozilla/TTS)
- [Hugging Face Models](https://huggingface.co/models?task=text-to-speech)

---

**Mental Health Note**: The emotional voicing system is designed to enhance empathy and trust in mental health conversations. Always ensure the AI combined with this emotional voice remains supportive and doesn't substitute professional mental health care.
