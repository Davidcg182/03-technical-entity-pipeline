# Technical Entity Pipeline

Pipeline de extracción de entidades técnicas: recibe un párrafo de texto libre (una descripción
de arquitectura, un log de error) y devuelve un objeto **validado** con las tecnologías
mencionadas, el nivel de criticidad y un resumen técnico.

**Pre-entrega 2 · Módulo 2 — Coderhouse AI Engineering.**

---

## El problema

Un LLM devuelve texto libre. Si tu sistema espera `tecnologias: list[str]`,
`nivel_de_criticidad: "baja"|"media"|"alta"` y `resumen_tecnico: str`, nada garantiza que el
modelo no invente una clave, deje la lista vacía o devuelva un nivel de criticidad que no es
ninguno de los tres permitidos. Este repo resuelve eso con dos piezas: un **contrato de datos**
(Pydantic) que el modelo está obligado a seguir, y **resiliencia** ante fallos transitorios del
proveedor.

## Arquitectura

```
texto libre ──▶ ChatPromptTemplate ──▶ ChatModel.with_structured_output(EntidadesTecnicas) ──▶ EntidadesTecnicas
                                              │
                                   .with_retry(stop_after_attempt=3,
                                               wait_exponential_jitter=True)
```

```
schemas.py   EntidadesTecnicas (Pydantic): tecnologias, nivel_de_criticidad, resumen_tecnico
chain.py     Cadena LCEL + process_text(text: str) -> EntidadesTecnicas
main.py      Script de prueba asíncrono: 2 casos de ejemplo + 1 prueba de estrés (texto ambiguo)
```

## Instalación y ejecución

Requiere **Python 3.12+**.

```bash
python3 -m venv .venv && source .venv/bin/activate   # o: uv venv --python 3.12 .venv
pip install -r requirements.txt                      # o: uv pip install -r requirements.txt
cp .env.example .env   # completar con tu proveedor y clave
python main.py
python main.py --provider anthropic
```

## Mapeo a la rúbrica (p.49)

| Criterio | Peso | Cómo se cumple |
| --- | --- | --- |
| Definición del Esquema y Salida Estructurada | 30% | `schemas.py`: `EntidadesTecnicas` con `Field(min_length=1)` en `tecnologias`/`resumen_tecnico` y `Enum` para `nivel_de_criticidad`; `chain.py` usa `model.with_structured_output(EntidadesTecnicas)`. |
| Implementación de Cadena LCEL y Prompting | 30% | `prompt \| modelo_resiliente` con `ChatPromptTemplate` modular (sin f-strings hardcodeadas dentro de la cadena). |
| Ejecución Asíncrona y Resiliencia | 25% | `process_text` es `async`, usa `.ainvoke()`, y la cadena está envuelta en `.with_retry()`; logs en cada paso (`chain.py`). |
| Estructura del Repositorio y Script de Prueba | 15% | `schemas.py` + `chain.py` separados; `main.py` como script de prueba con 2 casos + 1 prueba de estrés. |

## Decisiones y limitaciones conocidas

- **No se valida `finish_reason` explícitamente.** `with_structured_output` usa Tool Calling por
  debajo y abstrae el mensaje crudo del modelo — no expone directamente si la respuesta se cortó
  por límite de tokens. Si eso llegara a pasar, el JSON resultante sería incompleto y Pydantic lo
  rechazaría igual (`ValidationError`), que es lo que captura `main.py`. No es la misma detección
  temprana que sugiere el enunciado (p.47), pero el efecto — no dejar pasar un objeto incompleto —
  se cumple.
- **El reintento (`with_retry`) es para fallos transitorios**, no para que el modelo "aprenda" de
  un error de validación. Si el texto de entrada genuinamente no tiene tecnologías mencionables,
  reintentar 3 veces no lo arregla — ver `NOTES.md` del módulo en el repositorio de aprendizaje.
- Reutiliza el patrón de selección de proveedor (`LLM_PROVIDER`/`OPENAI_BASE_URL`) del cliente
  unificado del Módulo 1, sin reproducir su arquitectura completa de Ports & Adapters.
