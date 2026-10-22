import subprocess
import sys

import pytest

from zmerge import __version__
from zmerge.cli import main


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert capsys.readouterr().out.strip() == f"zmerge {__version__}"


def test_no_arguments_prints_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 0
    assert "usage: zmerge" in capsys.readouterr().out


def test_module_entry_point() -> None:
    result = subprocess.run([sys.executable, "-m", "zmerge", "--version"], capture_output=True, text=True, check=True)
    assert result.stdout.strip() == f"zmerge {__version__}"
