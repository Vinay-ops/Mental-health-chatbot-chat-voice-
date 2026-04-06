"""
Fish Audio Text-to-Speech Service for Mental Health Chatbot
High-fidelity emotional speech synthesis.
"""

import os
import requests
from typing import Optional, Tuple

class EmotionalTTSService:
    """
    Provide emotional text-to-speech synthesis using Fish Audio.
    """
    
    def __init__(self, method: str = "fish"):
        """Initialize TTS service."""
        self.method = "fish"
    
    def synthesize(
        self, 
        text: str, 
        emotion: str = "neutral",
        output_path: Optional[str] = None
    ) -> Tuple[bool, str, Optional[bytes]]:
        """
        Synthesize emotional speech from text using Fish Audio.
        """
        if not text or len(text.strip()) == 0:
            return False, "Empty text provided", None
        
        # Clean text
        text = text.strip()[:5000]
        
        return self._synthesize_fish_audio(text, emotion, output_path)

    def _synthesize_fish_audio(
        self, 
        text: str, 
        emotion: str,
        output_path: Optional[str]
    ) -> Tuple[bool, str, Optional[bytes]]:
        """Use Fish Audio for high-fidelity emotional speech."""
        try:
            # Try environment variable first, then use the provided fallback key
            api_key = os.getenv("FISH_AUDIO_API_KEY") or "70869140e4924ee8a6c5764dcea17557"
            
            if not api_key:
                return False, "Fish Audio API key missing", None
            
            # Map emotions to Fish Audio tags
            emotion_tags = {
                "empathetic": "[warm, empathetic, caring]",
                "calm": "[soothing, calm, peaceful]",
                "encouraging": "[bright, encouraging, positive]",
                "supportive": "[supportive, attentive]",
                "neutral": "[professional, clear]"
            }
            
            tag = emotion_tags.get(emotion, "[neutral]")
            formatted_text = f"{tag} {text}"
            
            url = "https://api.fish.audio/v1/tts"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "model": "s1"
            }
            
            data = {
                "text": formatted_text
            }
            
            print(f"DEBUG: Calling Fish Audio API (v1/tts) with key ending in ...{api_key[-4:]}")
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                audio_bytes = response.content
                print(f"DEBUG: Fish Audio synthesis successful. Received {len(audio_bytes)} bytes.")
                if output_path:
                    with open(output_path, 'wb') as f:
                        f.write(audio_bytes)
                return True, "Fish Audio synthesis successful", audio_bytes
            else:
                error_msg = f"Fish Audio API error: {response.status_code} - {response.text}"
                print(f"DEBUG: {error_msg}")
                return False, error_msg, None
                
        except Exception as e:
            return False, f"Fish Audio Exception: {str(e)}", None
    
    def get_available_methods(self) -> dict:
        """Return available TTS methods."""
        return {
            "fish": bool(os.getenv("FISH_AUDIO_API_KEY"))
        }


def synthesize_with_emotion(
    text: str,
    emotion: str = "empathetic",
    output_path: Optional[str] = None
) -> Tuple[bool, str, Optional[bytes]]:
    """Convenience function for Fish Audio synthesis."""
    tts = EmotionalTTSService()
    return tts.synthesize(text, emotion=emotion, output_path=output_path)
