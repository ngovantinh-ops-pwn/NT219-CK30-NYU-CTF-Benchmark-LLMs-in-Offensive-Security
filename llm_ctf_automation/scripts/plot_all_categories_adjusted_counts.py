from pathlib import Path

import matplotlib.pyplot as plt

from category_right_direction_stats import load_rows as load_category_rows
from category_right_direction_stats import pick_best_rows as pick_best_category_rows
from category_right_direction_stats import summarize
from pwn_right_direction_stats import load_rows as load_pwn_rows
from pwn_right_direction_stats import pick_best_rows as pick_best_pwn_rows


def main() -> None:
    category_rows = load_category_rows()
    category_best = pick_best_category_rows(category_rows)
    category_summary = summarize(category_best)

    pwn_rows = load_pwn_rows()
    pwn_best = pick_best_pwn_rows(pwn_rows)
    all_pwn_chals = sorted({row["challenge"] for row in pwn_rows})

    single_solved = {
        c for c in all_pwn_chals if ("single", c) in pwn_best and pwn_best[("single", c)]["success"]
    }
    dcipher_solved = {
        c for c in all_pwn_chals if ("dcipher", c) in pwn_best and pwn_best[("dcipher", c)]["success"]
    }
    dcipher_right = {
        c for c in all_pwn_chals if ("dcipher", c) in pwn_best and pwn_best[("dcipher", c)]["right_direction"]
    }

    category_summary["pwn"]["dcipher"]["solved"] = len(dcipher_solved | single_solved)
    category_summary["pwn"]["dcipher"]["right_direction"] = len(dcipher_right | single_solved)
    category_summary["pwn"]["dcipher"]["total"] = 40
    category_summary["pwn"]["single"]["total"] = 40
    category_summary["pwn"]["baseline"]["total"] = 40

    categories = ["crypto", "forensics", "pwn", "rev", "web"]
    mode_keys = ["baseline", "single", "dcipher"]
    mode_labels = ["baseline", "run_single", "dcipher_adjusted"]
    colors = ["#7f8c8d", "#2e86de", "#e67e22"]

    solve_data = [[category_summary[c][m]["solved"] for c in categories] for m in mode_keys]
    right_data = [[category_summary[c][m]["right_direction"] for c in categories] for m in mode_keys]
    totals = [[category_summary[c][m]["total"] for c in categories] for m in mode_keys]

    x = range(len(categories))
    width = 0.24

    fig, axes = plt.subplots(1, 2, figsize=(15, 5.8), sharey=False)
    plots = [
        (axes[0], solve_data, "Solve Count by Category"),
        (axes[1], right_data, "Right-Direction Count by Category"),
    ]

    for ax, data, title in plots:
        for idx, (values, label, color) in enumerate(zip(data, mode_labels, colors)):
            offset = (idx - 1) * width
            bars = ax.bar([i + offset for i in x], values, width=width, label=label, color=color)
            for j, bar in enumerate(bars):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.2,
                    f"{values[j]}/{totals[idx][j]}",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

        ax.set_title(title)
        ax.set_ylabel("Number of Challenges")
        ax.set_xticks(list(x))
        ax.set_xticklabels(categories)
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        ax.set_ylim(0, max(max(series) for series in data) + 4)

    axes[0].legend()
    fig.suptitle("All Categories: Solve vs Right Direction")
    fig.tight_layout()

    out_dir = Path(__file__).resolve().parents[1] / "artifacts"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "all_categories_adjusted_counts.png"
    fig.savefig(out_file, dpi=200, bbox_inches="tight")
    print(out_file)


if __name__ == "__main__":
    main()
