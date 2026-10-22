"""Unit tests for CrossFileSignatureVerifier."""

from local_coder.verifier.cross_file_verifier import CrossFileSignatureVerifier


def test_should_detect_call_site_missing_required_parameter() -> None:
    verifier = CrossFileSignatureVerifier()
    files = {
        "aggregator.py": "class Aggregator:\n    def __init__(self, window_size: int):\n        self.window_size = window_size\n",
        "test_agg.py": "def test_run():\n    a = Aggregator()\n",
    }

    mismatches = verifier.find_mismatched_calls(files)

    assert len(mismatches) == 1
    file_path, sym, provided, required = mismatches[0]
    assert file_path == "test_agg.py"
    assert sym == "Aggregator"
    assert provided == 0
    assert required == 1


def test_should_repair_unsupplied_parameter_defaults() -> None:
    verifier = CrossFileSignatureVerifier()
    files = {
        "aggregator.py": "class Aggregator:\n    def __init__(self, window_size: int):\n        self.window_size = window_size\n",
        "test_agg.py": "def test_run():\n    a = Aggregator()\n",
    }

    repaired = verifier.repair_missing_parameter_defaults(files)

    # Aggregator.__init__ should now have a default value
    assert "def __init__(self, window_size: int=10):" in repaired["aggregator.py"]
    # Re-evaluating should yield 0 mismatches
    remaining_mismatches = verifier.find_mismatched_calls(repaired)
    assert len(remaining_mismatches) == 0
