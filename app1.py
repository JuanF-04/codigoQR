# Proyecto: Sistema de Asistencia con Streamlit y Supabase
import streamlit as st
import cv2
import qrcode
from datetime import datetime
import os
import pandas as pd
import numpy as np
from supabase import create_client, Client

# Configuración de la página
st.set_page_config(page_title="Asistencia QR", page_icon="🎓", layout="centered")
st.title("📚 Registro de Asistencia - App Streamlit")

# Configuración de Supabase (reemplaza con tus credenciales)
@st.cache_resource
def init_supabase():
    url = st.secrets["postgresql://postgres.fqcfrnfnsfxvjurnhtkd:zlfR123@#$@aws-0-us-east-1.pooler.supabase.com:6543/postgres"]["url"]
    return create_client(url)

supabase = init_supabase()

# Datos de materias y generación de códigos QR únicos
materias = {
    "Álgebra Lineal": "MAT01",
    "Cálculo Diferencial": "MAT02",
    "Física General": "MAT03",
    "Programación I": "MAT04",
    "Bases de Datos": "MAT05",
    "Estadística": "MAT06",
    "Inteligencia Artificial": "MAT07",
    "Redes de Computadoras": "MAT08"
}

# Generar códigos QR para cada materia
for nombre, qr_id in materias.items():
    nombre_archivo = f"QR_{nombre.replace(' ', '')}.png"
    if not os.path.exists(nombre_archivo):
        img_qr = qrcode.make(qr_id)
        img_qr.save(nombre_archivo)

# Funciones para interactuar con Supabase
def cargar_usuarios():
    response = supabase.table('usuarios').select("*").execute()
    if not response.data:
        # Crear usuario admin por defecto si no hay usuarios
        registrar_usuario("admin", "Administrador", "admin", "administrador")
        return cargar_usuarios()
    return pd.DataFrame(response.data)

def registrar_usuario(nuevo_usuario, nombre_completo, password, rol):
    data = {
        "usuario": nuevo_usuario,
        "nombre": nombre_completo,
        "password": password,
        "rol": rol
    }
    supabase.table('usuarios').insert(data).execute()

def autenticar_usuario(usuario, password):
    response = supabase.table('usuarios').select("*").eq("usuario", usuario).eq("password", password).execute()
    if response.data:
        registro = response.data[0]
        return registro['nombre'], registro['rol']
    return None, None

def registrar_asistencia(nombre, id_materia, materia, fecha, hora):
    data = {
        "nombre": nombre,
        "id_materia": id_materia,
        "materia": materia,
        "fecha": fecha,
        "hora": hora
    }
    supabase.table('asistencias').insert(data).execute()

def obtener_asistencias(filtro_materia=None, filtro_fecha=None):
    query = supabase.table('asistencias').select("*")
    
    if filtro_materia and filtro_materia != "Todas":
        query = query.eq("materia", filtro_materia)
    if filtro_fecha:
        fecha_str = filtro_fecha.strftime("%Y-%m-%d")
        query = query.eq("fecha", fecha_str)
    
    response = query.execute()
    return pd.DataFrame(response.data)

def verificar_asistencia_existente(nombre, id_materia, fecha):
    response = supabase.table('asistencias').select("*").eq("nombre", nombre).eq("id_materia", id_materia).eq("fecha", fecha).execute()
    return len(response.data) > 0

# Inicializar variables de sesión
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.usuario = ""
    st.session_state.nombre = ""
    st.session_state.rol = ""

# Panel de autenticación: Login / Registro
if not st.session_state.logged_in:
    opcion = st.radio("Seleccione una opción:", ["Iniciar Sesión", "Registrarse"], index=0)
    
    if opcion == "Iniciar Sesión":
        st.subheader("Iniciar Sesión")
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            nombre, rol = autenticar_usuario(usuario, password)
            if nombre:
                st.session_state.logged_in = True
                st.session_state.usuario = usuario
                st.session_state.nombre = nombre
                st.session_state.rol = rol
                st.success(f"Bienvenido, **{nombre}**. Has iniciado sesión como **{rol}**.")
                st.experimental_rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    
    else:  # Registro
        st.subheader("Registrarse")
        nuevo_usuario = st.text_input("Nombre de usuario")
        nombre_completo = st.text_input("Nombre completo")
        password = st.text_input("Contraseña", type="password")
        rol = st.selectbox("Rol de usuario", ["estudiante", "administrador"])
        if st.button("Crear Cuenta"):
            if nuevo_usuario.strip() == "" or password.strip() == "" or nombre_completo.strip() == "":
                st.warning("Complete todos los campos.")
            else:
                usuarios_df = cargar_usuarios()
                if nuevo_usuario in usuarios_df['usuario'].values:
                    st.error("El nombre de usuario ya existe.")
                else:
                    registrar_usuario(nuevo_usuario, nombre_completo, password, rol)
                    st.success("Registro exitoso. Inicia sesión en la pestaña 'Iniciar Sesión'.")
                    st.experimental_rerun()

# Si el usuario ya inició sesión
if st.session_state.logged_in:
    st.sidebar.success(f"Sesión: {st.session_state.nombre} ({st.session_state.rol})")
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.session_state.usuario = ""
        st.session_state.nombre = ""
        st.session_state.rol = ""
        st.experimental_rerun()
    
    # Vista para estudiantes
    if st.session_state.rol == "estudiante":
        st.header("Registrar Asistencia")
        st.write("Selecciona la materia a la que asistirás y, luego, escanea el código QR correspondiente.")
        
        materia_seleccionada = st.selectbox("Selecciona la materia:", list(materias.keys()))
        
        nombre_qr = f"QR_{materia_seleccionada.replace(' ', '')}.png"
        if os.path.exists(nombre_qr):
            st.image(nombre_qr, width=150, caption=f"Código QR para {materia_seleccionada}")
        
        st.info(f"Por favor, escanea el código QR de **{materia_seleccionada}**.")
        image = st.camera_input("Escanear Código QR")
        
        if image is not None:
            bytes_data = image.getvalue()
            arr = np.frombuffer(bytes_data, np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            detector = cv2.QRCodeDetector()
            data, bbox, _ = detector.detectAndDecode(img)
            
            if data:
                scanned_qr = data.strip()
                if scanned_qr != materias[materia_seleccionada]:
                    st.error("El código QR escaneado NO corresponde a la materia seleccionada. Inténtalo nuevamente.")
                else:
                    estudiante = st.session_state.nombre
                    ahora = datetime.now()
                    fecha_str = ahora.strftime("%Y-%m-%d")
                    hora_str = ahora.strftime("%H:%M:%S")
                    
                    existe_registro = verificar_asistencia_existente(
                        estudiante, 
                        materias[materia_seleccionada], 
                        fecha_str
                    )
                    
                    if existe_registro:
                        st.warning("Ya has registrado tu asistencia para esta materia hoy.")
                    else:
                        registrar_asistencia(
                            estudiante,
                            materias[materia_seleccionada],
                            materia_seleccionada,
                            fecha_str,
                            hora_str
                        )
                        st.success(f"Asistencia registrada para **{materia_seleccionada}** - {fecha_str} {hora_str}")
            else:
                st.error("No se pudo leer el código QR. Asegúrate de que esté correctamente enfocado.")
    
    # Vista para administradores
    elif st.session_state.rol == "administrador":
        st.header("Panel de Administrador - Registros de Asistencia")
        
        lista_materias = ["Todas"] + list(materias.keys())
        filtro_materia = st.selectbox("Filtrar por materia:", lista_materias)
        filtro_fecha = st.date_input("Filtrar por fecha:")
        
        df_asistencias = obtener_asistencias(filtro_materia, filtro_fecha)
        
        if not df_asistencias.empty:
            st.subheader("Registros de Asistencia")
            st.dataframe(df_asistencias)
            
            # Opción para descargar los datos
            csv = df_asistencias.to_csv(index=False).encode('utf-8')
            st.download_button(
                "Descargar registros como CSV",
                csv,
                "asistencias.csv",
                "text/csv",
                key='download-csv'
            )
        else:
            st.info("No se encontraron registros con los filtros seleccionados.")