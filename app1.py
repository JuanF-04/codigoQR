import streamlit as st
import pandas as pd
import numpy as np
import cv2
import qrcode
from datetime import datetime
import os
import psycopg2

# — Credenciales de administrador predeterminado —
ADMIN_USER = "Administrador"
ADMIN_PASS = "123"

st.set_page_config(page_title="Asistencia QR", page_icon="🎓", layout="centered")
st.title("📚 Registro de Asistencia - App Streamlit")

def conectar_bd():
    try:
        return psycopg2.connect(
            host="aws-0-us-east-1.pooler.supabase.com",
            port=6543,
            user="postgres.fqcfrnfnsfxvjurnhtkd",
            password="zlfR123@#$",
            dbname="postgres"
        )
    except Exception as e:
        st.error(f"Error de conexión a Supabase: {e}")
        return None

# Diccionario de materias y sus IDs
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

# Generar códigos QR
for nombre, qr_id in materias.items():
    nombre_archivo = f"QR_{nombre.replace(' ', '')}.png"
    if not os.path.exists(nombre_archivo):
        qrcode.make(qr_id).save(nombre_archivo)

def cargar_usuarios():
    conn = conectar_bd()
    if not conn:
        return pd.DataFrame()
    try:
        df = pd.read_sql("SELECT * FROM usuarios;", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"No se pudo cargar usuarios: {e}")
        return pd.DataFrame()

def registrar_usuario(usuario, nombre, password, rol):
    conn = conectar_bd()
    if not conn:
        return
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO usuarios (usuario, nombre, password, rol)
            VALUES (%s, %s, %s, %s);
        """, (usuario, nombre, password, rol))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        st.error(f"No se pudo registrar el usuario: {e}")

def autenticar_usuario(usuario, password):
    # 1) Admin predeterminado
    if usuario == ADMIN_USER and password == ADMIN_PASS:
        return "Administrador de sistema", "administrador"
    # 2) Usuarios en BD
    df = cargar_usuarios()
    match = df[(df['usuario'] == usuario) & (df['password'] == password)]
    if not match.empty:
        row = match.iloc[0]
        return row['nombre'], row['rol']
    return None, None

# Estado de sesión
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.usuario   = ""
    st.session_state.nombre    = ""
    st.session_state.rol       = ""

# Pantalla de login / registro
if not st.session_state.logged_in:
    opcion = st.radio("Seleccione una opción:", ["Iniciar Sesión", "Registrarse"], index=0)
    if opcion == "Iniciar Sesión":
        st.subheader("🔑 Iniciar Sesión")
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            nombre, rol = autenticar_usuario(usuario, password)
            if nombre:
                st.session_state.logged_in = True
                st.session_state.usuario    = usuario
                st.session_state.nombre     = nombre
                st.session_state.rol        = rol
                st.success(f"Bienvenido, **{nombre}**. Rol: **{rol}**.")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    else:
        st.subheader("🆕 Registrarse (solo estudiantes)")
        nuevo_usuario   = st.text_input("Nombre de usuario")
        nombre_completo = st.text_input("Nombre completo")
        password        = st.text_input("Contraseña", type="password")
        rol             = "estudiante"
        if st.button("Crear Cuenta"):
            if not (nuevo_usuario and nombre_completo and password):
                st.warning("Complete todos los campos.")
            else:
                df = cargar_usuarios()
                if nuevo_usuario in df['usuario'].values or nuevo_usuario == ADMIN_USER:
                    st.error("El nombre de usuario ya existe.")
                else:
                    registrar_usuario(nuevo_usuario, nombre_completo, password, rol)
                    st.success("✅ ¡Te has registrado exitosamente! Ahora serás redirigido a Iniciar Sesión...")
                    st.rerun()

# Interfaz tras login
if st.session_state.logged_in:
    st.sidebar.success(f"{st.session_state.nombre} ({st.session_state.rol})")
    if st.sidebar.button("🔒 Cerrar Sesión"):
        for k in ["logged_in", "usuario", "nombre", "rol"]:
            st.session_state[k] = False if k == "logged_in" else ""
        st.rerun()

    # Panel para estudiantes
    if st.session_state.rol == "estudiante":
        st.header("Registrar Asistencia")
        mat_sel = st.selectbox("Materia:", list(materias.keys()))
        qr_file = f"QR_{mat_sel.replace(' ', '')}.png"

        if os.path.exists(qr_file):
            st.image(qr_file, width=150, caption=f"QR de {mat_sel}")

        if "qr_mode" not in st.session_state:
            st.session_state.qr_mode = False

        col1, col2 = st.columns(2)
        if col1.button("📷 Activar escáner QR"):
            st.session_state.qr_mode = True
            st.rerun()
        if col2.button("❌ Cancelar"):
            st.session_state.qr_mode = False
            st.rerun()

        if st.session_state.qr_mode:
            img = st.camera_input("Escanea el código QR")
            if img:
                data = cv2.QRCodeDetector().detectAndDecode(
                    cv2.imdecode(np.frombuffer(img.getvalue(), np.uint8), cv2.IMREAD_COLOR)
                )[0].strip()
                if data == materias[mat_sel]:
                    conn = conectar_bd()
                    if conn:
                        cur = conn.cursor()
                        ahora = datetime.now()
                        fecha = ahora.strftime("%Y-%m-%d")
                        hora  = ahora.strftime("%H:%M:%S")
                        cur.execute("""
                            SELECT 1 FROM asistencias
                            WHERE nombre=%s AND id_materia=%s AND fecha=%s
                        """, (st.session_state.nombre, materias[mat_sel], fecha))
                        if cur.fetchone():
                            st.warning("Asistencia ya registrada hoy.")
                        else:
                            cur.execute("""
                                INSERT INTO asistencias
                                (nombre, id_materia, materia, fecha, hora, created_at)
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """, (
                                st.session_state.nombre,
                                materias[mat_sel],
                                mat_sel,
                                fecha,
                                hora,
                                ahora.strftime("%Y-%m-%d %H:%M:%S")
                            ))
                            conn.commit()
                            st.success(f"Asistencia registrada: {fecha} {hora}")
                        cur.close()
                        conn.close()
                else:
                    st.error("QR no corresponde a la materia.")
                st.session_state.qr_mode = False
                st.rerun()

    # Panel para administrador
    elif st.session_state.rol == "administrador":
        st.header("📋 Panel de Administrador")
        conn = conectar_bd()
        if conn:
            df = pd.read_sql("SELECT * FROM asistencias;", conn)
            conn.close()

            # Filtro de materia
            filtro_mat = st.selectbox("Filtrar materia:", ["Todas"] + list(materias.keys()))
            if filtro_mat != "Todas":
                df = df[df['materia'] == filtro_mat]

            # Filtro de fecha opcional
            filtrar_por_fecha = st.checkbox("Filtrar por fecha", value=False)
            if filtrar_por_fecha:
                fecha_sel = st.date_input("Seleccione fecha")
                df = df[df['fecha'] == fecha_sel.strftime("%Y-%m-%d")]

            # Mostrar siempre la tabla
            st.subheader("Registros de Asistencia")
            st.dataframe(df)
        else:
            st.error("No hay conexión a la base de datos.")
