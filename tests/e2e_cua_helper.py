"""Helper to call cua-driver CLI from Python tests."""
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

CUA_DRIVER = Path(r"C:\Users\Manu\AppData\Local\Programs\Cua\cua-driver\bin\cua-driver.exe")


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def cua_call(tool: str, payload: dict, timeout: float = 30.0) -> dict:
    if not CUA_DRIVER.exists():
        raise FileNotFoundError(f"cua-driver not found at {CUA_DRIVER}")
    stdin = json.dumps(payload, ensure_ascii=False)
    proc = subprocess.run(
        [str(CUA_DRIVER), "--dangerously-bypass-approvals", "call", tool],
        input=stdin,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    output = _strip_ansi(proc.stdout)
    # The last JSON object in stdout is the tool response.
    objects = []
    decoder = json.JSONDecoder()
    idx = 0
    text_len = len(output)
    while idx < text_len:
        try:
            obj, end = decoder.raw_decode(output, idx)
            objects.append(obj)
            idx = end
        except json.JSONDecodeError:
            idx += 1
    if not objects:
        raise RuntimeError(f"No JSON response from cua-driver. stdout={output!r} stderr={proc.stderr!r}")
    return objects[-1]


def cua_start_session(session: str) -> dict:
    return cua_call("start_session", {"session": session})


def cua_end_session(session: str) -> dict:
    return cua_call("end_session", {"session": session})


def cua_get_browser_state(session: str, target_id: str, tab_id: str, include_screenshot: bool = False) -> dict:
    return cua_call(
        "get_browser_state",
        {
            "session": session,
            "target_id": target_id,
            "tab_id": tab_id,
            "snapshot_format": "semantic_v2",
            "include_screenshot": include_screenshot,
        },
    )


def cua_browser_navigate(session: str, target_id: str, tab_id: str, url: str) -> dict:
    return cua_call(
        "browser_navigate",
        {"session": session, "target_id": target_id, "tab_id": tab_id, "url": url},
    )


def cua_browser_click(session: str, target_id: str, tab_id: str, ref: str) -> dict:
    return cua_call(
        "browser_click",
        {"session": session, "target_id": target_id, "tab_id": tab_id, "ref": ref},
    )


def cua_browser_type(session: str, target_id: str, tab_id: str, ref: str, text: str) -> dict:
    return cua_call(
        "browser_type",
        {"session": session, "target_id": target_id, "tab_id": tab_id, "ref": ref, "text": text},
    )


def save_screenshot(state: dict, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    b64 = state.get("screenshot_png_b64") or state.get("screenshot")
    if b64:
        import base64

        path.write_bytes(base64.b64decode(b64))


def find_ref_by_text(state: dict, text: str, role: str | None = None) -> str | None:
    """Find first content ref whose name/text contains the given text."""
    refs = state.get("content_refs", [])
    for r in refs:
        name = (r.get("name") or "").lower()
        if text.lower() in name:
            if role is None or r.get("role") == role:
                return r.get("ref")
    return None
