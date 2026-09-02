# Importamos la integración correcta y actualizada de Ollama para LangChain
from langchain_ollama import ChatOllama

# Importamos las clases para manejar los mensajes del chat (Sistema, Humano y Herramienta)
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

# Importamos el decorador @tool que convierte una función normal en una herramienta de IA
from langchain_core.tools import tool

# Importamos Pydantic para crear el "Guardrail" (el molde estricto de validación)
from pydantic import BaseModel, Field
from typing import Optional
import json

# =====================================================================
# 1. EL GUARDRAIL (ESQUEMA ESTRICTO DE PYDANTIC)
# =====================================================================
# Esta clase obliga al LLM a estructurar su respuesta con estos campos exactos.
# Si el LLM intenta inventar datos o dejar el eje primario vacío, Pydantic lo bloqueará.
class CalculoDistanciaSchema(BaseModel):
    elemento_objetivo: str = Field(description="El nombre del elemento MEP o arquitectónico. Ej: 'Tubo PVC', 'Muro'.")
    eje_referencia_1: str = Field(description="El eje primario cercano. Obligatorio. Ej: 'A', '4'.")
    eje_referencia_2: Optional[str] = Field(description="El eje secundario si es una intersección. Ej: '1', 'B'.")

# =====================================================================
# 2. DEFINICIÓN DE LA HERRAMIENTA
# =====================================================================
# El decorador @tool le dice a LangChain: "Esta función puede ser usada por el LLM".
# Le pasamos args_schema=CalculoDistanciaSchema para que use nuestro molde estricto[cite: 1].
@tool(args_schema=CalculoDistanciaSchema)
def herramienta_calcular_distancia(elemento_objetivo: str, eje_referencia_1: str, eje_referencia_2: str = None):
    """Calcula la distancia de un elemento en el plano. Usa esta herramienta SIEMPRE que el usuario pregunte por distancias, ubicaciones o cruces."""
    
    # Esta es una simulación (Mock). En la Etapa 2, aquí conectaremos SQLite/SpatiaLite[cite: 1].
    print("\n[⚡ LOG INTERNO: El Cerebro Dual ha activado la herramienta espacial ⚡]")
    print(f" -> Buscando: {elemento_objetivo}")
    print(f" -> Eje Primario: {eje_referencia_1}")
    if eje_referencia_2:
        print(f" -> Eje Secundario: {eje_referencia_2}")
    
    # Retornamos un texto simulando lo que devolvería la base de datos
    return f"Base de datos informa: El {elemento_objetivo} cerca del eje {eje_referencia_1} está a 2.5 metros."

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
    llm_con_herramientas = llm.bind_tools([herramienta_calcular_distancia])
    
    return llm_con_herramientas

# =====================================================================
# 4. EL SYSTEM PROMPT ESTRICTO
# =====================================================================
# Esta es la personalidad inamovible y las reglas de seguridad[cite: 1].
SYSTEM_PROMPT = """Eres un experto topógrafo y supervisor de obra. Tu tarea es asistir en la revisión técnica de planos CAD mediante herramientas conectadas a bases de datos.

Reglas Absolutas:
1. Responde con un tono directo, respetuoso y de colega de campo, utilizando el término 'Inge'.
2. JAMÁS muestres estructuras JSON, código Python, consultas SQL ni mensajes de error del sistema (Tracebacks).
3. Si una herramienta te rechaza la consulta por falta de datos de referencia (ej. el usuario pide buscar 'un muro' pero no especifica un eje), no adivines. Debes responder exactamente así: 'Inge, necesito una referencia espacial más precisa. ¿Me confirma cerca de qué eje o intersección estamos revisando para calcularlo correcto?'"""

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