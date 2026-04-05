"""
Emotional Text-to-Speech Service for Mental Health Chatbot
Supports Google Cloud TTS with emotional expression and fallback to pyttsx3
"""

import os
import base64
import requests
from pathlib import Path
from typing import Optional, Tuple
import json

# Try importing Google TTS library
try:
    from google.cloud import texttospeech
    GOOGLE_TTS_AVAILABLE = True
except ImportError:
    GOOGLE_TTS_AVAILABLE = False

# Fallback to pyttsx3 for offline
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


class EmotionalTTSService:
    """
    Provide emotional text-to-speech synthesis with multiple backend options.
    Priority: Google Cloud TTS (with emotions) > REST API > Pyttsx3 (fallback)
    """
    
    def __init__(self, method: str = "google"):
        """
        Initialize TTS service.
        
        Args:
            method: "google", "pyttsx3", or "rest"
        """
        self.method = method
        self.google_client = None
        self.pyttsx3_engine = None
        
        if method == "google" and GOOGLE_TTS_AVAILABLE:
            try:
                self.google_client = texttospeech.TextToSpeechClient()
                self.method = "google"
            except Exception as e:
                print(f"Google TTS init failed: {e}. Falling back to pyttsx3")
                self.method = "pyttsx3"
                
        if method == "pyttsx3" and PYTTSX3_AVAILABLE:
            self.pyttsx3_engine = pyttsx3.init()
            self._setup_pyttsx3()
    
    def _setup_pyttsx3(self):
        """Configure pyttsx3 for better emotional output."""
        if not self.pyttsx3_engine:
            return
        
        # Set properties for warmer, empathetic tone
        self.pyttsx3_engine.setProperty('rate', 150)  # Slower, more deliberate
        self.pyttsx3_engine.setProperty('volume', 0.9)
        
        # Try to get female voice if available (typically warmer for empathy)
        voices = self.pyttsx3_engine.getProperty('voices')
        if len(voices) > 1:
            self.pyttsx3_engine.setProperty('voice', voices[1].id)  # Usually female on Windows
    
    def synthesize(
        self, 
        text: str, 
        emotion: str = "neutral",
        output_path: Optional[str] = None
    ) -> Tuple[bool, str, Optional[bytes]]:
        """
        Synthesize emotional speech from text.
        
        Args:
            text: Text to convert to speech
            emotion: "neutral", "empathetic", "encouraging", "calm", "supportive"
            output_path: Optional file path to save audio
            
        Returns:
            (success, message, audio_bytes)
        """
        if not text or len(text.strip()) == 0:
            return False, "Empty text provided", None
        
        # Clean text
        text = text.strip()[:5000]  # Limit to 5000 chars
        
        # Priority: Fish Audio (if key exists) > Google > Pyttsx3
        fish_key = os.getenv("FISH_AUDIO_API_KEY")
        
        if self.method == "fish" or (self.method == "google" and fish_key):
            # Auto-switch to Fish if key exists and it's better quality
            return self._synthesize_fish_audio(text, emotion, output_path)
        elif self.method == "google" and self.google_client:
            return self._synthesize_google(text, emotion, output_path)
        elif self.method == "pyttsx3" and self.pyttsx3_engine:
            return self._synthesize_pyttsx3(text, emotion, output_path)
        else:
            return self._synthesize_rest_api(text, emotion, output_path)

    def _synthesize_fish_audio(
        self, 
        text: str, 
        emotion: str,
        output_path: Optional[str]
    ) -> Tuple[bool, str, Optional[bytes]]:
        """Use Fish Audio for high-fidelity emotional speech."""
        try:
            api_key = os.getenv("FISH_AUDIO_API_KEY")
            if not api_key:
                return False, "Fish Audio API key missing in environment variables", None
            
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
            
            data = {"text": formatted_text}
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                audio_bytes = response.content
                
                if output_path:
                    with open(output_path, 'wb') as f:
                        f.write(audio_bytes)
                
                return True, "Fish Audio synthesis successful", audio_bytes
            else:
                return False, f"Fish Audio API error: {response.status_code} - {response.text}", None
                
        except Exception as e:
            print(f"Fish Audio error: {e}")
            return False, f"Fish Audio failed: {str(e)}", None
    
    def _synthesize_google(
        self, 
        text: str, 
        emotion: str,
        output_path: Optional[str]
    ) -> Tuple[bool, str, Optional[bytes]]:
        """Use Google Cloud Text-to-Speech with emotional voices."""
        try:
            # Emotion-specific voice selection
            voice_config = self._get_emotional_voice_config(emotion)
            
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice_config["voice_name"],
                ssml_gender=voice_config["gender"]
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=voice_config["speaking_rate"],
                pitch=voice_config["pitch"]
            )
            
            response = self.google_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )
            
            audio_bytes = response.audio_content
            
            if output_path:
                with open(output_path, 'wb') as f:
                    f.write(audio_bytes)
            
            return True, "Google TTS synthesis successful", audio_bytes
            
        except Exception as e:
            print(f"Google TTS error: {e}")
            return False, f"Google TTS failed: {str(e)}", None
    
    def _synthesize_pyttsx3(
        self, 
        text: str, 
        emotion: str,
        output_path: Optional[str]
    ) -> Tuple[bool, str, Optional[bytes]]:
        """Fallback to pyttsx3 with emotional adjustments."""
        try:
            if not self.pyttsx3_engine:
                return False, "pyttsx3 not available", None
            
            # Adjust speed and volume based on emotion
            emotion_settings = {
                "calm": {"rate": 120, "volume": 0.95},
                "empathetic": {"rate": 140, "volume": 0.9},
                "encouraging": {"rate": 160, "volume": 1.0},
                "supportive": {"rate": 130, "volume": 0.95},
                "neutral": {"rate": 150, "volume": 0.9}
            }
            
            settings = emotion_settings.get(emotion, emotion_settings["neutral"])
            self.pyttsx3_engine.setProperty('rate', settings["rate"])
            self.pyttsx3_engine.setProperty('volume', settings["volume"])
            
            if output_path:
                self.pyttsx3_engine.save_to_file(text, output_path)
                self.pyttsx3_engine.runAndWait()
                
                # Read file to bytes
                with open(output_path, 'rb') as f:
                    audio_bytes = f.read()
                    
                return True, "pyttsx3 synthesis successful", audio_bytes
            else:
                # Just play it
                self.pyttsx3_engine.say(text)
                self.pyttsx3_engine.runAndWait()
                return True, "pyttsx3 synthesis successful", None
                
        except Exception as e:
            print(f"pyttsx3 error: {e}")
            return False, f"pyttsx3 failed: {str(e)}", None
    
    def _synthesize_rest_api(
        self, 
        text: str, 
        emotion: str,
        output_path: Optional[str]
    ) -> Tuple[bool, str, Optional[bytes]]:
        """Fallback to free online TTS API (Pyttsx3 REST or similar)."""
        try:
            # Using Hugging Face Inference API free tier
            HF_TOKEN = os.getenv("HF_API_TOKEN", "")
            
            if HF_TOKEN:
                return self._synthesize_huggingface(text, emotion, output_path, HF_TOKEN)
            else:
                return False, "No REST API credentials available", None
                
        except Exception as e:
            print(f"REST API error: {e}")
            return False, f"REST API synthesis failed: {str(e)}", None
    
    def _synthesize_huggingface(
        self,
        text: str,
        emotion: str,
        output_path: Optional[str],
        hf_token: str
    ) -> Tuple[bool, str, Optional[bytes]]:
        """Use Hugging Face Text-to-Speech models."""
        try:
            # Using a quality TTS model from Hugging Face
            model = "microsoft/speecht5_tts"  # High quality, free
            url = f"https://api-inference.huggingface.co/models/{model}"
            
            headers = {"Authorization": f"Bearer {hf_token}"}
            data = {"inputs": text}
            
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                audio_bytes = response.content
                
                if output_path:
                    with open(output_path, 'wb') as f:
                        f.write(audio_bytes)
                
                return True, "Hugging Face TTS synthesis successful", audio_bytes
            else:
                return False, f"Hugging Face API error: {response.status_code}", None
                
        except Exception as e:
            return False, f"Hugging Face synthesis failed: {str(e)}", None
    
    def _get_emotional_voice_config(self, emotion: str) -> dict:
        """
        Get voice configuration based on emotion for Google TTS.
        
        Google Cloud TTS voice names and their emotional characteristics:
        - en-US-Neural2-A: Male, bright, youthful
        - en-US-Neural2-B: Male, dark, professional  
        - en-US-Neural2-C: Female, warm, friendly (BEST FOR EMPATHY)
        - en-US-Neural2-D: Male, warm, mature
        - en-US-Neural2-E: Female, bright, cheerful
        - en-US-Neural2-F: Female, deep, authoritative
        """
        emotion_mapping = {
            "empathetic": {
                "voice_name": "en-US-Neural2-C",  # Warm female voice
                "gender": texttospeech.SsmlVoiceGender.FEMALE,
                "speaking_rate": 0.95,  # Slightly slower, more deliberate
                "pitch": 0.0  # Normal pitch
            },
            "calm": {
                "voice_name": "en-US-Neural2-D",  # Warm male voice
                "gender": texttospeech.SsmlVoiceGender.MALE,
                "speaking_rate": 0.8,  # Slower
                "pitch": -2.0  # Slightly lower for calming effect
            },
            "encouraging": {
                "voice_name": "en-US-Neural2-E",  # Bright female voice
                "gender": texttospeech.SsmlVoiceGender.FEMALE,
                "speaking_rate": 1.1,  # Slightly faster, energetic
                "pitch": 1.0  # Slightly higher for positivity
            },
            "supportive": {
                "voice_name": "en-US-Neural2-C",  # Warm female voice
                "gender": texttospeech.SsmlVoiceGender.FEMALE,
                "speaking_rate": 0.9,
                "pitch": 0.0
            },
            "neutral": {
                "voice_name": "en-US-Neural2-B",  # Professional male voice
                "gender": texttospeech.SsmlVoiceGender.MALE,
                "speaking_rate": 1.0,
                "pitch": 0.0
            }
        }
        
        return emotion_mapping.get(emotion, emotion_mapping["neutral"])
    
    def get_available_methods(self) -> dict:
        """Return available TTS methods."""
        return {
            "fish": bool(os.getenv("FISH_AUDIO_API_KEY")),
            "google": GOOGLE_TTS_AVAILABLE,
            "pyttsx3": PYTTSX3_AVAILABLE,
            "huggingface": bool(os.getenv("HF_API_TOKEN"))
        }


def synthesize_with_emotion(
    text: str,
    emotion: str = "empathetic",
    output_path: Optional[str] = None
) -> Tuple[bool, str, Optional[bytes]]:
    """
    Convenience function for one-off TTS synthesis.
    
    Emotions:
    - "empathetic": Warm, understanding tone (best for mental health)
    - "calm": Soothing, slower pace
    - "encouraging": Energetic, positive
    - "supportive": Caring, attentive
    - "neutral": Standard, professional
    """
    
    # Try to use Fish Audio by default if key exists
    if os.getenv("FISH_AUDIO_API_KEY"):
        tts = EmotionalTTSService(method="fish")
    elif GOOGLE_TTS_AVAILABLE:
        tts = EmotionalTTSService(method="google")
    elif PYTTSX3_AVAILABLE:
        tts = EmotionalTTSService(method="pyttsx3")
    else:
        tts = EmotionalTTSService(method="rest")
    
    return tts.synthesize(text, emotion=emotion, output_path=output_path)


if __name__ == "__main__":
    # Test the service
    test_text = "Hello! I'm here to listen. How are you feeling today? Remember, you're not alone in this journey."
    
    # Test with Google TTS (requires credentials)
    tts = EmotionalTTSService(method="google")
    success, message, audio = tts.synthesize(
        test_text,
        emotion="empathetic",
        output_path="test_empathetic.mp3"
    )
    
    print(f"Status: {success}")
    print(f"Message: {message}")
    print(f"Available methods: {tts.get_available_methods()}")
