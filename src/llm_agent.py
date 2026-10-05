# Importamos la integración correcta y actualizada de Ollama para LangChain
from langchain_ollama import ChatOllama

# Importamos las clases para manejar los mensajes del chat (Sistema, Humano y Herramienta)
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

# Importamos el decorador @tool que convierte una función normal en una herramienta de IA
from langchain_core.tools import tool
import sqlite3
# Importamos Pydantic para crear el "Guardrail" (el molde estricto de validación)
from pydantic import BaseModel, Field
from typing import Optional
import json

import chromadb
from chromadb.utils import embedding_functions

# =====================================================================
# 1. EL GUARDRAIL (ESQUEMA ESTRICTO DE PYDANTIC)
# =====================================================================
# Esta clase obliga al LLM a estructurar su respuesta con estos campos exactos.
# Si el LLM intenta inventar datos o dejar el eje primario vacío, Pydantic lo bloqueará.
class CalculoDistanciaSchema(BaseModel):
    elemento_objetivo: str = Field(description="El nombre del elemento MEP o arquitectónico. Ej: 'Tubo PVC', 'Muro'.")
    eje_referencia_1: str = Field(description="El eje primario cercano. Obligatorio. Ej: 'A', '4'.")
    eje_referencia_2: Optional[str] = Field(description="El eje secundario si es una intersección. Ej: '1', 'B'.")

class ExplorarPlanoSchema(BaseModel):
    tipo_informacion: str = Field(description="Qué buscar. Usa 'ejes' para textos/referencias o 'capas' para elementos geométricos.")

# =====================================================================
# 2. DEFINICIÓN DE LA HERRAMIENTAS
# =====================================================================
# El decorador @tool le dice a LangChain: "Esta función puede ser usada por el LLM".
# Le pasamos args_schema=CalculoDistanciaSchema para que use nuestro molde estricto[cite: 1].
@tool(args_schema=CalculoDistanciaSchema)
def herramienta_calcular_distancia(elemento_objetivo: str, eje_referencia_1: str, eje_referencia_2: str = None):
    """Calcula la distancia de un elemento en el plano. Usa esta herramienta SIEMPRE que el usuario pregunte por distancias, ubicaciones o cruces."""
    
    db_path = "data/db_sqlite/planos_geometria.db"
    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    conn.load_extension('mod_spatialite')
    cursor = conn.cursor()

    try:
        if eje_referencia_2:
            # Validación estricta: Asegurar que AMBOS textos existen antes de promediar o cruzar
            cursor.execute("""
                SELECT coord_x, coord_y 
                FROM entidades_textuales 
                WHERE contenido IN (?, ?)
            """, (eje_referencia_1, eje_referencia_2))
            
            puntos = cursor.fetchall()
            
            if len(puntos) != 2:
                return f"Base de datos informa: No se encontraron ambos ejes ('{eje_referencia_1}' y '{eje_referencia_2}') para calcular la intersección."
            
            # Nota Topográfica: Este sigue siendo el promedio de los textos. 
            # Lo ideal aquí es cambiar la query para usar ST_Intersection sobre las líneas de los ejes.
            x_origen = (puntos[0][0] + puntos[1][0]) / 2.0
            y_origen = (puntos[0][1] + puntos[1][1]) / 2.0
            
        else:
            cursor.execute("""
                SELECT coord_x, coord_y 
                FROM entidades_textuales 
                WHERE contenido = ? LIMIT 1
            """, (eje_referencia_1,))
            
            coordenadas_origen = cursor.fetchone()
            
            if not coordenadas_origen:
                return f"Base de datos informa: No se encontró el eje de referencia '{eje_referencia_1}' en el plano actual."
                
            x_origen, y_origen = coordenadas_origen

        termino_busqueda = f"%{elemento_objetivo.upper()}%"
        
        cursor.execute("""
            SELECT 
                capa_origen,
                Distance(MakePoint(?, ?, -1), geometria) AS distancia_m
            FROM entidades_geometricas
            WHERE UPPER(capa_origen) LIKE ?
            ORDER BY distancia_m ASC
            LIMIT 1
        """, (x_origen, y_origen, termino_busqueda))
        
        resultado = cursor.fetchone()
        
    except sqlite3.OperationalError as e:
        return f"Error interno en base de datos espacial: {str(e)}"
    finally:
        conn.close()

    if resultado:
        capa_encontrada, distancia = resultado
        referencia_txt = f"{eje_referencia_1} y {eje_referencia_2}" if eje_referencia_2 else eje_referencia_1
        return (f"Base de datos informa: El elemento '{capa_encontrada}' más cercano a la referencia "
                f"('{referencia_txt}') se encuentra a {distancia:.3f} metros.")
    else:
        return f"Base de datos informa: No se encontraron geometrías asociadas a '{elemento_objetivo}' en este plano."


@tool(args_schema=ExplorarPlanoSchema)
def herramienta_explorar_plano(tipo_informacion: str):
    """Usa esta herramienta SOLO cuando el usuario pregunte de manera general qué ejes, elementos o capas existen en el plano, sin pedir cálculos de distancia."""
    
    db_path = "data/db_sqlite/planos_geometria.db"
    import sqlite3
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        if tipo_informacion == 'ejes':
            # Extraemos los textos únicos (burbujas de ejes)
            cursor.execute("SELECT DISTINCT contenido FROM entidades_textuales LIMIT 50")
            resultados = [row[0] for row in cursor.fetchall() if row[0]]
            if resultados:
                return f"Base de datos informa: Los ejes/textos disponibles en el plano son: {', '.join(resultados)}"
            return "Base de datos informa: No se encontraron textos ni ejes."
            
        else:
            # Extraemos las capas únicas (elementos)
            cursor.execute("SELECT DISTINCT capa_origen FROM entidades_geometricas LIMIT 50")
            resultados = [row[0] for row in cursor.fetchall() if row[0]]
            if resultados:
                return f"Base de datos informa: Las capas/elementos disponibles son: {', '.join(resultados)}"
            return "Base de datos informa: No se encontraron elementos geométricos."
            
    except sqlite3.Error as e:
        return f"Error de base de datos: {e}"
    finally:
        conn.close()

class ConsultaEspecificacionesSchema(BaseModel):
    termino_busqueda: str = Field(description="El concepto, material o área a buscar en las notas del plano. Ej: 'espesor muro', 'CTO. QA EQUIPOS'.")

@tool(args_schema=ConsultaEspecificacionesSchema)
def herramienta_consultar_especificaciones(termino_busqueda: str):
    """Busca especificaciones técnicas, materiales, espesores o notas asociadas a un área en el plano."""
    try:
        # Conectamos con ChromaDB usando el modelo de embeddings local
        ollama_ef = embedding_functions.OllamaEmbeddingFunction(
            url="http://localhost:11434/api/embeddings",
            model_name="nomic-embed-text"
        )
        client = chromadb.PersistentClient(path="data/db_chroma")
        coleccion = client.get_collection(name="notas_especificaciones", embedding_function=ollama_ef)
        
        # Buscamos los 3 textos más relevantes por similitud semántica
        resultados = coleccion.query(
            query_texts=[termino_busqueda],
            n_results=3
        )
        
        if resultados['documents'] and resultados['documents'][0]:
            textos_encontrados = resultados['documents'][0]
            return f"Base de datos semántica informa. Notas encontradas que podrían responder la duda: {'; '.join(textos_encontrados)}"
        return "No se encontraron especificaciones relacionadas a ese término en el plano."
    except Exception as e:
        return f"Error al consultar el motor semántico: {e}"

# =====================================================================
# 3. INICIALIZACIÓN DEL LLM
# =====================================================================
def inicializar_agente_langchain():
    # Instanciamos el modelo local exacto que tienes descargado (qwen2.5-coder:7b)[cite: 1].
    # temperature=0.1 evita que el modelo se ponga creativo e invente cosas.
    llm = ChatOllama(
        model="qwen2.5-coder:7b",
        temperature=0.1, 
    )
    
    # .bind_tools() es la magia: "amarra" la herramienta al modelo. 
    # Ahora el LLM sabe que tiene esta función disponible en su arsenal.
    llm_con_herramientas = llm.bind_tools([herramienta_calcular_distancia, herramienta_explorar_plano, herramienta_consultar_especificaciones])
    
    return llm_con_herramientas

# =====================================================================
# 4. EL SYSTEM PROMPT ESTRICTO
# =====================================================================
SYSTEM_PROMPT = """Eres un experto topógrafo y supervisor de obra. Tu tarea es asistir en la revisión técnica de planos CAD mediante herramientas conectadas a bases de datos.

Reglas Absolutas:
1. Responde con un tono directo, respetuoso y de colega de campo, utilizando el término 'Inge'.
2. PROHIBIDO EXPRESAMENTE escribir o mostrar código fuente, consultas SQL, estructuras JSON o Tracebacks en tu respuesta.
3. INSTRUCCIONES DE HERRAMIENTAS:
   - Si el usuario pregunta qué ejes, textos o capas existen en general, ESTÁS OBLIGADO a usar 'herramienta_explorar_plano'.
   - Si el usuario pide ubicaciones o distancias, usa 'herramienta_calcular_distancia'.
   - Si el usuario pide detalles constructivos, materiales o espesores, ESTÁS OBLIGADO a usar 'herramienta_consultar_especificaciones'.
4. REGLA DE RECHAZO: SOLO si intentas calcular una distancia y te falta un eje de referencia, responde exactamente así: 'Inge, necesito una referencia espacial más precisa. ¿Me confirma cerca de qué eje o intersección estamos revisando para calcularlo correcto?' ¡No uses esta frase si solo te piden explorar los ejes disponibles!"""
# =====================================================================
# 5. EL BUCLE DE LA TERMINAL (PRUEBA EN VIVO)
# =====================================================================
def chat_terminal():
    # Arrancamos el cerebro y cargamos las herramientas
    llm = inicializar_agente_langchain()
    
    # Creamos la memoria a corto plazo, iniciando con las instrucciones del sistema
    historial_mensajes = [SystemMessage(content=SYSTEM_PROMPT)]
    
    print("--- OmniCAD Terminal Test (Con Tool Calling) ---")
    print("Escribe 'salir' para terminar.\n")
    
    while True:
        # 1. Capturamos lo que escribes
        user_input = input("Tú: ")
        if user_input.lower() in ['salir', 'exit', 'quit']:
            break
            
        # 2. Agregamos tu mensaje al historial
        historial_mensajes.append(HumanMessage(content=user_input))
        
        # 3. Le mandamos todo el historial al LLM
        respuesta = llm.invoke(historial_mensajes)
        
        # 4. EVALUAMOS LA RESPUESTA DEL LLM:
        # ¿El LLM decidió usar una herramienta (es decir, detectó un elemento y un eje)?
        if respuesta.tool_calls:
            # Iteramos sobre las herramientas que el LLM decidió llamar
            for tool_call in respuesta.tool_calls:
                # Extraemos el nombre de la herramienta y los argumentos que el LLM identificó
                nombre_herramienta = tool_call["name"]
                argumentos = tool_call["args"]
                
                # Ejecutamos la función de Python pasándole los argumentos extraídos por la IA
                resultado_herramienta = herramienta_calcular_distancia.invoke(argumentos)
                
                # Le informamos a LangChain el resultado de la herramienta agregando un ToolMessage
                historial_mensajes.append(respuesta) # Guardamos la intención de llamar la herramienta
                historial_mensajes.append(ToolMessage(
                    tool_call_id=tool_call["id"],
                    name=nombre_herramienta,
                    content=resultado_herramienta
                ))
                
                # Volvemos a llamar al LLM para que lea el resultado de la herramienta y te lo explique en lenguaje natural
                respuesta_final = llm.invoke(historial_mensajes)
                print(f"\nOmniCAD: {respuesta_final.content}\n")
                
                # Guardamos la respuesta final en la memoria
                historial_mensajes.append(respuesta_final)
                
        # ¿O el LLM decidió responder normalmente (ej. le faltan datos o es solo una charla)?
        else:
            print(f"\nOmniCAD: {respuesta.content}\n")
            historial_mensajes.append(respuesta)

if __name__ == "__main__":
    chat_terminal()