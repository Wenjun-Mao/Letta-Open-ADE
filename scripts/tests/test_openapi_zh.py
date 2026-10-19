"""The split vocabulary retains CLI/module translation behavior."""

from scripts.generate_openapi_zh_manual import _translate_title_value
from scripts.openapi_zh.manual_text import SUMMARY_TRANSLATIONS


def test_private_export_titles_and_summary_have_reviewed_chinese_translations():
    missing, unknown = set(), set()
    for title in (
        "Saved Attempts",
        "Private Observation Response",
        "Observations",
        "Records",
    ):
        translated = _translate_title_value(title, missing, unknown)
        assert translated != title
    assert not missing and not unknown
    assert (
        "Export opt-in development-workspace observations for one saved run"
        in SUMMARY_TRANSLATIONS
    )
