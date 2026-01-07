import polars as pl

from src.data_transformation.transform_reddit import (
    _convert_timestamps,
    _extract_to_dataframe,
    _fill_nulls,
    _normalize_urls,
    _validate_data_quality,
    clean_raw_data,
)
from src.models.reddit import SubredditListingResponse


class TestExtractToDataframe:
    def test_extracts_records_from_nested_structure(
        self, sample_subreddit_response: SubredditListingResponse
    ) -> None:
        """Should extract subreddit data from nested API response."""
        result = _extract_to_dataframe([sample_subreddit_response])

        assert len(result) == 1
        assert result["subreddit_name"][0] == "Python"
        assert result["subscribers"][0] == 1500000

    def test_empty_list_returns_empty_dataframe_with_schema(self) -> None:
        """Empty input should return empty DataFrame with correct columns."""
        result = _extract_to_dataframe([])

        assert result.is_empty()
        # Should have schema even when empty
        expected_columns = {
            "subreddit_name", "title", "description", "subscribers",
            "is_nsfw", "url", "created_date"
        }
        assert set(result.columns) == expected_columns

    def test_multiple_responses_combined(
        self, sample_subreddit_response_multiple: SubredditListingResponse
    ) -> None:
        """Multiple subreddits in response should all be extracted."""
        result = _extract_to_dataframe([sample_subreddit_response_multiple])

        assert len(result) == 2
        names = result["subreddit_name"].to_list()
        assert "Python" in names
        assert "learnpython" in names

    def test_missing_optional_fields_become_null(self) -> None:
        """API response missing optional fields should result in null values."""
        response: SubredditListingResponse = {
            "kind": "Listing",
            "data": {
                "children": [
                    {
                        "kind": "t5",
                        "data": {
                            "display_name": "test",
                            "title": "Test Sub",
                            # Missing: public_description, subscribers, over18, url, created_utc
                        }
                    }
                ]
            }
        }

        result = _extract_to_dataframe([response])

        assert len(result) == 1
        assert result["subreddit_name"][0] == "test"
        assert result["description"][0] is None


class TestNormalizeUrls:
    def test_prepends_reddit_domain_to_relative_url(self) -> None:
        """Relative URLs should get reddit.com prepended."""
        df = pl.DataFrame({"url": ["/r/Python/"]})
        result = _normalize_urls(df)

        assert result["url"][0] == "https://reddit.com/r/Python/"

    def test_does_not_double_prepend_absolute_url(self) -> None:
        """URLs already starting with http should NOT be modified."""
        df = pl.DataFrame({"url": ["https://reddit.com/r/Python/"]})
        result = _normalize_urls(df)

        # BUG: Currently this fails - it double-prepends
        assert result["url"][0] == "https://reddit.com/r/Python/"
        assert "https://reddit.comhttps://" not in result["url"][0]

    def test_handles_empty_url(self) -> None:
        """Empty URL should get domain prepended (results in just the domain)."""
        df = pl.DataFrame({"url": [""]})
        result = _normalize_urls(df)

        assert result["url"][0] == "https://reddit.com"


class TestConvertTimestamps:
    def test_converts_unix_epoch_to_date_string(self) -> None:
        """Unix timestamp should be converted to YYYY-MM-DD format."""
        # 1234567890 = 2009-02-13
        df = pl.DataFrame({"created_date": [1234567890.0]})
        result = _convert_timestamps(df)

        assert result["created_date"][0] == "2009-02-13"

    def test_handles_null_timestamp(self) -> None:
        """Null timestamp should remain null after conversion."""
        df = pl.DataFrame({"created_date": [None]}, schema={"created_date": pl.Float64})
        result = _convert_timestamps(df)

        assert result["created_date"][0] is None


class TestFillNulls:
    def test_applies_default_values_to_nulls(self) -> None:
        """Null values should be filled with appropriate defaults."""
        df = pl.DataFrame({
            "subreddit_name": [None],
            "title": [None],
            "description": [None],
            "subscribers": [None],
            "is_nsfw": [None],
            "url": [None],
            "created_date": [None],
        }, schema={
            "subreddit_name": pl.String,
            "title": pl.String,
            "description": pl.String,
            "subscribers": pl.Int64,
            "is_nsfw": pl.Boolean,
            "url": pl.String,
            "created_date": pl.String,
        })

        result = _fill_nulls(df)

        assert result["subreddit_name"][0] == ""
        assert result["title"][0] == ""
        assert result["description"][0] == ""
        assert result["subscribers"][0] == 0
        assert result["is_nsfw"][0] is False
        assert result["url"][0] == ""
        assert result["created_date"][0] == ""

    def test_preserves_existing_non_null_values(self) -> None:
        """Non-null values should not be changed by fill_nulls."""
        df = pl.DataFrame({
            "subreddit_name": ["Python"],
            "title": ["Python Programming"],
            "description": ["News about Python"],
            "subscribers": [1500000],
            "is_nsfw": [True],
            "url": ["https://reddit.com/r/Python/"],
            "created_date": ["2009-02-13"],
        })

        result = _fill_nulls(df)

        assert result["subreddit_name"][0] == "Python"
        assert result["subscribers"][0] == 1500000
        assert result["is_nsfw"][0] is True


class TestValidateDataQuality:
    def test_filters_empty_subreddit_names(self) -> None:
        """Records with empty subreddit_name should be filtered out."""
        df = pl.DataFrame({
            "subreddit_name": ["Python", "", "learnpython"],
        })

        result = _validate_data_quality(df)

        assert len(result) == 2
        assert "" not in result["subreddit_name"].to_list()

    def test_filters_null_subreddit_names(self) -> None:
        """Records with null subreddit_name should be filtered out."""
        df = pl.DataFrame({
            "subreddit_name": ["Python", None, "learnpython"],
        })

        result = _validate_data_quality(df)

        assert len(result) == 2
        assert None not in result["subreddit_name"].to_list()

    def test_keeps_valid_records(self) -> None:
        """Records with valid subreddit_name should be kept."""
        df = pl.DataFrame({
            "subreddit_name": ["Python", "learnpython", "rust"],
        })

        result = _validate_data_quality(df)

        assert len(result) == 3

    def test_all_invalid_returns_empty_dataframe(self) -> None:
        """If all records are invalid, should return empty DataFrame."""
        df = pl.DataFrame({
            "subreddit_name": ["", None, ""],
        })

        result = _validate_data_quality(df)

        assert result.is_empty()


class TestCleanRawData:
    def test_full_pipeline_processes_valid_data(
        self, sample_subreddit_response: SubredditListingResponse
    ) -> None:
        """Full pipeline should process valid data end-to-end."""
        result = clean_raw_data([sample_subreddit_response])

        assert len(result) == 1
        assert result["subreddit_name"][0] == "Python"
        assert "https://reddit.com" in result["url"][0]
        assert "processed_at" in result.columns

    def test_empty_input_returns_empty_dataframe(self) -> None:
        """Empty input should return empty DataFrame."""
        result = clean_raw_data([])

        assert result.is_empty()

    def test_pipeline_filters_invalid_records(self) -> None:
        """Records with empty/null subreddit_name should be filtered."""
        response: SubredditListingResponse = {
            "kind": "Listing",
            "data": {
                "children": [
                    {
                        "kind": "t5",
                        "data": {
                            "display_name": "Python",
                            "title": "Python",
                            "public_description": "desc",
                            "subscribers": 100,
                            "over18": False,
                            "url": "/r/Python/",
                            "created_utc": 1234567890.0,
                        }
                    },
                    {
                        "kind": "t5",
                        "data": {
                            "display_name": "",  # Invalid - will be filtered
                            "title": "Empty",
                            "public_description": "desc",
                            "subscribers": 50,
                            "over18": False,
                            "url": "/r/empty/",
                            "created_utc": 1234567890.0,
                        }
                    },
                ]
            }
        }

        result = clean_raw_data([response])

        assert len(result) == 1
        assert result["subreddit_name"][0] == "Python"
