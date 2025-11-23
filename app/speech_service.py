"""
IBM Speech-to-Text and Text-to-Speech service clients.
"""
from typing import Optional, BinaryIO
from ibm_watson import SpeechToTextV1, TextToSpeechV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from app.config import Config
from app.logger import get_logger
from app.error_recovery import speech_circuit_breaker, retry

logger = get_logger(__name__)


class SpeechService:
    """IBM Speech services wrapper"""
    
    def __init__(self):
        self.stt_client: Optional[SpeechToTextV1] = None
        self.tts_client: Optional[TextToSpeechV1] = None
        self._stt_initialized = False
        self._tts_initialized = False
    
    def connect(self) -> bool:
        """Initialize Speech services connections"""
        if not Config.ENABLE_SPEECH:
            logger.info("Speech services disabled")
            return False
        
        # Initialize Speech-to-Text
        if Config.STT_API_KEY and Config.STT_URL:
            try:
                authenticator = IAMAuthenticator(Config.STT_API_KEY)
                self.stt_client = SpeechToTextV1(authenticator=authenticator)
                self.stt_client.set_service_url(Config.STT_URL)
                self._stt_initialized = True
                logger.info("Connected to IBM Speech-to-Text")
            except Exception as e:
                logger.error(f"Failed to connect to Speech-to-Text: {str(e)}")
        
        # Initialize Text-to-Speech
        if Config.TTS_API_KEY and Config.TTS_URL:
            try:
                authenticator = IAMAuthenticator(Config.TTS_API_KEY)
                self.tts_client = TextToSpeechV1(authenticator=authenticator)
                self.tts_client.set_service_url(Config.TTS_URL)
                self._tts_initialized = True
                logger.info("Connected to IBM Text-to-Speech")
            except Exception as e:
                logger.error(f"Failed to connect to Text-to-Speech: {str(e)}")
        
        return self._stt_initialized or self._tts_initialized
    
    def is_stt_connected(self) -> bool:
        """Check if Speech-to-Text is connected"""
        return self._stt_initialized and self.stt_client is not None
    
    def is_tts_connected(self) -> bool:
        """Check if Text-to-Speech is connected"""
        return self._tts_initialized and self.tts_client is not None
    
    @retry(max_attempts=3, delay=1.0)
    def transcribe_audio(self, audio_file: BinaryIO, content_type: str = "audio/wav") -> Optional[str]:
        """Transcribe audio file to text"""
        if not self.is_stt_connected():
            return None
        
        try:
            return speech_circuit_breaker.call(self._transcribe_audio_impl, audio_file, content_type)
        except Exception as e:
            logger.error(f"Speech-to-Text failed after retries: {str(e)}")
            return None
    
    def _transcribe_audio_impl(self, audio_file: BinaryIO, content_type: str) -> Optional[str]:
        """Internal implementation of transcribe_audio"""
        response = self.stt_client.recognize(
            audio=audio_file,
            content_type=content_type,
            model="en-US_BroadbandModel"
        ).get_result()
        
        # Extract transcript
        results = response.get("results", [])
        if not results:
            return None
        
        transcript = ""
        for result in results:
            alternatives = result.get("alternatives", [])
            if alternatives:
                transcript += alternatives[0].get("transcript", "") + " "
        
        return transcript.strip()
    
    def synthesize_speech(self, text: str, voice: str = "en-US_AllisonV3Voice") -> Optional[bytes]:
        """Convert text to speech audio"""
        if not self.is_tts_connected():
            return None
        
        try:
            response = self.tts_client.synthesize(
                text=text,
                voice=voice,
                accept="audio/wav"
            ).get_result()
            
            return response.content
        except Exception as e:
            logger.error(f"Text-to-Speech synthesis failed: {str(e)}")
            return None


# Global Speech service instance
speech_service = SpeechService()

