"""End-to-end commercial flow using cua-driver.

Run with: python tests/e2e_cua.py

This script drives a real Chrome browser through the public storefront and
saves a screenshot report. It validates the critical commercial path:
landing -> catalog -> product detail -> cart -> checkout gate.
"""
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

CUA_DRIVER = Path(r"C:\Users\Manu\AppData\Local\Programs\Cua\cua-driver\bin\cua-driver.exe")
BASE_URL = os.environ.get("E2E_BASE_URL", "https://tienda-eaciot.onrender.com")
API_URL = f"{BASE_URL}/api/products"
SCREENSHOT_DIR = Path(__file__).resolve().parent.parent / "e2e_screenshots"
SESSION = "eaciot-commercial-flow"


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
    output = proc.stdout
    decoder = json.JSONDecoder()
    idx = 0
    objects = []
    while idx < len(output):
        try:
            obj, end = decoder.raw_decode(output, idx)
            objects.append(obj)
            idx = end
        except json.JSONDecodeError:
            idx += 1
    if not objects:
        raise RuntimeError(f"No JSON response from {tool}: stdout={output!r} stderr={proc.stderr!r}")
    return objects[-1]


def start_chrome() -> int:
    chrome = shutil.which("chrome") or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    profile = Path.home() / "AppData" / "Local" / "Temp" / "opencode" / "cua_chrome_profile"
    profile.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [
            chrome,
            "--remote-debugging-port=9222",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "about:blank",
        ]
    )
    time.sleep(3)
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process -Filter \"Name='chrome.exe'\" | Where-Object { $_.CommandLine -like '*remote-debugging-port=9222*' -and $_.CommandLine -notlike '*--type=*' } | Select-Object -ExpandProperty ProcessId",
        ],
        capture_output=True,
        text=True,
    )
    pids = [int(x) for x in result.stdout.strip().splitlines() if x.strip().isdigit()]
    if not pids:
        raise RuntimeError("Chrome main process not found")
    return pids[0]


def get_window_id(pid: int) -> int:
    state = cua_call("list_windows", {"pid": pid, "on_screen_only": True})
    for w in state.get("windows", []):
        if w.get("app_name") == "chrome.exe":
            return w["window_id"]
    raise RuntimeError("No Chrome window found")


def bind_browser(pid: int, window_id: int):
    prepared = cua_call("browser_prepare", {"session": SESSION, "pid": pid})
    assert prepared.get("prepared"), f"browser_prepare failed: {prepared}"
    state = cua_call(
        "get_browser_state",
        {"session": SESSION, "pid": pid, "window_id": window_id, "snapshot_format": "semantic_v2"},
    )
    return state["target_id"], state["tabs"][0]["tab_id"]


def navigate(target_id: str, tab_id: str, url: str):
    cua_call("browser_navigate", {"session": SESSION, "target_id": target_id, "tab_id": tab_id, "url": url})


def click(target_id: str, tab_id: str, ref: str):
    cua_call("browser_click", {"session": SESSION, "target_id": target_id, "tab_id": tab_id, "ref": ref})


def click_xy(target_id: str, tab_id: str, x: float, y: float):
    cua_call("browser_click", {"session": SESSION, "target_id": target_id, "tab_id": tab_id, "x": x, "y": y})


def snapshot(target_id: str, tab_id: str, screenshot: bool = False, query: str | None = None) -> dict:
    payload = {
        "session": SESSION,
        "target_id": target_id,
        "tab_id": tab_id,
        "snapshot_format": "semantic_v2",
        "include_screenshot": screenshot,
    }
    if query:
        payload["query"] = query
    return cua_call("get_browser_state", payload)


def save_screenshot(state: dict, name: str):
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    b64 = state.get("screenshot_png_b64") or state.get("screenshot")
    if b64:
        (SCREENSHOT_DIR / f"{name}.png").write_bytes(__import__("base64").b64decode(b64))
        print(f"  Screenshot: {SCREENSHOT_DIR / name}.png")
    else:
        print(f"  No screenshot for {name}")


def find_ref(state: dict, text: str, role: str | None = None) -> str | None:
    for r in state.get("content_refs", []):
        name = (r.get("name") or "").lower()
        if text.lower() in name:
            if role is None or r.get("role") == role:
                return r.get("ref")
    return None


def find_ref_by_query(target_id: str, tab_id: str, query: str) -> str | None:
    state = snapshot(target_id, tab_id, query=query)
    return find_ref(state, query)


def wait_and_shot(target_id: str, tab_id: str, name: str) -> dict:
    time.sleep(2)
    state = snapshot(target_id, tab_id, screenshot=True)
    save_screenshot(state, name)
    return state


def fetch_first_product_id() -> str:
    req = urllib.request.Request(API_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    items = data if isinstance(data, list) else data.get("items", data.get("data", []))
    if not items:
        raise RuntimeError("No products returned from API")
    return str(items[0]["id"])


def main():
    print("Starting cua-driver E2E commercial flow...")
    cua_call("start_session", {"session": SESSION})

    pid = start_chrome()
    print(f"Chrome PID: {pid}")
    window_id = get_window_id(pid)
    target_id, tab_id = bind_browser(pid, window_id)
    print(f"Bound target={target_id} tab={tab_id}")

    # 1. Landing page
    print("\n1. Landing page")
    navigate(target_id, tab_id, BASE_URL)
    state = wait_and_shot(target_id, tab_id, "01_landing")
    assert "Bienvenido a Tienda Eaciot" in json.dumps(state), "Landing text missing"

    # 2. Product catalog
    print("\n2. Product catalog")
    navigate(target_id, tab_id, f"{BASE_URL}/products/")
    state = wait_and_shot(target_id, tab_id, "02_products")
    assert "Productos" in json.dumps(state), "Products heading missing"

    # 3. First product detail
    print("\n3. Product detail")
    product_id = fetch_first_product_id()
    print(f"  First product id: {product_id}")
    navigate(target_id, tab_id, f"{BASE_URL}/products/{product_id}")
    state = wait_and_shot(target_id, tab_id, "03_product_detail")
    assert "Agregar al carrito" in json.dumps(state), "Add to cart button missing"

    # 4. Add to cart via graceful no-JS fallback route
    print("\n4. Add to cart")
    navigate(target_id, tab_id, f"{BASE_URL}/cart/add/{product_id}")
    state = wait_and_shot(target_id, tab_id, "04_added_to_cart")

    # 5. Cart
    print("\n5. Shopping cart")
    navigate(target_id, tab_id, f"{BASE_URL}/cart")
    state = wait_and_shot(target_id, tab_id, "05_cart")
    assert "Proceder al pago" in json.dumps(state), "Checkout button missing"

    # 6. Checkout gate (requires auth)
    print("\n6. Checkout gate")
    navigate(target_id, tab_id, f"{BASE_URL}/checkout")
    state = wait_and_shot(target_id, tab_id, "06_checkout_gate")
    page_text = json.dumps(state)
    assert any(x in page_text for x in ["Iniciar", "Registrarse", "Checkout", "Direcci", "Total"]), "Unexpected checkout gate"

    print("\nCommercial flow E2E completed successfully.")
    print(f"Screenshots saved in: {SCREENSHOT_DIR}")
    cua_call("end_session", {"session": SESSION})


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"E2E failed: {e}", file=sys.stderr)
        try:
            cua_call("end_session", {"session": SESSION})
        except Exception:
            pass
        raise
