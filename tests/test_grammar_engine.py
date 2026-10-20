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
