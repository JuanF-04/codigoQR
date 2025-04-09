# Proyecto: Sistema de Asistencia con Streamlit y PostgreSQL
import streamlit as st
import cv2
import qrcode
from datetime import datetime
import os
import psycopg2
from psycopg2 import sql
import pandas as pd
import numpy as np

# Configuración de la página
st.set_page_config(page_title="Asistencia QR", page_icon="🎓", layout="centered")
st.title("📚 Registro de Asistencia - App Streamlit")

# Configuración de la conexión a PostgreSQL
@st.cache_resource
def init_db_connection():
    try:
        conn = psycopg2.connect(st.secrets["postgresql"]["postgresql://postgres.fqcfrnfnsfxvjurnhtkd:zlfR123@#$@aws-0-us-east-1.pooler.supabase.com:6543/postgres"])
        return conn
    except Exception as e:
        st.error(f"Error al conectar a la base de datos: {e}")
        return None

conn = init_db_connection()

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

# Funciones para interactuar con PostgreSQL
def cargar_usuarios():
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM usuarios;")
            usuarios = cur.fetchall()
            if not usuarios:
                # Crear usuario admin por defecto si no hay usuarios
                registrar_usuario("admin", "Administrador", "admin", "administrador")
                return cargar_usuarios()
            return pd.DataFrame(usuarios, columns=['id', 'usuario', 'nombre', 'password', 'rol', 'created_at'])
    except Exception as e:
        st.error(f"Error al cargar usuarios: {e}")
        return pd.DataFrame()

def registrar_usuario(nuevo_usuario, nombre_completo, password, rol):
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("INSERT INTO usuarios (usuario, nombre, password, rol) VALUES (%s, %s, %s, %s)"),
                [nuevo_usuario, nombre_completo, password, rol]
            )
            conn.commit()
    except Exception as e:
        st.error(f"Error al registrar usuario: {e}")

def autenticar_usuario(usuario, password):
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("SELECT nombre, rol FROM usuarios WHERE usuario = %s AND password = %s"),
                [usuario, password]
            )
            result = cur.fetchone()
            return result if result else (None, None)
    except Exception as e:
        st.error(f"Error al autenticar usuario: {e}")
        return None, None

def registrar_asistencia(nombre, id_materia, materia, fecha, hora):
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("""
                    INSERT INTO asistencias (nombre, id_materia, materia, fecha, hora) 
                    VALUES (%s, %s, %s, %s, %s)
                """),
                [nombre, id_materia, materia, fecha, hora]
            )
            conn.commit()
    except Exception as e:
        st.error(f"Error al registrar asistencia: {e}")

def obtener_asistencias(filtro_materia=None, filtro_fecha=None):
    try:
        query = "SELECT * FROM asistencias"
        conditions = []
        params = []
        
        if filtro_materia and filtro_materia != "Todas":
            conditions.append("materia = %s")
            params.append(filtro_materia)
        
        if filtro_fecha:
            conditions.append("fecha = %s")
            params.append(filtro_fecha.strftime("%Y-%m-%d"))
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        with conn.cursor() as cur:
            cur.execute(query, params)
            columns = [desc[0] for desc in cur.description]
            data = cur.fetchall()
            return pd.DataFrame(data, columns=columns)
    except Exception as e:
        st.error(f"Error al obtener asistencias: {e}")
        return pd.DataFrame()

def verificar_asistencia_existente(nombre, id_materia, fecha):
    try:
        with conn.cursor() as cur:
            cur.execute(
                sql.SQL("""
                    SELECT COUNT(*) FROM asistencias 
                    WHERE nombre = %s AND id_materia = %s AND fecha = %s
                """),
                [nombre, id_materia, fecha]
            )
            return cur.fetchone()[0] > 0
    except Exception as e:
        st.error(f"Error al verificar asistencia: {e}")
        return False

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