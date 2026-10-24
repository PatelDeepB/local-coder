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


def test_should_match_with_ellipsis_wildcard() -> None:
    # Arrange
    patcher = PrecisionPatcher()
    original = (
        "def compute_total(items: list[int]) -> int:\n"
        "    # Step 1: Initialize accumulator\n"
        "    acc = 0\n"
        "    for it in items:\n"
        "        acc += it\n"
        "    return acc\n"
    )
    search_b = "def compute_total(items: list[int]) -> int:\n    ...\n    return acc"
    replace_b = "def compute_total(items: list[int]) -> int:\n    return sum(items)"

    # Act
    res = patcher.apply_search_replace(original, search_b, replace_b)

    # Assert
    assert res.is_success is True
    assert "return sum(items)" in res.modified_content
    assert "acc = 0" not in res.modified_content


def test_should_recover_swapped_search_and_replace() -> None:
    # Arrange: LLM put existing code in replace and new code in search
    patcher = PrecisionPatcher()
    original = "x = 100\ny = 200\n"
    search_b = "x = 150\ny = 200\n"
    replace_b = "x = 100\ny = 200\n"

    # Act
    res = patcher.apply_search_replace(original, search_b, replace_b)

    # Assert
    assert res.is_success is True
    assert "x = 150" in res.modified_content


def test_should_recover_when_intended_replacement_in_search_and_ellipsis_in_replace() -> None:
    # Arrange: LLM emitted replacement in search and ... in replace
    patcher = PrecisionPatcher()
    original = (
        "class Status:\n"
        "    IDLE = 'IDLE'\n"
        "    BUSY = 'BUSY'\n"
    )
    search_b = (
        "class Status:\n"
        "    IDLE = 'IDLE'\n"
        "    BUSY = 'BUSY'\n"
        "    PAUSED = 'PAUSED'\n"
    )
    replace_b = "..."

    # Act
    res = patcher.apply_search_replace(original, search_b, replace_b)

    # Assert
    assert res.is_success is True
    assert "PAUSED = 'PAUSED'" in res.modified_content


def test_should_append_when_search_block_is_empty_and_replace_block_provided() -> None:
    # Arrange
    patcher = PrecisionPatcher()
    original = "def foo():\n    return 1\n"
    search_b = ""
    replace_b = "def bar():\n    return 2"

    # Act
    res = patcher.apply_search_replace(original, search_b, replace_b)

    # Assert
    assert res.is_success is True
    assert "def foo():" in res.modified_content
    assert "def bar():" in res.modified_content

