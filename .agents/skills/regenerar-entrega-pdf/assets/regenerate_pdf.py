#!/usr/bin/env python3
"""Regenerate a LaTeX PDF and move it to the project's delivery directory.

Usage:
    python3 .agents/skills/regenerar-entrega-pdf/assets/regenerate_pdf.py path/to/work.tex
    python3 .agents/skills/regenerar-entrega-pdf/assets/regenerate_pdf.py path/to/work.tex -o path/to/output --passes 2
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


AUXILIARY_SUFFIXES = (
    ".aux",
    ".log",
    ".out",
    ".toc",
    ".fls",
    ".fdb_latexmk",
    ".synctex.gz",
    ".nav",
    ".snm",
    ".vrb",
    ".lof",
    ".lot",
    ".bcf",
    ".run.xml",
)
TP_FILENAME = re.compile(r"(?:teorico|practico)-tp-[1-9][0-9]*\.tex")


def positive_passes(value: str) -> int:
    """Parse --passes and reject zero or negative values."""
    try:
        passes = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("debe ser un entero") from exc
    if passes < 1:
        raise argparse.ArgumentTypeError("debe ser mayor o igual que 1")
    return passes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenera un PDF desde un archivo .tex usando pdflatex."
    )
    parser.add_argument("tex", type=Path, help="ruta al archivo .tex")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="carpeta destino del PDF (por defecto: tps/entregas)",
    )
    parser.add_argument(
        "--passes",
        type=positive_passes,
        default=2,
        help="cantidad de pasadas de pdflatex (por defecto: 2)",
    )
    return parser.parse_args()


def default_output_dir() -> Path:
    """Return this repository's conventional delivery directory."""
    return Path(__file__).resolve().parents[4] / "tps" / "entregas"


def cleanup_auxiliaries(directory: Path, stem: str) -> None:
    for suffix in AUXILIARY_SUFFIXES:
        candidate = directory / f"{stem}{suffix}"
        if candidate.is_file() or candidate.is_symlink():
            candidate.unlink()


def pdf_metadata(pdf: Path) -> tuple[str | None, str | None]:
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf)],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None, None
    if result.returncode != 0:
        return None, None

    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition(":")
        if separator:
            values[key.strip()] = value.strip()
    return values.get("Title"), values.get("Pages")


def main() -> int:
    args = parse_args()
    tex = args.tex.expanduser().resolve()
    if not tex.is_file():
        print(f"[ERROR] no existe el archivo fuente: {tex}", file=sys.stderr)
        return 1
    if tex.suffix.lower() != ".tex":
        print(f"[ERROR] el archivo fuente no tiene extension .tex: {tex}", file=sys.stderr)
        return 1
    if not TP_FILENAME.fullmatch(tex.name):
        print(
            "[ERROR] el archivo fuente debe llamarse "
            "<teorico|practico>-tp-<numero>.tex",
            file=sys.stderr,
        )
        return 1

    source_dir = tex.parent
    output_dir = (args.output_dir or default_output_dir()).expanduser().resolve()
    source_pdf = source_dir / f"{tex.stem}.pdf"
    output_pdf = output_dir / source_pdf.name

    print(f"[OK] archivo fuente: {tex}")
    print(f"[OK] directorio de trabajo: {source_dir}")
    if shutil.which("pdflatex") is None:
        print("[ERROR] pdflatex no esta disponible en PATH", file=sys.stderr)
        return 1
    print(f"[OK] pdflatex disponible: {shutil.which('pdflatex')}")

    # Avoid mistaking an old source PDF for a successful compilation.
    try:
        if source_pdf.exists():
            source_pdf.unlink()
    except OSError as exc:
        print(f"[ERROR] no se pudo quitar el PDF previo de la fuente: {exc}", file=sys.stderr)
        return 1

    command = [
        "pdflatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        tex.name,
    ]
    for pass_number in range(1, args.passes + 1):
        print(f"[PASS] pasada {pass_number}/{args.passes}: {' '.join(command)}")
        try:
            result = subprocess.run(command, cwd=source_dir, check=False)
        except OSError as exc:
            print(f"[ERROR] no se pudo ejecutar pdflatex: {exc}", file=sys.stderr)
            return 1
        if result.returncode != 0:
            print(
                f"[ERROR] pasada {pass_number}/{args.passes} fallo con codigo {result.returncode}",
                file=sys.stderr,
            )
            return 1
        print(f"[OK] pasada {pass_number}/{args.passes}: codigo 0")

    if not source_pdf.is_file():
        print(f"[ERROR] pdflatex termino sin generar el PDF: {source_pdf}", file=sys.stderr)
        return 1
    print(f"[OK] PDF generado: {source_pdf}")

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        source_pdf.replace(output_pdf)
    except OSError as exc:
        print(f"[ERROR] no se pudo mover el PDF a {output_pdf}: {exc}", file=sys.stderr)
        return 1
    print(f"[OK] PDF movido: {output_pdf}")

    try:
        cleanup_auxiliaries(source_dir, tex.stem)
        if output_dir != source_dir:
            cleanup_auxiliaries(output_dir, tex.stem)
    except OSError as exc:
        print(f"[ERROR] no se pudieron limpiar los auxiliares: {exc}", file=sys.stderr)
        return 1
    print(f"[OK] limpieza: auxiliares de {tex.stem} eliminados en fuente y destino")

    title, pages = pdf_metadata(output_pdf)
    if title is not None and pages is not None:
        print(f"[OK] pdfinfo: titulo={title!r}; paginas={pages}")
    else:
        print("[OK] pdfinfo: no disponible o sin metadatos verificables")
    print(f"[OK] ruta final: {output_pdf}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
