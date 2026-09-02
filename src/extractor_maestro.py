import ezdxf
import pandas as pd
import math
import sqlite3
import re
import time

def limpiar_nombre_tabla(nombre):
    # Reemplaza espacios y caracteres raros por guiones bajos para que SQLite no llore
    limpio = re.sub(r'\W+', '_', nombre.lower())
    # Le ponemos un prefijo para identificar fácil las tablas de AutoCAD
    return f"capa_{limpio}"

def extractor_maestro(ruta_archivo):
    print("==================================================")
    print(f"🚀 Iniciando Extractor Maestro: {ruta_archivo}")
    print("==================================================")
    
    inicio = time.time()
    
    try:
        doc = ezdxf.readfile(ruta_archivo)
        msp = doc.modelspace()
        
        # Diccionario para agrupar todo. Formato: {'nombre_capa': [lista_de_datos]}
        datos_por_capa = {}
        
        print("🔍 Escaneando geometría del plano...")
        
        for entity in msp:
            capa = entity.dxf.layer
            tipo = entity.dxftype()
            
            # Si es la primera vez que vemos esta capa, le creamos su lista
            if capa not in datos_por_capa:
                datos_por_capa[capa] = []
                
            info = {"Tipo_Entidad": tipo, "Detalle": "", "Coordenadas_Ubicacion": ""}
            
            # Extraemos la carnita según el tipo
            if tipo == 'LWPOLYLINE':
                vertices = [(round(p[0], 2), round(p[1], 2)) for p in entity.get_points('xy')]
                info["Detalle"] = f"Polígono ({len(vertices)} lados)"
                info["Coordenadas_Ubicacion"] = str(vertices[:4])
            elif tipo == 'INSERT':
                pto = entity.dxf.insert
                info["Detalle"] = f"Bloque: {entity.dxf.name}"
                info["Coordenadas_Ubicacion"] = f"X: {round(pto.x, 2)}, Y: {round(pto.y, 2)}"
            elif tipo == 'CIRCLE':
                centro = entity.dxf.center
                info["Detalle"] = f"Radio: {round(entity.dxf.radius, 2)}"
                info["Coordenadas_Ubicacion"] = f"Centro X: {round(centro.x, 2)}, Y: {round(centro.y, 2)}"
            elif tipo == 'LINE':
                ini = entity.dxf.start
                fin = entity.dxf.end
                longitud = math.sqrt((fin.x - ini.x)**2 + (fin.y - ini.y)**2)
                info["Detalle"] = f"Línea (L: {round(longitud, 2)})"
                info["Coordenadas_Ubicacion"] = f"De ({round(ini.x, 2)}, {round(ini.y, 2)}) a ({round(fin.x, 2)}, {round(fin.y, 2)})"
            else:
                info["Detalle"] = "Otro elemento"
                info["Coordenadas_Ubicacion"] = "N/A"
                
            datos_por_capa[capa].append(info)
            
        print("💾 Procesamiento terminado. Mandando a la base de datos...")
        
        # Conectamos a SQLite
        conn = sqlite3.connect('planos_data.db')
        tablas_creadas = 0
        
        for capa, datos in datos_por_capa.items():
            df = pd.DataFrame(datos)
            
            # Filtramos para no guardar capas vacías por error
            if not df.empty:
                nombre_tabla = limpiar_nombre_tabla(capa)
                df.to_sql(nombre_tabla, conn, if_exists='replace', index=False)
                tablas_creadas += 1
                
        conn.close()
        tiempo_total = round(time.time() - inicio, 2)
        
        print("\n✅ ¡Misión Cumplida!")
        print(f"⏱️ Tiempo total: {tiempo_total} segundos")
        print(f"📂 Total de tablas independientes creadas en SQLite: {tablas_creadas}")
        
    except Exception as e:
        print(f"❌ Error catastrófico: {e}")

if __name__ == "__main__":
    nombre_archivo = "plano_prueba.dxf" 
    extractor_maestro(nombre_archivo)