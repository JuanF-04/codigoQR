import streamlit as st
import numpy as np
import pandas as pd
import cv2
from datetime import datetime
import psycopg2

# Configuración de página
st.set_page_config(page_title="Registro Asistencia QR", page_icon="📸", layout="centered")

# Conexión a Supabase (PostgreSQL)
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
        st.error(f"Error de conexión a la base de datos: {e}")
        return None

# Cargar usuarios
def cargar_usuarios():
    conn = conectar_bd()
    if not conn: return pd.DataFrame()
    try:
        df = pd.read_sql("SELECT * FROM usuarios;", conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"No se pudo cargar usuarios: {e}")
        return pd.DataFrame()

# Autenticación
def autenticar_usuario(usuario, password):
    df = cargar_usuarios()
    user = df[(df["usuario"] == usuario) & (df["password"] == password)]
    if not user.empty:
        return user.iloc[0]["nombre"]
    return None

# Materias disponibles
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

# Estado de sesión
if "nombre" not in st.session_state:
    st.session_state.nombre = None

# Login
if not st.session_state.nombre:
    st.title("🔐 Iniciar sesión")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        nombre = autenticar_usuario(usuario, password)
        if nombre:
            st.session_state.nombre = nombre
            st.success(f"Bienvenido, {nombre}")
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos.")

# Escáner de QR
else:
    st.sidebar.success(f"👤 {st.session_state.nombre}")
    st.title("📸 Escanea tu código QR")

    materia = st.selectbox("Selecciona tu materia", list(materias.keys()))

    img = st.camera_input("Escanea el código QR del salón o maestro")

    if img:
        img_array = np.frombuffer(img.getvalue(), np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        qr_detector = cv2.QRCodeDetector()
        data, _, _ = qr_detector.detectAndDecode(frame)

        if data == materias[materia]:
            conn = conectar_bd()
            if conn:
                try:
                    now = datetime.now()
                    cur = conn.cursor()
                    cur.execute("""
                        SELECT 1 FROM asistencias
                        WHERE nombre=%s AND id_materia=%s AND fecha=%s
                    """, (st.session_state.nombre, data, now.date()))
                    if cur.fetchone():
                        st.warning("⚠️ Ya registraste tu asistencia hoy.")
                    else:
                        cur.execute("""
                            INSERT INTO asistencias (nombre, id_materia, materia, fecha, hora, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            st.session_state.nombre,
                            data,
                            materia,
                            now.date().isoformat(),
                            now.strftime("%H:%M:%S"),
                            now.strftime("%Y-%m-%d %H:%M:%S")
                        ))
                        conn.commit()
                        st.success("✅ Asistencia registrada correctamente.")
                    cur.close(); conn.close()
                except Exception as e:
                    st.error(f"Error al registrar asistencia: {e}")
        else:
            st.error("❌ El código QR no coincide con la materia seleccionada.")
