"""Shared publication figure style for BREEZE."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt


PALETTE = {
    "blue": "#0F4D92",
    "blue_mid": "#3775BA",
    "blue_soft": "#B4C0E4",
    "orange": "#D67A2C",
    "orange_soft": "#F0C0A0",
    "rose": "#B64342",
    "rose_soft": "#E4CCD8",
    "green": "#4E9A51",
    "green_soft": "#AADCA9",
    "teal": "#42949E",
    "violet": "#7C6CCF",
    "neutral_dark": "#3A3A3A",
    "neutral_mid": "#767676",
    "neutral_soft": "#D8D8D8",
    "neutral_pale": "#F4F4F4",
    "paper": "#FFFFFF",
}


METHOD_COLORS = {
    "real_only": PALETTE["neutral_dark"],
    "real": PALETTE["neutral_dark"],
    "llm": PALETTE["blue"],
    "rule": PALETTE["orange"],
    "random_open_loop": PALETTE["neutral_mid"],
    "noise_aug": PALETTE["blue_soft"],
    "vae": "#C8C8D8",
    "gan": "#B8B8C8",
    "open_loop_basic": "#D6D6D6",
    "open_loop_phys": PALETTE["green_soft"],
    "stats_only": "#CFE4E4",
    "envelope_only": "#8BCF8B",
    "breeze_k0": "#DCE5F4",
    "breeze_k1": "#B7C8E4",
    "breeze_k2": "#7599CC",
    "breeze_k3": PALETTE["blue"],
    "breeze_v2_full": PALETTE["rose"],
}


def apply_style(font_size: float = 7.5) -> None:
    plt.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": font_size,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.75,
        "lines.linewidth": 1.0,
        "legend.frameon": False,
        "figure.dpi": 300,
        "savefig.bbox": "tight",
        "savefig.facecolor": "white",
    })


def save_figure(fig, path: Path, dpi: int = 600) -> None:
    """Save editable vector files plus high-resolution review rasters."""
    path.parent.mkdir(parents=True, exist_ok=True)
    stem = path.with_suffix("")
    svg_path = stem.with_suffix(".svg")
    fig.savefig(stem.with_suffix(".pdf"))
    fig.savefig(svg_path)
    svg_path.write_text("\n".join(line.rstrip() for line in svg_path.read_text().splitlines()) + "\n")
    fig.savefig(stem.with_suffix(".png"), dpi=300)
    fig.savefig(stem.with_suffix(".tiff"), dpi=dpi, pil_kwargs={"compression": "tiff_lzw"})


def panel_label(ax, label: str, x: float = -0.12, y: float = 1.04) -> None:
    ax.text(
        x, y, label,
        transform=ax.transAxes,
        ha="left", va="bottom",
        fontsize=8.5, fontweight="bold",
        color="black",
    )
