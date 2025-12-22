#!/usr/bin/env python3
import os
import re
import json
import argparse
from typing import Dict, List, Any

# ---------- simple helpers ----------

def is_probably_elf(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            magic = f.read(4)
        return magic == b"\x7fELF"
    except Exception:
        return False


def extract_ascii_strings(path: str, min_len: int = 4) -> List[str]:
    strings = []
    try:
        with open(path, "rb") as f:
            data = f.read()
    except Exception:
        return strings

    cur = []
    for b in data:
        if 32 <= b < 127:  # printable ASCII
            cur.append(chr(b))
        else:
            if len(cur) >= min_len:
                strings.append("".join(cur))
            cur = []
    if len(cur) >= min_len:
        strings.append("".join(cur))
    return strings


def uniq_preserve(seq):
    seen = set()
    out = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


# ---------- pattern matchers ----------

URL_RE = re.compile(r"https?://[a-zA-Z0-9\.\-_/:%\?\=&]+")
HOST_RE = re.compile(r"\b[a-zA-Z0-9\.\-]+\.(?:tuya(?:cloud)?\.com|tuyaeu\.com|tuyaus\.com|amazonaws\.com|aliyun\.com)\b")
MQTT_RE = re.compile(r"\b(mqtt|mqtts|amqps?)\b", re.IGNORECASE)
TOPIC_RE = re.compile(r"([a-zA-Z0-9/_\-]+/(?:status|state|command|event|online|offline|dp|control|upgrade))")
DEVICE_ID_KEYS = [
    "devId", "deviceId", "uuid", "uid", "authKey", "localKey",
    "productKey", "pk_id", "schemaId", "cid", "clientId",
]
KEY_LIKE_RE = re.compile(r"\b[0-9a-fA-F]{16,64}\b")
BASE64_RE = re.compile(r"\b[A-Za-z0-9+/]{16,}={0,2}\b")

# Realtek / ioctl / Wi-Fi / SoC hints
REALTEK_RE = re.compile(r"(rts3903|rts3906|rts_soc|Realtek|RTL8188|8188fu|rts_)", re.IGNORECASE)
IOCTL_RE = re.compile(r"\bioctl\b", re.IGNORECASE)

# Sensor / ISP hints (expand as needed)
SENSOR_RE = re.compile(
    r"\b(ov[0-9]{3,4}|gc[0-9]{3,4}|ar0[0-9]{3}|imx[0-9]{3,4}|jxf[0-9]{3,4}|"
    r"ispfw|isp_firmware|sensor_init|sensor_drv|mipi_rx)\b",
    re.IGNORECASE,
)

PAIRING_RE = re.compile(r"(pairing|ap_mode|smartconfig|ezconfig|binding|unbind|activation)", re.IGNORECASE)


def analyze_strings(strings: List[str]) -> Dict[str, List[str]]:
    urls = []
    hosts = []
    mqtt_strings = []
    mqtt_topics = []
    device_id_hits = []
    key_like = []
    base64_like = []
    realtek = []
    ioctls = []
    sensor = []
    pairing = []

    for s in strings:
        if URL_RE.search(s):
            urls.extend(URL_RE.findall(s))
        if HOST_RE.search(s):
            hosts.extend(HOST_RE.findall(s))
        if MQTT_RE.search(s):
            mqtt_strings.append(s)
        if TOPIC_RE.search(s):
            mqtt_topics.extend([m for m in TOPIC_RE.findall(s) if len(m) > 4])
        for key in DEVICE_ID_KEYS:
            if key in s:
                device_id_hits.append(s)
                break
        if KEY_LIKE_RE.search(s):
            key_like.extend(KEY_LIKE_RE.findall(s))
        if BASE64_RE.search(s):
            base64_like.extend(BASE64_RE.findall(s))
        if REALTEK_RE.search(s):
            realtek.append(s)
        if IOCTL_RE.search(s):
            ioctls.append(s)
        if SENSOR_RE.search(s):
            sensor.append(s)
        if PAIRING_RE.search(s):
            pairing.append(s)

    return {
        "urls": uniq_preserve(urls),
        "hosts": uniq_preserve(hosts),
        "mqtt_strings": uniq_preserve(mqtt_strings),
        "mqtt_topics": uniq_preserve(mqtt_topics),
        "device_id_hits": uniq_preserve(device_id_hits),
        "key_like": uniq_preserve(key_like),
        "base64_like": uniq_preserve(base64_like),
        "realtek": uniq_preserve(realtek),
        "ioctls": uniq_preserve(ioctls),
        "sensor": uniq_preserve(sensor),
        "pairing": uniq_preserve(pairing),
    }


# ---------- Qiling profile skeleton ----------

def build_qiling_profile_skeleton(rootfs: str, tycam_path: str) -> Dict[str, Any]:
    # This is a *starting point* you can hand‑edit for actual Qiling use.
    return {
        "description": "Skeleton Qiling profile for Tuya RTS3903 tycam",
        "rootfs": rootfs,
        "target": tycam_path,
        "arch": "mipsel",
        "os": "linux",
        "entry_point": "auto",
        "env": {
            "PATH": "/usr/bin:/usr/sbin:/bin:/sbin:/opt/bin/:/opt/skyeye/bin/",
            "LD_LIBRARY_PATH": "./:/usr/local/lib:/usr/lib:/opt/lib",
        },
        "hooks": {
            "ioctl": "TODO: hook ioctl to emulate rts_soc_camera, wifi, etc.",
            "open": "TODO: handle /dev/video*, /dev/ttyS*, /proc/* paths",
            "socket": "TODO: track MQTT / Tuya cloud traffic, stub connect",
        },
        "notes": [
            "ty_platform.sh echoes 1 > /sys/devices/platform/rts_soc_camera/loadfw",
            "You will likely need to stub /sys/devices/platform/rts_soc_camera/*",
            "ty_monitor.sh expects /tmp/.mq_status, /etc/tuya/DevStatus.txt, nvram, etc.",
        ],
    }


# ---------- main scan ----------

def scan_rootfs(root: str, out_json: str = None, qiling_profile: str = None):
    results: Dict[str, Any] = {}
    tycam_candidate = None

    for dirpath, dirnames, filenames in os.walk(root):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            if not is_probably_elf(full):
                continue

            rel = os.path.relpath(full, root)
            strings = extract_ascii_strings(full)
            info = analyze_strings(strings)

            # Save non‑empty data only
            if any(info.values()):
                results[rel] = info

            # Try to spot tycam automatically
            if os.path.basename(full) == "tycam":
                tycam_candidate = full

    # Print human‑readable report
    print("=== Tuya RTS3903 Static Recon Report ===")
    print(f"Rootfs: {root}")
    print(f"Binaries analyzed: {len(results)}")
    print()

    for rel, info in sorted(results.items()):
        print(f"--- {rel} ---")
        for key in [
            "urls",
            "hosts",
            "mqtt_topics",
            "mqtt_strings",
            "device_id_hits",
            "key_like",
            "base64_like",
            "sensor",
            "realtek",
            "ioctls",
            "pairing",
        ]:
            vals = info.get(key) or []
            if not vals:
                continue
            print(f"  [{key}]")
            for v in vals:
                print(f"    {v}")
        print()

    # Build Qiling profile skeleton if requested
    qiling_profile_data = None
    if qiling_profile and tycam_candidate:
        qiling_profile_data = build_qiling_profile_skeleton(root, tycam_candidate)
        with open(qiling_profile, "w") as f:
            json.dump(qiling_profile_data, f, indent=2)
        print(f"[+] Wrote Qiling profile skeleton to: {qiling_profile}")
    elif qiling_profile:
        print("[!] Qiling profile requested, but tycam not found.")

    # Write JSON if requested
    if out_json:
        out = {
            "rootfs": root,
            "results": results,
        }
        if qiling_profile_data:
            out["qiling_profile"] = qiling_profile_data
        with open(out_json, "w") as f:
            json.dump(out, f, indent=2)
        print(f"[+] Wrote JSON report to: {out_json}")


def main():
    ap = argparse.ArgumentParser(
        description="Static recon of Tuya RTS3903 firmware: endpoints, MQTT, IDs, keys, Realtek hints."
    )
    ap.add_argument(
        "rootfs",
        help="Path to root of mounted firmware filesystem (e.g. mountpoint of your ext2 image).",
    )
    ap.add_argument(
        "--out-json",
        help="Optional JSON file to write structured results to.",
    )
    ap.add_argument(
        "--qiling-profile",
        help="Optional path to write a Qiling profile skeleton for tycam.",
    )
    args = ap.parse_args()

    scan_rootfs(args.rootfs, out_json=args.out_json, qiling_profile=args.qiling_profile)


if __name__ == "__main__":
    main()
