import os
import unittest
from unittest.mock import patch

from smartbms.release import PUBLIC_REPOSITORY_URL, release_info


class ReleaseInfoTests(unittest.TestCase):
    def test_public_repository_and_release_version_are_stable(self):
        info = release_info()

        self.assertEqual(info.version, "1.0.0")
        self.assertEqual(info.test_count, 99)
        self.assertEqual(
            PUBLIC_REPOSITORY_URL,
            "https://github.com/LZZ434/smartbms-rcx",
        )

    def test_host_commit_is_shortened_without_breaking_local_fallback(self):
        with patch.dict(os.environ, {"GITHUB_SHA": "1234567890abcdef"}):
            self.assertEqual(release_info().commit, "1234567")
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(release_info().commit, "local")


if __name__ == "__main__":
    unittest.main()
