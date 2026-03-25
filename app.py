import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Reservas Pistas - Camping", page_icon="🎾", layout="wide")

# --- CONSTANTES ---
ARCHIVO_DATOS = "reservas_camping.csv"
PISTAS = ["TENIS 1", "TENIS 2", "PADEL 1", "PADEL 2"]
COLUMNAS_DF = ['Fecha', 'Pista', 'Hora', 'Parcela', 'Nombre', 'Pagado']
DIAS_SEMANA_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]

# --- GENERACIÓN DE FRANJAS HORARIAS (Cada 30 min) ---
def generar_franjas():
    franjas = []
    hora_actual = datetime.strptime("08:00", "%H:%M")
    hora_cierre = datetime.strptime("22:00", "%H:%M")
    while hora_actual < hora_cierre:
        franjas.append(hora_actual.strftime("%H:%M"))
        hora_actual += timedelta(minutes=30)
    return franjas

HORAS = generar_franjas()

# --- FUNCIONES DE DATOS ---
def cargar_datos():
    if os.path.exists(ARCHIVO_DATOS):
        return pd.read_csv(ARCHIVO_DATOS)
    return pd.DataFrame(columns=COLUMNAS_DF)

def guardar_datos(df):
    df.to_csv(ARCHIVO_DATOS, index=False)

df = cargar_datos()

# --- INICIALIZAR ESTADO DE SESIÓN DE LOS WIDGETS ---
if "input_fecha" not in st.session_state:
    st.session_state.input_fecha = date.today()
if "input_hora" not in st.session_state:
    st.session_state.input_hora = HORAS[0]

# --- CABECERA Y FILTROS ---
st.title("🎾 Gestión Semanal de Pistas - Camping")

col_filtro1, col_filtro2 = st.columns(2)
with col_filtro1:
    fecha_inicio_vista = st.date_input("📅 Selecciona el día de inicio de la semana", date.today())
with col_filtro2:
    pista_vista = st.selectbox("🎾 Selecciona la Pista a visualizar", PISTAS)

# Calculamos los 7 días y generamos las CABECERAS (ahora va arriba para poder mapear el clic)
fechas_semana = [fecha_inicio_vista + timedelta(days=i) for i in range(7)]
fechas_str = [str(d) for d in fechas_semana]

cabeceras_columnas = []
columnas_finde = [] 
columna_seleccionada = None

for d in fechas_semana:
    nombre_dia = DIAS_SEMANA_ES[d.weekday()]
    fecha_corta = d.strftime("%d/%m")
    es_finde = d.weekday() >= 5
    es_dia_elegido = (d == fecha_inicio_vista)
    
    iconos = ""
    if es_dia_elegido: iconos += "📌 " 
    if es_finde: iconos += "🔴 " 
        
    nombre_col = f"{iconos}{nombre_dia} {fecha_corta}".strip()
    
    if es_finde: columnas_finde.append(nombre_col)
    if es_dia_elegido: columna_seleccionada = nombre_col
        
    cabeceras_columnas.append(nombre_col)

st.markdown("---")

# --- PROCESAR CLIC EN EL CUADRANTE ---
if "grid_reservas" in st.session_state:
    seleccion = st.session_state.grid_reservas.get("selection", {})
    filas_sel = seleccion.get("rows", [])
    cols_sel = seleccion.get("columns", [])
    
    if filas_sel and cols_sel:
        idx_fila = filas_sel[0]       # Es un número (índice de la hora)
        nombre_col_sel = cols_sel[0]  # Es un texto (ej: "🔴 Sáb 28/03")
        
        # Buscamos en qué posición está esa columna para sacar la fecha real
        if nombre_col_sel in cabeceras_columnas:
            idx_col = cabeceras_columnas.index(nombre_col_sel)
            # Actualizamos directamente las variables de los selectores
            st.session_state.input_hora = HORAS[idx_fila]
            st.session_state.input_fecha = fechas_semana[idx_col]

# --- LAYOUT PRINCIPAL ---
col_form, col_cuadrante = st.columns([1, 2.8])

# --- COLUMNA 1: FORMULARIOS ---
with col_form:
    st.header("📝 Nueva Reserva")
    with st.form("form_nueva_reserva"):
        # Vinculamos los campos usando el parámetro 'key'
        fecha_reserva = st.date_input("Fecha de la reserva", key="input_fecha")
        pista_sel = st.selectbox("Pista", PISTAS, index=PISTAS.index(pista_vista))
        hora_sel = st.selectbox("Hora de Inicio", HORAS, key="input_hora")
        duracion_sel = st.selectbox("Duración", ["60 minutos", "90 minutos", "120 minutos"])
        
        parcela_input = st.text_input("Nº de Parcela")
        nombre_input = st.text_input("Nombre del Cliente")
        pagado_check = st.checkbox("¿Reserva Pagada?")
        
        btn_guardar = st.form_submit_button("Guardar Reserva")
        
        if btn_guardar:
            if not parcela_input or not nombre_input:
                st.error("⚠️ Parcela y nombre obligatorios.")
            else:
                minutos = int(duracion_sel.split()[0])
                bloques_necesarios = minutos // 30
                idx_inicio = HORAS.index(hora_sel)
                
                if idx_inicio + bloques_necesarios > len(HORAS):
                    st.error("❌ Excede el horario de cierre (22:00).")
                else:
                    franjas_a_ocupar = HORAS[idx_inicio : idx_inicio + bloques_necesarios]
                    ocupado = df[(df['Fecha'] == str(fecha_reserva)) & 
                                 (df['Pista'] == pista_sel) & 
                                 (df['Hora'].isin(franjas_a_ocupar))]
                    
                    if not ocupado.empty:
                        st.error("❌ Conflicto. La pista ya está ocupada en ese tramo.")
                    else:
                        nuevas_filas = [{
                            'Fecha': str(fecha_reserva),
                            'Pista': pista_sel,
                            'Hora': franja,
                            'Parcela': parcela_input,
                            'Nombre': nombre_input,
                            'Pagado': "Sí" if pagado_check else "No"
                        } for franja in franjas_a_ocupar]
                        
                        df = pd.concat([df, pd.DataFrame(nuevas_filas)], ignore_index=True)
                        guardar_datos(df)
                        st.success("✅ Reserva confirmada.")
                        st.rerun()

    st.markdown("---")
    
    st.header("🗑️ Cancelar Tramo")
    df_cancelar = df[(df['Pista'] == pista_vista) & (df['Fecha'].isin(fechas_str))]
    
    if not df_cancelar.empty:
        with st.form("form_cancelar"):
            opciones_canc = [f"{fila['Fecha']} | {fila['Hora']} | Parc {fila['Parcela']}" for _, fila in df_cancelar.iterrows()]
            seleccion_canc = st.selectbox("Selecciona el tramo a liberar", opciones_canc)
            btn_cancelar = st.form_submit_button("Eliminar tramo")
            
            if btn_cancelar:
                fecha_canc, hora_canc, resto = [x.strip() for x in seleccion_canc.split("|")]
                condicion = (df['Fecha'] == fecha_canc) & (df['Hora'] == hora_canc) & (df['Pista'] == pista_vista)
                df = df[~condicion]
                guardar_datos(df)
                st.success("🗑️ Tramo liberado.")
                st.rerun()
    else:
        st.info("No hay reservas en esta pista durante estos 7 días.")

# --- COLUMNA 2: CUADRANTE SEMANAL ---
with col_cuadrante:
    st.header(f"🗓️ Semana: {pista_vista}")
    st.caption("👈 Haz clic en cualquier celda para rellenar el formulario de reserva automáticamente.")
    
    cuadrante = pd.DataFrame(index=HORAS, columns=cabeceras_columnas)
    df_vista = df[(df['Pista'] == pista_vista) & (df['Fecha'].isin(fechas_str))]
    
    for _, fila in df_vista.iterrows():
        idx_fecha = fechas_str.index(fila['Fecha'])
        nombre_columna = cabeceras_columnas[idx_fecha]
        icono_pago = "💰" if fila['Pagado'] == "Sí" else "⏳"
        texto_celda = f"P.{fila['Parcela']} | {fila['Nombre']} {icono_pago}"
        cuadrante.at[fila['Hora'], nombre_columna] = texto_celda
        
    cuadrante = cuadrante.fillna("Libre")
    
    def aplicar_estilos(col):
        if col.name == columna_seleccionada:
            return ['background-color: #fffacd; color: #000000; font-weight: bold'] * len(col)
        elif col.name in columnas_finde:
            return ['background-color: #ffeeee; color: #8b0000'] * len(col)
        return [''] * len(col)

    cuadrante_estilizado = cuadrante.style.apply(aplicar_estilos, axis=0)
    
    # Renderizamos la tabla con interactividad
    st.dataframe(
        cuadrante_estilizado, 
        use_container_width=True, 
        height=800,
        selection_mode="single-cell", 
        on_select="rerun",            
        key="grid_reservas"           
    )
