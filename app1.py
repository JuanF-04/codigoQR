import streamlit as st
import pandas as pd
import numpy as np
import cv2
import qrcode
from datetime import datetime
import os
import psycopg2

# — Credenciales de administrador —
ADMIN_USER = "Administrador"
ADMIN_PASS = "123"

st.set_page_config(page_title="Asistencia QR", page_icon="🎓", layout="centered")

# 1) Función helper para fondo
def set_bg(style: str):
    """Recibe CSS dentro de <style> para pintar el fondo."""
    st.markdown(f"<style>{style}</style>", unsafe_allow_html=True)

# 2) CSS por sección
CSS_LOGIN = """
.stApp {
    background: linear-gradient(135deg, #89f7fe 0%, #66a6ff 100%);
}
"""
CSS_REGISTER = """
.stApp {
    background: linear-gradient(135deg, #c3ffbd 0%, #69d2e7 100%);
}
"""
CSS_ESTUDIANTE = """
.stApp {
    background: linear-gradient(135deg, #ffecd2 0%, #fcb69f 100%);
}
"""
CSS_ADMIN = """
.stApp {
    background: linear-gradient(135deg, #f8cdda 0%, #1d2b64 100%);
}
"""

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
        st.error(f"Error de conexión: {e}")
        return None

# Diccionario de materias
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

# Generar QR estático
for nombre, qr_id in materias.items():
    fn = f"QR_{nombre.replace(' ','')}.png"
    if not os.path.exists(fn):
        qrcode.make(qr_id).save(fn)

# Cargar usuarios
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

# Registrar usuario
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

# Autenticar usuario
def autenticar_usuario(usuario, password):
    if usuario == ADMIN_USER and password == ADMIN_PASS:
        return "Administrador de sistema", "administrador"
    df = cargar_usuarios()
    match = df[(df.usuario == usuario) & (df.password == password)]
    if not match.empty:
        row = match.iloc[0]
        return row.nombre, row.rol
    return None, None

# — Sesión —
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.usuario   = ""
    st.session_state.nombre    = ""
    st.session_state.rol       = ""
    st.session_state.opcion    = "Iniciar Sesión"  # inicializa radio

# —– Login / Registro —–
if not st.session_state.logged_in:
    opcion = st.radio(
        "Seleccione una opción:",
        ["Iniciar Sesión", "Registrarse"],
        key="opcion"
    )

    if opcion == "Iniciar Sesión":
        set_bg(CSS_LOGIN)
        st.subheader("🔑 Iniciar Sesión")
        user = st.text_input("Usuario")
        pwd  = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            nombre, rol = autenticar_usuario(user, pwd)
            if nombre:
                st.session_state.update({
                    "logged_in": True,
                    "usuario": user,
                    "nombre": nombre,
                    "rol": rol
                })
                st.success(f"Bienvenido, **{nombre}** ({rol})")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    else:
        set_bg(CSS_REGISTER)
        st.subheader("🆕 Registrarse (solo estudiantes)")
        new_u = st.text_input("Nombre de usuario")
        full  = st.text_input("Nombre completo")
        pwd2  = st.text_input("Contraseña", type="password")
        if st.button("Crear Cuenta"):
            if not (new_u and full and pwd2):
                st.warning("Complete todos los campos.")
            else:
                df = cargar_usuarios()
                if new_u in df.usuario.values or new_u == ADMIN_USER:
                    st.error("El usuario ya existe.")
                else:
                    registrar_usuario(new_u, full, pwd2, "estudiante")
                    st.success("✅ Registrado. Ahora inicia sesión.")
                    # tras registro, cambiar a login y recargar
                    st.session_state.opcion = "Iniciar Sesión"
                    st.rerun()

# —– Panel tras login —–
if st.session_state.logged_in:
    st.sidebar.success(f"{st.session_state.nombre} ({st.session_state.rol})")
    if st.sidebar.button("🔒 Cerrar Sesión"):
        for k in ["logged_in","usuario","nombre","rol","opcion"]:
            st.session_state[k] = False if k == "logged_in" else ""
        st.session_state.opcion = "Iniciar Sesión"
        st.rerun()

    # Estudiante
    if st.session_state.rol == "estudiante":
        set_bg(CSS_ESTUDIANTE)
        st.header("Registrar Asistencia")
        mat_sel = st.selectbox("Materia:", list(materias.keys()))
        fn = f"QR_{mat_sel.replace(' ','')}.png"
        if os.path.exists(fn):
            st.image(fn, width=150, caption=f"QR de {mat_sel}")

        if "qr_mode" not in st.session_state:
            st.session_state.qr_mode = False

        c1, c2 = st.columns(2)
        if c1.button("📷 Escanear QR"):
            st.session_state.qr_mode = True
            st.rerun()
        if c2.button("❌ Cancelar"):
            st.session_state.qr_mode = False
            st.rerun()

        if st.session_state.qr_mode:
            img = st.camera_input("Escanea el QR")
            if img:
                data = cv2.QRCodeDetector().detectAndDecode(
                    cv2.imdecode(np.frombuffer(img.getvalue(), np.uint8), cv2.IMREAD_COLOR)
                )[0].strip()
                if data == materias[mat_sel]:
                    conn = conectar_bd()
                    if conn:
                        cur = conn.cursor()
                        now = datetime.now()
                        fstr = now.strftime("%Y-%m-%d")
                        hstr = now.strftime("%H:%M:%S")
                        cur.execute("""
                            SELECT 1 FROM asistencias
                            WHERE nombre=%s AND id_materia=%s AND fecha=%s
                        """, (st.session_state.nombre, materias[mat_sel], fstr))
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
                                fstr,
                                hstr,
                                now.strftime("%Y-%m-%d %H:%M:%S")
                            ))
                            conn.commit()
                            st.success(f"Asistencia registrada: {fstr} {hstr}")
                        cur.close()
                        conn.close()
                else:
                    st.error("QR no coincide.")
                st.session_state.qr_mode = False
                st.rerun()

    # Administrador
    elif st.session_state.rol == "administrador":
        set_bg(CSS_ADMIN)
        st.header("📋 Panel de Administrador")
        conn = conectar_bd()
        if conn:
            df = pd.read_sql("SELECT * FROM asistencias;", conn, parse_dates=["fecha"])
            conn.close()
            df["fecha"] = df["fecha"].dt.date

            filtro_mat = st.selectbox("Filtrar materia:", ["Todas"] + list(materias.keys()))
            if filtro_mat != "Todas":
                df = df[df.materia == filtro_mat]

            if st.checkbox("Filtrar por fecha"):
                fecha_sel = st.date_input("Seleccione fecha")
                df = df[df.fecha == fecha_sel]

            st.subheader("Registros de Asistencia")
            st.dataframe(df)
        else:
            st.error("Sin conexión a BD.")
