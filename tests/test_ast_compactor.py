"""Unit tests for ASTSemanticCompactor and virtual context compaction."""

from local_coder.knowledge.ast_compactor import ASTSemanticCompactor


def test_should_compact_python_function_bodies_to_ellipsis() -> None:
    compactor = ASTSemanticCompactor()
    raw_code = (
        "import os\n"
        "from typing import Optional\n\n"
        "class TaskManager:\n"
        "    '''Manages lifecycle of tasks.'''\n"
        "    def __init__(self, capacity: int = 100) -> None:\n"
        "        self.capacity = capacity\n"
        "        self.tasks = []\n"
        "        print('Initializing heavy resources...')\n\n"
        "    def execute_task(self, task_id: str) -> bool:\n"
        "        '''Executes task by id.'''\n"
        "        for i in range(100):\n"
        "            if i == 50:\n"
        "                return True\n"
        "        return False\n"
    )

    compacted = compactor.compact_python_code(raw_code)

    assert "class TaskManager:" in compacted
    assert "def __init__(self, capacity: int=100) -> None:" in compacted
    assert "def execute_task(self, task_id: str) -> bool:" in compacted
    assert "'''Executes task by id.'''" in compacted or '"""Executes task by id."""' in compacted
    assert "..." in compacted
    # Heavy body code should be stripped
    assert "for i in range(100):" not in compacted
    assert "print('Initializing heavy resources...')" not in compacted


def test_should_build_virtual_workspace_schema_for_multiple_files() -> None:
    compactor = ASTSemanticCompactor()
    files = {
        "models.py": "class User:\n    id: int\n    def save(self): pass\n",
        "service.py": "class UserService:\n    def get_user(self, uid: int):\n        x = 10\n        return x\n",
        "active.py": "class ActiveController: pass",
    }

    schema = compactor.build_virtual_workspace_schema(files, active_file="active.py")

    assert "--- Interface: models.py ---" in schema
    assert "--- Interface: service.py ---" in schema
    assert "active.py" not in schema
    assert "class User:" in schema
    assert "class UserService:" in schema


def test_should_build_workspace_schema_from_directory(tmp_path) -> None:
    compactor = ASTSemanticCompactor()
    (tmp_path / "models.py").write_text("class Account:\n    balance: float = 0.0\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("def run_app():\n    return True\n", encoding="utf-8")

    schema = compactor.build_workspace_schema(tmp_path)

    assert "--- Interface: models.py ---" in schema
    assert "--- Interface: app.py ---" in schema
    assert "class Account:" in schema
