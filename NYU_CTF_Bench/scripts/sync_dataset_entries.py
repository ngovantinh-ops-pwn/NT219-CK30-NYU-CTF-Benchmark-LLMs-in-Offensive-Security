import argparse
import json
from pathlib import Path


CATEGORY_SHORT = {
    "crypto": "cry",
    "forensics": "for",
    "misc": "msc",
    "pwn": "pwn",
    "rev": "rev",
    "web": "web",
}


def safe_name(value: str) -> str:
    value = value.replace(" ", "_").lower()
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in value).rstrip("_")
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned


def event_short(event: str) -> str:
    tail = event.rsplit("-", 1)[-1].lower()
    return tail[0]


def canonical_name(year: str, event: str, category: str, challenge: str) -> str:
    return f"{year}{event_short(event)}-{CATEGORY_SHORT[category]}-{safe_name(challenge)}"


def detect_event(event_name: str) -> str:
    normalized = event_name.lower()
    if "qual" in normalized:
        return f"{event_name}-Quals" if "qual" not in event_name else event_name
    if "final" in normalized:
        return f"{event_name}-Finals" if "final" not in event_name else event_name
    return event_name


def main():
    parser = argparse.ArgumentParser(description="Sync challenge.json directories into an NYU_CTF_Bench dataset JSON.")
    parser.add_argument("--dataset-json", required=True, help="Path to test_dataset.json or development_dataset.json")
    parser.add_argument("--root", required=True, help="Directory to scan for challenge.json files")
    parser.add_argument("--year", required=True, help="Year to assign to discovered challenges")
    parser.add_argument("--event", required=True, help="Event name, for example PicoCTF-Quals")
    parser.add_argument("--split-prefix", default="test", choices=["test", "development", "removed"], help="Expected leading path segment")
    parser.add_argument("--dry-run", action="store_true", help="Print proposed entries without writing")
    args = parser.parse_args()

    dataset_path = Path(args.dataset_json).resolve()
    root = Path(args.root).resolve()
    bench_root = dataset_path.parent.resolve()

    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    added = {}

    for challenge_file in sorted(root.rglob("challenge.json")):
        challenge_dir = challenge_file.parent
        rel_dir = challenge_dir.relative_to(bench_root).as_posix()
        parts = rel_dir.split("/")
        if len(parts) < 5:
            raise ValueError(f"Unexpected challenge path shape: {rel_dir}")

        split_prefix = parts[0]
        category = parts[-2]

        if split_prefix != args.split_prefix:
            continue
        if category not in CATEGORY_SHORT:
            raise ValueError(f"Unknown category '{category}' in {rel_dir}")

        challenge_meta = json.loads(challenge_file.read_text(encoding="utf-8"))
        challenge_name = challenge_meta.get("name", challenge_dir.name)
        key = canonical_name(args.year, args.event, category, challenge_name)

        entry = {
            "year": str(args.year),
            "event": args.event,
            "category": category,
            "challenge": challenge_name,
            "path": rel_dir,
        }

        if key not in dataset:
            dataset[key] = entry
            added[key] = entry

    if args.dry_run:
        print(json.dumps(added, indent=2))
        print(f"Would add {len(added)} entries")
        return

    dataset_path.write_text(json.dumps(dataset, indent=2) + "\n", encoding="utf-8")
    print(f"Added {len(added)} entries to {dataset_path}")
    for key in added:
        print(key)


if __name__ == "__main__":
    main()
