"""Reproducible visual and provenance QA for preview-only manuscript figures."""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageOps

import figure_revision_data as data


QA = data.PREVIEW / "qa"
FIGURES = {
    "Fig. 3": ("fig3_downstream_effects", "fig3_downstream_effects"),
    "Fig. 4": ("fig4_waveform_envelope", "fig4_waveform_envelope"),
    "Fig. 5": ("fig5_physical_error", "fig5_physical_error"),
    "Fig. 6": ("fig6_admission_mechanism", "fig6_admission_mechanism"),
    "Fig. 7": ("fig7_cross_condition", "fig7_cross_condition"),
    "Fig. S1": ("figS1_pu_distributions", "figS1_pu_distributions"),
    "Fig. S2": ("figS2_healthy_waveform_envelope", "figS2_healthy_waveform_envelope"),
    "Fig. S3": ("figS3_pu_failure_chain", "figS3_pu_failure_chain"),
}
OLD_NEW = {
    "Fig. 3": (["downstream_bars.png"], "Fig. 3: seed bars -> paired-effect forest"),
    "Fig. 4": (["waveforms.png"], "Fig. 4: ordered examples -> medoids and population spectra"),
    "Fig. 5": (["metric_distances.png", "boxplots.png"], "Fig. 5: raw heatmap/boxplots -> rule-relative errors"),
    "Fig. 6": (["acceptance_k.png", "failure_reasons.png"], "Fig. 6: proposal accounting -> audited cumulative admission"),
    "Fig. 7": (["cross_condition_heatmap.png"], "Fig. 7: mixed continuous/discrete generalization evidence"),
    "Fig. S1": (["boxplots.png"], "Fig. S1: boxplots -> distribution-complete ECDF"),
    "Fig. S2": (["waveforms.png"], "Fig. S2: healthy evidence moved to the supplement"),
    "Fig. S3": (["failure_case.png"], "Fig. S3: failure panel -> complete evidence-stop chain"),
}

# Full-severity matrices from Machado et al. (2009), applied in linear sRGB.
CVD_MATRICES = {
    "protanopia": np.array(
        [[0.152286, 1.052583, -0.204868],
         [0.114503, 0.786281, 0.099216],
         [-0.003882, -0.048116, 1.051998]]
    ),
    "deuteranopia": np.array(
        [[0.367322, 0.860646, -0.227968],
         [0.280085, 0.672501, 0.047413],
         [-0.011820, 0.042940, 0.968881]]
    ),
    "tritanopia": np.array(
        [[1.255528, -0.076749, -0.178779],
         [-0.078411, 0.930809, 0.147602],
         [0.004733, 0.691367, 0.303900]]
    ),
}


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = (
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
    )
    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _linearize(rgb: np.ndarray) -> np.ndarray:
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)


def _encode_srgb(rgb: np.ndarray) -> np.ndarray:
    return np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * np.power(rgb, 1 / 2.4) - 0.055)


def simulate_cvd(image: Image.Image, matrix: np.ndarray) -> Image.Image:
    rgb = np.asarray(image.convert("RGB"), dtype=np.float64) / 255.0
    transformed = _linearize(rgb) @ matrix.T
    encoded = _encode_srgb(np.clip(transformed, 0.0, 1.0))
    return Image.fromarray(np.uint8(np.clip(encoded, 0.0, 1.0) * 255 + 0.5), "RGB")


def _fit(image: Image.Image, width: int, height: int) -> Image.Image:
    fitted = image.copy()
    fitted.thumbnail((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (width, height), "white")
    canvas.paste(fitted, ((width - fitted.width) // 2, (height - fitted.height) // 2))
    return canvas


def _panel_grid(panels: list[tuple[str, Image.Image]], columns: int = 2) -> Image.Image:
    cell_w, cell_h, label_h = 1300, 950, 72
    rows = (len(panels) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_w, rows * (cell_h + label_h)), "white")
    draw = ImageDraw.Draw(sheet)
    for index, (label, panel) in enumerate(panels):
        row, column = divmod(index, columns)
        x, y = column * cell_w, row * (cell_h + label_h)
        sheet.paste(_fit(panel, cell_w, cell_h), (x, y + label_h))
        draw.text((x + 24, y + 18), label, fill="#202020", font=_font(30, bold=True))
    return sheet


def create_cvd_and_grayscale() -> list[Path]:
    outputs: list[Path] = []
    cvd_dir = QA / "cvd"
    gray_dir = QA / "grayscale"
    cvd_dir.mkdir(parents=True, exist_ok=True)
    gray_dir.mkdir(parents=True, exist_ok=True)
    grayscale_panels = []
    for label, (directory, stem) in FIGURES.items():
        original = Image.open(data.PREVIEW / directory / f"{stem}.png").convert("RGB")
        panels = [("Original", original)]
        panels.extend((name.capitalize(), simulate_cvd(original, matrix)) for name, matrix in CVD_MATRICES.items())
        sheet = _panel_grid(panels)
        path = cvd_dir / f"{stem}_cvd.png"
        sheet.save(path, dpi=(150, 150))
        outputs.append(path)
        gray = ImageOps.grayscale(original).convert("RGB")
        gray_path = gray_dir / f"{stem}_grayscale.png"
        gray.save(gray_path, dpi=(300, 300))
        outputs.append(gray_path)
        grayscale_panels.append((label, gray))
    gray_sheet = _panel_grid(grayscale_panels)
    gray_sheet_path = gray_dir / "grayscale_contact_sheet.png"
    gray_sheet.save(gray_sheet_path, dpi=(150, 150))
    outputs.append(gray_sheet_path)
    return outputs


def _stack(images: list[Image.Image], width: int, height: int) -> Image.Image:
    cell_h = height // max(len(images), 1)
    canvas = Image.new("RGB", (width, height), "white")
    for index, image in enumerate(images):
        canvas.paste(_fit(image, width, cell_h), (0, index * cell_h))
    return canvas


def create_old_new_sheets() -> list[Path]:
    out = QA / "old_new"
    out.mkdir(parents=True, exist_ok=True)
    formal = data.REPO / "breeze" / "paper" / "figs"
    outputs: list[Path] = []
    aggregate_panels = []
    for label, (old_names, description) in OLD_NEW.items():
        old_images = [Image.open(formal / name).convert("RGB") for name in old_names]
        old_column = _stack(old_images, 1300, 950)
        directory, stem = FIGURES[label]
        new_column = _fit(
            Image.open(data.PREVIEW / directory / f"{stem}.png").convert("RGB"),
            1300,
            950,
        )
        sheet = _panel_grid([("Current formal", old_column), ("Revision preview", new_column)])
        title_h = 100
        titled = Image.new("RGB", (sheet.width, sheet.height + title_h), "white")
        titled.paste(sheet, (0, title_h))
        ImageDraw.Draw(titled).text((30, 25), description, fill="#202020", font=_font(34, bold=True))
        stem = label.lower().replace(".", "").replace(" ", "_")
        path = out / f"old_new_{stem}.png"
        titled.save(path, dpi=(150, 150))
        outputs.append(path)
        aggregate_panels.append((label, titled))
    aggregate = _panel_grid(aggregate_panels)
    aggregate_path = out / "old_new_contact_sheet.png"
    aggregate.save(aggregate_path, dpi=(150, 150))
    outputs.append(aggregate_path)
    return outputs


def _parse_page_size(text: str) -> tuple[float, float]:
    match = re.search(r"Page size:\s+([0-9.]+) x ([0-9.]+) pts", text)
    if not match:
        raise RuntimeError("pdfinfo did not report page size")
    return float(match.group(1)), float(match.group(2))


def audit_exports() -> Path:
    rows = []
    for label, (directory, stem) in FIGURES.items():
        root = data.PREVIEW / directory
        pdf = root / f"{stem}.pdf"
        svg = root / f"{stem}.svg"
        png = root / f"{stem}.png"
        tiff = root / f"{stem}.tiff"
        pdf_info = subprocess.check_output(["pdfinfo", str(pdf)], text=True)
        width_pt, height_pt = _parse_page_size(pdf_info)
        fonts = subprocess.check_output(["pdffonts", str(pdf)], text=True).splitlines()[2:]
        svg_text = svg.read_text()
        with Image.open(png) as image:
            png_width, png_height = image.size
        with Image.open(tiff) as image:
            tiff_width, tiff_height = image.size
            dpi = image.info.get("dpi", (0, 0))
        rows.append(
            {
                "figure": label,
                "pdf_width_pt": width_pt,
                "pdf_height_pt": height_pt,
                "pdf_width_mm": width_pt * 25.4 / 72.0,
                "embedded_font_rows": len([line for line in fonts if line.strip()]),
                "svg_text_elements": svg_text.count("<text"),
                "svg_path_elements": svg_text.count("<path"),
                "png_width_px_300dpi": png_width,
                "png_height_px_300dpi": png_height,
                "tiff_width_px_600dpi": tiff_width,
                "tiff_height_px_600dpi": tiff_height,
                "tiff_dpi_x": float(dpi[0]),
                "tiff_dpi_y": float(dpi[1]),
            }
        )
    out = QA / "export_audit.csv"
    pd.DataFrame(rows).to_csv(out, index=False, lineterminator="\n")
    return out


def audit_manifests() -> Path:
    rows = []
    for manifest_path in sorted(data.PREVIEW.glob("*/source-manifest.json")):
        manifest = json.loads(manifest_path.read_text())
        for kind in ("code", "sources", "outputs"):
            for item in manifest.get(kind, []):
                path = data.REPO / item["path"]
                rows.append(
                    {
                        "manifest": data._relative(manifest_path),
                        "status": manifest["status"],
                        "kind": kind,
                        "path": item["path"],
                        "exists": path.exists(),
                        "sha256_matches": path.exists() and data.sha256(path) == item["sha256"],
                    }
                )
    out = QA / "manifest_audit.csv"
    pd.DataFrame(rows).to_csv(out, index=False, lineterminator="\n")
    return out


def audit_formal_hashes() -> Path:
    baseline = pd.read_csv(data.ANALYSIS / "figure_revision_baseline_sha256.csv")
    formal = baseline[
        baseline["path"].eq("breeze/paper/main_cas.tex")
        | baseline["path"].eq("breeze/paper/main_cas.pdf")
        | baseline["path"].str.startswith("breeze/paper/figs/")
    ].copy()
    formal["current_sha256"] = formal["path"].map(lambda value: data.sha256(data.REPO / value))
    formal["unchanged"] = formal["sha256"].eq(formal["current_sha256"])
    out = QA / "formal_hash_audit.csv"
    formal.to_csv(out, index=False, lineterminator="\n")
    return out


def build_cas_reading_size_pdf() -> tuple[Path, list[Path]]:
    out = QA / "cas_reading_size"
    out.mkdir(parents=True, exist_ok=True)
    tex = out / "cas_figure_qa.tex"
    blocks = []
    for label, (directory, stem) in FIGURES.items():
        figure = data.PREVIEW / directory / f"{stem}.pdf"
        rel = os.path.relpath(figure, out)
        blocks.append(
            "\\begin{figure*}[p]\n"
            "\\centering\n"
            f"\\includegraphics[width=\\textwidth]{{{rel}}}\n"
            f"\\caption{{{label} preview at CAS full-text width.}}\n"
            "\\end{figure*}\n\\clearpage"
        )
    tex.write_text(
        "\\documentclass[a4paper,fleqn]{cas-dc}\n"
        "\\usepackage{graphicx}\n"
        "\\begin{document}\n"
        "\\shorttitle{BREEZE figure QA}\n"
        "\\shortauthors{Figure QA}\n"
        "\\title[mode=title]{BREEZE revision-preview reading-size audit}\n"
        "\\author[1]{Figure QA}\n"
        "\\address[1]{Preview-only artifact}\n"
        "\\begin{abstract}This temporary document verifies preview figures at CAS manuscript width.\\end{abstract}\n"
        "\\maketitle\n"
        + "\n".join(blocks)
        + "\n\\end{document}\n"
    )
    template = data.REPO / "breeze" / "els-cas-templates"
    env = os.environ.copy()
    env["TEXINPUTS"] = str(template) + os.pathsep + env.get("TEXINPUTS", "")
    env["LC_ALL"] = "C"
    env["LANG"] = "C"
    subprocess.run(
        ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", tex.name],
        cwd=out,
        env=env,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    pdf = out / "cas_figure_qa.pdf"
    render_prefix = out / "cas_figure_qa_page"
    subprocess.run(
        ["pdftoppm", "-png", "-r", "150", str(pdf), str(render_prefix)],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    pages = sorted(out.glob("cas_figure_qa_page-*.png"))
    for suffix in (".abs", ".aux", ".fdb_latexmk", ".fls", ".out"):
        (out / f"cas_figure_qa{suffix}").unlink(missing_ok=True)
    return pdf, pages


def main() -> None:
    QA.mkdir(parents=True, exist_ok=True)
    outputs = [audit_exports(), audit_manifests(), audit_formal_hashes()]
    outputs.extend(create_cvd_and_grayscale())
    outputs.extend(create_old_new_sheets())
    pdf, pages = build_cas_reading_size_pdf()
    outputs.extend([pdf, *pages])
    index = QA / "qa-index.json"
    index.write_text(
        json.dumps(
            {
                "cvd_method": "Machado et al. (2009) full-severity matrices in linear sRGB; visual screening only",
                "outputs": [data._relative(path) for path in outputs],
            },
            indent=2,
        )
        + "\n"
    )
    print(index)


if __name__ == "__main__":
    main()
