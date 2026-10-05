import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from src.llm_agent import inicializar_agente_langchain, herramienta_calcular_distancia, herramienta_explorar_plano, SYSTEM_PROMPT

# Configuración de la página web
st.set_page_config(page_title="OmniCAD | Visor Espacial", page_icon="🏗️", layout="centered")

# Diccionario para enrutar las herramientas dinámicamente
from src.llm_agent import inicializar_agente_langchain, herramienta_calcular_distancia, herramienta_explorar_plano, herramienta_consultar_especificaciones, SYSTEM_PROMPT

mapa_herramientas = {
    "herramienta_calcular_distancia": herramienta_calcular_distancia,
    "herramienta_explorar_plano": herramienta_explorar_plano,
    "herramienta_consultar_especificaciones": herramienta_consultar_especificaciones
}

# =====================================================================
# 1. VARIABLES DE ESTADO ESTRICTAS (Protección contra recargas)
# =====================================================================
if "autenticado" not in st.session_state:
    st.session_state.autenticado = True # Por ahora lo dejamos True para la demo en oficina

if "historial_mensajes" not in st.session_state:
    # Iniciamos la memoria inyectando el Guardrail y la personalidad del sistema
    st.session_state.historial_mensajes = [SystemMessage(content=SYSTEM_PROMPT)]

# Cacheamos el modelo en la VRAM de la RTX para que no se recargue en cada mensaje
@st.cache_resource
def cargar_agente():
    return inicializar_agente_langchain()

if "agente_cargado" not in st.session_state:
    st.session_state.agente_cargado = cargar_agente()

llm = st.session_state.agente_cargado

# =====================================================================
# 2. INTERFAZ GRÁFICA (Frontend)
# =====================================================================
st.title("OmniCAD / CAD-Check 🏗️")
st.caption("Asistente Inteligente de Análisis de Planos - Prototipo V1")
st.divider()

# Dibujar los mensajes anteriores en la pantalla
for msg in st.session_state.historial_mensajes:
    if isinstance(msg, HumanMessage):
        st.chat_message("user", avatar="👷").write(msg.content)
    elif isinstance(msg, AIMessage) and msg.content:
        # MAGIA: Filtramos el mensaje si empieza con llave y parece un llamado de herramienta
        if not (msg.content.strip().startswith('{') and '"name":' in msg.content):
            st.chat_message("assistant", avatar="🤖").write(msg.content)

# =====================================================================
# 3. MOTOR DE CHAT Y TOOL CALLING
# =====================================================================
if prompt := st.chat_input("Ej. ¿A qué distancia está el tubo PVC del cruce A y 1?"):
    
    # 3.1 Imprimir y guardar mensaje del usuario
    st.chat_message("user", avatar="👷").write(prompt)
    st.session_state.historial_mensajes.append(HumanMessage(content=prompt))

    # 3.2 Procesamiento de la IA
    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Analizando base de datos espacial..."):
            
            # El LLM decide qué hacer con el historial
            respuesta = llm.invoke(st.session_state.historial_mensajes)
            
            # CASO A: El LLM detectó que debe usar la herramienta
            if respuesta.tool_calls:
                for tool_call in respuesta.tool_calls:
                    nombre_herramienta = tool_call["name"]
                    argumentos = tool_call["args"]
                    
                    # MAGIA NUEVA: Busca qué herramienta usar en el diccionario y la ejecuta
                    if nombre_herramienta in mapa_herramientas:
                        herramienta_a_usar = mapa_herramientas[nombre_herramienta]
                        resultado_db = herramienta_a_usar.invoke(argumentos)
                        
                        # Registramos el uso en la memoria
                        st.session_state.historial_mensajes.append(respuesta)
                        st.session_state.historial_mensajes.append(ToolMessage(
                            tool_call_id=tool_call["id"],
                            name=nombre_herramienta,
                            content=str(resultado_db)
                        ))
                
                # Segunda llamada al LLM para que lea el resultado de la DB y te lo explique
                respuesta_final = llm.invoke(st.session_state.historial_mensajes)
                st.write(respuesta_final.content)
                st.session_state.historial_mensajes.append(respuesta_final)
                
# CASO B: El LLM responde normalmente (o escupe el JSON en texto plano)
            else:
                try:
                    # Intentamos ver si el texto crudo es en realidad el JSON de una herramienta
                    import json
                    parsed_json = json.loads(respuesta.content)
                    
                    if isinstance(parsed_json, dict) and "name" in parsed_json and "arguments" in parsed_json:
                        nombre_herramienta = parsed_json["name"]
                        argumentos = parsed_json["arguments"]
                        
                        if nombre_herramienta in mapa_herramientas:
                            herramienta_a_usar = mapa_herramientas[nombre_herramienta]
                            resultado_db = herramienta_a_usar.invoke(argumentos)
                            
                            # Registramos el uso en la memoria fingiendo que fue una llamada oficial
                            st.session_state.historial_mensajes.append(respuesta)
                            st.session_state.historial_mensajes.append(ToolMessage(
                                tool_call_id="id_forzado_123",
                                name=nombre_herramienta,
                                content=str(resultado_db)
                            ))
                            
                            # Segunda llamada al LLM para que lea el resultado de la DB y te lo explique
                            respuesta_final = llm.invoke(st.session_state.historial_mensajes)
                            st.write(respuesta_final.content)
                            st.session_state.historial_mensajes.append(respuesta_final)
                        else:
                            st.write(respuesta.content)
                            st.session_state.historial_mensajes.append(respuesta)
                    else:
                        st.write(respuesta.content)
                        st.session_state.historial_mensajes.append(respuesta)
                        
                except Exception:
                    # Si falla el parseo, significa que sí era texto conversacional real
                    st.write(respuesta.content)
                    st.session_state.historial_mensajes.append(respuesta)