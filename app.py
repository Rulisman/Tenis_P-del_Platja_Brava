import streamlit as st
import pandas as pd
from datetime import date
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Reservas Pistas - Camping", page_icon="🎾", layout="wide")

# --- CONSTANTES ---
ARCHIVO_DATOS = "reservas_camping.csv"
PISTAS = ["Tenis 1", "Tenis 2", "Pádel 1", "Pádel 2"]
# Genera franjas desde las 08:00 hasta las 22:00 (última franja 21:00 - 22:00)
HORAS = [f"{h:02d}:00 - {h+1:02d}:00" for h in range(8, 22)]
COLUMNAS_DF = ['Fecha', 'Pista', 'Hora', 'Parcela', 'Nombre', 'Pagado']

# --- FUNCIONES DE DATOS ---
def cargar_datos():
    """Carga el CSV de reservas o crea un DataFrame vacío si no existe."""
    if os.path.exists(ARCHIVO_DATOS):
        return pd.read_csv(ARCHIVO_DATOS)
    else:
        return pd.DataFrame(columns=COLUMNAS_DF)

def guardar_datos(df):
    """Guarda el DataFrame en el archivo CSV."""
    df.to_csv(ARCHIVO_DATOS, index=False)

# --- CARGA DE DATOS INICIAL ---
df = cargar_datos()

# --- INTERFAZ DE USUARIO ---
st.title("🎾 Gestión de Pistas Deportivas - Camping")

# Selector de fecha central
fecha_seleccionada = st.date_input("📅 Selecciona el día para ver/gestionar reservas", date.today())

# Dividimos la pantalla en dos columnas
col_form, col_cuadrante = st.columns([1, 2.5])

# --- COLUMNA 1: FORMULARIO DE RESERVA ---
with col_form:
    st.header("📝 Nueva Reserva")
    with st.form("form_nueva_reserva"):
        pista_sel = st.selectbox("Pista", PISTAS)
        hora_sel = st.selectbox("Franja Horaria", HORAS)
        parcela_input = st.text_input("Nº de Parcela")
        nombre_input = st.text_input("Nombre del Cliente")
        pagado_check = st.checkbox("¿Reserva Pagada?")
        
        btn_guardar = st.form_submit_button("Guardar Reserva")
        
        if btn_guardar:
            # Validaciones básicas
            if not parcela_input or not nombre_input:
                st.error("⚠️ El número de parcela y el nombre son obligatorios.")
            else:
                # Comprobar si la pista ya está ocupada esa fecha y hora
                ocupado = df[(df['Fecha'] == str(fecha_seleccionada)) & 
                             (df['Pista'] == pista_sel) & 
                             (df['Hora'] == hora_sel)]
                
                if not ocupado.empty:
                    st.error(f"❌ La pista {pista_sel} ya está reservada a las {hora_sel}.")
                else:
                    # Crear nueva fila de reserva
                    nueva_reserva = pd.DataFrame([{
                        'Fecha': str(fecha_seleccionada),
                        'Pista': pista_sel,
                        'Hora': hora_sel,
                        'Parcela': parcela_input,
                        'Nombre': nombre_input,
                        'Pagado': "Sí" if pagado_check else "No"
                    }])
                    
                    # Añadir al dataframe y guardar
                    df = pd.concat([df, nueva_reserva], ignore_index=True)
                    guardar_datos(df)
                    st.success("✅ Reserva confirmada correctamente.")
                    st.rerun() # Recarga la app para actualizar el cuadrante

# --- COLUMNA 2: CUADRANTE VISUAL ---
with col_cuadrante:
    st.header("🗓️ Cuadrante del Día")
    
    # Filtramos las reservas solo para el día seleccionado
    df_dia = df[df['Fecha'] == str(fecha_seleccionada)]
    
    # Construimos un Dataframe pivoteado (Matriz: Horas x Pistas)
    cuadrante = pd.DataFrame(index=HORAS, columns=PISTAS)
    
    # Rellenamos el cuadrante con las reservas existentes
    for _, fila in df_dia.iterrows():
        icono_pago = "💰 Pagado" if fila['Pagado'] == "Sí" else "⏳ Pendiente"
        texto_celda = f"Parc {fila['Parcela']} | {fila['Nombre']} \n({icono_pago})"
        cuadrante.at[fila['Hora'], fila['Pista']] = texto_celda
        
    # Llenamos los huecos vacíos con "Libre"
    cuadrante = cuadrante.fillna("Libre")
    
    # Mostramos el DataFrame con un diseño amplio
    st.dataframe(cuadrante, use_container_width=True, height=530)
