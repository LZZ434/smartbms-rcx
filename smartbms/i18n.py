"""Offline presentation-layer localization for the SmartBMS portfolio."""

from __future__ import annotations

from string import Formatter
from typing import Any, Literal, cast


Language = Literal["zh", "en"]
SUPPORTED_LANGUAGES: tuple[Language, ...] = ("zh", "en")
LANGUAGE_NAMES: dict[Language, str] = {"zh": "中文", "en": "English"}
PAGE_IDS = (
    "overview",
    "plant_control",
    "energy_optimization",
    "rcx_diagnostics",
    "bms_points_alarms",
    "learning_lab",
)

TRANSLATIONS: dict[Language, dict[str, str]] = {
    "en": {
        "app.title": "SmartBMS-RCx",
        "page.overview": "Overview",
        "page.plant_control": "Plant & Control",
        "page.energy_optimization": "Energy Optimization",
        "page.rcx_diagnostics": "RCx Diagnostics",
        "page.bms_points_alarms": "BMS Points & Alarms",
        "page.learning_lab": "Learning Lab",
    },
    "zh": {
        "app.title": "SmartBMS-RCx",
        "page.overview": "项目概览",
        "page.plant_control": "设备与控制",
        "page.energy_optimization": "能源优化",
        "page.rcx_diagnostics": "再调试（RCx）诊断",
        "page.bms_points_alarms": "BMS 点表与报警",
        "page.learning_lab": "学习实验室",
    },
}


def _validate_language(language: str) -> Language:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"unsupported language: {language}")
    return cast(Language, language)


def _placeholders(value: str) -> set[str]:
    return {
        field_name
        for _, field_name, _, _ in Formatter().parse(value)
        if field_name is not None
    }


def validate_catalogs() -> None:
    if set(TRANSLATIONS["zh"]) != set(TRANSLATIONS["en"]):
        raise ValueError("translation catalogs must contain identical keys")
    for key in TRANSLATIONS["en"]:
        if _placeholders(TRANSLATIONS["zh"][key]) != _placeholders(
            TRANSLATIONS["en"][key]
        ):
            raise ValueError(f"translation placeholders differ for {key}")


def t(language: str, key: str, **values: Any) -> str:
    selected = _validate_language(language)
    try:
        template = TRANSLATIONS[selected][key]
    except KeyError as exc:
        raise KeyError(f"missing translation key: {key}") from exc
    return template.format(**values)


def page_label(page_id: str, language: str) -> str:
    if page_id not in PAGE_IDS:
        raise ValueError(f"unsupported page: {page_id}")
    return t(language, f"page.{page_id}")


validate_catalogs()
