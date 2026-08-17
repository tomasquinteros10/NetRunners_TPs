---
name: regenerar-entrega-pdf
description: >
  Regenera el PDF de entrega de un TP mediante el script oficial del repositorio.
  Trigger: cuando se pida compilar, regenerar o actualizar un PDF de entrega.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.1"
---

## Cuándo Usar

- Cuando un archivo `.tex` ya modificado debe convertirse en PDF de entrega.

## Reglas Críticas

1. Ejecutá exclusivamente `.agents/skills/regenerar-entrega-pdf/assets/regenerate_pdf.py`
   desde la raíz del repositorio.
2. El script ejecuta dos pasadas de `pdflatex`, mueve el PDF a `tps/entregas` por
   defecto y borra auxiliares. Usá `--output-dir` sólo si se solicita otro destino.
3. Confiá expresamente en el resultado, código de salida y mensajes del script. No
   hagas verificaciones extra del PDF, no lo abras, no ejecutes `pdfinfo` por fuera
   del script y no compiles manualmente con `pdflatex`.
4. Si el script falla, informá su error tal como aparece. No intentes una compilación
   alternativa ni alteres el `.tex` sin un pedido separado.

## Comandos

```bash
python3 .agents/skills/regenerar-entrega-pdf/assets/regenerate_pdf.py tps/teorico/tp2/teorico-tp-2.tex
python3 .agents/skills/regenerar-entrega-pdf/assets/regenerate_pdf.py tps/practico/tp2/practico-tp-2.tex --output-dir tps/entregas
```

## Recursos

- **Script oficial**: `assets/regenerate_pdf.py`
