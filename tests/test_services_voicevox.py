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
        mock_resp.__aenter__.return_value.raise_for_status = AsyncMock()
        mock_post.return_value = mock_resp

        audio = await service.synthesize("こんにちは")
        assert audio == b"audio"
