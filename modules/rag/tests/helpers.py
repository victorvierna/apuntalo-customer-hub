"""Small made-up guides, so the tests do not depend on the real help texts."""

import tempfile
import unittest
from pathlib import Path

BONOS = """\
# Bonos de sesiones

Un bono reúne varias sesiones de un servicio para un cliente.

## Crear un bono

1. Abre **Clientes** y elige la ficha.
2. Pulsa **Nuevo bono** y guarda.

## Preguntas frecuentes

### ¿Una sesión gastada se puede devolver?
Sí, desde los movimientos del [bono](../12-bonos/bonos.md).

### ¿Caduca el bono?
Depende de la fecha de caducidad que pongas al crearlo.
"""

COBROS = """\
# Cobros a clientes

## Qué significan las cifras

| Cifra | Qué es |
|---|---|
| Cobrado online | Pagos completados |
| Neto online | Cobrado menos devuelto |

![Pantalla de reembolso con el importe devuelto](../imagenes/pago.png)

## Preguntas frecuentes

### ¿Caduca el bono?
Esta pregunta repite título a propósito: su ref no debe chocar.

### ¿Caduca el bono?
Y esta también.
"""

README = "# Ayuda\n\n- [Bonos](12-bonos/bonos.md)\n- [Cobros](13-cobros/cobros.md)\n"


class GuidesTestCase(unittest.TestCase):
    """Writes the guides to ``<tmp>/ayuda/`` as they sit in ``data/faqs/``."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.guides_dir = Path(tmp.name) / "ayuda"
        self.write("12-bonos/bonos.md", BONOS)
        self.write("13-cobros/cobros.md", COBROS)
        self.write("README.md", README)

    def write(self, relative: str, text: str) -> None:
        path = self.guides_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
