"""Mini-script de prueba asíncrono del Pipeline de Extracción de Entidades Técnicas.

    python main.py                    # casos de ejemplo + prueba de estrés
    python main.py --provider anthropic
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os

from dotenv import load_dotenv
from pydantic import ValidationError

from chain import process_text

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

CASOS_EJEMPLO = [
    "Migramos el servicio de autenticación de Flask a FastAPI y agregamos Redis "
    "como cache de sesiones. El rollout fue sin incidentes.",
    "ALERTA: el pod de postgres-primary está en CrashLoopBackOff desde hace 40 "
    "minutos; las réplicas de lectura siguen sirviendo tráfico pero las "
    "escrituras fallan con connection refused. Equipo de guardia notificado.",
]

# Prueba de estrés (p.47, paso 5): texto ambiguo, sin tecnologías claras ni
# señal de criticidad explícita. Verifica si el validador se queja o si el
# modelo igual produce algo dentro del esquema (estimación razonable).
CASO_AMBIGUO = "Che, ayer el sistema iba lento pero ya se solucionó solo, no sé bien qué pasó."


async def ejecutar_caso(etiqueta: str, texto: str) -> None:
    print(f"\n{'=' * 68}\n{etiqueta}\n{'=' * 68}")
    try:
        resultado = await process_text(texto)
        print(resultado.model_dump_json(indent=2))
    except ValidationError as exc:
        # Pydantic lanzó ValidationError: el LLM devolvió algo con la forma
        # correcta pero que no cumple una restricción del esquema (p.ej. lista
        # de tecnologías vacía). with_retry ya agotó sus 3 intentos.
        logging.error("Falló la validación tras los reintentos: %s", exc)
    except Exception as exc:  # noqa: BLE001 - frontera del script de prueba
        logging.error("Error de ejecución de la cadena: %s", exc)


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", choices=["openai", "anthropic"], default=None)
    args = parser.parse_args()

    load_dotenv()
    if args.provider:
        os.environ["LLM_PROVIDER"] = args.provider

    for i, texto in enumerate(CASOS_EJEMPLO, start=1):
        await ejecutar_caso(f"Caso {i}", texto)

    await ejecutar_caso("Prueba de estrés (texto ambiguo)", CASO_AMBIGUO)


if __name__ == "__main__":
    asyncio.run(main())
