import sys
import sqlite3
import ezdxf
import pandas as pd
import numpy as np
import chromadb
import langchain

def main():
    print("==================================================")
    print("🚀 Servidor de Análisis CAD/BIM Inicializado")
    print("==================================================")
    print(f"Versión de Python: {sys.version.split()[0]}")
    print(f"Ezdxf: {ezdxf.__version__}")
    print(f"Pandas: {pd.__version__}")
    
    # Prueba de conexión a la base de datos local
    try:
        conn = sqlite3.connect('planos_data.db')
        print("✅ Conexión a SQLite (planos_data.db) establecida con éxito.")
        conn.close()
    except Exception as e:
        print(f"❌ Error conectando a SQLite: {e}")

if __name__ == "__main__":
    main()