import chromadb
import os

# Ruta exacta dictada por la estructura del proyecto
CHROMA_PATH = "data/db_chroma"

def inicializar_chromadb():
    """
    Inicializa el Motor B Semántico de OmniCAD.
    Crea el directorio persistente y la colección para las notas y especificaciones.
    """
    os.makedirs(CHROMA_PATH, exist_ok=True)
    
    # Inicializar el cliente persistente en la ruta especificada
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    # Crear o recuperar la colección estricta
    # Nota: El modelo nomic-embed-text se conectará durante la fase de ingesta/consulta vía LangChain u Ollama
    coleccion = client.get_or_create_collection(
        name="notas_especificaciones",
        metadata={"hnsw:space": "cosine"} # Métrica de distancia recomendada para embeddings de texto
    )
    
    print(f"Motor B (ChromaDB) inicializado correctamente en: {CHROMA_PATH}")
    print(f"Colección activa: {coleccion.name}")
    print("Recordatorio de ingesta: Exigir metadatos {'id_plano': 'UUID', 'origen': 'cajetin_o_nota_libre'}")

if __name__ == "__main__":
    inicializar_chromadb()