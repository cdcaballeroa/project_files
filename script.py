import streamlit as st
import pandas as pd
import base64
import io

import re
import json
import pandas as pd
from io import StringIO, BytesIO

def procesar_csv_bytes(file_bytes: BytesIO):
    """
    Procesa un archivo CSV desde un BytesIO y devuelve un diccionario con las tablas encontradas.

    Args:
        file_bytes (BytesIO): Archivo CSV en memoria.

    Returns:
        tuple: Un diccionario con las tablas y un código de estado HTTP.
    """
    try:
        content = file_bytes.getvalue().decode('utf-8', errors='replace')

        raw_sections = re.split(r'\n\s*\n+', content)
        sections = [sec.strip() for sec in raw_sections if sec.strip()]
        
        tablas = {}
        for idx, section in enumerate(sections, start=1):
            lines = section.split('\n')

            if len(lines) == 1:
                tablas[f"tabla_{idx}"] = {"titulo": lines[0]}
                continue
            
            if all(':' in line for line in lines if line.strip()):
                data = {key.strip(): value.strip().strip(',')
                        for line in lines if (parts := line.split(':', 1)) and len(parts) == 2
                        for key, value in [parts]}
                tablas[f"tabla_{idx}"] = data
                continue
            
            try:
                read_csv_kwargs = {"encoding": "utf-8"}
                if pd.__version__ >= "1.3.0":
                    read_csv_kwargs["on_bad_lines"] = "skip"
                else:
                    read_csv_kwargs["error_bad_lines"] = False
                
                df = pd.read_csv(StringIO(section), **read_csv_kwargs)
                
                if not df.empty:
                    df.columns = df.columns.str.strip()
                    tablas[f"tabla_{idx}"] = df
                    continue
            except pd.errors.ParserError:
                pass  

            data = {f"columna_{i}": [part.strip() for part in line.split(',')] 
                    if ',' in line else line.strip() for i, line in enumerate(lines)}
            tablas[f"tabla_{idx}"] = data

        return tablas, 200
    except UnicodeDecodeError:
        return {"error": "Error al leer el archivo, posible problema de codificación"}, 400
    except Exception as e:
        return {"error": f"Error al procesar el archivo CSV: {str(e)}"}, 500


def calcular_propiedades_habitacion(tablas):
    """
    Calcula valores para cada habitación en las tablas encontradas.

    Args:
        tablas (dict): Diccionario de tablas procesadas.

    Returns:
        dict: JSON con los resultados en formato de diccionario.
    """
    resultados = {}

    for tabla_key, value in tablas.items():
        if isinstance(value, pd.DataFrame):
            df = value.copy()
            df.columns = df.columns.str.strip()

            columnas_requeridas = ["Tierra Superficie: : m²", "Paredes sin apertura: m²"]
            if not all(col in df.columns for col in columnas_requeridas):
                continue

            for _, row in df.iterrows():
                try:
                    nombre_habitacion = row.iloc[0]  # Primera columna es el nombre

                    superficie = float(row.get("Tierra Superficie: : m²", 0) or 0)
                    paredes_sin_apertura = float(row.get("Paredes sin apertura: m²", 0) or 0)

                    techo = None
                    if "Tierra Perímetro: m" in df.columns and "Techo Perímetro: m" in df.columns:
                        perimetro_tierra = float(row.get("Tierra Perímetro: m", 0) or 0)
                        perimetro_techo = float(row.get("Techo Perímetro: m", 0) or 0)
                        diferencia = abs(perimetro_tierra - perimetro_techo)
                        techo = superficie * 1.15 if diferencia >= 0.1 else superficie

                    resultados[nombre_habitacion] = {
                        "MAGICPLAN - ÁREA PISO": superficie,
                        "MAGICPLAN - ÁREA PARED": paredes_sin_apertura,
                        "MAGICPLAN - ÁREA TECHO": techo
                    }
                except Exception as e:
                    resultados[f"Error en {tabla_key}"] = f"Error al procesar habitación: {str(e)}"

    return resultados

def inicio():
    st.title("Bienvenido a la Aplicación")
    st.write("Esta es una aplicación de múltiples pantallas con Streamlit.")
    
    st.subheader("Carga de archivos")
    plano_pdf = st.file_uploader("Sube un archivo PDF (Plano)", type=["pdf"])
    resultados_csv = st.file_uploader("Sube un archivo CSV (Resultados MagicPlan)", type=["csv"])
    costos_excel = st.file_uploader("Sube un archivo Excel (Costos y Relaciones)", type=["xls", "xlsx"])
    
    if plano_pdf and resultados_csv and costos_excel:
        st.session_state["plano_pdf"] = load_pdf(plano_pdf)
        tablas, codigo = procesar_csv_bytes(resultados_csv)
        st.session_state["resultados_csv"] = calcular_propiedades_habitacion(tablas)
        #######
        st.header('TABLAS')
        st.json(tablas)
        st.header('DATOS')
        st.json(st.session_state["resultados_csv"])
        st.session_state["costos_excel"] = load_excel(costos_excel)
        st.success("Todos los archivos han sido cargados correctamente. Ahora puedes ir a la pantalla de Vista de Archivos.")


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

def export_excel():
    if "costos_excel" in st.session_state:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            columnas_exportar = ["Item", "ACTIVIDAD DE OBRA - LISTA DE PRECIOS UNITARIOS", "Unidad", "Valor Unitario ofertado (**)"]
            df_exportado = st.session_state["costos_excel"][columnas_exportar]
            df_exportado.to_excel(writer, index=False, sheet_name="Datos Exportados")
        output.seek(0)
        return output
    return None

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
        habitaciones = [key for key in st.session_state["resultados_csv"].keys() if "piso" not in key.lower()]
        actividades = st.session_state["costos_excel"]
        estados = {}
        subtotales = {}
        
        for habitacion in habitaciones:
            activo = habitacion.startswith("#")
            estados[habitacion] = st.checkbox(habitacion, value=activo, key=f"habitacion_{habitacion}")
            subtotal = 0.0
            
            if estados[habitacion]:
                with st.expander(f"Modificaciones de {habitacion}"):
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
                                check = st.checkbox(f"{actividad} [Unidad: {unidad}] (Precio unitario: ${valor_unitario:,.2f})", key=f"check_{habitacion}_{actividad}")
                                if check:
                                    cantidad_key = f"cantidad_{habitacion}_{actividad}"
                                    valor_guardado_key = f"valor_{habitacion}_{actividad}"
                                    cantidad_format = "%.0f" if unidad in ["UN", "UND"] else "%.4f"
                                    if "USUARIO" in medicion.upper():
                                        cantidad = st.number_input(f"Ingrese la cantidad ({unidad}).", min_value=0.0, format=cantidad_format, key=cantidad_key)
                                    
                                        if valor_guardado_key not in st.session_state:
                                            st.session_state[valor_guardado_key] = 0.0
                                        
                                        if st.button(f"Guardar cantidad", key=f"button_{habitacion}_{actividad}"):
                                            st.session_state[valor_guardado_key] = cantidad * valor_unitario
                                            st.success(f"Valor guardado para {actividad}: ${st.session_state[valor_guardado_key]:,.2f}")
                                    else:
                                        cantidad = st.number_input("Valor MagicPlan", value=st.session_state["resultados_csv"][habitacion][medicion], min_value=0.0, key=cantidad_key)
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
        
        # Botón para exportar el archivo Excel ingresado
        excel_file = export_excel()
        if excel_file:
            st.sidebar.download_button(label="Exportar Excel", data=excel_file, file_name="Datos_Exportados.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

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
