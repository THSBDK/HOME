#!/usr/bin/env python3
import os
import re
import argparse
import json
from typing import List, Dict, Any, Tuple

NV_GET_RE = re.compile(rb'nvram\s+get\s+([A-Za-z0-9_]+)')
NV_FILE_NAME_RE = re.compile(r'nvram', re.IGNORECASE)


def walk_files(root: str) -> List[str]:
    paths = []
    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            paths.append(full)
    return paths


def find_nvram_binary(root: str) -> List[str]:
    hits = []
    for path in walk_files(root):
        base = os.path.basename(path)
        if base == "nvram":
            hits.append(path)
    return hits


def scan_for_nvram_gets(root: str) -> Dict[str, List[str]]:
    keys_to_files: Dict[str, List[str]] = {}
    for path in walk_files(root):
        try:
            with open(path, "rb") as f:
                data = f.read()
        except Exception:
            continue

        matches = NV_GET_RE.findall(data)
        if not matches:
            continue

        rel = os.path.relpath(path, root)
        for m in matches:
            try:
                key = m.decode("ascii", "ignore")
            except Exception:
                continue
            keys_to_files.setdefault(key, []).append(rel)

    return keys_to_files


def guess_nvram_storage_files(root: str) -> List[str]:
    candidates = []
    for path in walk_files(root):
        base = os.path.basename(path)
        # heuristic: smallish files whose name contains "nvram"
        if NV_FILE_NAME_RE.search(base):
            try:
                size = os.path.getsize(path)
            except Exception:
                continue
            if 0 < size <= 1024 * 1024:  # up to 1MB
                candidates.append(os.path.relpath(path, root))
    return candidates


def main():
    ap = argparse.ArgumentParser(
        description="Scan a Tuya/RTS3903 rootfs for nvram usage and candidate credential keys."
    )
    ap.add_argument(
        "rootfs",
        help="Path to root of mounted firmware filesystem (e.g. mountpoint of your ext2 image).",
    )
    ap.add_argument(
        "--out-json",
        help="Optional JSON file to write structured results to.",
    )
    args = ap.parse_args()

    root = args.rootfs
    if not os.path.isdir(root):
        raise SystemExit(f"Rootfs directory not found: {root}")

    print(f"=== NVRAM credential scan ===")
    print(f"Rootfs: {root}\n")

    # 1) Find nvram binary/binaries
    nv_bins = find_nvram_binary(root)
    print(f"[nvram binaries] ({len(nv_bins)} found)")
    for p in nv_bins:
        print("  ", os.path.relpath(p, root))
    print()

    # 2) Find nvram get KEY usage across scripts/binaries
    keys_to_files = scan_for_nvram_gets(root)

    # highlight keys that look like credentials / IDs
    interesting_prefixes = ["UUID", "AUTHKEY", "P2PID", "PID", "DEV", "MAC", "ETH_", "WIFI", "TZ"]
    interesting_keys = {k: v for k, v in keys_to_files.items()
                        if any(k.upper().startswith(pref) for pref in interesting_prefixes)}

    print(f"[nvram get usage] ({len(keys_to_files)} unique keys)")
    for key, files in sorted(keys_to_files.items()):
        print(f"  {key}:")
        for f in sorted(set(files)):
            print(f"    {f}")
    print()

    print(f"[likely credential-related keys]")
    if not interesting_keys:
        print("  (none matched simple prefixes; check full list above)")
    else:
        for key, files in sorted(interesting_keys.items()):
            print(f"  {key}:")
            for f in sorted(set(files)):
                print(f"    {f}")
    print()

    # 3) Guess nvram storage files (for manual hex inspection later)
    nv_files = guess_nvram_storage_files(root)
    print(f"[nvram-like storage files] ({len(nv_files)} candidates)")
    for p in nv_files:
        print("  ", p)
    print()

    if args.out_json:
        out: Dict[str, Any] = {
            "rootfs": root,
            "nvram_binaries": [os.path.relpath(p, root) for p in nv_bins],
            "nvram_keys": keys_to_files,
            "interesting_keys": interesting_keys,
            "nvram_storage_candidates": nv_files,
        }
        with open(args.out_json, "w") as f:
            json.dump(out, f, indent=2)
        print(f"[+] Wrote JSON report to {args.out_json}")


if __name__ == "__main__":
    main()
