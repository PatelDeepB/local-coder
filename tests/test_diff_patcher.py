"""Unit tests for precision search/replace hunk patching."""

from local_coder.ast_engine.diff_patcher import PrecisionPatcher


def test_should_apply_exact_search_replace_hunk() -> None:
    # Arrange
    patcher = PrecisionPatcher()
    original = (
        "def hello():\n"
        "    message = 'world'\n"
        "    return message\n"
    )
    search_b = "    message = 'world'\n"
    replace_b = "    message = 'galaxy'\n"

    # Act
    res = patcher.apply_search_replace(original, search_b, replace_b)

    # Assert
    assert res.is_success is True
    assert "message = 'galaxy'" in res.modified_content
    assert "-    message = 'world'" in res.diff_unified
    assert "+    message = 'galaxy'" in res.diff_unified


def test_should_fail_gracefully_when_search_block_not_found() -> None:
    # Arrange
    patcher = PrecisionPatcher()
    original = "x = 10\n"

    # Act
    res = patcher.apply_search_replace(original, "y = 20", "y = 30")

    # Assert
    assert res.is_success is False
    assert "could not be located" in (res.error_message or "")
