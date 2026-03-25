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
    # Cargamos los datos frescos dentro del modal
    df_actual = cargar_datos()
    
    # Comprobamos si el tramo específico en el que hemos hecho clic ya está ocupado
    ocupado = df_actual[(df_actual['Fecha'] == fecha_str) & 
                        (df_actual['Hora'] == hora) & 
                        (df_actual['Pista'] == pista)]
    
    # --- MODO 1: EDITAR / ELIMINAR RESERVA EXISTENTE ---
    if not ocupado.empty:
        fila = ocupado.iloc[0]
        st.markdown(f"**Editando tramo:** 🎾 {pista} | 📅 {fecha_str} | ⏰ {hora}")
        
        parc = st.text_input("Nº de Parcela", value=fila['Parcela'])
        nom = st.text_input("Nombre del Cliente", value=fila['Nombre'])
        pag = st.checkbox("¿Reserva Pagada?", value=(fila['Pagado'] == "Sí"))
        
        col1, col2 = st.columns(2)
        if col1.button("💾 Guardar Cambios", use_container_width=True):
            # Actualizamos la fila exacta
            idx = ocupado.index[0]
            df_actual.at[idx, 'Parcela'] = parc
            df_actual.at[idx, 'Nombre'] = nom
            df_actual.at[idx, 'Pagado'] = "Sí" if pag else "No"
            guardar_datos(df_actual)
            st.session_state.contador_tabla += 1 # Truco para recargar la tabla limpia
            st.rerun()
            
        if col2.button("🗑️ Liberar Tramo", use_container_width=True):
            # Borramos la fila
            df_actual.drop(ocupado.index, inplace=True)
            guardar_datos(df_actual)
            st.session_state.contador_tabla += 1
            st.rerun()

    # --- MODO 2: CREAR NUEVA RESERVA ---
    else:
        st.markdown(f"**Nueva reserva:** 🎾 {pista} | 📅 {fecha_str} | ⏰ Inicio: {hora}")
        
        duracion = st.selectbox("Duración", ["60 minutos", "90 minutos", "120 minutos"])
        parc = st.text_input("Nº de Parcela")
        nom = st.text_input("Nombre del Cliente")
        pag = st.checkbox("¿Reserva Pagada?")
        
        if st.button("💾 Confirmar Reserva", use_container_width=True):
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
                        st.session_state.contador_tabla += 1
                        st.rerun()

# --- INICIALIZAR ESTADO ---
# Usamos un contador en el nombre de la tabla para que pierda la memoria del clic tras guardar
if "contador_tabla" not in st.session_state:
    st.session_state.contador_tabla = 0

df = cargar_datos()

# --- INTERFAZ: CABECERA Y FILTROS ---
st.title("🎾 Gestión de Pistas")

col_filtro1, col_filtro2 = st.columns(2)
with col_filtro1:
    fecha_inicio_vista = st.date_input("📅 Día de inicio de la semana", date.today())
with col_filtro2:
    pista_vista = st.selectbox("🎾 Pista a visualizar", PISTAS)

st.markdown("---")

# Calculamos los 7 días y generamos las cabeceras
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
    
    iconos = "📌 " if es_dia_elegido else ""
    iconos += "🔴 " if es_finde else ""
        
    nombre_col = f"{iconos}{nombre_dia} {fecha_corta}".strip()
    
    if es_finde: columnas_finde.append(nombre_col)
    if es_dia_elegido: columna_seleccionada = nombre_col
    cabeceras_columnas.append(nombre_col)

# --- PROCESAR CLIC EN EL CUADRANTE ---
clave_tabla = f"grid_reservas_{st.session_state.contador_tabla}"

if clave_tabla in st.session_state:
    seleccion = st.session_state[clave_tabla].get("selection", {})
    filas_sel = seleccion.get("rows", [])
    cols_sel = seleccion.get("columns", [])
    
    if filas_sel and cols_sel:
        idx_fila = filas_sel[0]
        nombre_col_sel = cols_sel[0]
        
        if nombre_col_sel in cabeceras_columnas:
            idx_col = cabeceras_columnas.index(nombre_col_sel)
            hora_clic = HORAS[idx_fila]
            fecha_clic = fechas_str[idx_col]
            
            # Lanzamos la ventana modal
            modal_gestionar_reserva(fecha_clic, hora_clic, pista_vista)

# --- CUADRANTE SEMANAL A PANTALLA COMPLETA ---
st.header(f"🗓️ {pista_vista}")
st.caption("👆 **Haz clic en cualquier celda (libre u ocupada) para gestionarla directamente.**")

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

# Mostramos la tabla gigante
st.dataframe(
    cuadrante_estilizado, 
    use_container_width=True, 
    height=800,
    selection_mode="single-cell", 
    on_select="rerun",            
    key=clave_tabla           
)
