"""Deterministic Manifest-Driven Synthesis (MDS) Engine.

Solves cognitive drift in small local models by decomposing goals into a strict
file manifest, then synthesizing and validating each file with 100% dedicated model capacity.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional
import json
import re

from local_coder.agent.compiler_gate import CompilerGate
from local_coder.knowledge.coding_knowledge_db import CodingKnowledgeDB
from local_coder.knowledge.pattern_bank import CleanPatternBank
from local_coder.neural.grammar_engine import parse_tool_call_json
from local_coder.neural.llama_runner import LlamaModelRunner
from local_coder.verifier.syntax_validator import SyntaxValidator
from local_coder.workspace.shadow_workspace import ShadowWorkspace


@dataclass(frozen=True)
class FileManifestItem:
    """Represents a single file specification to be synthesized."""

    file_path: str
    purpose: str
    key_requirements: str


MANIFEST_PLANNER_PROMPT = """You are a Software Architect.
Given a user's coding goal, produce a minimal, complete manifest of every file required to make the project fully functional.
Output ONLY a JSON array of file objects in this exact format:
```json
[
  {
    "file_path": "package.json",
    "purpose": "Package manifest with dependencies and scripts",
    "key_requirements": "Valid JSON, react, react-dom, dev scripts"
  },
  {
    "file_path": "public/index.html",
    "purpose": "HTML5 entry point",
    "key_requirements": "Root container div with id='root', mobile viewport"
  },
  {
    "file_path": "src/App.jsx",
    "purpose": "Main interactive application component",
    "key_requirements": "State management, task addition, status toggle, no placeholders"
  },
  {
    "file_path": "src/index.css",
    "purpose": "Application styles",
    "key_requirements": "Responsive layout, modern CSS variables, container styles"
  },
  {
    "file_path": "src/index.js",
    "purpose": "Application DOM mount script",
    "key_requirements": "ReactDOM.render mounting App to document.getElementById('root')"
  }
]
```
Do not include any conversational commentary. Output ONLY the JSON array.
"""


FILE_SYNTHESIZER_PROMPT = """You are a Principal Software Engineer.
Your task is to write the COMPLETE, production-ready source code for a specific file in a project.

PROJECT GOAL: {user_goal}
TARGET FILE: {file_path}
PURPOSE: {purpose}
REQUIREMENTS: {key_requirements}

CRITICAL RULES:
1. Write the COMPLETE implementation for this file. Never use placeholders like '// Add code here' or 'TODO'.
2. For JSON files (e.g. package.json), output 100% valid JSON with double-quoted keys and values.
3. Write clean, self-contained, syntactically valid code matching the language conventions with all necessary imports.
4. Output your code inside a single code block matching the file extension:
```{lang}
<complete source code>
```
"""


class ManifestSynthesizer:
    """Orchestrates deterministic project scaffolding file by file without cognitive drift."""

    def __init__(
        self,
        runner: Any,
        workspace: ShadowWorkspace,
        coding_knowledge: Optional[CodingKnowledgeDB] = None,
    ) -> None:
        self.runner = runner
        self.workspace = workspace
        self.syntax_validator = SyntaxValidator()
        self.compiler_gate = CompilerGate()
        self.pattern_bank = CleanPatternBank()
        self.coding_knowledge = coding_knowledge or CodingKnowledgeDB()

    def generate_manifest(self, user_goal: str) -> list[FileManifestItem]:
        """Decomposes the user goal into a concrete list of physical files to create."""
        res = self.runner.generate(
            prompt=f"Goal: {user_goal}\n\nProduce the complete project file manifest JSON array:",
            system_prompt=MANIFEST_PLANNER_PROMPT,
            max_tokens=500,
            temperature=0.1,
        )

        content = res.content.strip()
        m = re.search(r"\[\s*\{.*\}\s*\]", content, flags=re.DOTALL)
        if m:
            try:
                raw_items = json.loads(m.group(0), strict=False)
                manifest: list[FileManifestItem] = []
                for item in raw_items:
                    fp = item.get("file_path") or item.get("path")
                    if fp:
                        manifest.append(
                            FileManifestItem(
                                file_path=fp,
                                purpose=item.get("purpose", "Application source file"),
                                key_requirements=item.get("key_requirements", "Clean working code"),
                            )
                        )
                if manifest:
                    return manifest
            except Exception:
                pass

        # Fallback to verified clean architectural patterns
        matched_pat = self.pattern_bank.match_pattern(user_goal)
        if matched_pat:
            return [
                FileManifestItem(
                    file_path=fb.file_path,
                    purpose=fb.purpose,
                    key_requirements=", ".join(fb.key_requirements),
                )
                for fb in matched_pat.files
            ]

        return [
            FileManifestItem("solution.py", "Main implementation", "Core algorithms and classes"),
            FileManifestItem("test_solution.py", "Unit test suite", "Pytest verification cases"),
        ]

    def synthesize_file(self, item: FileManifestItem, user_goal: str) -> str:
        """Synthesizes the complete source code for a single file in the manifest."""
        ext = Path(item.file_path).suffix.lstrip(".")
        lang_map = {
            "py": "python",
            "js": "javascript",
            "jsx": "jsx",
            "ts": "typescript",
            "tsx": "tsx",
            "html": "html",
            "css": "css",
            "json": "json",
            "md": "markdown",
        }
        lang = lang_map.get(ext, ext or "text")

        prompt = FILE_SYNTHESIZER_PROMPT.format(
            user_goal=user_goal,
            file_path=item.file_path,
            purpose=item.purpose,
            key_requirements=item.key_requirements,
            lang=lang,
        )

        guidance = self.pattern_bank.build_guidance_prompt(user_goal, item.file_path)
        if guidance:
            prompt = f"{guidance}\n\n{prompt}"

        if self.coding_knowledge:
            hits = self.coding_knowledge.search(f"{item.purpose} {item.file_path}", limit=1)
            if hits:
                h = hits[0]
                sig = h.signature[:300] + ("..." if len(h.signature) > 300 else "")
                code_snippet = h.canonical_code[:500] + ("..." if len(h.canonical_code) > 500 else "")
                contract_block = (
                    f"=== CANONICAL MODERN IDIOM: {h.topic} ({h.version}) ===\n"
                    f"Signature: {sig}\n"
                    f"Reference Pattern:\n```\n{code_snippet}\n```\n"
                )
                prompt = f"{contract_block}\n\n{prompt}"

        res = self.runner.generate(
            prompt=prompt,
            max_tokens=1024,
            temperature=0.2,
        )

        raw = res.content.strip()
        # Extract code from code block
        m = re.search(r"```(?:[a-zA-Z0-9_-]+)?\s*\n(.*?)\n```", raw, flags=re.DOTALL)
        if m:
            code = m.group(1).strip()
        else:
            code = raw.replace("```", "").strip()

        # Sanitize common small LLM placeholders
        if item.file_path.endswith(".py"):
            code = code.replace("your_project_name", "core_project")
            code = code.replace("your_secret_key_here", "django-insecure-dev-key")
            # Auto-heal missing Django imports
            if "redirect(" in code and "from django.shortcuts import" in code and "redirect" not in code:
                code = code.replace("from django.shortcuts import", "from django.shortcuts import redirect,")
            if "TaskForm(" in code and "from tasks.forms import" not in code and "class TaskForm" not in code:
                code = "from tasks.forms import TaskForm\n" + code
            # Auto-heal missing typing imports
            for sym in ("Dict", "List", "Optional", "Tuple", "Any", "Union"):
                if (f"{sym}[" in code or f": {sym}" in code or f"-> {sym}" in code) and f"import {sym}" not in code and f", {sym}" not in code:
                    if "from typing import" in code:
                        code = code.replace("from typing import", f"from typing import {sym},")
                    else:
                        code = f"from typing import {sym}\n" + code

        # Sanitize JSON files
        if item.file_path.endswith(".json"):
            try:
                # verify and re-dump for perfect formatting
                parsed = json.loads(code, strict=False)
                code = json.dumps(parsed, indent=2)
            except Exception:
                # If json has trailing comma or missing brace, clean it
                code = self._repair_json_string(code)

        # Active compiler gate check and self-repair
        diag = self.compiler_gate.check_file_content(item.file_path, code)
        if not diag.is_valid and diag.errors:
            repair_prompt = self.compiler_gate.format_repair_prompt(diag, code, item.file_path)
            repair_res = self.runner.generate(prompt=repair_prompt, max_tokens=1024, temperature=0.1)
            repaired_raw = repair_res.content.strip()
            rm = re.search(r"```(?:[a-zA-Z0-9_-]+)?\s*\n(.*?)\n```", repaired_raw, flags=re.DOTALL)
            repaired_code = rm.group(1).strip() if rm else repaired_raw.replace("```", "").strip()
            if self.compiler_gate.check_file_content(item.file_path, repaired_code).is_valid:
                code = repaired_code

        return code

    def _repair_json_string(self, raw_json: str) -> str:
        """Repairs common minor JSON syntax defects from small LLMs."""
        cleaned = re.sub(r",\s*([\}\]])", r"\1", raw_json)
        try:
            parsed = json.loads(cleaned, strict=False)
            return json.dumps(parsed, indent=2)
        except Exception:
            return raw_json

    def execute_manifest_synthesis(
        self,
        user_goal: str,
        on_file_synthesized: Optional[Callable[[str, int, int], None]] = None,
    ) -> list[str]:
        """Executes full deterministic synthesis across all manifest items."""
        manifest = self.generate_manifest(user_goal)
        synthesized_files: list[str] = []

        total = len(manifest)
        for idx, item in enumerate(manifest, start=1):
            code = self.synthesize_file(item, user_goal)

            # Stage in shadow workspace
            self.workspace.stage_edit(item.file_path, code)
            synthesized_files.append(item.file_path)

            if on_file_synthesized:
                on_file_synthesized(item.file_path, idx, total)

        return synthesized_files
