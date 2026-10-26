import os

import pytest
import subprocess
from pathlib import Path


@pytest.mark.skipif(os.name == "nt", reason="demo script is bash")
def test_run_demo_script():
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        ["bash", "examples/run_demo.sh"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert "TOTAL: 6 findings" in proc.stdout
    assert "C9" in proc.stdout
