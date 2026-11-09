"""Stdlib client for a local SystemOne server."""

import json
import urllib.error
import urllib.request
from dataclasses import dataclass


class SystemOneError(Exception):
    """The server returned an HTTP error, or it could not be reached."""


@dataclass(frozen=True)
class Decision:
    answers: dict
    model: str
    latency_s: float | None = None


class SystemOneClient:
    """Call `system_one` the same way a caller posts `{"state", "questions"}`."""

    def __init__(self, base_url: str = "http://127.0.0.1:18100", timeout: float = 30) -> None:
        if not isinstance(base_url, str) or base_url == "":
            raise ValueError("base_url must be a non-empty string")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def system_one(self, state: str | None, questions: dict) -> Decision:
        body = self._request("POST", "/decide", {"state": state, "questions": questions})
        answers = body.get("answers")
        model = body.get("model")
        if not isinstance(answers, dict) or not isinstance(model, str):
            raise SystemOneError("SystemOne response is missing answers or model")
        latency = body.get("latency_s")
        if latency is not None and not isinstance(latency, (int, float)):
            raise SystemOneError("SystemOne response has a bad latency_s")
        return Decision(answers=answers, model=model, latency_s=latency)

    def health(self) -> dict:
        body = self._request("GET", "/health", None)
        if body.get("status") != "ok" or not isinstance(body.get("model"), str):
            raise SystemOneError("SystemOne health response has the wrong shape")
        return body

    def _request(self, method: str, path: str, payload: dict | None) -> dict:
        data = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json; charset=utf-8"
        request = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            try:
                message = _http_error_message(exc)
            finally:
                exc.close()
            raise SystemOneError(message) from exc
        except urllib.error.URLError as exc:
            raise SystemOneError(
                f"could not reach SystemOne at {self.base_url}: {exc.reason}"
            ) from exc
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SystemOneError("SystemOne returned a non-JSON response") from exc
        if not isinstance(body, dict):
            raise SystemOneError("SystemOne returned a non-object response")
        return body


def _http_error_message(exc: urllib.error.HTTPError) -> str:
    raw = exc.read().decode("utf-8", errors="replace")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict) and isinstance(parsed.get("error"), str) and parsed["error"]:
        return parsed["error"]
    text = raw.strip()
    if text:
        return text
    return str(exc.reason)
