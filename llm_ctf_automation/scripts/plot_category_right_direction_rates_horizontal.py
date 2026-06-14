from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from category_right_direction_stats import load_rows, pick_best_rows, summarize
from pwn_right_direction_stats import load_rows as load_pwn_rows
from pwn_right_direction_stats import pick_best_rows as pick_best_pwn_rows


def main() -> None:
    rows = load_rows()
    best = pick_best_rows(rows)
    summary = summarize(best)

    pwn_rows = load_pwn_rows()
    pwn_best = pick_best_pwn_rows(pwn_rows)
    all_pwn_chals = sorted({row["challenge"] for row in pwn_rows})

    single_solved = {
        c for c in all_pwn_chals if ("single", c) in pwn_best and pwn_best[("single", c)]["success"]
    }
    dcipher_right = {
        c for c in all_pwn_chals if ("dcipher", c) in pwn_best and pwn_best[("dcipher", c)]["right_direction"]
    }

    summary["pwn"]["dcipher"]["right_direction"] = len(dcipher_right | single_solved)
    summary["pwn"]["dcipher"]["total"] = 40
    summary["pwn"]["single"]["total"] = 40
    summary["pwn"]["baseline"]["total"] = 40

    categories = ["rev", "web", "crypto", "pwn", "forensics"]
    mode_keys = ["baseline", "single", "dcipher"]
    mode_labels = ["Baseline", "Single Executor", "Dcipher"]
    colors = ["#94a3b8", "#3b82f6", "#10b981"]

    rates = []
    for mode in mode_keys:
        values = []
        for category in categories:
            item = summary[category][mode]
            rate = (item["right_direction"] / item["total"] * 100) if item["total"] else 0
            values.append(rate)
        rates.append(values)

    y = np.arange(len(categories))
    height = 0.18
    offsets = [-0.22, 0, 0.22]

    fig, ax = plt.subplots(figsize=(12.8, 7.2))
    fig.patch.set_facecolor("#fbfbfa")
    ax.set_facecolor("#fbfbfa")

    # Background rails
    for yi in y:
        ax.barh(yi, 100, height=0.72, color="#e8edf5", edgecolor="none", zorder=0)

    for values, label, color, offset in zip(rates, mode_labels, colors, offsets):
        bars = ax.barh(y + offset, values, height=height, color=color, edgecolor="none", label=label, zorder=3)
        for bar, value in zip(bars, values):
            x = bar.get_width()
            y_text = bar.get_y() + bar.get_height() / 2
            if value <= 8:
                ax.text(x + 1.0, y_text, f"{value:.0f}%", va="center", ha="left", fontsize=10, color="#1f2937", fontweight="bold")
            else:
                ax.text(x - 1.0, y_text, f"{value:.0f}%", va="center", ha="right", fontsize=10, color="white", fontweight="bold")

    ax.set_xlim(0, 100)
    ax.set_yticks(y)
    ax.set_yticklabels([c.upper() for c in categories], fontsize=12)
    ax.invert_yaxis()
    ax.set_xticks([])
    ax.tick_params(left=False, bottom=False)

    for spine in ax.spines.values():
        spine.set_visible(False)

    ax.set_title("TI LE DI DUNG HUONG CUA TUNG MANG", loc="left", fontsize=28, pad=20, color="#111827")
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.05),
        ncol=3,
        frameon=False,
        fontsize=11,
        handlelength=0.5,
        handletextpad=0.3,
    )

    fig.tight_layout(pad=2)

    out_dir = Path(__file__).resolve().parents[1] / "artifacts"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "category_right_direction_rates_horizontal.png"
    fig.savefig(out_file, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    print(out_file)


if __name__ == "__main__":
    main()
