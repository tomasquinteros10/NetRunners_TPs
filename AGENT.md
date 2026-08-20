# NetRunners TPs

Repositorio de informes LaTeX para Trabajos Prácticos de Redes de Computadoras.

## Skills Locales

| Skill | Uso | Archivo |
| --- | --- | --- |
| `crear-tp` | Crea el esqueleto de un TP teórico o práctico y guía la transcripción manual de consignas. | `.agents/skills/crear-tp/SKILL.md` |
| `regenerar-entrega-pdf` | Genera el PDF final con el script oficial, confiando sólo en su resultado. | `.agents/skills/regenerar-entrega-pdf/SKILL.md` |

Al crear, iniciar o cargar consignas de un TP, cargá `crear-tp`. Al regenerar su
PDF de entrega, cargá `regenerar-entrega-pdf`.

## Estructura

```text
tps/
  teorico/tp<N>/               Fuentes de TPs teóricos
  practico/tp<N>/              Fuentes de TPs prácticos
  entregas/                    PDFs generados para entregar
.agents/skills/
  crear-tp/assets/             Scaffolder, plantilla y logo
  regenerar-entrega-pdf/assets/ Regenerador de PDFs
```

## Crear o Modificar TPs

Desde la raíz:

```bash
python3 .agents/skills/crear-tp/assets/create_tp.py teorico 2 "Título del TP"
python3 .agents/skills/crear-tp/assets/create_tp.py practico 2 "Título del TP"
```

El script no procesa consignas. Transcribilas manualmente a TeX a partir del
texto o de la lectura del PDF provisto. Cada TP recibe una copia de `logo.png`
y su fuente usa la ruta local `logo.png`.

Para generar la entrega:

```bash
python3 .agents/skills/regenerar-entrega-pdf/assets/regenerate_pdf.py tps/teorico/tp2/teorico-tp-2.tex
```

El PDF queda en `tps/entregas` salvo que se indique `--output-dir`.

## Prerrequisitos Linux

- Python 3: `sudo apt install python3`
- LaTeX y `pdflatex`: `sudo apt install texlive-latex-base texlive-latex-recommended`
- TikZ para TPs que lo usen, incluido TP 1: `sudo apt install texlive-pictures`
- `pdfinfo` es opcional para el resumen que muestra el regenerador:
  `sudo apt install poppler-utils`

No hacen falta dependencias Python externas: ambos scripts usan sólo la biblioteca
estándar.
