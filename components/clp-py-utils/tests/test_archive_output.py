import unittest

from pydantic import ValidationError

from clp_py_utils.clp_config import ArchiveOutput


class ArchiveOutputTest(unittest.TestCase):
    def test_defaults_use_coordinator_and_engine_specific_names(self):
        output = ArchiveOutput()

        self.assertEqual(256 * 1024 * 1024, output.target_uncompressed_size)
        self.assertEqual(288 * 1024 * 1024, output.clp_s.target_encoded_size)
        self.assertEqual(32 * 1024 * 1024, output.clp.target_dictionaries_size)
        self.assertEqual(256 * 1024 * 1024, output.clp.target_encoded_file_size)
        self.assertEqual(256 * 1024 * 1024, output.clp.target_segment_size)

    def test_legacy_fields_are_normalized(self):
        output = ArchiveOutput.model_validate(
            {
                "target_archive_size": 100,
                "target_dictionaries_size": 20,
                "target_encoded_file_size": 30,
                "target_segment_size": 40,
            }
        )

        self.assertEqual(100, output.target_uncompressed_size)
        self.assertEqual(60, output.clp_s.target_encoded_size)
        self.assertEqual(20, output.clp.target_dictionaries_size)
        self.assertEqual(30, output.clp.target_encoded_file_size)
        self.assertEqual(40, output.clp.target_segment_size)
        self.assertNotIn("target_archive_size", output.model_dump())

    def test_quoted_legacy_sizes_are_coerced_before_derivation(self):
        output = ArchiveOutput.model_validate(
            {
                "target_archive_size": "100",
                "target_dictionaries_size": "20",
                "target_encoded_file_size": "30",
                "target_segment_size": "40",
            }
        )

        self.assertEqual(100, output.target_uncompressed_size)
        self.assertEqual(60, output.clp_s.target_encoded_size)
        self.assertEqual(20, output.clp.target_dictionaries_size)
        self.assertEqual(30, output.clp.target_encoded_file_size)
        self.assertEqual(40, output.clp.target_segment_size)

    def test_partial_legacy_fields_use_legacy_defaults(self):
        output = ArchiveOutput.model_validate({"target_segment_size": 100})

        self.assertEqual(256 * 1024 * 1024, output.target_uncompressed_size)
        self.assertEqual(100 + 32 * 1024 * 1024, output.clp_s.target_encoded_size)
        self.assertEqual(100, output.clp.target_segment_size)

    def test_mixed_legacy_and_canonical_fields_are_rejected(self):
        with self.assertRaises(ValidationError):
            ArchiveOutput.model_validate(
                {
                    "target_archive_size": 100,
                    "target_uncompressed_size": 100,
                }
            )

    def test_non_positive_canonical_fields_are_rejected(self):
        with self.assertRaises(ValidationError):
            ArchiveOutput.model_validate({"target_uncompressed_size": 0})
        with self.assertRaises(ValidationError):
            ArchiveOutput.model_validate({"clp_s": {"target_encoded_size": -1}})


if __name__ == "__main__":
    unittest.main()
