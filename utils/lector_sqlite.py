import sqlite3
import pandas as pd

def revisar_base_datos():
    print("==================================================")
    print("🗄️ Lector de Base de Datos SQLite Iniciado")
    print("==================================================")
    
    try:
        # 1. Nos conectamos a la base de datos
        conn = sqlite3.connect('planos_data.db')
        
        # 2. Le preguntamos a SQLite qué tablas tiene guardadas
        query_tablas = "SELECT name FROM sqlite_master WHERE type='table';"
        tablas = pd.read_sql_query(query_tablas, conn)
        nombres_tablas = tablas['name'].tolist()
        
        print(f"📊 Se encontraron {len(nombres_tablas)} tablas guardadas.\n")
        print("Muestra de las primeras 15 tablas:")
        for nombre in nombres_tablas[:15]:
            print(f" - {nombre}")
            
        print("\n" + "-"*50)
        
        # 3. Vamos a inspeccionar la de columnas (o la primera que encuentre si le cambiaste el nombre)
        tabla_prueba = "capa_arq_columnas" 
        
        if tabla_prueba in nombres_tablas:
            print(f"🔍 Abriendo los registros de la tabla: '{tabla_prueba}'...")
            df = pd.read_sql_query(f"SELECT * FROM {tabla_prueba}", conn)
            
            print(f"Total de elementos en esta capa: {len(df)}")
            print("Muestra de los primeros 10 registros:")
            pd.set_option('display.max_colwidth', None)
            print(df.head(10).to_string(index=False))
        else:
            print(f"⚠️ La tabla '{tabla_prueba}' no está. Abriendo '{nombres_tablas[0]}' en su lugar...")
            df = pd.read_sql_query(f"SELECT * FROM {nombres_tablas[0]}", conn)
            print(df.head(5).to_string(index=False))
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error al leer la base de datos: {e}")

if __name__ == "__main__":
    revisar_base_datos()