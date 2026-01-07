from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from src.data_ingestion.exceptions import IngestionError
from src.data_ingestion.fetch_reddit import fetch_popular_subreddits
from src.models.reddit import SubredditListingResponse


class TestFetchPopularSubreddits:
    def test_success_returns_parsed_response(
        self,
        mocker: Any,
        sample_subreddit_response: SubredditListingResponse,
    ) -> None:
        """Successful 200 response should return parsed JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = sample_subreddit_response

        mocker.patch("httpx.get", return_value=mock_response)

        result = fetch_popular_subreddits()

        assert result == sample_subreddit_response
        assert result["kind"] == "Listing"

    def test_network_error_raises_ingestion_error(self, mocker: Any) -> None:
        """Network errors (timeout, connection refused) should raise IngestionError."""
        mocker.patch(
            "httpx.get",
            side_effect=httpx.RequestError("Connection refused"),
        )

        with pytest.raises(IngestionError) as exc_info:
            fetch_popular_subreddits()

        assert "Network error" in str(exc_info.value)

    def test_http_403_raises_ingestion_error(self, mocker: Any) -> None:
        """HTTP 403 Forbidden should raise IngestionError."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        mocker.patch("httpx.get", return_value=mock_response)

        with pytest.raises(IngestionError) as exc_info:
            fetch_popular_subreddits()

        assert "403" in str(exc_info.value)

    def test_http_500_raises_ingestion_error(self, mocker: Any) -> None:
        """HTTP 500 Server Error should raise IngestionError."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mocker.patch("httpx.get", return_value=mock_response)

        with pytest.raises(IngestionError) as exc_info:
            fetch_popular_subreddits()

        assert "500" in str(exc_info.value)

    def test_uses_correct_url_and_headers(self, mocker: Any) -> None:
        """Should call Reddit API with correct URL and User-Agent header."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"kind": "Listing", "data": {"children": []}}

        mock_get = mocker.patch("httpx.get", return_value=mock_response)

        fetch_popular_subreddits()

        mock_get.assert_called_once()
        call_args = mock_get.call_args

        assert "reddit.com/subreddits/popular.json" in call_args[0][0]
        assert "User-Agent" in call_args[1]["headers"]
        assert call_args[1]["timeout"] == 30
