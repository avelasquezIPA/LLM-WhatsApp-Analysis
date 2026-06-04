"""Paso 5b: Búsqueda semántica (RAG) - Programa Apapachar
=======================================================
Permite hacer preguntas de investigación sobre los mensajes de WhatsApp.
El sistema recupera los chunks más relevantes y los usa como contexto
para que Claude responda basándose únicamente en texto real.

Esto es RAG: Retrieval Augmented Generation.
  1. La pregunta se convierte en un embedding
  2. Se buscan los chunks más similares en ChromaDB
  3. Esos chunks se envían a Claude como contexto
  4. Claude responde basándose solo en ese contexto

Uso:
  uv run python scripts/python_scripts/05b_semantic_search.py

Input:  data/vectorstore/ (ChromaDB)
"""

from __future__ import annotations

import os
from pathlib import Path

import anthropic
import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
VECTORSTORE_PATH = ROOT / "data" / "vectorstore"
MODELO_NOMBRE = "paraphrase-multilingual-mpnet-base-v2"

load_dotenv(ROOT / ".env")

# ---------------------------------------------------------------------------
# Inicializar clientes (se cargan una sola vez)
# ---------------------------------------------------------------------------
print("Cargando modelo de embeddings...")
modelo = SentenceTransformer(MODELO_NOMBRE)

print("Conectando a ChromaDB...")
cliente_chroma = chromadb.PersistentClient(path=str(VECTORSTORE_PATH))
coleccion = cliente_chroma.get_collection("apapachar_chunks")
print(f"  {coleccion.count()} chunks disponibles.\n")

cliente_claude = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))


# ---------------------------------------------------------------------------
# Funciones principales
# ---------------------------------------------------------------------------
def buscar_chunks(pregunta: str, n_resultados: int = 5) -> list[dict]:
    """Recupera los chunks más relevantes para una pregunta."""
    embedding = modelo.encode([pregunta])
    resultados = coleccion.query(
        query_embeddings=embedding.tolist(),
        n_results=n_resultados,
        include=["documents", "metadatas", "distances"],
    )
    chunks = []
    for doc, meta, dist in zip(
        resultados["documents"][0],
        resultados["metadatas"][0],
        resultados["distances"][0],
    ):
        chunks.append(
            {
                "chunk_id": meta["chunk_id"],
                "ciudad": meta["city_grupo"],
                "semana": meta["n_week"],
                "tema": meta["tema"],
                "similitud": round(1 - dist, 3),
                "texto": doc,
            }
        )
    return chunks


def responder(pregunta: str, n_chunks: int = 4, verbose: bool = True) -> str:
    """Responde una pregunta de investigación usando RAG.

    Args:
        pregunta: Pregunta en español sobre los mensajes de Apapachar.
        n_chunks: Número de chunks a recuperar como contexto (default 4).
        verbose: Si True, muestra los chunks recuperados antes de la respuesta.

    """
    chunks = buscar_chunks(pregunta, n_resultados=n_chunks)

    if verbose:
        print(f"\nChunks recuperados para: '{pregunta}'")
        print("-" * 60)
        for c in chunks:
            print(
                f"  {c['chunk_id']:18s} | sem {c['semana']:2d} | "
                f"similitud: {c['similitud']:.3f} | {c['tema'][:45]}"
            )
        print()

    # Construir contexto con metadata visible para Claude
    contexto = "\n\n---\n\n".join(
        [
            f"[Chunk: {c['chunk_id']} | Ciudad: {c['ciudad']} | "
            f"Semana {c['semana']} | Tema: {c['tema']}]\n{c['texto']}"
            for c in chunks
        ]
    )

    prompt = f"""Eres un asistente de investigación del Programa Apapachar, \
un programa de crianza positiva y prevención de violencia contra la niñez \
en Colombia.

Responde la siguiente pregunta basándote ÚNICAMENTE en los mensajes de \
WhatsApp proporcionados. Si la información no está en los mensajes, dilo \
explícitamente. Cita el chunk relevante cuando sea posible.

PREGUNTA:
{pregunta}

MENSAJES RELEVANTES:
{contexto}

RESPUESTA:"""

    respuesta = cliente_claude.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return respuesta.content[0].text


# ---------------------------------------------------------------------------
# Demo interactivo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    preguntas_demo = [
        "¿En qué semanas los participantes expresaron dificultades con sus hijos?",
        "¿Cómo participaron los padres hombres en el programa?",
        "¿Qué emociones mencionaron más los participantes?",
    ]

    print("=" * 60)
    print("BÚSQUEDA SEMÁNTICA - Programa Apapachar")
    print("=" * 60)

    for pregunta in preguntas_demo:
        print(f"\nPREGUNTA: {pregunta}")
        print("=" * 60)
        respuesta = responder(pregunta, n_chunks=4, verbose=True)
        print("RESPUESTA:")
        print(respuesta)
        print("\n" + "=" * 60)

    # Modo interactivo
    print("\n--- Modo interactivo (escribe 'salir' para terminar) ---\n")
    while True:
        pregunta = input("Tu pregunta: ").strip()
        if pregunta.lower() in ("salir", "exit", "q"):
            break
        if not pregunta:
            continue
        respuesta = responder(pregunta, n_chunks=4, verbose=True)
        print("\nRESPUESTA:")
        print(respuesta)
        print()
