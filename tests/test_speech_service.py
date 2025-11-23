import pytest
from unittest.mock import Mock, patch, MagicMock
from app.speech_service import SpeechService

@pytest.fixture
def mock_config():
    with patch('app.speech_service.Config') as mock:
        mock.ENABLE_SPEECH = True
        mock.STT_API_KEY = "stt-key"
        mock.STT_URL = "https://stt.ibm.com"
        mock.TTS_API_KEY = "tts-key"
        mock.TTS_URL = "https://tts.ibm.com"
        yield mock

@pytest.fixture
def speech_client(mock_config):
    with patch('app.speech_service.SpeechToTextV1') as mock_stt, \
         patch('app.speech_service.TextToSpeechV1') as mock_tts, \
         patch('app.speech_service.IAMAuthenticator'):
        
        client = SpeechService()
        client.connect()
        return client

def test_connect_success(speech_client):
    assert speech_client.is_stt_connected() is True
    assert speech_client.is_tts_connected() is True

def test_transcribe_audio(speech_client):
    # Mock recognize response
    mock_response = MagicMock()
    mock_response.get_result.return_value = {
        "results": [
            {"alternatives": [{"transcript": "Hello world"}]}
        ]
    }
    speech_client.stt_client.recognize.return_value = mock_response
    
    # Mock file object
    mock_file = Mock()
    result = speech_client.transcribe_audio(mock_file)
    
    assert result == "Hello world"

def test_synthesize_speech(speech_client):
    # Mock synthesize response
    mock_response = MagicMock()
    mock_response.get_result.return_value.content = b"audio-data"
    speech_client.tts_client.synthesize.return_value = mock_response
    
    result = speech_client.synthesize_speech("Hello")
    
    assert result == b"audio-data"
