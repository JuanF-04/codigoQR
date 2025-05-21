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
materias = { ... }  # igual que antes

# Generar QR si no existen
for nombre, qr_id in materias.items():
    fn = f"QR_{nombre.replace(' ', '')}.png"
    if not os.path.exists(fn):
        qrcode.make(qr_id).save(fn)

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
        return False
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO usuarios (usuario, nombre, password, rol)
            VALUES (%s, %s, %s, %s);
        """, (usuario, nombre, password, rol))
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        st.error(f"No se pudo registrar el usuario: {e}")
        return False

def autenticar_usuario(usuario, password):
    if usuario == ADMIN_USER and password == ADMIN_PASS:
        return "Administrador de sistema", "administrador"
    df = cargar_usuarios()
    m = df[(df['usuario']==usuario)&(df['password']==password)]
    if not m.empty:
        r = m.iloc[0]
        return r['nombre'], r['rol']
    return None, None

# Estado inicial
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.usuario = ""
    st.session_state.nombre  = ""
    st.session_state.rol     = ""

# Login / Registro
if not st.session_state.logged_in:
    opcion = st.radio("Seleccione una opción:", ["Iniciar Sesión", "Registrarse"])
    
    if opcion == "Iniciar Sesión":
        st.subheader("🔑 Iniciar Sesión")
        usr = st.text_input("Usuario")
        pwd = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            nombre, rol = autenticar_usuario(usr, pwd)
            if nombre:
                st.session_state.logged_in = True
                st.session_state.usuario    = usr
                st.session_state.nombre     = nombre
                st.session_state.rol        = rol
                st.experimental_rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    else:
        st.subheader("🆕 Registrarse (solo estudiantes)")
        nuevo_usr   = st.text_input("Nombre de usuario")
        nom_compl   = st.text_input("Nombre completo")
        pwd_new     = st.text_input("Contraseña", type="password")
        rol_new     = "estudiante"
        if st.button("Crear Cuenta"):
            if not (nuevo_usr and nom_compl and pwd_new):
                st.warning("Complete todos los campos.")
            else:
                df = cargar_usuarios()
                if nuevo_usr in df['usuario'].values or nuevo_usr == ADMIN_USER:
                    st.error("El nombre de usuario ya existe.")
                else:
                    if registrar_usuario(nuevo_usr, nom_compl, pwd_new, rol_new):
                        st.success("✅ ¡Te has registrado exitosamente!")
                        st.experimental_rerun()

# Panel tras login
if st.session_state.logged_in:
    st.sidebar.success(f"{st.session_state.nombre} ({st.session_state.rol})")
    if st.sidebar.button("🔒 Cerrar Sesión"):
        for k in ["logged_in", "usuario", "nombre", "rol"]:
            st.session_state[k] = False if k=="logged_in" else ""
        st.experimental_rerun()

    if st.session_state.rol == "estudiante":
        # ... tu lógica de escaneo y registro de asistencia ...
        pass
    elif st.session_state.rol == "administrador":
        # ... tu lógica de panel admin ...
        pass
