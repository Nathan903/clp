import unittest

from pydantic import ValidationError

from job_orchestration.scheduler.job_config import OutputConfig


class OutputConfigTest(unittest.TestCase):
    def test_legacy_queued_job_is_normalized(self):
        output = OutputConfig.model_validate(
            {
                "target_archive_size": 100,
                "target_dictionaries_size": 20,
                "target_encoded_file_size": 30,
                "target_segment_size": 40,
                "compression_level": 3,
            }
        )

        self.assertEqual(100, output.target_uncompressed_size)
        self.assertEqual(60, output.clp_s.target_encoded_size)
        self.assertEqual(20, output.clp.target_dictionaries_size)
        self.assertEqual(30, output.clp.target_encoded_file_size)
        self.assertEqual(40, output.clp.target_segment_size)

    def test_canonical_serialization_does_not_emit_legacy_root_fields(self):
        output = OutputConfig.model_validate(
            {
                "target_uncompressed_size": 100,
                "clp_s": {"target_encoded_size": 60},
                "clp": {
                    "target_dictionaries_size": 20,
                    "target_encoded_file_size": 30,
                    "target_segment_size": 40,
                },
                "compression_level": 3,
            }
        )

        serialized = output.model_dump()
        self.assertNotIn("target_archive_size", serialized)
        self.assertNotIn("target_dictionaries_size", serialized)
        self.assertNotIn("target_encoded_file_size", serialized)
        self.assertNotIn("target_segment_size", serialized)

    def test_mixed_legacy_and_canonical_fields_are_rejected(self):
        with self.assertRaises(ValidationError):
            OutputConfig.model_validate(
                {
                    "target_archive_size": 100,
                    "target_uncompressed_size": 100,
                    "target_dictionaries_size": 20,
                    "target_encoded_file_size": 30,
                    "target_segment_size": 40,
                    "compression_level": 3,
                }
            )

    def test_sizes_must_be_positive(self):
        with self.assertRaises(ValidationError):
            OutputConfig.model_validate(
                {
                    "target_uncompressed_size": 0,
                    "clp_s": {"target_encoded_size": 60},
                    "compression_level": 3,
                }
            )


if __name__ == "__main__":
    unittest.main()
