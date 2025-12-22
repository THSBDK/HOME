#!/usr/bin/env python3
import argparse
import os
import re
import json
from typing import List, Dict, Any, Tuple

# ---------- basic helpers ----------

def read_file(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


def extract_ascii_strings(data: bytes, min_len: int = 4) -> List[str]:
    out = []
    cur = []
    for b in data:
        if 32 <= b < 127:
            cur.append(chr(b))
        else:
            if len(cur) >= min_len:
                out.append("".join(cur))
            cur = []
    if len(cur) >= min_len:
        out.append("".join(cur))
    return out


def extract_utf16le_strings(data: bytes, min_len: int = 4) -> List[str]:
    out = []
    cur = []
    # iterate as 2-byte units
    for i in range(0, len(data) - 1, 2):
        lo, hi = data[i], data[i+1]
        if hi == 0 and 32 <= lo < 127:
            cur.append(chr(lo))
        else:
            if len(cur) >= min_len:
                out.append("".join(cur))
            cur = []
    if len(cur) >= min_len:
        out.append("".join(cur))
    return out


def uniq(seq: List[str]) -> List[str]:
    seen = set()
    res = []
    for s in seq:
        if s not in seen:
            seen.add(s)
            res.append(s)
    return res


# ---------- patterns ----------

JSON_RE = re.compile(r'\{[^{}]{0,512}\}')
PROTOBUF_FIELD_RE = re.compile(rb'[\x08\x10\x18\x20\x28\x30\x38\x40\x48\x50\x58\x60\x68\x70\x78\x80\x88\x90\x98\xa0\xa8\xb0\xb8\xc0\xc8\xd0\xd8\xe0\xe8\xf0\xf8][\x01-\x7f]')
MQTT_TOPIC_RE = re.compile(r'(/[a-zA-Z0-9_\-]+){2,}')
TUYA_DP_RE = re.compile(r'"(?:devId|gwId|dps|uid|localKey|schemaId|productKey|cid)"')
AES_KEY_HEX_RE = re.compile(r'\b[0-9a-fA-F]{32}\b|\b[0-9a-fA-F]{48}\b|\b[0-9a-fA-F]{64}\b')
BASE64_KEY_RE = re.compile(r'\b[A-Za-z0-9+/]{22,}={0,2}\b')
RSA_PEM_RE = re.compile(r'-----BEGIN (RSA |EC |)PUBLIC KEY-----')
TUYA_SIG_HINT_RE = re.compile(r'(signature|authKey|localKey|HMAC|SHA256|ECDSA|curve25519|X-Amz-Signature)', re.IGNORECASE)


def find_json_like(strings: List[str]) -> List[str]:
    hits = []
    for s in strings:
        if "{" in s and "}" in s and ":" in s:
            if len(s) <= 512:  # crude filter to avoid huge junk
                hits.append(s)
    return uniq(hits)


def find_mqtt_topics(strings: List[str]) -> List[str]:
    hits = []
    for s in strings:
        m = MQTT_TOPIC_RE.findall(s)
        if m:
            for _ in m:
                hits.append(s)
    return uniq(hits)


def find_tuya_dp(strings: List[str]) -> List[str]:
    hits = []
    for s in strings:
        if TUYA_DP_RE.search(s):
            hits.append(s)
    return uniq(hits)


def find_keys(strings: List[str]) -> Tuple[List[str], List[str]]:
    hex_hits = []
    b64_hits = []
    for s in strings:
        hex_hits.extend(AES_KEY_HEX_RE.findall(s))
        b64_hits.extend(BASE64_KEY_RE.findall(s))
    return uniq([h if isinstance(h, str) else h.decode("ascii", "ignore") for h in hex_hits]), \
           uniq([b if isinstance(b, str) else b.decode("ascii", "ignore") for b in b64_hits])


def find_tuya_sig(strings: List[str]) -> List[str]:
    hits = []
    for s in strings:
        if TUYA_SIG_HINT_RE.search(s):
            hits.append(s)
    return uniq(hits)


def protobuf_entropy_score(data: bytes) -> int:
    # extremely crude score: count of field-tag-like bytes
    matches = PROTOBUF_FIELD_RE.findall(data)
    return len(matches)


# ---------- main analysis ----------

def analyze_binary(path: str) -> Dict[str, Any]:
    data = read_file(path)

    ascii_strings = extract_ascii_strings(data, min_len=4)
    utf16_strings = extract_utf16le_strings(data, min_len=4)

    all_strings = ascii_strings + utf16_strings

    json_like = find_json_like(all_strings)
    mqtt_topics = find_mqtt_topics(all_strings)
    tuya_dp = find_tuya_dp(all_strings)
    hex_keys, b64_keys = find_keys(all_strings)
    tuya_sig = find_tuya_sig(all_strings)

    rsa_pem = []
    if RSA_PEM_RE.search(data.decode("latin1", "ignore")):
        rsa_pem.append("PEM public key header found (see binary in hex/strings for full block)")

    proto_score = protobuf_entropy_score(data)

    return {
        "path": path,
        "stats": {
            "ascii_strings": len(ascii_strings),
            "utf16_strings": len(utf16_strings),
            "protobuf_field_tag_score": proto_score,
        },
        "json_like": json_like,
        "mqtt_topics_like": mqtt_topics,
        "tuya_dp_fragments": tuya_dp,
        "aes_key_hex_candidates": hex_keys,
        "base64_key_candidates": b64_keys,
        "tuya_signature_related": tuya_sig,
        "rsa_pem_header": rsa_pem,
    }


def main():
    ap = argparse.ArgumentParser(
        description="Second‑stage deep scan of a Tuya/RTS3903 binary (ASCII+UTF16, JSON, MQTT, DP, keys, signatures)."
    )
    ap.add_argument("binary", help="Path to binary (e.g. /mnt/tuya/squashfs-root-1/skyeye/bin/tycam)")
    ap.add_argument("--out-json", help="Write JSON report to this file.")
    args = ap.parse_args()

    if not os.path.isfile(args.binary):
        raise SystemExit(f"Binary not found: {args.binary}")

    res = analyze_binary(args.binary)

    # human-readable
    print(f"=== Deep scan report ===")
    print(f"Path: {res['path']}")
    print(f"ASCII strings: {res['stats']['ascii_strings']}")
    print(f"UTF16LE strings: {res['stats']['utf16_strings']}")
    print(f"Protobuf field-tag score: {res['stats']['protobuf_field_tag_score']}")
    print()

    def dump_section(label: str, items: List[str], max_items: int = 40):
        print(f"[{label}] ({len(items)} hits)")
        for s in items[:max_items]:
            print("  ", s)
        if len(items) > max_items:
            print(f"  ... ({len(items) - max_items} more)")
        print()

    dump_section("JSON-like fragments", res["json_like"])
    dump_section("MQTT topic-like strings", res["mqtt_topics_like"])
    dump_section("Tuya DP-related fragments", res["tuya_dp_fragments"])
    dump_section("AES hex key candidates", res["aes_key_hex_candidates"])
    dump_section("Base64 key candidates", res["base64_key_candidates"])
    dump_section("Tuya signature-related strings", res["tuya_signature_related"])
    dump_section("RSA PEM markers", res["rsa_pem_header"])

    if args.out_json:
        with open(args.out_json, "w") as f:
            json.dump(res, f, indent=2)
        print(f"[+] Wrote JSON report to {args.out_json}")


if __name__ == "__main__":
    main()
