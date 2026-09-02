import ezdxf
from ezdxf import DXFStructureError
import uuid
from collections import Counter

def extraer_datos_dxf(ruta_archivo, id_plano_uuid):
    """
    Desensambla un archivo DXF reteniendo solo información espacial y geométrica vital.
    Resuelve entidades anidadas y serializa coordenadas para bases de datos relacionales.
    """
    try:
        doc = ezdxf.readfile(ruta_archivo)
        msp = doc.modelspace()
    except IOError:
        print(f"Error crítico: No se pudo leer el archivo en disco: {ruta_archivo}")
        return None, None
    except dxferror.DXFStructureError:
        print(f"Error crítico: El archivo {ruta_archivo} tiene una estructura DXF corrupta o inválida.")
        return None, None

    entidades_textuales = []
    entidades_geometricas = []

    # Protocolo de blindaje: Filtro estricto de entidades
    lista_negra = {'HATCH', 'DIMENSION', 'VIEWPORT', 'IMAGE'}
    lista_blanca = {'TEXT', 'MTEXT', 'LINE', 'LWPOLYLINE', 'INSERT'}

# Protocolo de blindaje: Filtro estricto de entidades y capas
    lista_negra_entidades = {'HATCH', 'DIMENSION', 'VIEWPORT', 'IMAGE'}
    lista_blanca_entidades = {'TEXT', 'MTEXT', 'LINE', 'LWPOLYLINE', 'INSERT'}
    
    # El francotirador: Agregamos MOBILIARIO y las capas IFC basura
    palabras_basura_capas = [
        'MUEBLE', 'MOBILIARIO', 'VEGETACION', 'ARBOL', 'VEHICULO', 'PERSONA', 
        'IFCANNOTATION', 'IFCELECTRICAPPLIANCE', 'IFCBUILDINGELEMENTPROXY',
        'ENTORNO', 'HATCH', 'SOMBRA', 'DECORACION'
    ]

    def procesar_entidad(entity):
        tipo = entity.dxftype()

        # 1. Filtro primario por tipo de entidad
        if tipo in lista_negra_entidades:
            return
            
        # 2. Extraer capa y aplicar filtro ANTES de abrir bloques
        capa = entity.dxf.layer if hasattr(entity.dxf, 'layer') else 'Desconocida'
        capa_upper = capa.upper()
        
        if any(palabra in capa_upper for palabra in palabras_basura_capas):
            return  # Si la capa es basura, abortamos inmediatamente
            
        # 3. Desempaquetar bloques (ahora sí, de forma segura)
        if tipo == 'INSERT':
            for virtual_entity in entity.virtual_entities():
                procesar_entidad(virtual_entity)
            return

        # 4. Retener elementos de valor espacial/matemático
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
                datos_geometria = None
                
                if tipo == 'LINE':
                    datos_geometria = {
                        'start': (entity.dxf.start[0], entity.dxf.start[1]),
                        'end': (entity.dxf.end[0], entity.dxf.end[1])
                    }
                elif tipo == 'LWPOLYLINE':
                    puntos = [(punto[0], punto[1]) for punto in entity.get_points()]
                    datos_geometria = {'vertices': puntos}

                if datos_geometria:
                    entidades_geometricas.append({
                        'id_geometria': str(uuid.uuid4()),
                        'id_plano': id_plano_uuid,
                        'capa_origen': capa,
                        'tipo_entidad': tipo,
                        'geometria': datos_geometria
                    })

    # Iniciar el escaneo del Modelspace
    for entity in msp:
        procesar_entidad(entity)

    return entidades_textuales, entidades_geometricas

if __name__ == "__main__":
    # Simulación de ingesta de un plano real
    id_prueba = str(uuid.uuid4())
    
    # IMPORTANTE: Reemplaza esto con el nombre de tu nuevo archivo
    ruta_plano = "plano_prueba.dxf" 
    
    print(f"Iniciando extracción de {ruta_plano}...")
    textos, geometrias = extraer_datos_dxf(ruta_plano, id_prueba)
    
    if textos is not None:
        print("\n--- RESULTADOS DE EXTRACCIÓN ---")
        print(f"ID del Plano: {id_prueba}")
        print(f"Textos recuperados (Ejes, notas, cotas puras): {len(textos)}")
        print(f"Geometrías retenidas (Líneas, polilíneas, bloques explotados): {len(geometrias)}")
        print("--------------------------------")

if geometrias:
        print("\n--- LAS 5 CAPAS MÁS ATASCADAS ---")
        contador_capas = Counter([g['capa_origen'] for g in geometrias])
        for capa, cantidad in contador_capas.most_common(5):
            print(f"Capa: '{capa}' -> {cantidad} elementos")

