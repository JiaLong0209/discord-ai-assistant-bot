import pytest
from unittest.mock import MagicMock
from services.gemini import GeminiService

def test_extract_clean_text_removes_thought_tags():
    mock_resp = MagicMock()
    mock_resp.candidates = []
    mock_resp.text = "<thought>Thinking about what to say...</thought>こんにちはっピ！"
    assert GeminiService.extract_clean_text(mock_resp) == "こんにちはっピ！"

def test_extract_clean_text_removes_drafting_prefix():
    mock_resp = MagicMock()
    mock_resp.candidates = []
    mock_resp.text = """Character analysis here...
Drafting final response:
「こんにちはっピ！」
翻譯：「你好嗶！」"""
    expected = """「こんにちはっピ！」
翻譯：「你好嗶！」"""
    assert GeminiService.extract_clean_text(mock_resp) == expected

def test_extract_clean_text_removes_meta_scratchpad():
    mock_resp = MagicMock()
    mock_resp.candidates = []
    mock_resp.text = """* Character: Takopy
• Constraint Checklist:
  1. Ends with pi: Yes
• Internal Monologue: Serious thinking
「やあ、yoshitakaくん！こんにちはっピ！」
翻譯： 「呀，yoshitaka君！你好嗶！」"""
    expected = """「やあ、yoshitakaくん！こんにちはっピ！」
翻譯： 「呀，yoshitaka君！你好嗶！」"""
    assert GeminiService.extract_clean_text(mock_resp) == expected

def test_convert_history_to_gemini_format_merges_consecutive_roles():
    service = GeminiService(api_key="fake-key", model_text="gemini-3.1-flash-lite")
    history = [
        {"role": "user", "content": "Hello 1"},
        {"role": "user", "content": "Hello 2"},
        {"role": "assistant", "content": "Hi there!"},
        {"role": "user", "content": "How are you?"},
    ]
    formatted = service.convert_history_to_gemini_format(history)
    assert len(formatted) == 3
    assert formatted[0]["role"] == "user"
    assert formatted[0]["parts"][0]["text"] == "Hello 1\nHello 2"
    assert formatted[1]["role"] == "model"
    assert formatted[2]["role"] == "user"

