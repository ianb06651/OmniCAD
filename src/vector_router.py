import sqlite3
import uuid
import chromadb
from chromadb.utils import embedding_functions
from src.extractor_dxf import extraer_datos_dxf

def poblar_sqlite(ruta_dxf, nombre_archivo, disciplina):
    id_plano = str(uuid.uuid4())
    print(f"Extrayendo datos de {ruta_dxf}...")
    textos, geometrias = extraer_datos_dxf(ruta_dxf, id_plano)
    
    if not textos and not geometrias:
        print("No se extrajo información útil.")
        return

    # --- 1. INYECCIÓN A SQLITE ---
    conn = sqlite3.connect("data/db_sqlite/planos_geometria.db")
    conn.enable_load_extension(True)
    conn.load_extension('mod_spatialite')
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO metadata_planos (id_plano, nombre_archivo, disciplina, revision) 
        VALUES (?, ?, ?, ?)
    """, (id_plano, nombre_archivo, disciplina, "R0"))

    for t in textos:
        cursor.execute("""
            INSERT INTO entidades_textuales (id_texto, id_plano, capa_origen, contenido, coord_x, coord_y) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (t['id_texto'], t['id_plano'], t['capa_origen'], t['contenido'], t['coord_x'], t['coord_y']))
    
    for g in geometrias:
        wkb_bytes = bytes.fromhex(g['geometria_wkb'])
        cursor.execute("""
            INSERT INTO entidades_geometricas (id_geometria, id_plano, capa_origen, tipo_entidad, geometria) 
            VALUES (?, ?, ?, ?, GeomFromWKB(?, -1))
        """, (g['id_geometria'], g['id_plano'], g['capa_origen'], g['tipo_entidad'], wkb_bytes))

# --- 2. INYECCIÓN A CHROMADB ---
    print("Inyectando notas al Motor Semántico...")
    try:
        ollama_ef = embedding_functions.OllamaEmbeddingFunction(
            url="http://localhost:11434/api/embeddings",
            model_name="nomic-embed-text"
        )
        chroma_client = chromadb.PersistentClient(path="data/db_chroma")
        coleccion_chroma = chroma_client.get_or_create_collection(
            name="notas_especificaciones",
            embedding_function=ollama_ef,
            metadata={"hnsw:space": "cosine"}
        )

        docs = []
        metadatos = []
        ids = []

        for t in textos:
            # Limpiar saltos de línea raros del DXF que rompen el tokenizador
            texto_limpio = t['contenido'].replace('\n', ' ').replace('\r', '').strip()
            if texto_limpio:
                docs.append(texto_limpio)
                metadatos.append({"id_plano": id_plano, "origen": "cajetin_o_nota_libre"})
                ids.append(t['id_texto'])

        if docs:
            print(f"Procesando {len(docs)} notas en lotes de 50...")
            lote_size = 50
            for i in range(0, len(docs), lote_size):
                coleccion_chroma.add(
                    documents=docs[i:i+lote_size],
                    metadatas=metadatos[i:i+lote_size],
                    ids=ids[i:i+lote_size]
                )
            print("¡Éxito! Notas inyectadas a ChromaDB de forma segura.")
            
    except Exception as e:
        print(f"Error crítico al conectar con ChromaDB u Ollama: {e}")

    # Guardamos los cambios de SQLite al final
    conn.commit()
    conn.close()

if __name__ == "__main__":
    poblar_sqlite("data/temp_dxf/plano_prueba.dxf", "A-100.1-OFP.dxf", "ARQ")