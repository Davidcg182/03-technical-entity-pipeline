"""Contrato de datos del pipeline: lo que el LLM está OBLIGADO a devolver.

`with_structured_output` fuerza al modelo (vía Tool Calling / JSON Mode del
proveedor) a encajar su respuesta en este esquema. Las restricciones de campo
(`min_length`, `Enum`) son validación semántica de UN solo campo — no cruzan
información entre campos, así que alcanza con Pydantic declarativo, sin
`model_validator`.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class NivelCriticidad(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"


class EntidadesTecnicas(BaseModel):
    """Entidades técnicas extraídas de un párrafo de texto libre."""

    tecnologias: list[str] = Field(
        min_length=1,
        description="Tecnologías, lenguajes o herramientas mencionadas en el texto.",
    )
    nivel_de_criticidad: NivelCriticidad = Field(
        description="Severidad/impacto que transmite el texto: baja, media o alta.",
    )
    resumen_tecnico: str = Field(
        min_length=1,
        description="Resumen técnico del texto en una o dos frases.",
    )
