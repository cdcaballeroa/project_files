import streamlit as st
import pandas as pd
import base64

def main():
    st.set_page_config(page_title="Aplicación Multi-Pantalla", layout="wide")
    
    # Sidebar para navegación
    menu = ["Inicio", "Registro/Login", "Vista de Archivos"]
    choice = st.sidebar.selectbox("Selecciona una pantalla", menu)
    
    # Campo de entrada para el límite máximo de gasto
    max_total = st.sidebar.number_input("Ingrese el valor máximo permitido", min_value=0.0, format="%.2f", key="max_total")
    
    if choice == "Inicio":
        inicio()
    elif choice == "Registro/Login":
        registro_login()
    elif choice == "Vista de Archivos":
        vista_archivos(max_total)

@st.cache_data
def load_pdf(file):
    return file.read()

@st.cache_data
def load_csv(file):
    return pd.read_csv(file)

@st.cache_data
def load_excel(file):
    return pd.read_excel(file, sheet_name="FORMATO DE OFERTA ECONÓMICA")

def inicio():
    st.title("Bienvenido a la Aplicación")
    st.write("Esta es una aplicación de múltiples pantallas con Streamlit.")
    
    st.subheader("Carga de archivos")
    plano_pdf = st.file_uploader("Sube un archivo PDF (Plano)", type=["pdf"])
    resultados_csv = st.file_uploader("Sube un archivo CSV (Resultados MagicPlan)", type=["csv"])
    costos_excel = st.file_uploader("Sube un archivo Excel (Costos y Relaciones)", type=["xls", "xlsx"])
    
    if plano_pdf and resultados_csv and costos_excel:
        st.session_state["plano_pdf"] = load_pdf(plano_pdf)
        st.session_state["resultados_csv"] = load_csv(resultados_csv)
        st.session_state["costos_excel"] = load_excel(costos_excel)
        st.success("Todos los archivos han sido cargados correctamente. Ahora puedes ir a la pantalla de Vista de Archivos.")

def vista_archivos(max_total):
    # Navbar con número a la derecha
    st.markdown(
        """
        <div style='display: flex; justify-content: space-between; align-items: center; background-color: #f1f1f1; padding: 10px;'>
            <h3 style='margin: 0;'>Vista de Archivos</h3>
            <span style='font-size: 18px; font-weight: bold;'>#12345</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    if "plano_pdf" in st.session_state:
        st.subheader("Plano PDF")
        base64_pdf = base64.b64encode(st.session_state["plano_pdf"]).decode("utf-8")
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700px" height="500px"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    
    if "resultados_csv" in st.session_state and "costos_excel" in st.session_state:
        st.subheader("Selección de Habitaciones")
        habitaciones = st.session_state["resultados_csv"].iloc[:, 0].tolist()
        actividades = st.session_state["costos_excel"]
        estados = {}
        subtotales = {}
        
        for habitacion in habitaciones:
            activo = habitacion.startswith("#")
            estados[habitacion] = st.checkbox(habitacion, value=activo, key=f"habitacion_{habitacion}")
            subtotal = 0.0
            
            if estados[habitacion]:
                with st.expander(f"Detalles de {habitacion}"):
                    habitacion_tipo = habitacion.split()[0].upper().replace("#", "")
                    
                    for _, row in actividades.iterrows():
                        actividad = row.get("ACTIVIDAD DE OBRA - LISTA DE PRECIOS UNITARIOS", "")
                        unidad = row.get("Unidad", None)
                        item = row.get("Item", "")
                        valor_unitario = row.get("Valor Unitario ofertado (**)", 0.0)
                        medicion = row.get("MEDICION", "")
                        
                        if pd.isna(unidad) or unidad == "":
                            if str(item).isdigit():
                                st.subheader(actividad)
                            else:
                                st.markdown(f"**{actividad}**")
                        else:
                            if row.get("ESPACIOS", "").upper() in [habitacion_tipo, "CASA"]:
                                check = st.checkbox(f"{actividad}", key=f"check_{habitacion}_{actividad}")
                                if check:
                                    cantidad_key = f"cantidad_{habitacion}_{actividad}"
                                    valor_guardado_key = f"valor_{habitacion}_{actividad}"
                                    cantidad_format = "%.0f" if unidad in ["UN", "UND"] else "%.4f"
                                    cantidad = st.number_input(f"Ingrese la cantidad.", min_value=0.0, format=cantidad_format, key=cantidad_key)
                                    
                                    if valor_guardado_key not in st.session_state:
                                        st.session_state[valor_guardado_key] = 0.0
                                    
                                    if st.button(f"Guardar cantidad", key=f"button_{habitacion}_{actividad}"):
                                        st.session_state[valor_guardado_key] = cantidad * valor_unitario
                                        st.success(f"Valor guardado para {actividad}: ${st.session_state[valor_guardado_key]:,.2f}")
                                    
                                    subtotal += st.session_state[valor_guardado_key]
            
            subtotales[habitacion] = subtotal
        
        total_general = sum(subtotales.values())
        st.sidebar.subheader("Subtotales por Habitación")
        df_subtotales = pd.DataFrame(list(subtotales.items()), columns=["Habitación", "Subtotal ($)"]).round(2)
        st.sidebar.dataframe(df_subtotales)
        st.sidebar.subheader("Total General")
        
        if total_general > max_total:
            st.sidebar.markdown(f"<span style='color: red; font-weight: bold;'>Total: ${total_general:,.2f}</span>", unsafe_allow_html=True)
        else:
            st.sidebar.markdown(f"Total: ${total_general:,.2f}")

def registro_login():
    st.title("Registro o Inicio de Sesión")
    opcion = st.radio("Elige una opción:", ["Iniciar Sesión", "Registrarse"])
    
    if opcion == "Iniciar Sesión":
        usuario = st.text_input("Usuario")
        contraseña = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            st.success(f"Bienvenido, {usuario}!")
    
    elif opcion == "Registrarse":
        nuevo_usuario = st.text_input("Nuevo Usuario")
        nueva_contraseña = st.text_input("Nueva Contraseña", type="password")
        confirmar_contraseña = st.text_input("Confirmar Contraseña", type="password")
        if st.button("Registrarse"):
            if nueva_contraseña == confirmar_contraseña:
                st.success("Registro exitoso. Ahora puedes iniciar sesión.")
            else:
                st.error("Las contraseñas no coinciden.")

if __name__ == "__main__":
    main()
