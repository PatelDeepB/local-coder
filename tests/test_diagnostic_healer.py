"""Unit tests for DiagnosticHealer and robust diff recovery."""

from pathlib import Path
import tempfile
from unittest.mock import MagicMock

from local_coder.agent.diagnostic_healer import DiagnosticHealer
from local_coder.neural.grammar_engine import parse_tool_call_json
from local_coder.workspace.shadow_workspace import ShadowWorkspace


def test_should_route_diff_hunk_in_write_file_to_apply_patch() -> None:
    # Arrange
    raw_output = (
        '<write_file path="app/models.py">\n'
        '<<<<< HEAD\n'
        'class Message:\n'
        '    def __str__(self): ...\n'
        '=======\n'
        'class Message:\n'
        '    def __str__(self):\n'
        '        return self.message\n'
        '>>>>>\n'
        '</write_file>'
    )

    # Act
    tool, args = parse_tool_call_json(raw_output)

    # Assert
    assert tool == "apply_search_replace_patch"
    assert args["file_path"] == "app/models.py"
    assert "class Message" in args["search_block"]
    assert "return self.message" in args["replace_block"]


def test_should_strip_pure_conflict_markers_in_write_file() -> None:
    # Arrange
    raw_output = (
        '<write_file path="app/models.py">\n'
        '<<<<< HEAD\n'
        '=======\n'
        'class Message:\n'
        '    def __str__(self):\n'
        '        return self.message\n'
        '>>>>>\n'
        '</write_file>'
    )

    # Act
    tool, args = parse_tool_call_json(raw_output)

    # Assert
    assert tool == "write_file"
    assert args["file_path"] == "app/models.py"
    assert "<<<<<" not in args["content"]
    assert "=======" not in args["content"]
    assert ">>>>>" not in args["content"]
    assert "return self.message" in args["content"]


def test_should_auto_recover_search_replace_hunk() -> None:
    # Arrange
    raw_output = (
        '<write_file path="calc.py">\n'
        '<<<<<<< SEARCH\n'
        'def calculate(x):\n'
        '    return 0\n'
        '=======\n'
        'def calculate(x):\n'
        '    return x * 2\n'
        '>>>>>>>\n'
        '</write_file>'
    )

    # Act
    tool, args = parse_tool_call_json(raw_output)

    # Assert
    assert tool == "apply_search_replace_patch"
    assert args["file_path"] == "calc.py"
    assert "return 0" in args["search_block"]
    assert "return x * 2" in args["replace_block"]


def test_should_normalize_django_views_missing_imports() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        views_file = root / "views.py"
        views_file.write_text(
            "def email_view(request):\n"
            "    form = MessageForm(request.POST)\n"
            "    send_mail('Hi', 'msg', 'a@b.com', ['c@d.com'])\n"
            "    return JsonResponse({'status': 'ok'})\n",
            encoding="utf-8",
        )

        runner = MagicMock()
        workspace = ShadowWorkspace(root_dir=root)
        healer = DiagnosticHealer(runner=runner, workspace=workspace)

        # Act
        repaired = healer._normalize_cross_module_imports(root)

        # Assert
        assert "views.py" in repaired
        updated_code = views_file.read_text(encoding="utf-8")
        assert "from django.http import JsonResponse" in updated_code
        assert "from django.core.mail import send_mail" in updated_code
        assert "from .forms import MessageForm" in updated_code


def test_should_normalize_django_urls_with_clean_router() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        root = Path(tmp_dir)
        urls_file = root / "urls.py"
        urls_file.write_text("from views import ForceListView\nrouter.register(r'f', ForceListView)\n", encoding="utf-8")

        runner = MagicMock()
        workspace = ShadowWorkspace(root_dir=root)
        healer = DiagnosticHealer(runner=runner, workspace=workspace)

        # Act
        repaired = healer._normalize_cross_module_imports(root)

        # Assert
        assert "urls.py" in repaired
        updated_urls = urls_file.read_text(encoding="utf-8")
        assert "from app.views import email_view" in updated_urls
        assert "urlpatterns = [" in updated_urls
