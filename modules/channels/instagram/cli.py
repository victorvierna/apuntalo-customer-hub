"""Runs instagram-cli and returns the ``data`` part of its JSON answer.

This is the only file that starts the external program. Every one-turn command
of instagram-cli, called with ``--output=json``, prints a single JSON object:

    {"ok": true, "data": ...}            on success (exit code 0)
    {"ok": false, "error": "message"}    on failure (exit code 1)

Arguments are passed as a list, never through a shell, so the text of a message
can never be interpreted as a command. Options are written as ``--name=value``
so a value that starts with ``-`` (e.g. a message "-hola") is not read as an
option.
"""

import json
import subprocess
from collections.abc import Callable, Sequence
from typing import Any

from .errors import (
    InstagramAuthError,
    InstagramCliError,
    InstagramCliNotFoundError,
    InstagramCliTimeoutError,
    InstagramFormatError,
)

DEFAULT_EXECUTABLE = "instagram-cli"

# Each command takes 5-6 s in practice; 60 s leaves room for a slow network.
DEFAULT_TIMEOUT_SECONDS = 60.0

# Fragments (lowercase) of the error messages that mean "a person must log in
# again". Taken from the instagram-cli and instagram-private-api sources.
_AUTH_ERROR_MARKERS = (
    "no session found",
    "please login",
    "failed to login",
    "login_required",
    "challenge_required",
    "checkpoint",
)

# Same signature as subprocess.run, so tests can pass a fake.
Runner = Callable[..., subprocess.CompletedProcess]


class InstagramCli:
    def __init__(
        self,
        executable: str = DEFAULT_EXECUTABLE,
        account: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        runner: Runner = subprocess.run,
    ) -> None:
        """
        Args:
            executable: Name or path of the instagram-cli program.
            account: Username of the Instagram account to use. If ``None``,
                instagram-cli uses the account that logged in last.
            timeout: Seconds to wait for each command.
            runner: Function that runs the command. Only tests change it.
        """
        self.executable = executable
        self.account = account
        self.timeout = timeout
        self._runner = runner

    def build_command(self, args: Sequence[str]) -> list[str]:
        command = [self.executable, *args, "--output=json"]
        if self.account:
            command.append(f"--username={self.account}")
        return command

    def run(self, args: Sequence[str]) -> Any:
        """Runs ``instagram-cli <args>`` and returns the ``data`` of the answer.

        Raises:
            InstagramCliNotFoundError: instagram-cli is not installed.
            InstagramCliTimeoutError: it took longer than ``timeout``.
            InstagramAuthError: there is no valid session.
            InstagramFormatError: the output is not the expected JSON.
            InstagramCliError: any other error reported by instagram-cli.
        """
        command = self.build_command(args)
        try:
            process = self._runner(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=self.timeout,
                check=False,
            )
        except FileNotFoundError as exc:
            raise InstagramCliNotFoundError(
                f"'{self.executable}' not found. Install it with "
                "'npm install -g @i7m/instagram-cli' (see docs/modules/instagram.md)."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise InstagramCliTimeoutError(
                f"'{args[0] if args else ''}' did not finish in {self.timeout:g} s."
            ) from exc

        try:
            payload = json.loads(process.stdout)
        except json.JSONDecodeError as exc:
            stderr = (process.stderr or "").strip()[-300:]
            raise InstagramCliError(
                f"instagram-cli did not return JSON (exit code {process.returncode}). "
                f"stderr: {stderr or '(empty)'}"
            ) from exc

        if not isinstance(payload, dict) or not isinstance(payload.get("ok"), bool):
            raise InstagramFormatError("instagram-cli answer has no boolean 'ok' field.")

        if not payload["ok"]:
            message = str(payload.get("error") or "unknown error")
            if any(marker in message.lower() for marker in _AUTH_ERROR_MARKERS):
                raise InstagramAuthError(message)
            raise InstagramCliError(message)

        return payload.get("data")
