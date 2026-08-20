---
name: crear-tp
description: >
  Crea y redacta un nuevo TP teórico o práctico de Redes de Computadoras a partir
  de la plantilla del repositorio. Trigger: cuando se pida iniciar, crear o cargar
  consignas de un TP nuevo.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.1"
---

## Cuándo Usar

- Al crear un TP teórico o práctico nuevo.
- Al incorporar consignas entregadas como texto o PDF a un TP ya creado.

## Reglas Críticas

1. Pedí antes el tipo (`teórico` o `práctico`), número y título. No los inventes.
2. Usá `.agents/skills/crear-tp/assets/create_tp.py` desde la raíz. El script usa
   los recursos ubicados junto a él, crea `tps/<tipo>/tp<numero>/` y sólo completa
   los metadatos de carátula; no redacta consignas.
3. Usá la metadata de integrantes y docente definida en
   `.agents/skills/crear-tp/assets/create_tp.py`.
   No la obtengas de un TP existente ni la modifiques manualmente.
4. No modifiques `\Integrantes`: el script la asigna desde su metadata.
5. Cada TP es autocontenido: el script copia `logo.png` y configura
   `\LogoArchivo{logo.png}`. No apuntes a recursos externos al TP.
6. Si las consignas llegan como texto, transcribilas y estructuralas manualmente en
   TeX. Si llegan como PDF, leé el PDF con la herramienta disponible y transcribí
   con criterio su contenido a TeX nuevo. No uses OCR, conversiones masivas ni
   generación automática de LaTeX para las consignas.
7. Escapá los caracteres especiales de TeX al transcribir texto literal y preservá
   la numeración, fórmulas, tablas y figuras de la consigna cuando correspondan.

## Flujo

1. Confirmá tipo, número y título con la persona usuaria.
2. Creá el esqueleto con el comando correspondiente.
3. Reemplazá las secciones de ejemplo por las consignas transcritas a mano. Usá
   `\section{Consignas}` y listas `enumerate` cuando el material lo amerite.
4. No generes el PDF salvo que lo pidan expresamente; para eso cargá la skill
   `regenerar-entrega-pdf`.

## Comandos

```bash
python3 .agents/skills/crear-tp/assets/create_tp.py teorico 2 "Título del TP"
python3 .agents/skills/crear-tp/assets/create_tp.py practico 2 "Título del TP"
```

El resultado sigue esta convención:

```text
tps/teorico/tp2/teorico-tp-2.tex
tps/practico/tp2/practico-tp-2.tex
```

## Recursos

- **Plantilla**: `assets/plantilla-tp.tex`
- **Logo**: `assets/logo.png`
- **Metadata de scaffold**: `assets/create_tp.py`
- **Estructura**: `tps/README.md`
