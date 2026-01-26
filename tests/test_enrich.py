from datetime import UTC, datetime, timedelta

import polars as pl

from src.transformation.enrich import enrich_communities, enrich_posts


class TestEnrichPosts:
    """Tests for enrich_posts function."""

    def _make_post_df(
        self,
        url: str | None = None,
        body: str | None = "test body",
        upvotes: int = 10,
        downvotes: int = 2,
        num_comments: int = 5,
        score: int = 8,
        published_date: str = "2025-01-20T12:00:00Z",
    ) -> pl.DataFrame:
        """Helper to create a single-row post DataFrame with proper schema."""
        return pl.DataFrame(
            {
                "url": [url],
                "body": [body],
                "upvotes": [upvotes],
                "downvotes": [downvotes],
                "num_comments": [num_comments],
                "score": [score],
                "published_date": [published_date],
            },
            schema={
                "url": pl.String,
                "body": pl.String,
                "upvotes": pl.Int64,
                "downvotes": pl.Int64,
                "num_comments": pl.Int64,
                "score": pl.Int64,
                "published_date": pl.String,
            },
        )

    def test_content_type_text_when_url_is_null(self) -> None:
        """Posts with null URL should be classified as 'text'."""
        df = self._make_post_df(url=None)

        result = enrich_posts(df)

        assert result["content_type"][0] == "text"

    def test_content_type_text_when_url_is_empty(self) -> None:
        """Posts with empty string URL should be classified as 'text'."""
        df = self._make_post_df(url="")

        result = enrich_posts(df)

        assert result["content_type"][0] == "text"

    def test_content_type_image_for_image_urls(self) -> None:
        """Posts with image URLs should be classified as 'image'."""
        df = pl.DataFrame(
            {
                "url": [
                    "https://example.com/photo.jpg",
                    "https://example.com/image.png",
                    "https://example.com/anim.gif",
                ],
                "body": ["", "", ""],
                "upvotes": [10, 20, 30],
                "downvotes": [2, 3, 4],
                "num_comments": [5, 6, 7],
                "score": [8, 17, 26],
                "published_date": ["2025-01-20T12:00:00Z"] * 3,
            }
        )

        result = enrich_posts(df)

        assert result["content_type"].to_list() == ["image", "image", "image"]

    def test_content_type_link_for_non_image_urls(self) -> None:
        """Posts with non-image URLs should be classified as 'link'."""
        df = self._make_post_df(url="https://example.com/article")

        result = enrich_posts(df)

        assert result["content_type"][0] == "link"

    def test_body_length_calculation(self) -> None:
        """Body length should count characters correctly."""
        df = pl.DataFrame(
            {
                "url": ["", ""],
                "body": ["Hello", "Hello World!"],
                "upvotes": [10, 10],
                "downvotes": [2, 2],
                "num_comments": [5, 5],
                "score": [8, 8],
                "published_date": ["2025-01-20T12:00:00Z"] * 2,
            }
        )

        result = enrich_posts(df)

        assert result["body_length"].to_list() == [5, 12]

    def test_body_length_zero_for_null_body(self) -> None:
        """Null body should result in body_length of 0."""
        df = self._make_post_df(url="https://example.com", body=None)

        result = enrich_posts(df)

        assert result["body_length"][0] == 0

    def test_comment_density_calculation(self) -> None:
        """Comment density should be num_comments / score."""
        df = self._make_post_df(num_comments=20, score=10)

        result = enrich_posts(df)

        assert result["comment_density"][0] == 2.0  # 20 / 10

    def test_comment_density_clips_score_to_one(self) -> None:
        """Score of 0 or negative should be clipped to 1 to avoid division issues."""
        df = pl.DataFrame(
            {
                "url": ["", ""],
                "body": ["test", "test"],
                "upvotes": [0, 5],
                "downvotes": [0, 10],
                "num_comments": [5, 10],
                "score": [0, -5],
                "published_date": ["2025-01-20T12:00:00Z"] * 2,
            }
        )

        result = enrich_posts(df)

        # Both should use clipped score of 1
        assert result["comment_density"].to_list() == [5.0, 10.0]

    def test_age_hours_calculation(self) -> None:
        """Age hours should be positive for past dates."""
        past_time = datetime.now(UTC) - timedelta(hours=24)
        df = self._make_post_df(published_date=past_time.isoformat())

        result = enrich_posts(df)

        # Should be approximately 24 hours (allow some tolerance)
        age = result["age_hours"][0]
        assert 23.9 < age < 24.1

    def test_engagement_ratio_normal_calculation(self) -> None:
        """Engagement ratio should be upvotes / total votes."""
        df = self._make_post_df(upvotes=80, downvotes=20)

        result = enrich_posts(df)

        assert result["engagement_ratio"][0] == 0.8  # 80 / 100

    def test_engagement_ratio_zero_votes_defaults_to_half(self) -> None:
        """Zero upvotes and downvotes should default to 0.5."""
        df = self._make_post_df(upvotes=0, downvotes=0)

        result = enrich_posts(df)

        assert result["engagement_ratio"][0] == 0.5  # 0/0 -> NaN -> 0.5

    def test_engagement_ratio_null_treated_as_zero(self) -> None:
        """Null upvotes/downvotes should be treated as 0."""
        df = pl.DataFrame(
            {
                "url": [""],
                "body": ["test"],
                "upvotes": [None],
                "downvotes": [None],
                "num_comments": [5],
                "score": [8],
                "published_date": ["2025-01-20T12:00:00Z"],
            },
            schema={
                "url": pl.String,
                "body": pl.String,
                "upvotes": pl.Int64,
                "downvotes": pl.Int64,
                "num_comments": pl.Int64,
                "score": pl.Int64,
                "published_date": pl.String,
            },
        )

        result = enrich_posts(df)

        # null/null -> 0/0 -> NaN -> 0.5
        assert result["engagement_ratio"][0] == 0.5


class TestEnrichCommunities:
    """Tests for enrich_communities function."""

    def _make_community_df(
        self,
        description: str | None = "A test community",
        users_active_week: int | None = 100,
        published_date: str = "2024-01-01T00:00:00Z",
    ) -> pl.DataFrame:
        """Helper to create a single-row community DataFrame with proper schema."""
        return pl.DataFrame(
            {
                "description": [description],
                "users_active_week": [users_active_week],
                "published_date": [published_date],
            },
            schema={
                "description": pl.String,
                "users_active_week": pl.Int64,
                "published_date": pl.String,
            },
        )

    def test_description_length_calculation(self) -> None:
        """Description length should count characters correctly."""
        df = self._make_community_df(
            description="A community about Python programming")

        result = enrich_communities(df)

        assert result["description_length"][0] == 36

    def test_description_length_zero_for_null(self) -> None:
        """Null description should result in length of 0."""
        df = self._make_community_df(description=None)

        result = enrich_communities(df)

        assert result["description_length"][0] == 0

    def test_is_active_community_boundary(self) -> None:
        """Threshold is > 10: exactly 10 is inactive, 11 is active."""
        df = pl.DataFrame(
            {
                "description": ["at threshold", "above threshold"],
                "users_active_week": [10, 11],
                "published_date": ["2024-01-01T00:00:00Z"] * 2,
            }
        )

        result = enrich_communities(df)

        assert result["is_active_community"].to_list() == [False, True]

    def test_is_active_community_null_treated_as_zero(self) -> None:
        """Null users_active_week should be treated as 0 (inactive)."""
        df = self._make_community_df(users_active_week=None)

        result = enrich_communities(df)

        assert result["is_active_community"][0] is False

    def test_age_hours_calculation(self) -> None:
        """Age hours should be positive for past dates."""
        past_time = datetime.now(UTC) - timedelta(hours=48)
        df = self._make_community_df(published_date=past_time.isoformat())

        result = enrich_communities(df)

        age = result["age_hours"][0]
        assert 47.9 < age < 48.1
