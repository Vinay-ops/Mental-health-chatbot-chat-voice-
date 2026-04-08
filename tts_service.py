"""
Fish Audio Text-to-Speech Service for Mental Health Chatbot
High-fidelity emotional speech synthesis with natural speech patterns.
"""

import os
import requests
import re
from typing import Optional, Tuple

class EmotionalTTSService:
    """
    Provide emotional text-to-speech synthesis using Fish Audio.
    """
    
    def __init__(self, method: str = "fish"):
        """Initialize TTS service with enhanced voice parameters."""
        self.method = "fish"
        self.voice_model = "s1"  # Premium voice model
        
        # Enhanced emotion-to-voice mapping with natural characteristics
        self.emotion_config = {
            "empathetic": {
                "tags": "[warm, empathetic, caring, conversational]",
                "pitch": 1.0,
                "speed": 0.95,
                "emotion_strength": 0.8,
                "style": "natural"
            },
            "calm": {
                "tags": "[soothing, calm, peaceful, gentle, relaxed]",
                "pitch": 0.95,
                "speed": 0.90,
                "emotion_strength": 0.9,
                "style": "slow_smooth"
            },
            "encouraging": {
                "tags": "[bright, encouraging, positive, energetic, motivated]",
                "pitch": 1.05,
                "speed": 1.0,
                "emotion_strength": 0.7,
                "style": "uplifting"
            },
            "supportive": {
                "tags": "[supportive, attentive, understanding, patient, compassionate]",
                "pitch": 0.98,
                "speed": 0.92,
                "emotion_strength": 0.8,
                "style": "natural"
            },
            "neutral": {
                "tags": "[professional, clear, thoughtful, balanced]",
                "pitch": 1.0,
                "speed": 0.95,
                "emotion_strength": 0.5,
                "style": "natural"
            }
        }
    
    def synthesize(
        self, 
        text: str, 
        emotion: str = "neutral",
        output_path: Optional[str] = None
    ) -> Tuple[bool, str, Optional[bytes]]:
        """
        Synthesize emotional speech from text using Fish Audio with natural speech patterns.
        """
        if not text or len(text.strip()) == 0:
            return False, "Empty text provided", None
        
        # Clean and preprocess text for natural speech
        text = text.strip()[:5000]
        text = self._preprocess_text(text)
        
        return self._synthesize_fish_audio(text, emotion, output_path)
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text to sound more natural:
        - Add natural pauses
        - Handle common abbreviations
        - Improve punctuation for natural speech flow
        """
        # Ensure proper spacing after punctuation
        text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)
        
        # Add breathing space for long sentences (simulate natural pauses)
        # Split very long sentences with commas or add ellipsis for dramatic effect
        sentences = re.split(r'([.!?])', text)
        processed_sentences = []
        
        for i, sentence in enumerate(sentences):
            if i % 2 == 0:  # Actual sentence content
                # If sentence is very long, add implicit pauses
                if len(sentence.split()) > 20:
                    # Try to split at clauses if possible
                    sentence = re.sub(r',\s+', ', ... ', sentence)
                processed_sentences.append(sentence)
            else:
                processed_sentences.append(sentence)
        
        text = ''.join(processed_sentences)
        
        # Ensure text ends with proper punctuation
        if text and not text.strip().endswith(('.', '!', '?')):
            text = text.strip() + '.'
        
        return text

    def _synthesize_fish_audio(
        self, 
        text: str, 
        emotion: str,
        output_path: Optional[str]
    ) -> Tuple[bool, str, Optional[bytes]]:
        """Use Fish Audio for high-fidelity emotional speech with natural characteristics."""
        try:
            # Try environment variable first, then use the provided fallback key
            api_key = os.getenv("FISH_AUDIO_API_KEY") or "70869140e4924ee8a6c5764dcea17557"
            
            if not api_key:
                return False, "Fish Audio API key missing", None
            
            # Get emotion configuration
            emotion_lower = emotion.lower()
            config = self.emotion_config.get(emotion_lower, self.emotion_config["neutral"])
            
            # Build prompt with voice characteristics
            tag = config["tags"]
            formatted_text = f"{tag} {text}"
            
            url = "https://api.fish.audio/v1/tts"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Enhanced API payload with natural voice parameters
            data = {
                "text": formatted_text,
                "model": self.voice_model,
                "voice": "default",  # Use default high-quality voice
                "chunk_length": 100,
                "format": "wav",  # WAV format for better quality
                # Voice parameters for natural speech
                "pitch": config["pitch"],
                "speed": config["speed"],
                "emotion_strength": config["emotion_strength"],
                "style": config["style"]
            }
            
            print(f"DEBUG: Fish Audio synthesis - emotion: {emotion}, speed: {config['speed']}, pitch: {config['pitch']}")
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                audio_bytes = response.content
                print(f"DEBUG: Fish Audio synthesis successful. Received {len(audio_bytes)} bytes of high-quality audio.")
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
        """Return available TTS methods and voice characteristics."""
        return {
            "fish": bool(os.getenv("FISH_AUDIO_API_KEY")),
            "emotions": list(self.emotion_config.keys()),
            "voice_model": self.voice_model,
            "features": ["emotional", "natural_speech_patterns", "variable_speed", "variable_pitch"]
        }
    
    def get_emotion_characteristics(self, emotion: str) -> Optional[dict]:
        """Get voice characteristics for a specific emotion."""
        emotion_lower = emotion.lower()
        if emotion_lower in self.emotion_config:
            return self.emotion_config[emotion_lower].copy()
        return None


def synthesize_with_emotion(
    text: str,
    emotion: str = "empathetic",
    output_path: Optional[str] = None
) -> Tuple[bool, str, Optional[bytes]]:
    """Convenience function for Fish Audio synthesis."""
    tts = EmotionalTTSService()
    return tts.synthesize(text, emotion=emotion, output_path=output_path)
