"""Unit tests for deterministic LibCST transformations."""

from local_coder.ast_engine.cst_surgery import (
    make_function_async,
    replace_function_body,
    wrap_function_error_handler,
)


def test_should_convert_synchronous_function_to_async() -> None:
    # Arrange
    source = "def fetch_data(url: str):\n    return requests.get(url)\n"

    # Act
    modified, ok = make_function_async(source, "fetch_data")

    # Assert
    assert ok is True
    assert "async def fetch_data" in modified


def test_should_replace_function_body_surgically() -> None:
    # Arrange
    source = (
        "def compute_total(price: float, tax: float) -> float:\n"
        "    return price + 10.0\n"
    )
    new_body = "    return price * (1.0 + tax)"

    # Act
    modified, ok = replace_function_body(source, "compute_total", new_body)

    # Assert
    assert ok is True
    assert "return price * (1.0 + tax)" in modified
    assert "def compute_total(price: float, tax: float) -> float:" in modified


def test_should_wrap_function_body_in_error_handler() -> None:
    # Arrange
    source = "def risky_op():\n    x = 1 / 0\n    return x\n"

    # Act
    modified, ok = wrap_function_error_handler(source, "risky_op", exception_name="ZeroDivisionError", fallback_value="0")

    # Assert
    assert ok is True
    assert "try:" in modified
    assert "except ZeroDivisionError as exc:" in modified
    assert "return 0" in modified
