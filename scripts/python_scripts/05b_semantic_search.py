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

import anthropic
import chromadb
from config_loader import DATA_DIR, PROJECT_ROOT, cfg
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

# ---------------------------------------------------------------------------
# Configuración (valores leídos de config.yaml)
# ---------------------------------------------------------------------------
VECTORSTORE_PATH = DATA_DIR / cfg["data"]["intermediate"]["vectorstore"]
MODELO_NOMBRE = cfg["models"]["embedding_model"]
COLECCION_NOMBRE = cfg["vectordb"]["collection_chunks"]
CLAUDE_MODEL = cfg["models"]["claude_model"]
MAX_TOKENS_RAG = cfg["api"]["max_tokens_rag"]
DEFAULT_N_RESULTS = cfg["api"]["rag_default_n_results"]
PROJECT_NAME = cfg["project"]["name"]
PROJECT_DESC = cfg["project"]["description"]
_PROMPT_TEMPLATE = cfg["prompts"]["rag_answer"]

load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# Inicializar clientes (se cargan una sola vez)
# ---------------------------------------------------------------------------
print("Cargando modelo de embeddings...")
modelo = SentenceTransformer(MODELO_NOMBRE)

print("Conectando a ChromaDB...")
cliente_chroma = chromadb.PersistentClient(path=str(VECTORSTORE_PATH))
coleccion = cliente_chroma.get_collection(COLECCION_NOMBRE)
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


def responder(
    pregunta: str, n_chunks: int = DEFAULT_N_RESULTS, verbose: bool = True
) -> str:
    """Responde una pregunta de investigación usando RAG.

    Args:
        pregunta: Pregunta en español sobre los mensajes del programa.
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

    prompt = _PROMPT_TEMPLATE.format(
        project_name=PROJECT_NAME,
        project_description=PROJECT_DESC,
        pregunta=pregunta,
        contexto=contexto,
    )

    respuesta = cliente_claude.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS_RAG,
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
    print(f"BÚSQUEDA SEMÁNTICA - {PROJECT_NAME}")
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
