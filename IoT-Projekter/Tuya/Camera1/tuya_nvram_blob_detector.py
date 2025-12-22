#!/usr/bin/env python3
import os
import re
import argparse
import json

# Tuya credential markers
KEYWORDS = [
    b"UUID", b"AUTHKEY", b"P2PID", b"PID", b"MAC", b"SN",
    b"uuid", b"authkey", b"p2pid", b"pid", b"mac", b"sn",
    b"localKey", b"devId", b"productKey"
]

# ASCII KV pattern: KEY=VALUE
ASCII_KV_RE = re.compile(rb"([A-Za-z0-9_]{2,32})=([^\x00\r\n]{1,128})")

# UTF-16LE KV pattern
UTF16_KV_RE = re.compile(rb"((?:[A-Za-z0-9_]\x00){2,32})=((?:.\x00){2,128})")

def scan_blob(path):
    try:
        with open(path, "rb") as f:
            data = f.read()
    except:
        return None

    size = len(data)
    if size < 32 or size > 1024 * 1024:
        return None

    hits = {}

    # 1. Keyword search
    keyword_hits = []
    for kw in KEYWORDS:
        if kw in data:
            keyword_hits.append(kw.decode("ascii", "ignore"))
    if keyword_hits:
        hits["keyword_hits"] = keyword_hits

    # 2. ASCII key=value
    ascii_hits = []
    for m in ASCII_KV_RE.findall(data):
        key = m[0].decode("ascii", "ignore")
        val = m[1].decode("ascii", "ignore")
        ascii_hits.append((key, val))
    if ascii_hits:
        hits["ascii_kv"] = ascii_hits

    # 3. UTF-16LE key=value
    utf16_hits = []
    for m in UTF16_KV_RE.findall(data):
        key = m[0].decode("utf-16le", "ignore")
        val = m[1].decode("utf-16le", "ignore")
        utf16_hits.append((key, val))
    if utf16_hits:
        hits["utf16_kv"] = utf16_hits

    # 4. Heuristic: looks like TLV or structured binary
    entropy = len(set(data))
    if entropy < 200:
        hits["low_entropy_hint"] = True

    if hits:
        hits["size"] = size
        return hits

    return None


def main():
    ap = argparse.ArgumentParser(description="Detect Tuya/Realtek NVRAM blobs in firmware dumps.")
    ap.add_argument("path", help="Directory containing extracted firmware partitions (binwalk output).")
    ap.add_argument("--out-json", help="Write results to JSON.")
    args = ap.parse_args()

    root = args.path
    results = {}

    print(f"=== Tuya RTS3903 NVRAM Blob Detector ===")
    print(f"Scanning: {root}\n")

    for dirpath, dirs, files in os.walk(root):
        for fn in files:
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)

            res = scan_blob(full)
            if res:
                results[rel] = res
                print(f"[+] Possible NVRAM blob: {rel}")
                if "keyword_hits" in res:
                    print("    Keywords:", res["keyword_hits"])
                if "ascii_kv" in res:
                    print("    ASCII KV pairs:", len(res["ascii_kv"]))
                if "utf16_kv" in res:
                    print("    UTF16 KV pairs:", len(res["utf16_kv"]))
                print("    Size:", res["size"])
                print()

    if not results:
        print("No NVRAM-like blobs detected. Try scanning the raw firmware .bin file directly.")

    if args.out_json:
        with open(args.out_json, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\n[+] JSON written to {args.out_json}")


if __name__ == "__main__":
    main()
