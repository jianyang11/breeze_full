"""Framework and responsibility-boundary diagrams for BREEZE."""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Rectangle

sys.path.insert(0, str(Path(__file__).parent))
from figure_style import PALETTE, apply_style, panel_label, save_figure


FIGS = Path(__file__).parent.parent / "paper" / "figs"


def _box(ax, x, y, w, h, title, lines=(), fc="#F6F8FB", ec="#3A3A3A",
         title_color="#272727", lw=0.9):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.035,rounding_size=0.055",
        fc=fc, ec=ec, lw=lw,
    ))
    ax.text(x + 0.12, y + h - 0.22, title, ha="left", va="top",
            fontsize=7.1, fontweight="bold", color=title_color)
    for i, line in enumerate(lines):
        ax.text(x + 0.12, y + h - 0.48 - i * 0.23, line, ha="left", va="top",
                fontsize=6.3, color=PALETTE["neutral_dark"])


def _arrow(ax, x1, y1, x2, y2, color="#333333", lw=1.0, ls="-",
           connectionstyle="arc3"):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="-|>", mutation_scale=10,
        lw=lw, ls=ls, color=color,
        connectionstyle=connectionstyle,
    ))


def _mini_signal(ax, x, y, w, h, color):
    t = np.linspace(0, 1, 220)
    sig = 0.22 * np.sin(2 * np.pi * (6 * t + 0.4 * t**2))
    sig += 0.08 * np.sin(2 * np.pi * 31 * t)
    for loc in (0.18, 0.41, 0.66, 0.86):
        sig += 0.34 * np.exp(-((t - loc) / 0.014) ** 2)
    sig = sig / (np.max(np.abs(sig)) + 1e-12)
    ax.plot(x + t * w, y + h * (0.5 + 0.42 * sig), color=color, lw=0.8)
    ax.add_patch(Rectangle((x, y), w, h, fill=False, ec="#B0B0B0", lw=0.45))


def draw_framework():
    apply_style(7.2)
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")

    panel_label(ax, "a", x=0.01, y=0.97)
    ax.text(0.32, 5.76, "Closed-loop physics-verified admission", ha="left",
            va="top", fontsize=9.0, fontweight="bold")

    phases = [
        ("1  LLM recipe",
         ["JSON recipe", "fault class + condition", "feedback-aware resampling"],
         0.25, 3.55, 2.05, 1.55, "#FBEAD8", PALETTE["orange"]),
        ("2  Renderer",
         ["fixed equations", "vibration + currents", "seeded waveform"],
         2.75, 3.55, 2.05, 1.55, "#F7F0DF", "#A56B25"),
        ("3  Verifier",
         ["format and legality", "statistics + PSD shape", "envelope; supported MCSA"],
         5.25, 3.55, 2.35, 1.55, "#EAF2FB", PALETTE["blue"]),
        ("4  Admitted pool",
         ["recipe + seed", "gate report", "diversity-admitted window"],
         8.05, 3.55, 1.7, 1.55, "#EAF6EA", PALETTE["green"]),
    ]
    for title, lines, x, y, w, h, fc, ec in phases:
        _box(ax, x, y, w, h, title, lines, fc=fc, ec=ec, title_color=ec)
    for x1, x2 in [(2.3, 2.75), (4.8, 5.25), (7.6, 8.05)]:
        _arrow(ax, x1, 4.32, x2, 4.32)

    _box(ax, 0.25, 1.55, 2.25, 1.15, "Real train split",
         ["file-level split", "quantiles from train only", "no test leakage"],
         fc="#F0F6EC", ec=PALETTE["green"], title_color=PALETTE["green"])
    _arrow(ax, 2.5, 2.12, 5.25, 3.77, color=PALETTE["green"], ls="--",
           connectionstyle="arc3,rad=-0.15")
    ax.text(3.68, 2.67, "thresholds", fontsize=6.2, color=PALETTE["green"],
            ha="center", va="center", rotation=18)

    _box(ax, 5.25, 1.25, 2.35, 1.25, "Structured rejection",
         ["failed gate", "measured value vs bound", "next prompt constraint"],
         fc="#FCE9E6", ec=PALETTE["rose"], title_color=PALETTE["rose"])
    _arrow(ax, 6.4, 3.55, 6.4, 2.5, color=PALETTE["rose"])
    _arrow(ax, 5.25, 1.86, 1.28, 3.55, color=PALETTE["rose"],
           connectionstyle="arc3,rad=0.24")
    ax.text(3.12, 2.62, "feedback <= K rounds", fontsize=6.2,
            color=PALETTE["rose"], rotation=18, ha="center")

    _box(ax, 8.05, 1.35, 1.7, 1.05, "Diagnosis",
         ["real + admitted", "compact 1-D CNN", "paired tests"],
         fc="#F1ECF7", ec=PALETTE["violet"], title_color=PALETTE["violet"])
    _arrow(ax, 8.9, 3.55, 8.9, 2.4)

    ax.text(0.3, 0.42,
            "No target-data generator optimization and no waveform repair: rejected candidates remain rejected.",
            fontsize=6.6, color=PALETTE["neutral_dark"], ha="left")
    save_figure(fig, FIGS / "framework.pdf")
    plt.close(fig)


def draw_boundary():
    apply_style(7.2)
    fig, ax = plt.subplots(figsize=(7.2, 3.1))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 4.2)
    ax.axis("off")

    panel_label(ax, "a", x=0.01, y=0.96)
    ax.text(0.32, 4.02, "Recipe-renderer-verifier responsibility boundary",
            fontsize=9.0, fontweight="bold", ha="left", va="top")

    cols = [
        ("LLM", "Output: recipe", ["class + metadata", "structured feedback", "not a waveform proof"],
         "#FBEAD8", PALETTE["orange"], 0.20),
        ("Renderer", "Output: waveform", ["recipe + seed", "fixed signal equations", "no admission decision"],
         "#F7F0DF", "#A56B25", 2.65),
        ("Verifier", "Output: gate report", ["waveform + train bounds", "mixed physical predicates", "not physical truth"],
         "#EAF2FB", PALETTE["blue"], 5.10),
        ("Classifier", "Output: Acc./Macro-F1", ["real + admitted pool", "paired fixed seeds", "no deployment guarantee"],
         "#EAF6EA", PALETTE["green"], 7.55),
    ]
    for title, subtitle, items, fc, ec, x in cols:
        _box(ax, x, 1.30, 2.15, 1.85, title, [subtitle] + items,
             fc=fc, ec=ec, title_color=ec)
    _arrow(ax, 2.35, 2.22, 2.65, 2.22)
    _arrow(ax, 4.80, 2.22, 5.10, 2.22)
    _arrow(ax, 7.25, 2.22, 7.55, 2.22)

    ax.text(1.27, 0.85, "stochastic proposal", ha="center", fontsize=6.0,
            color=PALETTE["neutral_dark"])
    ax.text(3.72, 0.85, "deterministic construction", ha="center", fontsize=6.0,
            color=PALETTE["neutral_dark"])
    ax.text(6.17, 0.85, "train-calibrated decision", ha="center", fontsize=6.0,
            color=PALETTE["neutral_dark"])
    ax.text(8.62, 0.85, "downstream measurement", ha="center", fontsize=6.0,
            color=PALETTE["neutral_dark"])

    for x in (2.50, 4.95, 7.40):
        ax.plot([x, x], [0.58, 3.42], color=PALETTE["neutral_mid"], lw=0.65, ls="--")
    ax.text(0.35, 0.12,
            "Only the highlighted component owns each output; evidence is not transferred across responsibility boundaries.",
            ha="left", fontsize=6.4, color=PALETTE["rose"])
    save_figure(fig, FIGS / "responsibility_boundary.pdf")
    plt.close(fig)


def main():
    draw_framework()
    draw_boundary()
    print("framework.pdf saved")
    print("responsibility_boundary.pdf saved")


if __name__ == "__main__":
    main()
