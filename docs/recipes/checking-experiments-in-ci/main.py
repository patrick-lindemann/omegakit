from pathlib import Path

import pytest

test_file = Path(__file__).with_name("test_experiments.py")
raise SystemExit(pytest.main(["-q", "-p", "no:cacheprovider", str(test_file)]))
