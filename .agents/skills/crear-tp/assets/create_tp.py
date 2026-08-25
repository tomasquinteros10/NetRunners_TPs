#!/usr/bin/env python3
"""Create the initial TeX source for a NetRunners practical assignment."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path


ASSETS_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_ROOT = ASSETS_DIRECTORY.parents[3]
TEMPLATE = ASSETS_DIRECTORY / "plantilla-tp.tex"
LOGO = ASSETS_DIRECTORY / "logo.png"
TEACHERS = {
    "teorico": "FACUNDO NICOLAS OLIVA CUNEO",
    "practico": "SANTIAGO MARTIN HENN",
}
MEMBERS = (
    ("Bastida, Lucas Ramiro", "DNI 39444511"),
    ("Contessi, Ruben Andres", "DNI 33315235"),
    ("Garay, Ignacio Hernan", "DNI 44191925"),
    ("Giraudo, Juan Pablo", "DNI 34970089"),
    ("Peñaloza, Gonzalo Adrian", "DNI 40441355"),
    ("Quinteros del Castillo, Tomás Agustín", "DNI 46169739"),
    ("Vasconsellos Blason, Benjamin Alejandro", "DNI 45642879"),
)
DISPLAY_TYPES = {"teorico": "Teórico", "practico": "Práctico"}


def positive_number(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("debe ser un entero") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("debe ser mayor o igual que 1")
    return number


def latex_text(value: str) -> str:
    """Escape a command-line title while leaving Spanish letters unchanged."""
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in value)


def replace_command(source: str, command: str, value: str) -> str:
    pattern = rf"\\newcommand\{{\\{command}\}}\{{[^\n]*\}}"
    replacement = rf"\newcommand{{\{command}}}{{{value}}}"
    result, substitutions = re.subn(
        pattern, lambda _match: replacement, source, count=1
    )
    if substitutions != 1:
        raise ValueError(f"la plantilla no contiene el comando \\{command} esperado")
    return result


def members_latex() -> str:
    rows = "\n".join(f"    {name} & {document} \\\\" for name, document in MEMBERS)
    return "\\newcommand{\\Integrantes}{%\n  \\begin{tabular}{ll}\n" + rows + "\n  \\end{tabular}%\n}"


def replace_members(source: str) -> str:
    pattern = r"\\newcommand\{\\Integrantes\}\{.*?\n\}"
    result, substitutions = re.subn(
        pattern, lambda _match: members_latex(), source, count=1, flags=re.DOTALL
    )
    if substitutions != 1:
        raise ValueError("la plantilla no contiene el comando \\Integrantes esperado")
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crea un TP inicial desde la plantilla incluida en esta skill."
    )
    parser.add_argument("kind", choices=("teorico", "practico"), help="tipo de TP")
    parser.add_argument("number", type=positive_number, help="número de TP")
    parser.add_argument("title", help="título del TP")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not TEMPLATE.is_file() or not LOGO.is_file():
        print(
            f"[ERROR] faltan recursos de la skill: plantilla={TEMPLATE}; logo={LOGO}",
            file=sys.stderr,
        )
        return 1

    directory = REPOSITORY_ROOT / "tps" / args.kind / f"tp{args.number}"
    destination = directory / f"{args.kind}-tp-{args.number}.tex"
    if destination.exists():
        print(f"[ERROR] el TP ya existe: {destination}", file=sys.stderr)
        return 1

    try:
        content = TEMPLATE.read_text(encoding="utf-8")
        content = replace_command(content, "TipoTrabajo", "Trabajo Práctico")
        content = replace_command(content, "NumeroTrabajo", str(args.number))
        content = replace_command(content, "TipoTP", DISPLAY_TYPES[args.kind])
        content = replace_command(content, "NombreTrabajo", latex_text(args.title))
        content = replace_command(content, "Docente", TEACHERS[args.kind])
        content = replace_command(content, "LogoArchivo", "logo.png")
        content = replace_members(content)
        directory.mkdir(parents=True, exist_ok=True)
        shutil.copy2(LOGO, directory / LOGO.name)
        destination.write_text(content, encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"[ERROR] no se pudo crear el TP: {exc}", file=sys.stderr)
        return 1

    print(f"[OK] plantilla copiada: {TEMPLATE}")
    print(f"[OK] fuente creada: {destination}")
    print(f"[OK] logo copiado: {directory / LOGO.name}")
    print(f"[OK] docente: {TEACHERS[args.kind]}")
    print("[OK] integrantes: asignados desde la metadata del script")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
