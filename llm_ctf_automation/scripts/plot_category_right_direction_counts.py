from pathlib import Path

import matplotlib.pyplot as plt

from category_right_direction_stats import load_rows, pick_best_rows, summarize


def main() -> None:
    rows = load_rows()
    best = pick_best_rows(rows)
    summary = summarize(best)

    categories = ["crypto", "forensics", "pwn", "rev", "web"]
    baseline = [summary[category]["baseline"]["right_direction"] for category in categories]
    run_single = [summary[category]["single"]["right_direction"] for category in categories]
    dcipher = [summary[category]["dcipher"]["right_direction"] for category in categories]

    baseline_total = [summary[category]["baseline"]["total"] for category in categories]
    single_total = [summary[category]["single"]["total"] for category in categories]
    dcipher_total = [summary[category]["dcipher"]["total"] for category in categories]

    x = range(len(categories))
    width = 0.24

    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    ax.bar([i - width for i in x], baseline, width=width, label="baseline", color="#7f8c8d")
    ax.bar(x, run_single, width=width, label="run_single", color="#2e86de")
    ax.bar([i + width for i in x], dcipher, width=width, label="dcipher", color="#e67e22")

    ax.set_title("Correct Direction Count by Category and Mode")
    ax.set_ylabel("Number of Challenges")
    ax.set_xticks(list(x))
    ax.set_xticklabels(categories)
    ax.set_ylim(0, max(baseline + run_single + dcipher + [1]) + 4)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend()

    series = [
        (baseline, baseline_total, -width),
        (run_single, single_total, 0),
        (dcipher, dcipher_total, width),
    ]
    for values, totals, offset in series:
        for i, value in enumerate(values):
            ax.text(i + offset, value + 0.25, f"{value}/{totals[i]}", ha="center", va="bottom", fontsize=8.5)

    fig.tight_layout()

    out_dir = Path(__file__).resolve().parents[1] / "artifacts"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "category_right_direction_counts.png"
    fig.savefig(out_file, dpi=200, bbox_inches="tight")
    print(out_file)


if __name__ == "__main__":
    main()
