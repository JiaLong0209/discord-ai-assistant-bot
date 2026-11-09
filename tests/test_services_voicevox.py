import pytest
from unittest.mock import AsyncMock, patch
from services.voicevox import VoiceVoxService

@pytest.mark.asyncio
async def test_synthesize_calls_api():
    service = VoiceVoxService()

    with patch("aiohttp.ClientSession.post") as mock_post:
        mock_resp = AsyncMock()
        mock_resp.__aenter__.return_value.json = AsyncMock(return_value={})
        mock_resp.__aenter__.return_value.read = AsyncMock(return_value=b"audio")
        mock_resp.__aenter__.return_value.raise_for_status = lambda: None
        mock_post.return_value = mock_resp

        audio = await service.synthesize("こんにちは")
        assert audio == b"audio"


@pytest.mark.asyncio
async def test_synthesize_fallback_when_unavailable():
    # When VoiceVox server cannot be reached, it should return None rather than raising an exception
    service = VoiceVoxService(base_url="http://127.0.0.1:59999")
    audio = await service.synthesize("こんにちは")
    assert audio is None
