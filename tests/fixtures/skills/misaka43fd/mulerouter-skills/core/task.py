"""Task polling utilities for asynchronous API operations."""

import time
from dataclasses import dataclass
from enum import Enum

from .client import APIClient


class TaskStatus(Enum):
    """Task status values."""

    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PROCESSING = "processing"
    COMPLETED = "completed"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


@dataclass
class TaskResult:
    """Result of a task operation.

    Attributes:
        task_id: UUID of the task
        status: Current task status
        data: Full response data
        error: Error message if failed
        result_key: Key in data containing the result (e.g., 'images', 'videos')
        results: List of result URLs (images/videos)
    """

    task_id: str
    status: TaskStatus
    data: dict
    error: str | None = None
    result_key: str | None = None
    results: list[str] | None = None


def is_terminal_status(status: TaskStatus) -> bool:
    """Check if task status is terminal (completed or failed).

    Args:
        status: Task status

    Returns:
        True if status is terminal
    """
    return status in (TaskStatus.COMPLETED, TaskStatus.SUCCEEDED, TaskStatus.FAILED)


def is_success_status(status: TaskStatus) -> bool:
    """Check if task status indicates success.

    Args:
        status: Task status

    Returns:
        True if status indicates success
    """
    return status in (TaskStatus.COMPLETED, TaskStatus.SUCCEEDED)


def parse_task_response(response_data: dict, result_key: str = "images") -> TaskResult:
    """Parse task response into TaskResult.

    Args:
        response_data: Raw API response data
        result_key: Key containing the results (images, videos, etc.)

    Returns:
        Parsed TaskResult
    """
    task_info = response_data.get("task_info", {})
    task_id = task_info.get("id", "")
    status_str = task_info.get("status", "unknown")

    try:
        status = TaskStatus(status_str)
    except ValueError:
        status = TaskStatus.PENDING

    error = None
    if status == TaskStatus.FAILED:
        error_info = task_info.get("error", {})
        if isinstance(error_info, dict):
            error = error_info.get("detail") or error_info.get("title") or str(error_info)
        else:
            error = str(error_info)

    results = response_data.get(result_key) if is_success_status(status) else None

    return TaskResult(
        task_id=task_id,
        status=status,
        data=response_data,
        error=error,
        result_key=result_key,
        results=results,
    )


def poll_task(
    client: APIClient,
    task_path: str,
    task_id: str,
    result_key: str = "images",
    interval: float = 20.0,
    max_wait: float = 600.0,
    verbose: bool = True,
) -> TaskResult:
    """Poll a task until completion.

    Args:
        client: API client instance
        task_path: Base path for the task endpoint (e.g., /vendors/google/v1/nano-banana-pro/generation)
        task_id: UUID of the task to poll
        result_key: Key in response containing results
        interval: Polling interval in seconds
        max_wait: Maximum wait time in seconds
        verbose: Print status updates

    Returns:
        TaskResult with final status and results
    """
    start_time = time.time()
    poll_url = f"{task_path}/{task_id}"

    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait:
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                data={},
                error=f"Polling timeout after {max_wait}s",
            )

        response = client.get(poll_url)

        if not response.success:
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                data=response.data or {},
                error=response.error,
            )

        result = parse_task_response(response.data or {}, result_key)

        if verbose:
            print(f"[{elapsed:.1f}s] Task {task_id[:8]}... status: {result.status.value}")

        if is_terminal_status(result.status):
            return result

        time.sleep(interval)


def create_and_poll_task(
    client: APIClient,
    endpoint_path: str,
    request_body: dict,
    result_key: str = "images",
    interval: float = 20.0,
    max_wait: float = 600.0,
    verbose: bool = True,
) -> TaskResult:
    """Create a task and poll until completion.

    Args:
        client: API client instance
        endpoint_path: Path for the creation endpoint
        request_body: Request body for task creation
        result_key: Key in response containing results
        interval: Polling interval in seconds
        max_wait: Maximum wait time in seconds
        verbose: Print status updates

    Returns:
        TaskResult with final status and results
    """
    if verbose:
        print(f"Creating task at {endpoint_path}...")

    response = client.post(endpoint_path, json=request_body)

    if not response.success:
        return TaskResult(
            task_id="",
            status=TaskStatus.FAILED,
            data=response.data or {},
            error=response.error,
        )

    task_info = (response.data or {}).get("task_info", {})
    task_id = task_info.get("id")

    if not task_id:
        return TaskResult(
            task_id="",
            status=TaskStatus.FAILED,
            data=response.data or {},
            error="No task ID returned",
        )

    if verbose:
        print(f"Task created: {task_id}")

    return poll_task(
        client=client,
        task_path=endpoint_path,
        task_id=task_id,
        result_key=result_key,
        interval=interval,
        max_wait=max_wait,
        verbose=verbose,
    )
