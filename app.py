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

# --- FUNCIONES BASE ---
def generar_franjas():
    franjas = []
    hora_actual = datetime.strptime("08:00", "%H:%M")
    hora_cierre = datetime.strptime("22:00", "%H:%M")
    while hora_actual < hora_cierre:
        franjas.append(hora_actual.strftime("%H:%M"))
        hora_actual += timedelta(minutes=30)
    return franjas

HORAS = generar_franjas()

def cargar_datos():
    if os.path.exists(ARCHIVO_DATOS):
        return pd.read_csv(ARCHIVO_DATOS)
    return pd.DataFrame(columns=COLUMNAS_DF)

def guardar_datos(df_a_guardar):
    df_a_guardar.to_csv(ARCHIVO_DATOS, index=False)

# --- VENTANA MODAL DE EDICIÓN/RESERVA ---
@st.dialog("Gestión de Reserva")
def modal_gestionar_reserva(fecha_str, hora, pista):
    df_actual = cargar_datos()
    
    ocupado = df_actual[(df_actual['Fecha'] == fecha_str) & 
                        (df_actual['Hora'] == hora) & 
                        (df_actual['Pista'] == pista)]
    
    # MODO 1: EDITAR / ELIMINAR RESERVA EXISTENTE
    if not ocupado.empty:
        fila = ocupado.iloc[0]
        st.markdown(f"**Editando tramo:** 🎾 {pista} | 📅 {fecha_str} | ⏰ {hora}")
        
        parc = st.text_input("Nº de Parcela", value=str(fila['Parcela']))
        nom = st.text_input("Nombre del Cliente", value=str(fila['Nombre']))
        pag = st.checkbox("¿Reserva Pagada?", value=(fila['Pagado'] == "Sí"))
        
        col1, col2 = st.columns(2)
        if col1.button("💾 Guardar Cambios", use_container_width=True):
            idx = ocupado.index[0]
            df_actual.at[idx, 'Parcela'] = parc
            df_actual.at[idx, 'Nombre'] = nom
            df_actual.at[idx, 'Pagado'] = "Sí" if pag else "No"
            guardar_datos(df_actual)
            st.rerun()
            
        if col2.button("🗑️ Liberar Tramo", use_container_width=True):
            df_actual.drop(ocupado.index, inplace=True)
            guardar_datos(df_actual)
            st.rerun()

    # MODO 2: CREAR NUEVA RESERVA
    else:
        st.markdown(f"**Nueva reserva:** 🎾 {pista} | 📅 {fecha_str} | ⏰ Inicio: {hora}")
        
        duracion = st.selectbox("Duración", ["60 minutos", "90 minutos", "120 minutos"])
        parc = st.text_input("Nº de Parcela")
        nom = st.text_input("Nombre del Cliente")
        pag = st.checkbox("¿Reserva Pagada?")
        
        if st.button("💾 Confirmar", use_container_width=True):
            if not parc or not nom:
                st.error("⚠️ Parcela y nombre obligatorios.")
            else:
                minutos = int(duracion.split()[0])
                bloques_necesarios = minutos // 30
                idx_inicio = HORAS.index(hora)
                
                if idx_inicio + bloques_necesarios > len(HORAS):
                    st.error("❌ Excede el horario de cierre (22:00).")
                else:
                    franjas_a_ocupar = HORAS[idx_inicio : idx_inicio + bloques_necesarios]
                    conflicto = df_actual[(df_actual['Fecha'] == fecha_str) & 
                                          (df_actual['Pista'] == pista) & 
                                          (df_actual['Hora'].isin(franjas_a_ocupar))]
                    
                    if not conflicto.empty:
                        st.error("❌ Conflicto. Algunos tramos seleccionados ya están ocupados.")
                    else:
                        nuevas_filas = [{
                            'Fecha': fecha_str, 'Pista': pista, 'Hora': f,
                            'Parcela': parc, 'Nombre': nom, 'Pagado': "Sí" if pag else "No"
                        } for f in franjas_a_ocupar]
                        
                        df_actual = pd.concat([df_actual, pd.DataFrame(nuevas_filas)], ignore_index=True)
                        guardar_datos(df_actual)
                        st.rerun()


# --- INTERFAZ: CABECERA Y FILTROS ---
st.title("🎾 Gestión de Pistas")

df = cargar_datos()

col_filtro1, col_filtro2 = st.columns(2)
with col_filtro1:
    fecha_inicio_vista = st.date_input("📅 Día de inicio de la semana", date.today())
with col_filtro2:
    pista_vista = st.selectbox("🎾 Pista a visualizar", PISTAS)

st.markdown("---")

# Preparar datos de la semana
fechas_semana = [fecha_inicio_vista + timedelta(days=i) for i in range(7)]
fechas_str = [str(d) for d in fechas_semana]

# Diccionario de reservas para renderizar la matriz de botones super rápido
df_vista = df[(df['Pista'] == pista_vista) & (df['Fecha'].isin(fechas_str))]
reservas_dict = {}
for _, fila in df_vista.iterrows():
    reservas_dict[(fila['Fecha'], fila['Hora'])] = fila

st.header(f"🗓️ {pista_vista}")
st.caption("👆 **Haz clic en cualquier tramo para reservar, editar o liberar.**")

# --- GENERAR MATRIZ DE BOTONES (EL NUEVO CALENDARIO) ---
# 1. Cabeceras de los días
cols = st.columns([0.8] + [1.5]*7)
with cols[0]:
    st.markdown("<div style='text-align:center'><b>Hora</b></div>", unsafe_allow_html=True)

for i, d in enumerate(fechas_semana):
    nombre_dia = DIAS_SEMANA_ES[d.weekday()]
    fecha_corta = d.strftime("%d/%m")
    es_finde = "🔴" if d.weekday() >= 5 else ""
    es_hoy = "📌" if d == fecha_inicio_vista else ""
    
    with cols[i+1]:
        st.markdown(f"<div style='text-align:center'><b>{es_hoy} {es_finde} {nombre_dia} {fecha_corta}</b></div>", unsafe_allow_html=True)

st.markdown("<hr style='margin:0.5em 0'>", unsafe_allow_html=True)

# 2. Filas de horas y botones
for hora in HORAS:
    cols_fila = st.columns([0.8] + [1.5]*7)
    
    # Columna de la hora
    with cols_fila[0]:
        st.markdown(f"<div style='text-align:center; padding-top:8px;'><b>{hora}</b></div>", unsafe_allow_html=True)
        
    # Columnas de los días
    for i, d_str in enumerate(fechas_str):
        with cols_fila[i+1]:
            # Comprobamos si hay reserva en ese día y hora
            if (d_str, hora) in reservas_dict:
                res = reservas_dict[(d_str, hora)]
                icono_pago = "💰" if res['Pagado'] == "Sí" else "⏳"
                label = f"P.{res['Parcela']} | {res['Nombre']} {icono_pago}"
                
                # Botón ROJO (Ocupado)
                if st.button(label, key=f"btn_{d_str}_{hora}", use_container_width=True, type="primary"):
                    modal_gestionar_reserva(d_str, hora, pista_vista)
            else:
                # Botón GRIS (Libre)
                if st.button("Libre", key=f"btn_{d_str}_{hora}", use_container_width=True, type="secondary"):
                    modal_gestionar_reserva(d_str, hora, pista_vista)
