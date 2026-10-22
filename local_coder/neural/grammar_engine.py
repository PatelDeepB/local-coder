"""GBNF grammar definitions and JSON tool schema constraints."""

import ast
import json
import re
from typing import Any, Sequence


def build_tool_calling_grammar(tools: Sequence[Any]) -> str:
    """Builds a formal GBNF grammar forcing the LLM to emit valid JSON tool calls."""
    gbnf = (
        'root ::= "{" ws "\\"tool\\"" ws ":" ws string ws "," ws "\\"arguments\\"" ws ":" ws object ws "}"\n'
        'object ::= "{" ws (string ws ":" ws value (ws "," ws string ws ":" ws value)*)? ws "}"\n'
        'value ::= string | number | "true" | "false" | "null" | object | array\n'
        'array ::= "[" ws (value (ws "," ws value)*)? ws "]"\n'
        'string ::= "\\"" ([^"\\\\] | "\\\\" ["\\\\/bfnrt])* "\\""\n'
        'number ::= ("-"? ([0-9] | [1-9] [0-9]*)) ("." [0-9]+)? ([eE] [-+]? [0-9]+)?\n'
        'ws ::= [ \\t\\n\\r]*\n'
    )
    return gbnf


def parse_tool_call_json(raw_text: str) -> tuple[str, dict[str, Any]]:
    """Safely extracts tool name and arguments dictionary from model output."""
    clean = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()

    # Format 1: XML tag <write_file path="..."> ... </write_file>
    m_xml = re.search(r'<write_file\s+(?:path|file_path)=["\']([^"\']+)["\']\s*>(.*?)(?:</write_file>|$)', clean, flags=re.DOTALL)
    if m_xml:
        path = m_xml.group(1).strip()
        content = m_xml.group(2).strip()
        content = re.sub(r"^```[a-zA-Z0-9_-]*\n", "", content)
        content = re.sub(r"\n```$", "", content)
        return "write_file", {"file_path": path, "content": content}

    # Format 1B: XML tag with content attribute <write_file path="..." content='...'>
    m_xml_attr = re.search(r'<write_file\s+(?:path|file_path)=["\']([^"\']+)["\']\s+content=(["\'])(.*?)(?<!\\)\2[\s\}>]*$', clean, flags=re.DOTALL)
    if not m_xml_attr:
        m_xml_attr = re.search(r'<write_file\s+(?:path|file_path)=["\']([^"\']+)["\']\s+content=(["\'])(.*)', clean, flags=re.DOTALL)
    if m_xml_attr:
        path = m_xml_attr.group(1).strip()
        raw_c = m_xml_attr.group(3).strip()
        raw_c = re.sub(r'["\']\s*[\}>]+$', "", raw_c)
        clean_c = raw_c.replace(r"\'", "'").replace(r'\"', '"').replace(r"\n", "\n")
        return "write_file", {"file_path": path, "content": clean_c}

    # Format 2: XML tag <run_terminal> ... </run_terminal>
    m_cmd = re.search(r"<run_terminal>(.*?)(?:</run_terminal>|$)", clean, flags=re.DOTALL)
    if m_cmd:
        return "run_terminal", {"command": m_cmd.group(1).strip()}

    # Format 3: Markdown file block FILE: path/to/file ``` ... ```
    m_file = re.search(r"(?:FILE|PATH|WRITE_FILE):\s*([^\n\r]+)[\r\n]+```(?:[a-zA-Z0-9_-]+)?[\r\n](.*?)```", clean, flags=re.DOTALL)
    if m_file:
        path = m_file.group(1).strip().strip("`'\" ")
        content = m_file.group(2).strip()
        return "write_file", {"file_path": path, "content": content}

    # Format 4: Search-Replace Patch Hunk block
    m_xml_patch = re.search(r'<patch\s+(?:file|path|file_path)=["\']([^"\']+)["\']\s*>(.*?)(?:</patch>|$)', clean, flags=re.DOTALL)
    if m_xml_patch:
        patch_path = m_xml_patch.group(1).strip().strip("`'\" ")
        patch_body = m_xml_patch.group(2)
        m_hunk = re.search(r'<{5,9}\s*SEARCH[\r\n]+(.*?)[\r\n]+={5,9}[\r\n]+(.*?)[\r\n]+(?:>{5,9}|$)', patch_body, flags=re.DOTALL)
        if m_hunk:
            return "apply_search_replace_patch", {
                "file_path": patch_path,
                "search_block": m_hunk.group(1),
                "replace_block": m_hunk.group(2),
            }

    m_patch = re.search(
        r'(?:PATCH|DIFF|FILE):\s*([^\n\r]+).*?<{5,9}\s*SEARCH[\r\n]+(.*?)[\r\n]+={5,9}[\r\n]+(.*?)(?:[\r\n]+>{5,9}|$)',
        clean,
        flags=re.DOTALL,
    )
    if m_patch:
        patch_path = m_patch.group(1).strip().strip("`'\" ")
        search_block = m_patch.group(2)
        replace_block = m_patch.group(3)
        return "apply_search_replace_patch", {
            "file_path": patch_path,
            "search_block": search_block,
            "replace_block": replace_block,
        }

    # Pattern 1: Markdown json block
    md_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", clean, flags=re.DOTALL)
    candidate_texts = []
    if md_match:
        candidate_texts.append(md_match.group(1))

    # Pattern 2: Raw curly brace substring
    start_idx = clean.find("{")
    end_idx = clean.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        candidate_texts.append(clean[start_idx : end_idx + 1])

    for cand in candidate_texts:
        payload = None
        try:
            payload = json.loads(cand, strict=False)
        except Exception:
            try:
                payload = ast.literal_eval(cand)
            except Exception:
                pass

        if isinstance(payload, dict):
            tool_name = (
                payload.get("tool")
                or payload.get("name")
                or payload.get("function")
                or payload.get("action")
            )
            args = (
                payload.get("arguments")
                or payload.get("parameters")
                or payload.get("args")
                or {}
            )
            if tool_name and isinstance(args, dict):
                return str(tool_name).strip(), args

    # Robust Fallback Extractor: Handles escaped JSON within JSON (e.g. package.json)
    m_tool = re.search(r'["\'](?:tool|name|action)["\']:\s*["\']([^"\']+)["\']', clean)
    if m_tool:
        tool_name = m_tool.group(1).strip()
        if tool_name in ["write_file", "create_file"]:
            m_path = re.search(r'["\']file_path["\']:\s*["\']([^"\']+)["\']', clean)
            file_path = m_path.group(1).strip() if m_path else ""
            m_content = re.search(r'["\']content["\']:\s*(["\'])(.*)', clean, flags=re.DOTALL)
            if m_content and file_path:
                raw_c = m_content.group(2)
                raw_c = re.sub(r'["\']\s*\}\s*\}\s*```.*$', "", raw_c, flags=re.DOTALL)
                raw_c = re.sub(r'["\']\s*\}\s*\}\s*$', "", raw_c)
                try:
                    clean_content = raw_c.encode("utf-8").decode("unicode_escape")
                except Exception:
                    clean_content = raw_c.replace(r'\"', '"').replace(r"\n", "\n").replace(r"\\", "\\")
                return "write_file", {"file_path": file_path, "content": clean_content}

        elif tool_name in ["read_file", "list_dir"]:
            m_path = re.search(r'["\'](?:file_path|dir_path)["\']:\s*["\']([^"\']+)["\']', clean)
            path_arg = m_path.group(1).strip() if m_path else ""
            arg_key = "file_path" if tool_name == "read_file" else "dir_path"
            if path_arg:
                return tool_name, {arg_key: path_arg}

        elif tool_name in ["run_terminal", "run_terminal_command"]:
            m_cmd = re.search(r'["\']command["\']:\s*["\']([^"\']+)["\']', clean)
            cmd = m_cmd.group(1).strip() if m_cmd else ""
            if cmd:
                return "run_terminal", {"command": cmd}

    return "", {}
