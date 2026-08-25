import ezdxf
import pandas as pd
import time

def analizar_plano(ruta_archivo):
    print(f"⏳ Abriendo y leyendo {ruta_archivo}...")
    print("Esto puede tomar unos segundos debido al tamaño del archivo DXF...")
    
    inicio = time.time()
    
    try:
        # Leer el archivo DXF
        doc = ezdxf.readfile(ruta_archivo)
        msp = doc.modelspace() # Acceder al Espacio Modelo
        
        datos_entidades = []
        
        # Escanear cada entidad en el plano
        for entity in msp:
            datos_entidades.append({
                "Tipo_Entidad": entity.dxftype(),
                "Capa": entity.dxf.layer,
            })
            
        # Convertir la lista a una tabla (DataFrame) de Pandas
        df = pd.DataFrame(datos_entidades)
        
        tiempo_total = round(time.time() - inicio, 2)
        print(f"\n✅ ¡Lectura completada en {tiempo_total} segundos!")
        print(f"Total de entidades extraídas: {len(df):,}")
        
        # Agrupar y contar por Capa y Tipo de Entidad
        if not df.empty:
            resumen = df.groupby(['Capa', 'Tipo_Entidad']).size().reset_index(name='Cantidad')
            # Ordenar para ver las capas con más elementos primero
            resumen = resumen.sort_values(by='Cantidad', ascending=False)
            
            print("\n📊 Top 15 Capas con más elementos en el plano:")
            print(resumen.head(15).to_string(index=False))
        else:
            print("El espacio modelo parece estar vacío.")
            
    except IOError:
        print(f"❌ Error: No se encontró el archivo '{ruta_archivo}'. Revisa el nombre.")
    except ezdxf.DXFStructureError:
        print(f"❌ Error: El archivo está corrupto o no es un DXF válido.")

if __name__ == "__main__":
    # ¡OJO AQUÍ! Cambia "plano_prueba.dxf" por el nombre exacto de tu archivo si le pusiste otro
    nombre_de_tu_archivo = "PLANO GENERAL GUARNICIÓN EXTERIOR.dxf" 
    analizar_plano(nombre_de_tu_archivo)