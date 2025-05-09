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

# --- CONFIGURACIÓN DE SEGURIDAD ---
# Define aquí tu clave secreta o guárdala en Streamlit Secrets
ADMIN_SECRET = st.secrets.get("admin_secret", "MiSuperSecreto123")

# --- CONEXIÓN A LA BD ---
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

# --- CÓDIGO QR DE MATERIAS (sin cambios) ---
materias = {
    "Álgebra Lineal": "MAT01",
    "Cálculo Diferencial": "MAT02",
    # ...
}
for nombre, qr_id in materias.items():
    nombre_archivo = f"QR_{nombre.replace(' ', '')}.png"
    if not os.path.exists(nombre_archivo):
        qrcode.make(qr_id).save(nombre_archivo)

# --- FUNCIONES DE USUARIOS ---
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
    except Exception as e:
        st.error(f"No se pudo registrar el usuario: {e}")
    finally:
        conn.close()

def autenticar_usuario(usuario, password):
    df = cargar_usuarios()
    match = df[(df.usuario == usuario) & (df.password == password)]
    if not match.empty:
        return match.iloc[0].nombre, match.iloc[0].rol
    return None, None

# --- SESIÓN ---
if "logged_in" not in st.session_state:
    st.session_state.update({
        "logged_in": False,
        "usuario": "",
        "nombre": "",
        "rol": ""
    })

# --- LOGIN / REGISTRO ---
if not st.session_state.logged_in:
    opcion = st.radio("Seleccione:", ["Iniciar Sesión", "Registrarse"])
    if opcion == "Iniciar Sesión":
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            nombre, rol = autenticar_usuario(usuario, password)
            if nombre:
                st.session_state.update({
                    "logged_in": True,
                    "usuario": usuario,
                    "nombre": nombre,
                    "rol": rol
                })
                st.success(f"Bienvenido, {nombre} ({rol})")
                st.experimental_rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    else:  # Registro
        st.subheader("Crear cuenta de Estudiante")
        nuevo_user = st.text_input("Usuario")
        nombre_completo = st.text_input("Nombre completo")
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Registrarme"):
            if not (nuevo_user and nombre_completo and pwd):
                st.warning("Complete todos los campos.")
            elif nuevo_user in cargar_usuarios().usuario.values:
                st.error("El usuario ya existe.")
            else:
                registrar_usuario(nuevo_user, nombre_completo, pwd, "estudiante")
                st.success("Cuenta de estudiante creada. Ahora inicie sesión.")
                st.experimental_rerun()

# --- PANEL PRINCIPAL ---
else:
    st.sidebar.success(f"{st.session_state.nombre} ({st.session_state.rol})")
    if st.sidebar.button("Cerrar Sesión"):
        for k in ["logged_in","usuario","nombre","rol"]:
            st.session_state[k] = False if k=="logged_in" else ""
        st.experimental_rerun()

    if st.session_state.rol == "estudiante":
        # ... código de escaneo QR sin cambios ...
        st.header("Registrar Asistencia")
        # (tu lógica de QR aquí)

    elif st.session_state.rol == "administrador":
        st.header("Panel de Administrador")

        # 1) Vista de asistencias
        conn = conectar_bd()
        if conn:
            df = pd.read_sql("SELECT * FROM asistencias;", conn)
            conn.close()
            matriz = ["Todas"] + list(materias.keys())
            filtro = st.selectbox("Materia:", matriz)
            fecha = st.date_input("Fecha:")
            if filtro != "Todas":
                df = df[df.materia == filtro]
            df = df[df.fecha == fecha.strftime("%Y-%m-%d")]
            st.dataframe(df)

        # 2) Crear nuevos usuarios (estudiantes o administradores autorizados)
        st.subheader("Crear nuevo usuario")
        user_new = st.text_input("Usuario nuevo", key="u2")
        name_new = st.text_input("Nombre completo", key="n2")
        pwd_new = st.text_input("Contraseña", type="password", key="p2")
        role_new = st.selectbox("Rol", ["estudiante", "administrador"], key="r2")
        admin_key = None
        if role_new == "administrador":
            admin_key = st.text_input("Clave de administrador", type="password", key="k2")
        if st.button("Crear usuario", key="b2"):
            if not (user_new and name_new and pwd_new):
                st.warning("Complete todos los campos.")
            elif user_new in cargar_usuarios().usuario.values:
                st.error("El usuario ya existe.")
            elif role_new == "administrador" and admin_key != ADMIN_SECRET:
                st.error("Clave de administrador inválida.")
            else:
                registrar_usuario(user_new, name_new, pwd_new, role_new)
                st.success(f"Usuario '{user_new}' creado como {role_new}.")
