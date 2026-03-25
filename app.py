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
    else:
        return pd.DataFrame(columns=COLUMNAS_DF)

def guardar_datos(df):
    df.to_csv(ARCHIVO_DATOS, index=False)

# --- CARGA DE DATOS INICIAL ---
df = cargar_datos()

# --- INTERFAZ DE USUARIO ---
st.title("🎾 Gestión de Pistas Deportivas - Camping")

# Selector de fecha central
fecha_seleccionada = st.date_input("📅 Selecciona el día", date.today())

col_form, col_cuadrante = st.columns([1, 2.5])

# --- COLUMNA 1: FORMULARIOS (RESERVAR Y CANCELAR) ---
with col_form:
    st.header("📝 Nueva Reserva")
    with st.form("form_nueva_reserva"):
        pista_sel = st.selectbox("Pista", PISTAS)
        hora_sel = st.selectbox("Hora de Inicio", HORAS)
        duracion_sel = st.selectbox("Duración de la reserva", ["60 minutos", "90 minutos", "120 minutos"])
        parcela_input = st.text_input("Nº de Parcela")
        nombre_input = st.text_input("Nombre del Cliente")
        pagado_check = st.checkbox("¿Reserva Pagada?")
        
        btn_guardar = st.form_submit_button("Guardar Reserva")
        
        if btn_guardar:
            if not parcela_input or not nombre_input:
                st.error("⚠️ El número de parcela y el nombre son obligatorios.")
            else:
                minutos = int(duracion_sel.split()[0])
                bloques_necesarios = minutos // 30
                idx_inicio = HORAS.index(hora_sel)
                
                if idx_inicio + bloques_necesarios > len(HORAS):
                    st.error("❌ La reserva excede el horario de cierre (22:00).")
                else:
                    franjas_a_ocupar = HORAS[idx_inicio : idx_inicio + bloques_necesarios]
                    ocupado = df[(df['Fecha'] == str(fecha_seleccionada)) & 
                                 (df['Pista'] == pista_sel) & 
                                 (df['Hora'].isin(franjas_a_ocupar))]
                    
                    if not ocupado.empty:
                        st.error("❌ Conflicto de horario. La pista ya está ocupada en ese tramo.")
                    else:
                        nuevas_filas = []
                        for franja in franjas_a_ocupar:
                            nuevas_filas.append({
                                'Fecha': str(fecha_seleccionada),
                                'Pista': pista_sel,
                                'Hora': franja,
                                'Parcela': parcela_input,
                                'Nombre': nombre_input,
                                'Pagado': "Sí" if pagado_check else "No"
                            })
                        
                        df = pd.concat([df, pd.DataFrame(nuevas_filas)], ignore_index=True)
                        guardar_datos(df)
                        st.success(f"✅ Reserva de {minutos} min confirmada.")
                        st.rerun()

    st.markdown("---")
    
    st.header("🗑️ Cancelar Reserva")
    # Filtramos las reservas del día seleccionado para el menú de cancelación
    df_dia_cancelar = df[df['Fecha'] == str(fecha_seleccionada)]
    
    if not df_dia_cancelar.empty:
        with st.form("form_cancelar"):
            opciones_canc = []
            for _, fila in df_dia_cancelar.iterrows():
                # Formato visual: "10:30 - PADEL 1 (Parc 104)"
                opciones_canc.append(f"{fila['Hora']} - {fila['Pista']} (Parc {fila['Parcela']})")
                
            seleccion_canc = st.selectbox("Selecciona el tramo a liberar", opciones_canc)
            btn_cancelar = st.form_submit_button("Eliminar tramo")
            
            if btn_cancelar:
                # Extraemos la hora y la pista de la cadena de texto
                hora_canc = seleccion_canc.split(" - ")[0]
                pista_canc = seleccion_canc.split(" - ")[1].split(" (")[0]
                
                # Borramos la fila que coincida exactamente
                condicion = (df['Fecha'] == str(fecha_seleccionada)) & \
                            (df['Hora'] == hora_canc) & \
                            (df['Pista'] == pista_canc)
                
                df = df[~condicion]
                guardar_datos(df)
                st.success(f"🗑️ Tramo liberado correctamente.")
                st.rerun()
    else:
        st.info("Día libre, no hay reservas para cancelar.")

# --- COLUMNA 2: CUADRANTE VISUAL ---
with col_cuadrante:
    st.header("🗓️ Cuadrante del Día")
    
    df_dia = df[df['Fecha'] == str(fecha_seleccionada)]
    cuadrante = pd.DataFrame(index=HORAS, columns=PISTAS)
    
    for _, fila in df_dia.iterrows():
        icono_pago = "💰" if fila['Pagado'] == "Sí" else "⏳"
        texto_celda = f"P.{fila['Parcela']} | {fila['Nombre']} {icono_pago}"
        cuadrante.at[fila['Hora'], fila['Pista']] = texto_celda
        
    cuadrante = cuadrante.fillna("Libre")
    st.dataframe(cuadrante, use_container_width=True, height=800)
