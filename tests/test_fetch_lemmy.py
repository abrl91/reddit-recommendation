from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from src.ingestion.exceptions import IngestionError
from src.ingestion.fetch_lemmy import fetch
from src.models import LemmyPostResponse


class TestFetch:
    def test_success_returns_parsed_response(
        self,
        mocker: Any,
        sample_post_response: LemmyPostResponse,
    ) -> None:
        """Successful 200 response should return parsed JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_post_response

        mocker.patch("httpx.get", return_value=mock_response)

        result = fetch("posts", "hot")

        assert "posts" in result

    def test_network_error_raises_ingestion_error(self, mocker: Any) -> None:
        """Network errors (timeout, connection refused) should raise IngestionError."""
        mocker.patch(
            "httpx.get",
            side_effect=httpx.RequestError("Connection refused"),
        )

        with pytest.raises(IngestionError) as exc_info:
            fetch("posts", "hot")

        assert "Network error" in str(exc_info.value)

    def test_http_error_raises_ingestion_error(self, mocker: Any) -> None:
        """HTTP error status should raise IngestionError."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mocker.patch("httpx.get", return_value=mock_response)

        with pytest.raises(IngestionError) as exc_info:
            fetch("communities", "new")

        assert "500" in str(exc_info.value)

    def test_uses_correct_endpoint_for_posts(self, mocker: Any) -> None:
        """Posts source should use /post/list endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"posts": []}

        mock_get = mocker.patch("httpx.get", return_value=mock_response)

        fetch("posts", "hot")

        call_url = mock_get.call_args[0][0]
        assert "/post/list" in call_url
        assert "sort=Hot" in call_url

    def test_uses_correct_endpoint_for_communities(self, mocker: Any) -> None:
        """Communities source should use /community/list endpoint."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"communities": []}

        mock_get = mocker.patch("httpx.get", return_value=mock_response)

        fetch("communities", "hot")

        call_url = mock_get.call_args[0][0]
        assert "/community/list" in call_url
        assert "sort=Hot" in call_url
