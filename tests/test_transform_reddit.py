import polars as pl

from src.transformation.transform_reddit import (
    _convert_timestamps,
    _fill_nulls,
    _normalize_urls,
)
from src.transformation.prepare import _extract_to_dataframe
from src.models.reddit import SubredditData


class TestExtractToDataframe:
    def test_extracts_records_with_field_mapping(self) -> None:
        """Should map API field names to output column names."""
        records: list[SubredditData] = [
            {
                "display_name": "Python",
                "title": "Python Programming",
                "public_description": "News about Python",
                "subscribers": 1500000,
                "over18": False,
                "url": "/r/Python/",
                "created_utc": 1234567890.0,
            }
        ]

        result = _extract_to_dataframe(records)

        assert len(result) == 1
        assert result["subreddit_name"][0] == "Python"
        assert result["subscribers"][0] == 1500000
        assert result["description"][0] == "News about Python"
        assert result["is_nsfw"][0] is False

    def test_empty_list_returns_empty_dataframe_with_schema(self) -> None:
        """Empty input should return empty DataFrame with correct columns."""
        result = _extract_to_dataframe([])

        assert result.is_empty()
        expected_columns = {
            "subreddit_name", "title", "description", "subscribers",
            "is_nsfw", "url", "created_date"
        }
        assert set(result.columns) == expected_columns

    def test_multiple_records(self) -> None:
        """Multiple records should all be extracted."""
        records: list[SubredditData] = [
            {
                "display_name": "Python",
                "title": "Python Programming",
                "subscribers": 1500000,
            },
            {
                "display_name": "learnpython",
                "title": "Learn Python",
                "subscribers": 800000,
            },
        ]

        result = _extract_to_dataframe(records)

        assert len(result) == 2
        names = result["subreddit_name"].to_list()
        assert "Python" in names
        assert "learnpython" in names

    def test_missing_optional_fields_become_null(self) -> None:
        """Records missing optional fields should have null values."""
        records: list[SubredditData] = [
            {
                "display_name": "test",
                "title": "Test Sub",
                # Missing: public_description, subscribers, over18, url, created_utc
            }
        ]

        result = _extract_to_dataframe(records)

        assert len(result) == 1
        assert result["subreddit_name"][0] == "test"
        assert result["description"][0] is None
        assert result["subscribers"][0] is None


class TestNormalizeUrls:
    def test_prepends_reddit_domain_to_relative_url(self) -> None:
        """Relative URLs should get reddit.com prepended."""
        df = pl.DataFrame({"url": ["/r/Python/"]})
        result = _normalize_urls(df)

        assert result["url"][0] == "https://reddit.com/r/Python/"

    def test_does_not_modify_absolute_url(self) -> None:
        """URLs already starting with http should NOT be modified."""
        df = pl.DataFrame({"url": ["https://reddit.com/r/Python/"]})
        result = _normalize_urls(df)

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

    def test_fills_sources_column_when_present(self) -> None:
        """Sources column should be filled with empty list when null."""
        df = pl.DataFrame({
            "subreddit_name": ["Python"],
            "title": ["Python Programming"],
            "description": ["desc"],
            "subscribers": [1000],
            "is_nsfw": [False],
            "url": ["/r/Python/"],
            "created_date": ["2009-02-13"],
            "sources": [None],
        }, schema={
            "subreddit_name": pl.String,
            "title": pl.String,
            "description": pl.String,
            "subscribers": pl.Int64,
            "is_nsfw": pl.Boolean,
            "url": pl.String,
            "created_date": pl.String,
            "sources": pl.List(pl.String),
        })

        result = _fill_nulls(df)

        assert result["sources"][0].to_list() == []
