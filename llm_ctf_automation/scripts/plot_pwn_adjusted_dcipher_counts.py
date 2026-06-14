from pathlib import Path

import matplotlib.pyplot as plt

from pwn_right_direction_stats import load_rows, pick_best_rows


def main() -> None:
    rows = load_rows()
    best = pick_best_rows(rows)
    total = 40
    all_chals = sorted({row["challenge"] for row in rows})

    baseline_solved = {
        c for c in all_chals if ("baseline", c) in best and best[("baseline", c)]["success"]
    }
    baseline_right = {
        c for c in all_chals if ("baseline", c) in best and best[("baseline", c)]["right_direction"]
    }
    single_solved = {
        c for c in all_chals if ("single", c) in best and best[("single", c)]["success"]
    }
    single_right = {
        c for c in all_chals if ("single", c) in best and best[("single", c)]["right_direction"]
    }
    dcipher_solved = {
        c for c in all_chals if ("dcipher", c) in best and best[("dcipher", c)]["success"]
    }
    dcipher_right = {
        c for c in all_chals if ("dcipher", c) in best and best[("dcipher", c)]["right_direction"]
    }

    adjusted_dcipher_solved = dcipher_solved | single_solved
    adjusted_dcipher_right = dcipher_right | single_solved

    modes = ["baseline", "run_single", "dcipher_adjusted"]
    solve_counts = [len(baseline_solved), len(single_solved), len(adjusted_dcipher_solved)]
    right_counts = [len(baseline_right), len(single_right), len(adjusted_dcipher_right)]

    x = range(len(modes))
    width = 0.34

    fig, ax = plt.subplots(figsize=(9.2, 5.8))
    bars1 = ax.bar([i - width / 2 for i in x], solve_counts, width=width, label="solve", color="#2e86de")
    bars2 = ax.bar([i + width / 2 for i in x], right_counts, width=width, label="right direction", color="#e67e22")

    ax.set_title("Pwn Results on 40 Challenges (Adjusted Dcipher Assumption)")
    ax.set_ylabel("Number of Challenges")
    ax.set_xticks(list(x))
    ax.set_xticklabels(modes)
    ax.set_ylim(0, max(right_counts + solve_counts + [1]) + 4)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend()

    for bars, values in [(bars1, solve_counts), (bars2, right_counts)]:
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.25,
                f"{value}/{total}",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )

    fig.tight_layout()

    out_dir = Path(__file__).resolve().parents[1] / "artifacts"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "pwn_adjusted_dcipher_counts.png"
    fig.savefig(out_file, dpi=200, bbox_inches="tight")
    print(out_file)


if __name__ == "__main__":
    main()
