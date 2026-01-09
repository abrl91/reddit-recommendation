import pytest

from src.transformation.context import pipeline_step
from src.transformation.exceptions import TransformationError


class TestPipelineStep:
    def test_success_passes_through(self) -> None:
        """When no exception is raised, context manager should complete normally."""
        result = []
        with pipeline_step("test_step", record_count=10):
            result.append("executed")

        assert result == ["executed"]

    def test_wraps_generic_exception_in_transformation_error(self) -> None:
        """Generic exceptions should be wrapped in TransformationError."""
        with pytest.raises(TransformationError) as exc_info:
            with pipeline_step("failing_step", record_count=5):
                raise ValueError("something went wrong")

        assert "failing_step" in str(exc_info.value)
        assert exc_info.value.step == "failing_step"
        assert exc_info.value.record_count == 5

    def test_preserves_transformation_error_without_double_wrapping(self) -> None:
        """TransformationError should be re-raised as-is, not double-wrapped."""
        original_error = TransformationError("original error", step="original_step", record_count=3)

        with pytest.raises(TransformationError) as exc_info:
            with pipeline_step("outer_step", record_count=10):
                raise original_error

        # Should be the exact same error, not wrapped again
        assert exc_info.value is original_error
        assert exc_info.value.step == "original_step"
        assert exc_info.value.record_count == 3

    def test_includes_step_name_in_error_message(self) -> None:
        """Error message should include the step name for debugging."""
        with pytest.raises(TransformationError) as exc_info:
            with pipeline_step("normalize_urls"):
                raise RuntimeError("URL processing failed")

        assert "normalize_urls" in str(exc_info.value)

    def test_handles_none_record_count(self) -> None:
        """Should work when record_count is None."""
        with pytest.raises(TransformationError) as exc_info:
            with pipeline_step("test_step", record_count=None):
                raise ValueError("error")

        assert exc_info.value.record_count is None
