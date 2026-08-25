import ezdxf
import pandas as pd
import math
import sqlite3  # <-- Añadimos el motor de base de datos

def extraer_columnas(ruta_archivo, capa_objetivo):
    print(f"🔍 Escaneando columnas en la capa: '{capa_objetivo}'...")
    
    try:
        doc = ezdxf.readfile(ruta_archivo)
        msp = doc.modelspace()
        
        datos_columnas = []
        
        for entity in msp:
            if entity.dxf.layer.lower() == capa_objetivo.lower():
                tipo = entity.dxftype()
                
                if tipo == 'LWPOLYLINE':
                    vertices = [(round(p[0], 2), round(p[1], 2)) for p in entity.get_points('xy')]
                    datos_columnas.append({
                        "Tipo_Entidad": tipo,
                        "Detalle": f"Polígono ({len(vertices)} lados)",
                        "Ubicación_Coordenadas": str(vertices[:4])
                    })
                elif tipo == 'INSERT':
                    pto = entity.dxf.insert
                    datos_columnas.append({
                        "Tipo_Entidad": tipo,
                        "Detalle": f"Bloque: {entity.dxf.name}",
                        "Ubicación_Coordenadas": f"X: {round(pto.x, 2)}, Y: {round(pto.y, 2)}"
                    })
                elif tipo == 'CIRCLE':
                    centro = entity.dxf.center
                    datos_columnas.append({
                        "Tipo_Entidad": tipo,
                        "Detalle": f"Radio: {round(entity.dxf.radius, 2)}",
                        "Ubicación_Coordenadas": f"Centro X: {round(centro.x, 2)}, Y: {round(centro.y, 2)}"
                    })
                elif tipo == 'LINE':
                    inicio = entity.dxf.start
                    fin = entity.dxf.end
                    longitud = math.sqrt((fin.x - inicio.x)**2 + (fin.y - inicio.y)**2)
                    
                    datos_columnas.append({
                        "Tipo_Entidad": tipo,
                        "Detalle": f"Línea (Longitud: {round(longitud, 2)})",
                        "Ubicación_Coordenadas": f"De ({round(inicio.x, 2)}, {round(inicio.y, 2)}) a ({round(fin.x, 2)}, {round(fin.y, 2)})"
                    })
                    
        df = pd.DataFrame(datos_columnas)
        
        if not df.empty:
            print(f"\n✅ ¡Éxito! Se encontraron {len(df)} elementos en la capa '{capa_objetivo}'.")
            
            # --- NUEVA SECCIÓN: Guardar en SQLite ---
            print("💾 Guardando datos en la base de datos (planos_data.db)...")
            try:
                conn = sqlite3.connect('planos_data.db')
                # if_exists='replace' sobreescribe la tabla si vuelves a correr el script
                df.to_sql('geometria_columnas', conn, if_exists='replace', index=False)
                conn.close()
                print("✅ ¡Datos guardados exitosamente como tabla 'geometria_columnas'!")
            except Exception as e:
                print(f"❌ Error al guardar en base de datos: {e}")
            # ----------------------------------------
            
            print("\n📊 Muestra de las primeras 5 entidades:")
            pd.set_option('display.max_colwidth', None)
            print(df.head(5).to_string(index=False))
        else:
            print(f"❌ La capa '{capa_objetivo}' existe, pero parece no tener geometría compatible.")
            
    except Exception as e:
        print(f"❌ Error al procesar: {e}")

if __name__ == "__main__":
    nombre_archivo = "plano_prueba.dxf" 
    extraer_columnas(nombre_archivo, "arq_columnas")