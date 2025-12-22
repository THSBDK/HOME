import json, sys

data = json.load(open(sys.argv[1]))

for path, info in data.items():
    if any(k in info for k in ("keyword_hits", "ascii_kv", "utf16_kv")):
        print("=== HIT:", path)
        if "keyword_hits" in info:
            print("  keywords:", info["keyword_hits"])
        if "ascii_kv" in info:
            print("  ascii kv:", info["ascii_kv"])
        if "utf16_kv" in info:
            print("  utf16 kv:", info["utf16_kv"])
        print()
