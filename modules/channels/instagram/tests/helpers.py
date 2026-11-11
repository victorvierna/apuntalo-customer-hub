"""Test helpers: saved instagram-cli answers and a fake instagram-cli.

The fixtures have the exact structure of real instagram-cli 2.1.0 answers, but
every id, name and text is invented. Never put real customer data here.
"""

import json
import subprocess
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"

THREAD_ID = "340282366841710300000000000000000000001"


def fixture_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def fixture(name: str):
    return json.loads(fixture_text(name))


class FakeRunner:
    """Stands in for ``subprocess.run``: records the command, returns a canned answer."""

    def __init__(self, stdout: str = "", returncode: int = 0, stderr: str = "", raises=None):
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = stderr
        self.raises = raises
        self.calls: list[list[str]] = []
        self.kwargs: list[dict] = []

    @classmethod
    def from_fixture(cls, name: str) -> "FakeRunner":
        stdout = fixture_text(name)
        ok = json.loads(stdout)["ok"]
        return cls(stdout=stdout, returncode=0 if ok else 1)

    def __call__(self, command, **kwargs):
        self.calls.append(list(command))
        self.kwargs.append(kwargs)
        if self.raises is not None:
            raise self.raises
        return subprocess.CompletedProcess(command, self.returncode, self.stdout, self.stderr)

    @property
    def last_command(self) -> list[str]:
        return self.calls[-1]
