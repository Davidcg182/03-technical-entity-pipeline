"""Cadena LCEL: Prompt -> Modelo (salida estructurada) -> validación con reintento.

    chain = prompt | model.with_structured_output(EntidadesTecnicas)
    resilient_chain = chain.with_retry(stop_after_attempt=3, wait_exponential_jitter=True)

El reintento cubre errores TRANSITORIOS (red, rate limit, JSON mal formado por un
fallo puntual del proveedor) — no errores de formato permanentes (p.ej. pedirle al
modelo un campo que el texto de entrada no contiene; reintentar eso sólo repite el
fallo, ver NOTES.md del módulo).
"""

from __future__ import annotations

import logging
import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable

from schemas import EntidadesTecnicas

log = logging.getLogger("pipeline")

SYSTEM_PROMPT = (
    "Eres un analista técnico. A partir de un párrafo de texto libre (una "
    "descripción de arquitectura o un log de error), extraé las tecnologías "
    "mencionadas, el nivel de criticidad que transmite el texto y un resumen "
    "técnico breve. Si el texto no permite inferir con certeza un campo, hacé "
    "la mejor estimación posible en lugar de inventar datos no mencionados."
)


def construir_modelo(provider: str):
    """Reemplaza al SDK crudo de M1 por un ChatModel de LangChain."""
    temperature = float(os.environ.get("LLM_TEMPERATURE", "0.0"))

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=os.environ.get("LLM_MODEL") or "gpt-4o-mini",
            temperature=temperature,
            base_url=os.environ.get("OPENAI_BASE_URL") or None,
            api_key=os.environ["OPENAI_API_KEY"],
        )

    if provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=os.environ.get("LLM_MODEL") or "claude-sonnet-5",
            temperature=temperature,
            api_key=os.environ["ANTHROPIC_API_KEY"],
        )

    raise ValueError(f"Proveedor no soportado: {provider!r} (usar openai|anthropic)")


def construir_cadena(provider: str) -> Runnable:
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{texto}"),
    ])
    modelo = construir_modelo(provider)

    # Contrato de datos: el modelo está obligado a devolver un EntidadesTecnicas.
    modelo_estructurado = modelo.with_structured_output(EntidadesTecnicas)

    # Resiliencia: reintento con backoff exponencial + jitter ante fallos
    # transitorios (red, rate limit, JSON mal formado puntual).
    modelo_resiliente = modelo_estructurado.with_retry(
        stop_after_attempt=3,
        wait_exponential_jitter=True,
    )

    return prompt | modelo_resiliente


_chain: Runnable | None = None  # construido una sola vez, bajo demanda


def _get_chain() -> Runnable:
    global _chain
    if _chain is None:
        provider = os.environ.get("LLM_PROVIDER", "openai")
        _chain = construir_cadena(provider)
    return _chain


async def process_text(text: str) -> EntidadesTecnicas:
    """Ejecuta el pipeline completo (prompt -> modelo -> validación con
    reintento) sobre un párrafo de texto libre y devuelve el objeto validado.
    """
    log.info("Procesando texto (%d caracteres)...", len(text))
    resultado = await _get_chain().ainvoke({"texto": text})
    log.info(
        "Validación OK — criticidad=%s, %d tecnologías detectadas.",
        resultado.nivel_de_criticidad.value,
        len(resultado.tecnologias),
    )
    return resultado
