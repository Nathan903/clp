"""Tests for query archive-size metric accounting."""

# ruff: noqa: D101, D102, DTZ005, PT009, SLF001

import datetime
import unittest
from typing import Any
from unittest.mock import MagicMock, patch

from job_orchestration.executor.query import fs_search_task
from job_orchestration.executor.query import utils as query_utils
from job_orchestration.scheduler.constants import QueryTaskStatus
from job_orchestration.scheduler.job_config import SearchJobConfig
from job_orchestration.scheduler.query import query_scheduler
from job_orchestration.scheduler.scheduler_data import (
    InternalJobState,
    QueryTaskResult,
    SearchJob,
)


class _FakeCursor:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.query: str | None = None

    def close(self) -> None:
        pass

    def execute(self, query: str) -> None:
        self.query = query

    def fetchall(self) -> list[dict[str, Any]]:
        return self._rows


class _FakeConnection:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.cursor_instance = _FakeCursor(rows)
        self.dictionary = False

    def cursor(self, dictionary: bool = False) -> _FakeCursor:
        self.dictionary = dictionary
        return self.cursor_instance


class QueryArchiveSizeSelectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.search_config = SearchJobConfig(query_string="*", max_num_results=10)

    def test_archive_selection_without_datasets_includes_sizes(self) -> None:
        rows = [
            {
                "archive_id": "archive-id",
                "end_timestamp": 123,
                "uncompressed_size": 1000,
                "compressed_size": 100,
            }
        ]
        connection = _FakeConnection(rows)

        actual = query_scheduler._get_archives_for_search_without_datasets(
            connection,
            "clp_",
            self.search_config,
            None,
        )

        self.assertEqual(rows, actual)
        query = connection.cursor_instance.query
        self.assertIsNotNone(query)
        assert query is not None
        self.assertIn("uncompressed_size", query)
        self.assertIn("size AS compressed_size", query)

    def test_dataset_archive_selection_includes_sizes(self) -> None:
        connection = _FakeConnection([])

        query_scheduler.get_archives_for_search(
            connection,
            "clp_",
            self.search_config,
            None,
            ["alpha", "beta"],
        )

        query = connection.cursor_instance.query
        self.assertIsNotNone(query)
        assert query is not None
        self.assertEqual(2, query.count("uncompressed_size"))
        self.assertEqual(2, query.count("size AS compressed_size"))
        self.assertIn("'alpha' AS dataset", query)
        self.assertIn("'beta' AS dataset", query)


class QueryArchiveSizePropagationTest(unittest.TestCase):
    def test_search_signature_receives_archive_sizes(self) -> None:
        job = SearchJob(
            id="1",
            state=InternalJobState.WAITING_FOR_DISPATCH,
            search_config=SearchJobConfig(query_string="*", max_num_results=10),
            num_archives_to_search=1,
            num_archives_searched=0,
            remaining_archives_for_search=[],
        )
        archives = [
            {
                "archive_id": "archive-id",
                "dataset": "default",
                "uncompressed_size": 1000,
                "compressed_size": 100,
            }
        ]

        signature = MagicMock()
        with (
            patch.object(query_scheduler, "search") as search_task,
            patch.object(query_scheduler.celery, "group", side_effect=lambda tasks: list(tasks)),
        ):
            search_task.s.return_value = signature
            query_scheduler.get_task_group_for_job(
                archives,
                [42],
                job,
                {"host": "metadata-db"},
                "mongodb://results-cache",
            )

        search_task.s.assert_called_once_with(
            job_id="1",
            archive_id="archive-id",
            task_id=42,
            job_config_blob=job.get_cached_config_blob(),
            dataset="default",
            clp_metadata_db_conn_params={"host": "metadata-db"},
            results_cache_uri="mongodb://results-cache",
        )
        signature.set.assert_called_once_with(
            headers={
                query_scheduler.QUERY_TASK_UNCOMPRESSED_SIZE_HEADER: 1000,
                query_scheduler.QUERY_TASK_COMPRESSED_SIZE_HEADER: 100,
            }
        )

    def test_worker_reads_archive_sizes_from_headers(self) -> None:
        fs_search_task.search.push_request(
            headers={
                query_scheduler.QUERY_TASK_UNCOMPRESSED_SIZE_HEADER: 1000,
                query_scheduler.QUERY_TASK_COMPRESSED_SIZE_HEADER: 100,
            }
        )
        try:
            with patch.object(fs_search_task, "search_entry_point", return_value={}) as entry_point:
                fs_search_task.search.run(
                    job_id="1",
                    task_id=42,
                    job_config_blob=b"\x80",
                    archive_id="archive-id",
                    clp_metadata_db_conn_params={"host": "metadata-db"},
                    results_cache_uri="mongodb://results-cache",
                    dataset="default",
                )
        finally:
            fs_search_task.search.pop_request()

        entry_point.assert_called_once_with(
            "1",
            42,
            b"\x80",
            "archive-id",
            {"host": "metadata-db"},
            "mongodb://results-cache",
            dataset="default",
            uncompressed_size=1000,
            compressed_size=100,
        )

    def test_worker_accepts_tasks_without_archive_size_headers(self) -> None:
        fs_search_task.search.push_request(headers=None)
        try:
            with patch.object(fs_search_task, "search_entry_point", return_value={}) as entry_point:
                fs_search_task.search.run(
                    job_id="1",
                    task_id=42,
                    job_config_blob=b"\x80",
                    archive_id="archive-id",
                    clp_metadata_db_conn_params={"host": "metadata-db"},
                    results_cache_uri="mongodb://results-cache",
                )
        finally:
            fs_search_task.search.pop_request()

        entry_point.assert_called_once_with(
            "1",
            42,
            b"\x80",
            "archive-id",
            {"host": "metadata-db"},
            "mongodb://results-cache",
            dataset=None,
            uncompressed_size=None,
            compressed_size=None,
        )

    def test_controlled_failure_preserves_archive_sizes(self) -> None:
        with patch.object(query_utils, "update_query_task_metadata"):
            result = query_utils.report_task_failure(
                sql_adapter=MagicMock(),
                task_id=42,
                start_time=datetime.datetime.now(),
                uncompressed_size=1000,
                compressed_size=100,
            )

        task_result = QueryTaskResult.model_validate(result)
        self.assertEqual(1000, task_result.uncompressed_size)
        self.assertEqual(100, task_result.compressed_size)


class QueryScanMetricTest(unittest.TestCase):
    def setUp(self) -> None:
        self.uncompressed_counter = patch.object(
            query_scheduler, "uncompressed_bytes_scanned_counter"
        ).start()
        self.compressed_counter = patch.object(
            query_scheduler, "compressed_bytes_scanned_counter"
        ).start()
        self.addCleanup(patch.stopall)

    def test_records_both_archive_sizes(self) -> None:
        query_scheduler._record_search_bytes_scanned(
            QueryTaskResult(
                status=QueryTaskStatus.SUCCEEDED,
                task_id=42,
                duration=1.0,
                uncompressed_size=1000,
                compressed_size=100,
            )
        )

        self.uncompressed_counter.add.assert_called_once_with(1000)
        self.compressed_counter.add.assert_called_once_with(100)

    def test_records_neither_metric_when_a_size_is_missing(self) -> None:
        with patch.object(query_scheduler.logger, "error") as logger_error:
            query_scheduler._record_search_bytes_scanned(
                QueryTaskResult(
                    status=QueryTaskStatus.SUCCEEDED,
                    task_id=42,
                    duration=1.0,
                    uncompressed_size=1000,
                )
            )

        self.uncompressed_counter.add.assert_not_called()
        self.compressed_counter.add.assert_not_called()
        logger_error.assert_called_once()

    def test_records_neither_metric_for_negative_sizes(self) -> None:
        with patch.object(query_scheduler.logger, "error") as logger_error:
            query_scheduler._record_search_bytes_scanned(
                QueryTaskResult(
                    status=QueryTaskStatus.SUCCEEDED,
                    task_id=42,
                    duration=1.0,
                    uncompressed_size=-1,
                    compressed_size=100,
                )
            )

        self.uncompressed_counter.add.assert_not_called()
        self.compressed_counter.add.assert_not_called()
        logger_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
