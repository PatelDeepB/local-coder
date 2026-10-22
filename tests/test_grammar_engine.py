"""Unit tests for the multi-format tool call grammar engine."""

from local_coder.neural.grammar_engine import parse_tool_call_json


def test_should_parse_xml_write_file_tag() -> None:
    # Arrange
    raw_text = '<write_file path="src/App.jsx">\nimport React from "react";\nexport default function App() { return <div>Hello</div>; }\n</write_file>'

    # Act
    tool, args = parse_tool_call_json(raw_text)

    # Assert
    assert tool == "write_file"
    assert args.get("file_path") == "src/App.jsx"
    assert "export default function App" in args.get("content", "")


def test_should_parse_xml_run_terminal_tag() -> None:
    # Arrange
    raw_text = "<run_terminal>npm test -- --watchAll=false</run_terminal>"

    # Act
    tool, args = parse_tool_call_json(raw_text)

    # Assert
    assert tool == "run_terminal"
    assert args.get("command") == "npm test -- --watchAll=false"


def test_should_parse_markdown_file_block() -> None:
    # Arrange
    raw_text = 'FILE: package.json\n```json\n{\n  "name": "taskflow",\n  "version": "1.0.0"\n}\n```'

    # Act
    tool, args = parse_tool_call_json(raw_text)

    # Assert
    assert tool == "write_file"
    assert args.get("file_path") == "package.json"
    assert '"name": "taskflow"' in args.get("content", "")


def test_should_parse_standard_json_tool_call() -> None:
    # Arrange
    raw_text = '{"tool": "read_file", "arguments": {"file_path": "README.md"}}'

    # Act
    tool, args = parse_tool_call_json(raw_text)

    # Assert
    assert tool == "read_file"
    assert args.get("file_path") == "README.md"


def test_should_recover_nested_json_content_with_unescaped_quotes() -> None:
    # Arrange: LLMs frequently emit single quotes or unescaped quotes inside JSON strings
    raw_text = (
        '```json\n'
        '{"tool": "write_file", "arguments": {"file_path": "package.json", '
        '"content": "{\\n  \\"name\\": \\"TaskFlow\\",\\n  \\"scripts\\": {\\"start\\": \\"npm run dev"}\\n}"}}\n'
        '```'
    )

    # Act
    tool, args = parse_tool_call_json(raw_text)

    # Assert
    assert tool == "write_file"
    assert args.get("file_path") == "package.json"
    assert "TaskFlow" in args.get("content", "")


def test_should_parse_xml_attribute_write_file_format() -> None:
    # Arrange: LLM emits <write_file path="..." content='...'>
    raw_text = "<write_file path=\"src/App.js\" content='import React from \\'react\\';\\n\\nfunction App() { return <h1>Hello</h1>; }'}"

    # Act
    tool, args = parse_tool_call_json(raw_text)

    # Assert
    assert tool == "write_file"
    assert args.get("file_path") == "src/App.js"
    assert "function App()" in args.get("content", "")


def test_should_parse_search_replace_patch_hunk_format() -> None:
    # Arrange
    raw_text = (
        '<patch file="aggregator.py">\n'
        '<<<<<<< SEARCH\n'
        'def __init__(self, window_size):\n'
        '=======\n'
        'def __init__(self, window_size=10, filter_tags=None):\n'
        '>>>>>>>\n'
        '</patch>'
    )

    # Act
    tool, args = parse_tool_call_json(raw_text)

    # Assert
    assert tool == "apply_search_replace_patch"
    assert args.get("file_path") == "aggregator.py"
    assert "def __init__(self, window_size):" in args.get("search_block", "")
    assert "def __init__(self, window_size=10, filter_tags=None):" in args.get("replace_block", "")
