import json
import re
from pathlib import Path


ROOT = Path(r"D:\NT521-LTAT\llm_ctf_automation")
SEARCH_ROOTS = [
    ROOT / "logs_baseline" / "Admin",
    ROOT / "logs_dcipher" / "Admin",
    ROOT / "logs_single_executor" / "Admin",
    ROOT / "logs_other_category",
]

CATEGORY_LABELS = {
    "cry": "crypto",
    "for": "forensics",
    "pwn": "pwn",
    "rev": "rev",
    "web": "web",
}

CATEGORY_MARKERS = {
    "pwn": {
        "exploit": [
            "ret2win",
            "stack overflow",
            "format string",
            "use-after-free",
            "uaf",
            "double free",
            "tcache",
            "heap overflow",
            "ret2libc",
            "rop chain",
            "buffer overflow",
            "overwrite rip",
            "libc leak",
            "arbitrary write",
            "arbitrary read",
        ],
        "concrete": [
            "pop rdi",
            "ret gadget",
            "puts@got",
            "printf@got",
            "system@plt",
            "libc base",
            "/bin/sh",
            "one_gadget",
            "cyclic",
            "offset",
            "payload =",
            "payload=",
            "give_shell",
            "print_flag",
            "win(",
            "main buffer",
            "saved rip overwrite",
            "stack alignment",
        ],
    },
    "crypto": {
        "exploit": [
            "length extension",
            "hash length extension",
            "sha1",
            "hmac",
            "xor",
            "rsa",
            "ecc",
            "ecb",
            "cbc",
            "padding oracle",
            "nonce reuse",
            "crt",
            "small root",
            "discrete log",
            "forgery",
            "forg",
            "oracle",
            "lattice",
        ],
        "concrete": [
            "gmpy2",
            "sage",
            "sagemath",
            "pow(",
            "inverse(",
            "long_to_bytes",
            "bytes_to_long",
            "ciphertext",
            "plaintext",
            "mod n",
            "modulus",
            "private key",
            "public key",
            "factor",
            "decrypt",
            "encrypt",
            "solve_",
            "hashpumpy",
            "sha1_pad",
            "base64.b64decode",
        ],
    },
    "rev": {
        "exploit": [
            "symbolic",
            "angr",
            "z3",
            "deobfus",
            "decode",
            "reverse",
            "vm",
            "bytecode",
            "xor",
            "patch",
            "decrypt",
            "unpack",
        ],
        "concrete": [
            "strings",
            "ghidra",
            "radare2",
            "objdump",
            "disassemble",
            "decompile",
            "python3 - <<",
            "ord(",
            "chr(",
            "bytes.fromhex",
            "base64.b64decode",
            "flag{",
            "solver",
            "constraint",
        ],
    },
    "forensics": {
        "exploit": [
            "pcap",
            "packet",
            "stream",
            "carve",
            "extract",
            "exif",
            "metadata",
            "stego",
            "appended",
            "archive",
            "zip",
            "pdf",
            "deleted",
            "inode",
            "base64",
            "hidden",
        ],
        "concrete": [
            "binwalk",
            "foremost",
            "strings",
            "xxd",
            "hexdump",
            "od -",
            "tshark",
            "scapy",
            "exiftool",
            "file ",
            "unzip",
            "tar ",
            "grep -a",
            "python3 - <<",
            "carved",
        ],
    },
    "web": {
        "exploit": [
            "sql injection",
            "sqli",
            "lfi",
            "rfi",
            "ssti",
            "idor",
            "auth bypass",
            "cookie",
            "path traversal",
            "command injection",
            "file read",
            "template injection",
            "parameter pollution",
            "deserialization",
            "csrf",
        ],
        "concrete": [
            "requests.get",
            "requests.post",
            "curl ",
            "set-cookie",
            "cookie",
            "admin=true",
            "flag.txt",
            "php://filter",
            "../",
            "localhost",
            "status 200",
            "status 500",
            "/login",
            "/admin",
            "/view",
            "session",
        ],
    },
}


def mode_for(path: Path) -> str | None:
    text = str(path).lower()
    if "logs_baseline" in text or "baseline_" in text:
        return "baseline"
    if "logs_dcipher" in text or "d-cipher" in text or "dcipher_" in text:
        return "dcipher"
    if "logs_single_executor" in text or "single-executor" in text or "single_" in text:
        return "single"
    return None


def normalize_challenge_name(stem: str) -> str:
    return re.sub(r"-\d{12,}$", "", stem)


def category_for(challenge: str) -> str | None:
    parts = challenge.split("-")
    if len(parts) < 3:
        return None
    return CATEGORY_LABELS.get(parts[1])


def has_right_direction(category: str, success: bool, exploit_hits: list[str], concrete_hits: list[str]) -> bool:
    if success:
        return True

    if category == "pwn":
        return (len(exploit_hits) >= 1 and len(concrete_hits) >= 2) or len(concrete_hits) >= 4

    if category == "crypto":
        return (len(exploit_hits) >= 1 and len(concrete_hits) >= 2) or len(concrete_hits) >= 4

    if category == "rev":
        return (len(exploit_hits) >= 1 and len(concrete_hits) >= 2) or len(concrete_hits) >= 4

    if category == "forensics":
        return (len(exploit_hits) >= 2 and len(concrete_hits) >= 2) or len(concrete_hits) >= 5

    if category == "web":
        return (len(exploit_hits) >= 1 and len(concrete_hits) >= 2) or len(concrete_hits) >= 5

    return False


def load_rows() -> list[dict]:
    rows = []
    for search_root in SEARCH_ROOTS:
        if not search_root.exists():
            continue
        for log_file in search_root.rglob("*.json"):
            mode = mode_for(log_file)
            if not mode:
                continue

            challenge = normalize_challenge_name(log_file.stem)
            category = category_for(challenge)
            if category not in CATEGORY_MARKERS:
                continue

            raw_text = log_file.read_text(encoding="utf-8", errors="ignore").lower()
            try:
                data = json.loads(raw_text)
            except json.JSONDecodeError:
                success = False
                exit_reason = "parse_error"
            else:
                success = bool(data.get("success"))
                exit_reason = data.get("exit_reason")

            markers = CATEGORY_MARKERS[category]
            exploit_hits = [marker for marker in markers["exploit"] if marker in raw_text]
            concrete_hits = [marker for marker in markers["concrete"] if marker in raw_text]
            right_direction = has_right_direction(category, success, exploit_hits, concrete_hits)

            rows.append(
                {
                    "mode": mode,
                    "challenge": challenge,
                    "category": category,
                    "success": success,
                    "right_direction": right_direction,
                    "exit_reason": exit_reason,
                    "exploit_hits": exploit_hits,
                    "concrete_hits": concrete_hits,
                    "file": str(log_file),
                }
            )
    return rows


def pick_best_rows(rows: list[dict]) -> dict[tuple[str, str], dict]:
    best = {}
    for row in rows:
        key = (row["mode"], row["challenge"])
        score = (
            1 if row["success"] else 0,
            1 if row["right_direction"] else 0,
            len(row["exploit_hits"]) + len(row["concrete_hits"]),
        )
        current = best.get(key)
        if current is None or score > current["score"]:
            best[key] = {**row, "score": score}
    return best


def summarize(best: dict[tuple[str, str], dict]) -> dict[str, dict[str, dict[str, int]]]:
    summary: dict[str, dict[str, dict[str, int]]] = {}
    for category in ["crypto", "forensics", "pwn", "rev", "web"]:
        summary[category] = {}
        for mode in ["baseline", "single", "dcipher"]:
            mode_rows = [
                row
                for (row_mode, _), row in best.items()
                if row_mode == mode and row["category"] == category
            ]
            summary[category][mode] = {
                "right_direction": sum(1 for row in mode_rows if row["right_direction"]),
                "solved": sum(1 for row in mode_rows if row["success"]),
                "total": len(mode_rows),
            }
    return summary


def main() -> None:
    rows = load_rows()
    best = pick_best_rows(rows)
    summary = summarize(best)

    for category in ["crypto", "forensics", "pwn", "rev", "web"]:
        print(f"=== {category} ===")
        for mode in ["baseline", "single", "dcipher"]:
            item = summary[category][mode]
            print(
                f"{mode}: right_direction={item['right_direction']}/{item['total']} "
                f"solved={item['solved']}/{item['total']}"
            )
        print("")


if __name__ == "__main__":
    main()
