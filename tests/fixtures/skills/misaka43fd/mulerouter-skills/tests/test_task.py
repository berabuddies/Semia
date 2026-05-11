"""Tests for core.task module."""

from core.task import (
    TaskResult,
    TaskStatus,
    is_success_status,
    is_terminal_status,
    parse_task_response,
)


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_status_values(self) -> None:
        """Test status enum values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"


class TestIsTerminalStatus:
    """Tests for is_terminal_status function."""

    def test_terminal_statuses(self) -> None:
        """Test terminal statuses return True."""
        assert is_terminal_status(TaskStatus.COMPLETED) is True
        assert is_terminal_status(TaskStatus.SUCCEEDED) is True
        assert is_terminal_status(TaskStatus.FAILED) is True

    def test_non_terminal_statuses(self) -> None:
        """Test non-terminal statuses return False."""
        assert is_terminal_status(TaskStatus.PENDING) is False
        assert is_terminal_status(TaskStatus.PROCESSING) is False
        assert is_terminal_status(TaskStatus.RUNNING) is False
        assert is_terminal_status(TaskStatus.QUEUED) is False


class TestIsSuccessStatus:
    """Tests for is_success_status function."""

    def test_success_statuses(self) -> None:
        """Test success statuses return True."""
        assert is_success_status(TaskStatus.COMPLETED) is True
        assert is_success_status(TaskStatus.SUCCEEDED) is True

    def test_non_success_statuses(self) -> None:
        """Test non-success statuses return False."""
        assert is_success_status(TaskStatus.FAILED) is False
        assert is_success_status(TaskStatus.PENDING) is False


class TestParseTaskResponse:
    """Tests for parse_task_response function."""

    def test_parse_pending_task(self) -> None:
        """Test parsing a pending task response."""
        response = {
            "task_info": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "status": "pending",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            }
        }

        result = parse_task_response(response)
        assert result.task_id == "123e4567-e89b-12d3-a456-426614174000"
        assert result.status == TaskStatus.PENDING
        assert result.results is None
        assert result.error is None

    def test_parse_completed_task_with_images(self) -> None:
        """Test parsing a completed task with images."""
        response = {
            "task_info": {
                "id": "123",
                "status": "completed",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            },
            "images": ["https://example.com/image1.png", "https://example.com/image2.png"],
        }

        result = parse_task_response(response, result_key="images")
        assert result.status == TaskStatus.COMPLETED
        assert result.results == [
            "https://example.com/image1.png",
            "https://example.com/image2.png",
        ]

    def test_parse_completed_task_with_videos(self) -> None:
        """Test parsing a completed task with videos."""
        response = {
            "task_info": {
                "id": "456",
                "status": "succeeded",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
            },
            "videos": ["https://example.com/video.mp4"],
        }

        result = parse_task_response(response, result_key="videos")
        assert result.status == TaskStatus.SUCCEEDED
        assert result.results == ["https://example.com/video.mp4"]

    def test_parse_failed_task(self) -> None:
        """Test parsing a failed task with error."""
        response = {
            "task_info": {
                "id": "789",
                "status": "failed",
                "created_at": "2025-01-01T00:00:00Z",
                "updated_at": "2025-01-01T00:00:00Z",
                "error": {
                    "code": 3001,
                    "title": "Content Error",
                    "detail": "The prompt contains prohibited content",
                },
            }
        }

        result = parse_task_response(response)
        assert result.status == TaskStatus.FAILED
        assert result.error == "The prompt contains prohibited content"
        assert result.results is None

    def test_parse_unknown_status(self) -> None:
        """Test parsing response with unknown status defaults to PENDING."""
        response = {
            "task_info": {
                "id": "abc",
                "status": "unknown_status",
            }
        }

        result = parse_task_response(response)
        assert result.status == TaskStatus.PENDING


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_task_result_creation(self) -> None:
        """Test TaskResult creation."""
        result = TaskResult(
            task_id="test-123",
            status=TaskStatus.COMPLETED,
            data={"task_info": {"id": "test-123"}},
            results=["https://example.com/result.png"],
            result_key="images",
        )

        assert result.task_id == "test-123"
        assert result.status == TaskStatus.COMPLETED
        assert result.results == ["https://example.com/result.png"]
        assert result.error is None
