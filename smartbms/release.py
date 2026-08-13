"""Stable public-release metadata with safe hosting-environment fallbacks."""

from __future__ import annotations

from dataclasses import dataclass
import os

from smartbms import __version__


PUBLIC_REPOSITORY_URL = "https://github.com/LZZ434/smartbms-rcx"
VERIFIED_TEST_COUNT = 99


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    commit: str
    repository_url: str
    test_count: int


def release_info() -> ReleaseInfo:
    commit = os.environ.get("GITHUB_SHA") or os.environ.get(
        "STREAMLIT_GIT_COMMIT"
    )
    return ReleaseInfo(
        version=__version__,
        commit=commit[:7] if commit else "local",
        repository_url=PUBLIC_REPOSITORY_URL,
        test_count=VERIFIED_TEST_COUNT,
    )
