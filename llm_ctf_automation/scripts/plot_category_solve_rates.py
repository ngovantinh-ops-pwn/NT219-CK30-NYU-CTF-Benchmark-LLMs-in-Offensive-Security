from pathlib import Path

import matplotlib.pyplot as plt


def main() -> None:
    categories = ["crypto", "forensics", "pwn", "rev", "web"]
    baseline = [0.00, 0.00, 0.00, 0.00, 0.00]
    run_single = [45.00, 20.00, 30.00, 50.00, 42.11]
    dcipher = [45.00, 10.00, 35.00, 60.00, 52.63]

    x = range(len(categories))
    width = 0.24

    fig, ax = plt.subplots(figsize=(10, 5.8))
    ax.bar([i - width for i in x], baseline, width=width, label="baseline", color="#7f8c8d")
    ax.bar(x, run_single, width=width, label="run_single", color="#2e86de")
    ax.bar([i + width for i in x], dcipher, width=width, label="dcipher", color="#e67e22")

    ax.set_title("Solve Rate by Category and Mode")
    ax.set_ylabel("Solve Rate (%)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(categories)
    ax.set_ylim(0, 70)
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.legend()

    series = [
        ("baseline", baseline, -width),
        ("run_single", run_single, 0),
        ("dcipher", dcipher, width),
    ]
    for _, values, offset in series:
        for i, value in enumerate(values):
            ax.text(i + offset, value + 1.0, f"{value:.2f}%", ha="center", va="bottom", fontsize=9)

    fig.tight_layout()

    out_dir = Path(__file__).resolve().parents[1] / "artifacts"
    out_dir.mkdir(exist_ok=True)
    out_file = out_dir / "category_solve_rates.png"
    fig.savefig(out_file, dpi=200, bbox_inches="tight")
    print(out_file)


if __name__ == "__main__":
    main()
