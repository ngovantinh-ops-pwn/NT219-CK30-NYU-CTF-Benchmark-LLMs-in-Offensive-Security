from pathlib import Path

import matplotlib.pyplot as plt

from pwn_right_direction_stats import load_rows, pick_best_rows


def main() -> None:
    rows = load_rows()
    best = pick_best_rows(rows)
    modes = ["baseline", "single", "dcipher"]

    counts = []
    totals = []
    solved_counts = []
    for mode in modes:
        mode_rows = [row for (row_mode, _), row in best.items() if row_mode == mode]
        totals.append(len(mode_rows))
        counts.append(sum(1 for row in mode_rows if row["right_direction"]))
        solved_counts.append(sum(1 for row in mode_rows if row["success"]))

    colors = ["#7f8c8d", "#2e86de", "#e67e22"]
    x = range(len(modes))

    fig, ax = plt.subplots(figsize=(8.5, 5.6))
    bars = ax.bar(list(x), counts, color=colors, width=0.58)

    ax.set_title("Pwn Challenges with Correct Exploit Direction")
    ax.set_ylabel("Number of Challenges")
    ax.set_xticks(list(x))
    ax.set_xticklabels(["baseline", "run_single", "dcipher"])
    ax.set_ylim(0, max(counts + [1]) + 4)
    ax.grid(axis="y", linestyle="--", alpha=0.35)

    for i, bar in enumerate(bars):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.25,
            f"{counts[i]}/{totals[i]}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            max(bar.get_height() * 0.55, 0.6),
            f"solve {solved_counts[i]}",
            ha="center",
            va="center",
            fontsize=9,
            color="white",
            fontweight="bold",
        )

    fig.tight_layout()

    out_dir = Path(__file__).resolve().parents[1] / "artifacts"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "pwn_right_direction_counts.png"
    fig.savefig(out_file, dpi=200, bbox_inches="tight")
    print(out_file)


if __name__ == "__main__":
    main()
