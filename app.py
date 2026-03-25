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
    else:
        return pd.DataFrame(columns=COLUMNAS_DF)

def guardar_datos(df):
    df.to_csv(ARCHIVO_DATOS, index=False)

# --- CARGA DE DATOS INICIAL ---
df = cargar_datos()

# --- INTERFAZ DE USUARIO: CABECERA Y FILTROS ---
st.title("🎾 Gestión Semanal de Pistas - Camping")

col_filtro1, col_filtro2 = st.columns(2)
with col_filtro1:
    fecha_inicio_vista = st.date_input("📅 Selecciona el día de inicio", date.today())
with col_filtro2:
    pista_vista = st.selectbox("🎾 Selecciona la Pista a visualizar", PISTAS)

st.markdown("---")

col_form, col_cuadrante = st.columns([1, 2.8])

# --- COLUMNA 1: FORMULARIOS (RESERVAR Y CANCELAR) ---
with col_form:
    st.header("📝 Nueva Reserva")
    with st.form("form_nueva_reserva"):
        # Ahora permitimos elegir el día exacto de la reserva y por defecto coge la pista que estamos viendo
        fecha_reserva = st.date_input("Fecha de la reserva", fecha_inicio_vista)
        pista_sel = st.selectbox("Pista", PISTAS, index=PISTAS.index(pista_vista))
        hora_sel = st.selectbox("Hora de Inicio", HORAS)
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
                        nuevas_filas = []
                        for franja in franjas_a_ocupar:
                            nuevas_filas.append({
                                'Fecha': str(fecha_reserva),
                                'Pista': pista_sel,
                                'Hora': franja,
                                'Parcela': parcela_input,
                                'Nombre': nombre_input,
                                'Pagado': "Sí" if pagado_check else "No"
                            })
                        
                        df = pd.concat([df, pd.DataFrame(nuevas_filas)], ignore_index=True)
                        guardar_datos(df)
                        st.success("✅ Reserva confirmada.")
                        st.rerun()

    st.markdown("---")
    
    st.header("🗑️ Cancelar Tramo")
    # Generamos la lista de los 7 días que estamos visualizando
    fechas_semana = [fecha_inicio_vista + timedelta(days=i) for i in range(7)]
    fechas_str = [str(d) for d in fechas_semana]
    
    # Filtramos las reservas para mostrar en el desplegable de cancelar (solo la pista y semana visible)
    df_cancelar = df[(df['Pista'] == pista_vista) & (df['Fecha'].isin(fechas_str))]
    
    if not df_cancelar.empty:
        with st.form("form_cancelar"):
            opciones_canc = []
            for _, fila in df_cancelar.iterrows():
                # Formato: "YYYY-MM-DD | 10:30 | Parc 104"
                opciones_canc.append(f"{fila['Fecha']} | {fila['Hora']} | Parc {fila['Parcela']}")
                
            seleccion_canc = st.selectbox("Selecciona el tramo a liberar", opciones_canc)
            btn_cancelar = st.form_submit_button("Eliminar tramo")
            
            if btn_cancelar:
                fecha_canc, hora_canc, resto = [x.strip() for x in seleccion_canc.split("|")]
                
                condicion = (df['Fecha'] == fecha_canc) & \
                            (df['Hora'] == hora_canc) & \
                            (df['Pista'] == pista_vista)
                
                df = df[~condicion]
                guardar_datos(df)
                st.success("🗑️ Tramo liberado.")
                st.rerun()
    else:
        st.info("No hay reservas en esta pista durante estos 7 días.")

# --- COLUMNA 2: CUADRANTE SEMANAL ---
with col_cuadrante:
    st.header(f"🗓️ Semana: {pista_vista}")
    
    # Preparamos las cabeceras de las columnas (Ej: "Lun 25/03")
    cabeceras_columnas = []
    for d in fechas_semana:
        nombre_dia = DIAS_SEMANA_ES[d.weekday()]
        fecha_corta = d.strftime("%d/%m")
        cabeceras_columnas.append(f"{nombre_dia} {fecha_corta}")
        
    # Creamos el cuadrante vacío (Filas = Horas, Columnas = Días de la semana)
    cuadrante = pd.DataFrame(index=HORAS, columns=cabeceras_columnas)
    
    # Filtramos los datos solo para la pista seleccionada y los 7 días
    df_vista = df[(df['Pista'] == pista_vista) & (df['Fecha'].isin(fechas_str))]
    
    # Rellenamos el cuadrante
    for _, fila in df_vista.iterrows():
        # Buscamos a qué columna pertenece la fecha de esta reserva
        idx_fecha = fechas_str.index(fila['Fecha'])
        nombre_columna = cabeceras_columnas[idx_fecha]
        
        icono_pago = "💰" if fila['Pagado'] == "Sí" else "⏳"
        texto_celda = f"P.{fila['Parcela']} | {fila['Nombre']} {icono_pago}"
        
        # Colocamos el texto en su celda (Hora, Día)
        cuadrante.at[fila['Hora'], nombre_columna] = texto_celda
        
    cuadrante = cuadrante.fillna("Libre")
    
    # Mostramos el DataFrame
    st.dataframe(cuadrante, use_container_width=True, height=800)
