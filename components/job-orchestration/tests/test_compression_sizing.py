import json
import pathlib
import unittest
from unittest.mock import patch

from clp_py_utils.core import FileMetadata
from job_orchestration.executor.compress.compression_task import (
    _make_clp_command_and_env,
    _make_clp_s_command_and_env,
)
from job_orchestration.scheduler.compress.partition import PathsToCompressBuffer
from job_orchestration.scheduler.job_config import ClpIoConfig, FsInputConfig, OutputConfig


class CompressionSizingTest(unittest.TestCase):
    @staticmethod
    def _make_output_config() -> OutputConfig:
        return OutputConfig.model_validate(
            {
                "target_uncompressed_size": 100,
                "clp_s": {"target_encoded_size": 123},
                "clp": {
                    "target_dictionaries_size": 20,
                    "target_encoded_file_size": 30,
                    "target_segment_size": 40,
                },
                "compression_level": 3,
            }
        )

    @classmethod
    def _make_io_config(cls) -> ClpIoConfig:
        return ClpIoConfig(
            input=FsInputConfig(paths_to_compress=[], unstructured=False),
            output=cls._make_output_config(),
        )

    def test_scheduler_partitions_by_target_uncompressed_size(self):
        buffer = PathsToCompressBuffer(
            maintain_file_ordering=True,
            empty_directories_allowed=False,
            scheduling_job_id=1,
            clp_io_config=self._make_io_config(),
            clp_metadata_db_connection_config={},
        )

        for ix in range(3):
            buffer.add_file(FileMetadata(pathlib.Path(f"file-{ix}.log"), 60))
        self.assertEqual(0, buffer.num_tasks)

        buffer.add_file(FileMetadata(pathlib.Path("file-3.log"), 60))
        self.assertEqual(2, buffer.num_tasks)

        worker_config = json.loads(buffer.get_tasks()[0]["clp_io_config_json"])
        self.assertEqual(100, worker_config["output"]["target_uncompressed_size"])
        self.assertNotIn("target_archive_size", worker_config["output"])

    def test_clp_s_uses_direct_target_encoded_size(self):
        command, _ = _make_clp_s_command_and_env(
            pathlib.Path("/opt/clp"),
            pathlib.Path("/archives"),
            self._make_io_config(),
            False,
        )

        option_ix = command.index("--target-encoded-size")
        self.assertEqual("123", command[option_ix + 1])

    @patch(
        "job_orchestration.executor.compress.compression_task."
        "_get_db_connection_env_vars_for_clp_cmd",
        return_value={},
    )
    @patch(
        "job_orchestration.executor.compress.compression_task._get_db_connection_args_for_clp_cmd",
        return_value=[],
    )
    def test_clp_uses_engine_specific_targets(self, *_):
        command, _ = _make_clp_command_and_env(
            pathlib.Path("/opt/clp"),
            pathlib.Path("/archives"),
            self._make_io_config(),
            {},
        )

        self.assertEqual("20", command[command.index("--target-dictionaries-size") + 1])
        self.assertEqual("30", command[command.index("--target-encoded-file-size") + 1])
        self.assertEqual("40", command[command.index("--target-segment-size") + 1])


if __name__ == "__main__":
    unittest.main()
