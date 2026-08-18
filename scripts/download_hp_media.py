"""Descarga la media oficial HP a la PC del usuario (respaldo local).

Fuentes: SOLO contenido directo de HP (CDN oficial hp.widen.net y videos de
marketing alojados en hp.com). Sin marcas de agua de resellers, sin reviews
de terceros.

Destino: ~/Downloads/TiendaEaciot-HP-Media/<familia>/
Uso: python scripts/download_hp_media.py
"""
import sys
import time
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DEST = Path.home() / "Downloads" / "TiendaEaciot-HP-Media"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0"}

W = "https://hp.widen.net/content/{cid}/webp/{cid}.png?w=1200&dpi=72&color=ffffff00"

MANIFEST = {
    # familia: (nombres de archivo, ids widen / urls directas)
    "ob5_14_snapdragon_oled": [
        ("omni5_14_01.png", W.format(cid="wjdqxhhxgm")),
        ("omni5_14_02.png", W.format(cid="3y3pr8oa06")),
        ("omni5_14_03.png", W.format(cid="fusq71kuwi")),
        ("omni5_14_04.png", W.format(cid="c658jcrqdj")),
        ("omni5_14_05.png", W.format(cid="hcrud8duya")),
        ("omni5_14_06.png", W.format(cid="g2bgbs4x2j")),
    ],
    "ob5_16_intel": [
        ("omni5_16_01.png", W.format(cid="4s4rignnl6")),
        ("omni5_16_02.png", W.format(cid="iqed0xl7r5")),
        ("omni5_16_03.png", W.format(cid="mzom6ax1t2")),
        ("omni5_16_04.png", W.format(cid="xv6wfpz8ld")),
        ("omni5_16_05.png", W.format(cid="kptxu2gj2t")),
    ],
    "ob7_flip_16": [
        ("flip16_01.png", W.format(cid="mlslbfc0ow")),
        ("flip16_02.png", W.format(cid="wpvx8c8p0k")),
        ("flip16_03.png", W.format(cid="qx7pcdppml")),
        ("flip16_04.png", W.format(cid="vwoqv4lsoh")),
        ("flip16_05.png", W.format(cid="qruhwum7et")),
        ("flip16_06.png", W.format(cid="7slwnlywmp")),
    ],
    "ob7_aero_13": [
        ("aero_01.png", W.format(cid="nmsr64uw3x")),
        ("aero_02.png", W.format(cid="yztfffa2n8")),
        ("aero_03.png", W.format(cid="f9oynrwrmv")),
        ("aero_04.png", W.format(cid="zuwbufzrw6")),
    ],
    "ob7_14": [
        ("omni7_14_frontright.jpg",
         "https://www.hp.com/ca-en/shop/media/catalog/product/a/u/"
         "auster_14_ob7_cs_meteorsilver_wlan_nt_ircam_backlit_win11_catalog_frontright_5796054_cus.jpg"
         "?store=ca-en&image-type=image&quality=100&width=1200"),
    ],
    "videos_hp_oficiales": [
        ("WIN26_Copilot+PC.mp4",
         "https://www.hp.com/wcsstore/hpusstore/Treatment/Video/WIN26_Copilot+PC.mp4"),
        ("WIN25-Win11.mp4",
         "https://www.hp.com/wcsstore/hpusstore/Treatment/Video/WIN25-Win11.mp4"),
    ],
}


def main() -> None:
    total = ok = fail = 0
    for familia, items in MANIFEST.items():
        folder = DEST / familia
        folder.mkdir(parents=True, exist_ok=True)
        for fname, url in items:
            total += 1
            out = folder / fname
            if out.exists() and out.stat().st_size > 1000:
                print(f"· {familia}/{fname} (ya existe)")
                ok += 1
                continue
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=90) as resp:
                    data = resp.read()
                if len(data) < 1000:
                    raise RuntimeError(f"respuesta vacía ({len(data)} bytes)")
                out.write_bytes(data)
                print(f"✓ {familia}/{fname} ({len(data)//1024} KB)")
                ok += 1
            except Exception as exc:
                print(f"✗ {familia}/{fname}: {type(exc).__name__} {str(exc)[:80]}")
                fail += 1
            time.sleep(0.4)
    print(f"\nHecho: {ok}/{total} descargados, {fail} fallos.")
    print(f"Carpeta: {DEST}")


if __name__ == "__main__":
    main()
