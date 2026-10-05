import ezdxf
from ezdxf import DXFStructureError
import uuid
from shapely.geometry import LineString

def extraer_datos_dxf(ruta_archivo, id_plano_uuid):
    """
    Desensambla un archivo DXF reteniendo solo información espacial y geométrica vital.
    Resuelve entidades anidadas y serializa coordenadas a formato WKB Hexadecimal.
    """
    try:
        doc = ezdxf.readfile(ruta_archivo)
        msp = doc.modelspace()
    except IOError:
        print(f"Error crítico: No se pudo leer el archivo en disco: {ruta_archivo}")
        return None, None
    except DXFStructureError:
        print(f"Error crítico: El archivo {ruta_archivo} tiene una estructura DXF corrupta o inválida.")
        return None, None

    entidades_textuales = []
    entidades_geometricas = []

    lista_negra_entidades = {'HATCH', 'DIMENSION', 'VIEWPORT', 'IMAGE'}
    lista_blanca_entidades = {'TEXT', 'MTEXT', 'LINE', 'LWPOLYLINE', 'INSERT'}
    
    palabras_basura_capas = [
        'MUEBLE', 'MOBILIARIO', 'VEGETACION', 'ARBOL', 'VEHICULO', 'PERSONA', 
        'IFCANNOTATION', 'IFCELECTRICAPPLIANCE', 'IFCBUILDINGELEMENTPROXY',
        'ENTORNO', 'HATCH', 'SOMBRA', 'DECORACION', 'CARPINTERIA', 'FURNITURE', 
        'PISO', 'CANCELERIA'
    ]

    def procesar_entidad(entity):
        tipo = entity.dxftype()

        if tipo in lista_negra_entidades:
            return
            
        capa = entity.dxf.layer if hasattr(entity.dxf, 'layer') else 'Desconocida'
        capa_upper = capa.upper()
        
        if any(palabra in capa_upper for palabra in palabras_basura_capas):
            return  
            
        if tipo == 'INSERT':
            for virtual_entity in entity.virtual_entities():
                procesar_entidad(virtual_entity)
            return

        if tipo in lista_blanca_entidades:
            if tipo in {'TEXT', 'MTEXT'}:
                texto_contenido = entity.dxf.text if tipo == 'TEXT' else entity.plain_text()
                punto_ins = entity.dxf.insert
                
                if texto_contenido and texto_contenido.strip():
                    entidades_textuales.append({
                        'id_texto': str(uuid.uuid4()),
                        'id_plano': id_plano_uuid,
                        'capa_origen': capa,
                        'contenido': texto_contenido.strip(),
                        'coord_x': punto_ins[0],
                        'coord_y': punto_ins[1]
                    })
            else:
                geometria_wkb = None
                
                # Traducción a Shapely y exportación a WKB Hexadecimal
                if tipo == 'LINE':
                    start = (entity.dxf.start[0], entity.dxf.start[1])
                    end = (entity.dxf.end[0], entity.dxf.end[1])
                    linea = LineString([start, end])
                    geometria_wkb = linea.wkb_hex
                    
                elif tipo == 'LWPOLYLINE':
                    puntos = [(punto[0], punto[1]) for punto in entity.get_points()]
                    if len(puntos) >= 2:  # Shapely requiere al menos 2 puntos para un LineString
                        polilinea = LineString(puntos)
                        geometria_wkb = polilinea.wkb_hex

                if geometria_wkb:
                    entidades_geometricas.append({
                        'id_geometria': str(uuid.uuid4()),
                        'id_plano': id_plano_uuid,
                        'capa_origen': capa,
                        'tipo_entidad': tipo,
                        'geometria_wkb': geometria_wkb  # WKB listo para SpatiaLite
                    })

    for entity in msp:
        procesar_entidad(entity)

    return entidades_textuales, entidades_geometricas

if __name__ == "__main__":
    id_prueba = str(uuid.uuid4())
    ruta_plano = "data/temp_dxf/plano_prueba.dxf" 
    
    print(f"Iniciando extracción y serialización WKB de {ruta_plano}...")
    textos, geometrias = extraer_datos_dxf(ruta_plano, id_prueba)
    
    if textos is not None:
        print("\n--- RESULTADOS DE EXTRACCIÓN ---")
        print(f"ID del Plano: {id_prueba}")
        print(f"Textos recuperados: {len(textos)}")
        print(f"Geometrías convertidas a WKB: {len(geometrias)}")
        # Para comprobar que la serialización funciona
        if geometrias:
            print(f"\nMuestra de un vector serializado (Hex WKB):\n{geometrias[0]['geometria_wkb'][:60]}...")