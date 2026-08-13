import unittest

import pandas as pd

from smartbms.scenarios import run_portfolio_scenarios
from smartbms.trend_io import (
    MAX_UPLOAD_BYTES,
    TrendIngestionError,
    canonicalize_trend_frame,
    ingest_csv_bytes,
)


class TrendIngestionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = run_portfolio_scenarios().baseline.trends

    def test_valid_csv_round_trip_preserves_rows_and_canonical_types(self):
        result = ingest_csv_bytes(
            self.baseline.to_csv(index=False).encode("utf-8")
        )

        self.assertEqual(len(result.frame), len(self.baseline))
        self.assertTrue(
            pd.api.types.is_datetime64_any_dtype(result.frame["timestamp"])
        )
        self.assertEqual(result.frame["occupied"].dtype, bool)
        self.assertEqual(result.frame["scenario"].iloc[0], "baseline")

    def test_utf8_bom_csv_is_accepted(self):
        payload = (
            b"\xef\xbb\xbf"
            + self.baseline.head(4).to_csv(index=False).encode("utf-8")
        )

        result = ingest_csv_bytes(payload)

        self.assertIn("timestamp", result.frame.columns)

    def test_canonicalization_does_not_mutate_input_or_sort_rows(self):
        source = self.baseline.head(8).iloc[::-1].copy()
        original = source.copy(deep=True)

        result = canonicalize_trend_frame(source)

        pd.testing.assert_frame_equal(source, original)
        self.assertEqual(
            result.frame["timestamp"].tolist(),
            original["timestamp"].tolist(),
        )

    def test_empty_oversized_and_missing_timestamp_inputs_are_rejected(self):
        cases = (
            (b"", "empty_file"),
            (b"x" * (MAX_UPLOAD_BYTES + 1), "file_too_large"),
            (b"value\n1\n", "missing_timestamp"),
        )
        for payload, code in cases:
            with self.subTest(code=code):
                with self.assertRaises(TrendIngestionError) as caught:
                    ingest_csv_bytes(payload)
                self.assertEqual(caught.exception.code, code)

    def test_invalid_timestamp_numeric_and_boolean_values_are_rejected(self):
        frames = (
            (pd.DataFrame({"timestamp": ["bad"]}), "invalid_timestamp"),
            (
                pd.DataFrame(
                    {"timestamp": ["2026-08-01"], "hvac_power_kw": ["bad"]}
                ),
                "invalid_numeric",
            ),
            (
                pd.DataFrame(
                    {"timestamp": ["2026-08-01"], "occupied": ["maybe"]}
                ),
                "invalid_boolean",
            ),
        )
        for frame, code in frames:
            with self.subTest(code=code):
                with self.assertRaises(TrendIngestionError) as caught:
                    canonicalize_trend_frame(frame)
                self.assertEqual(caught.exception.code, code)

    def test_duplicate_columns_and_malformed_csv_are_rejected(self):
        frame = pd.DataFrame([["2026-08-01", "2026-08-02"]])
        frame.columns = ["timestamp", "timestamp"]

        with self.assertRaises(TrendIngestionError) as duplicate:
            canonicalize_trend_frame(frame)
        with self.assertRaises(TrendIngestionError) as malformed:
            ingest_csv_bytes(b'timestamp,value\n"unclosed,1\n')

        self.assertEqual(duplicate.exception.code, "duplicate_columns")
        self.assertEqual(malformed.exception.code, "malformed_csv")

    def test_duplicate_csv_headers_are_rejected_before_pandas_renames_them(self):
        payload = b"timestamp,hvac_power_kw,hvac_power_kw\n2026-08-01,1,2\n"

        with self.assertRaises(TrendIngestionError) as caught:
            ingest_csv_bytes(payload)

        self.assertEqual(caught.exception.code, "duplicate_columns")


if __name__ == "__main__":
    unittest.main()
