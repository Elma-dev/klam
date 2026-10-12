#!/usr/bin/env python3
"""Fetch a curated set of open-licensed (OFL) Arabic + Latin fonts.

Downloads fonts from the google/fonts repository into
``frontend/public/fonts`` and writes ``fonts/manifest.json`` used by the
web app (and, later, the ASS exporter) to register the same fonts.

Usage: python scripts/fetch_fonts.py
"""

from __future__ import annotations

import json
import pathlib
import urllib.parse
import urllib.request

BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl"
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "frontend" / "public" / "fonts"
LICENSES = OUT / "licenses"

# (family, upstream_dir, remote_filename, local_filename, weight, style, variable)
FONTS = [
    ("Cairo", "cairo", "Cairo[slnt,wght].ttf", "Cairo-Variable.ttf", "200 1000", "normal", True),
    ("Noto Naskh Arabic", "notonaskharabic", "NotoNaskhArabic[wght].ttf", "NotoNaskhArabic-Variable.ttf", "400 700", "normal", True),
    ("Amiri", "amiri", "Amiri-Regular.ttf", "Amiri-Regular.ttf", "400", "normal", False),
    ("Amiri", "amiri", "Amiri-Bold.ttf", "Amiri-Bold.ttf", "700", "normal", False),
    ("Tajawal", "tajawal", "Tajawal-Regular.ttf", "Tajawal-Regular.ttf", "400", "normal", False),
    ("Tajawal", "tajawal", "Tajawal-Medium.ttf", "Tajawal-Medium.ttf", "500", "normal", False),
    ("Tajawal", "tajawal", "Tajawal-Bold.ttf", "Tajawal-Bold.ttf", "700", "normal", False),
    ("IBM Plex Sans Arabic", "ibmplexsansarabic", "IBMPlexSansArabic-Regular.ttf", "IBMPlexSansArabic-Regular.ttf", "400", "normal", False),
    ("IBM Plex Sans Arabic", "ibmplexsansarabic", "IBMPlexSansArabic-SemiBold.ttf", "IBMPlexSansArabic-SemiBold.ttf", "600", "normal", False),
    ("IBM Plex Sans Arabic", "ibmplexsansarabic", "IBMPlexSansArabic-Bold.ttf", "IBMPlexSansArabic-Bold.ttf", "700", "normal", False),
    ("Inter", "inter", "Inter[opsz,wght].ttf", "Inter-Variable.ttf", "100 900", "normal", True),
]


def _download(url: str, dest: pathlib.Path) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:  # noqa: S310
            dest.write_bytes(resp.read())
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"  ! failed: {exc}")
        return False


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    LICENSES.mkdir(parents=True, exist_ok=True)
    entries = []
    for family, up_dir, remote, local, weight, style, variable in FONTS:
        url = f"{BASE}/{up_dir}/{urllib.parse.quote(remote)}"
        dest = OUT / local
        if dest.exists():
            print(f"  = {local} (cached)")
        else:
            print(f"  + {local}")
            if not _download(url, dest):
                continue
        entries.append(
            {
                "family": family,
                "file": local,
                "weight": weight,
                "style": style,
                "variable": variable,
                "license": "OFL-1.1",
            }
        )

    for up_dir in sorted({f[1] for f in FONTS}):
        lic = LICENSES / f"{up_dir}-OFL.txt"
        if not lic.exists():
            _download(f"{BASE}/{up_dir}/OFL.txt", lic)

    manifest = {"fonts": entries, "license": "OFL-1.1", "source": "google/fonts"}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nWrote {len(entries)} font entries to {OUT / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
