import sqlite3
import os

# Ruta exacta dictada por la estructura del proyecto
DB_PATH = "data/db_sqlite/planos_geometria.db"

def inicializar_sqlite_spatial():
    """
    Crea la base de datos relacional para el Cerebro Dual de OmniCAD.
    Habilita SpatiaLite, inicializa metadatos espaciales y registra columnas geométricas.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    
    # Habilitar la carga de extensiones para SpatiaLite
    conn.enable_load_extension(True)
    try:
        # Carga el binario de SpatiaLite (requiere mod_spatialite.dll en Windows)
        conn.load_extension('mod_spatialite')
    except sqlite3.OperationalError as e:
        print(f"Error crítico al cargar SpatiaLite: {e}")
        print("Asegúrate de tener mod_spatialite.dll en la raíz del entorno virtual o en tu PATH.")
        return

    cursor = conn.cursor()

    # Inicializar las tablas internas de metadatos espaciales de SpatiaLite
    # Solo es necesario ejecutarlo una vez al crear la DB
    try:
        cursor.execute("SELECT InitSpatialMetaData(1);")
    except sqlite3.OperationalError:
        pass # La metadata ya existe

    # Tabla 1: metadata_planos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS metadata_planos (
            id_plano TEXT PRIMARY KEY,
            nombre_archivo TEXT NOT NULL,
            disciplina TEXT CHECK(disciplina IN ('ARQ', 'TOP', 'MEP', 'EST')),
            revision TEXT,
            fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Tabla 2: entidades_textuales
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entidades_textuales (
            id_texto TEXT PRIMARY KEY,
            id_plano TEXT NOT NULL,
            capa_origen TEXT,
            contenido TEXT,
            coord_x REAL,
            coord_y REAL,
            FOREIGN KEY (id_plano) REFERENCES metadata_planos (id_plano)
        )
    ''')

    # Tabla 3: entidades_geometricas (Se crea sin la columna espacial inicialmente)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS entidades_geometricas (
            id_geometria TEXT PRIMARY KEY,
            id_plano TEXT NOT NULL,
            capa_origen TEXT,
            tipo_entidad TEXT CHECK(tipo_entidad IN ('LINE', 'LWPOLYLINE', 'INSERT')),
            FOREIGN KEY (id_plano) REFERENCES metadata_planos (id_plano)
        )
    ''')

    # Agregar la columna espacial utilizando la función estricta de SpatiaLite
    # SRID -1 indica un plano cartesiano crudo (típico en archivos CAD)
    try:
        cursor.execute("SELECT AddGeometryColumn('entidades_geometricas', 'geometria', -1, 'GEOMETRY', 'XY');")
        # Crear índice espacial (R-Tree) para que los cálculos de distancias sean instantáneos
        cursor.execute("SELECT CreateSpatialIndex('entidades_geometricas', 'geometria');")
    except sqlite3.OperationalError:
        pass # La columna y el índice ya fueron registrados previamente

    conn.commit()
    conn.close()
    print(f"Estructura SQLite y SpatiaLite inicializada correctamente en: {DB_PATH}")

if __name__ == "__main__":
    inicializar_sqlite_spatial()