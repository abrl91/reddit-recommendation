import polars as pl

from src.transformation.transform import fill_nulls


class TestFillNulls:
    def test_applies_default_values_to_community_nulls(self) -> None:
        """Null values should be filled with appropriate defaults."""
        df = pl.DataFrame(
            {
                "community_name": [None],
                "title": [None],
                "description": [None],
                "subscribers": [None],
                "is_nsfw": [None],
                "url": [None],
                "created_date": [None],
                "instance": [None],
            },
            schema={
                "community_name": pl.String,
                "title": pl.String,
                "description": pl.String,
                "subscribers": pl.Int64,
                "is_nsfw": pl.Boolean,
                "url": pl.String,
                "created_date": pl.String,
                "instance": pl.String,
            },
        )

        result = fill_nulls(df)

        assert result["community_name"][0] == ""
        assert result["title"][0] == ""
        assert result["description"][0] == ""
        assert result["subscribers"][0] == 0
        assert result["is_nsfw"][0] is False
        assert result["url"][0] == ""
        assert result["created_date"][0] == ""
        assert result["instance"][0] == "unknown"

    def test_applies_default_values_to_post_nulls(self) -> None:
        """Post-specific null values should be filled."""
        df = pl.DataFrame(
            {
                "body": [None],
                "score": [None],
                "num_comments": [None],
            },
            schema={
                "body": pl.String,
                "score": pl.Int64,
                "num_comments": pl.Int64,
            },
        )

        result = fill_nulls(df)

        assert result["body"][0] == ""
        assert result["score"][0] == 0
        assert result["num_comments"][0] == 0

    def test_preserves_existing_non_null_values(self) -> None:
        """Non-null values should not be changed by fill_nulls."""
        df = pl.DataFrame(
            {
                "community_name": ["Python"],
                "title": ["Python Programming"],
                "description": ["News about Python"],
                "subscribers": [1500000],
                "is_nsfw": [True],
                "url": ["https://lemmy.world/c/python"],
                "created_date": ["2023-01-01"],
                "instance": ["lemmy.world"],
            }
        )

        result = fill_nulls(df)

        assert result["community_name"][0] == "Python"
        assert result["subscribers"][0] == 1500000
        assert result["is_nsfw"][0] is True
        assert result["instance"][0] == "lemmy.world"

    def test_fills_sources_column_when_present(self) -> None:
        """Sources column should be filled with empty list when null."""
        df = pl.DataFrame(
            {
                "community_name": ["Python"],
                "sources": [None],
            },
            schema={
                "community_name": pl.String,
                "sources": pl.List(pl.String),
            },
        )

        result = fill_nulls(df)

        assert result["sources"][0].to_list() == []
