
import streamlit as st
import pandas as pd
import numpy as np
import cv2
import qrcode
from datetime import datetime
import os
import psycopg2

st.set_page_config(page_title="Asistencia QR", page_icon="🎓", layout="centered")
st.title("📚 Registro de Asistencia - App Streamlit")

def conectar_bd():
    try:
        conn = psycopg2.connect(
            host="aws-0-us-east-1.pooler.supabase.com",
            port=6543,
            user="postgres.fqcfrnfnsfxvjurnhtkd",
            password="zlfR123@#$",
            dbname="postgres"
        )
        return conn
    except Exception as e:
        st.error(f"Error de conexión a Supabase: {e}")
        return None

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

for nombre, qr_id in materias.items():
    nombre_archivo = f"QR_{nombre.replace(' ', '')}.png"
    if not os.path.exists(nombre_archivo):
        img_qr = qrcode.make(qr_id)
        img_qr.save(nombre_archivo)

def cargar_usuarios():
    conn = conectar_bd()
    if conn:
        try:
            df = pd.read_sql("SELECT * FROM usuarios;", conn)
            conn.close()
            return df
        except Exception as e:
            st.error(f"No se pudo cargar usuarios: {e}")
    return pd.DataFrame()

def registrar_usuario(nuevo_usuario, nombre_completo, password, rol):
    conn = conectar_bd()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO usuarios (usuario, nombre, password, rol)
                VALUES (%s, %s, %s, %s);
            """, (nuevo_usuario, nombre_completo, password, rol))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            st.error(f"No se pudo registrar el usuario: {e}")

def autenticar_usuario(usuario, password):
    df = cargar_usuarios()
    registro = df[(df['usuario'] == usuario) & (df['password'] == password)]
    if not registro.empty:
        return registro.iloc[0]['nombre'], registro.iloc[0]['rol']
    return None, None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.usuario = ""
    st.session_state.nombre = ""
    st.session_state.rol = ""

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
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    else:
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
                    st.rerun()

if st.session_state.logged_in:
    st.sidebar.success(f"Sesión: {st.session_state.nombre} ({st.session_state.rol})")
    if st.button("Cerrar Sesión"):
        st.session_state.logged_in = False
        st.session_state.usuario = ""
        st.session_state.nombre = ""
        st.session_state.rol = ""
        st.rerun()

    if st.session_state.rol == "estudiante":
        st.header("Registrar Asistencia")
        materia_seleccionada = st.selectbox("Selecciona la materia:", list(materias.keys()))
        nombre_qr = f"QR_{materia_seleccionada.replace(' ', '')}.png"
        if os.path.exists(nombre_qr):
            st.image(nombre_qr, width=150, caption=f"Código QR para {materia_seleccionada}")

        if "qr_mode" not in st.session_state:
            st.session_state.qr_mode = False

        if not st.session_state.qr_mode:
            if st.button("Activar escáner QR"):
                st.session_state.qr_mode = True
                st.rerun()
        else:
            image = st.camera_input("Escanea el código QR")
            if image is not None:
                bytes_data = image.getvalue()
                arr = np.frombuffer(bytes_data, np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                detector = cv2.QRCodeDetector()
                data, bbox, _ = detector.detectAndDecode(img)
                if data:
                    scanned_qr = data.strip()
                    if scanned_qr != materias[materia_seleccionada]:
                        st.error("El código QR no corresponde a la materia seleccionada.")
                    else:
                        conn = conectar_bd()
                        if conn:
                            try:
                                cursor = conn.cursor()
                                estudiante = st.session_state.nombre
                                ahora = datetime.now()
                                fecha_str = ahora.strftime("%Y-%m-%d")
                                hora_str = ahora.strftime("%H:%M:%S")
                                created_at = ahora.strftime("%Y-%m-%d %H:%M:%S")
                                cursor.execute("""
                                    SELECT * FROM asistencias
                                    WHERE nombre = %s AND id_materia = %s AND fecha = %s;
                                """, (estudiante, materias[materia_seleccionada], fecha_str))
                                existe = cursor.fetchall()
                                if existe:
                                    st.warning("Ya has registrado asistencia para esta materia hoy.")
                                else:
                                    cursor.execute("""
                                        INSERT INTO asistencias (nombre, id_materia, materia, fecha, hora, created_at)
                                        VALUES (%s, %s, %s, %s, %s, %s);
                                    """, (estudiante, materias[materia_seleccionada], materia_seleccionada, fecha_str, hora_str, created_at))
                                    conn.commit()
                                    st.success(f"Asistencia registrada para {materia_seleccionada} - {fecha_str} {hora_str}")
                                cursor.close()
                                conn.close()
                            except Exception as e:
                                st.error(f"No se pudo registrar la asistencia: {e}")
                st.session_state.qr_mode = False
                st.rerun()

    elif st.session_state.rol == "administrador":
        st.header("Panel de Administrador - Registros de Asistencia")
        conn = conectar_bd()
        if conn:
            try:
                df = pd.read_sql("SELECT * FROM asistencias;", conn)
                conn.close()
                lista_materias = ["Todas"] + list(materias.keys())
                filtro_materia = st.selectbox("Filtrar por materia:", lista_materias)
                filtro_fecha = st.date_input("Filtrar por fecha:")
                if filtro_materia != "Todas":
                    df = df[df['materia'] == filtro_materia]
                if filtro_fecha:
                    fecha_str = filtro_fecha.strftime("%Y-%m-%d")
                    df = df[df['fecha'] == fecha_str]
                st.subheader("Registros de Asistencia")
                st.dataframe(df)
            except Exception as e:
                st.error(f"No se pudieron cargar los registros: {e}")
        else:
            st.info("No hay conexión con la base de datos.")
