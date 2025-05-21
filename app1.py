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

# — Definición del diccionario de materias y sus IDs —
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

# — Generar QR si no existen —
for nombre, qr_id in materias.items():
    fn = f"QR_{nombre.replace(' ', '')}.png"
    if not os.path.exists(fn):
        qrcode.make(qr_id).save(fn)

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
    match = df[(df['usuario']==usuario)&(df['password']==password)]
    if not match.empty:
        row = match.iloc[0]
        return row['nombre'], row['rol']
    return None, None

# — Inicializar session_state —
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.usuario   = ""
    st.session_state.nombre    = ""
    st.session_state.rol       = ""
if "opcion" not in st.session_state:
    st.session_state.opcion = "Iniciar Sesión"
if "registered" not in st.session_state:
    st.session_state.registered = False

# — Pantalla de login / registro —
if not st.session_state.logged_in:
    # radio controlada por session_state.opcion
    opcion = st.radio("Seleccione una opción:",
                      ["Iniciar Sesión","Registrarse"],
                      key="opcion")
    
    if opcion == "Iniciar Sesión":
        st.subheader("🔑 Iniciar Sesión")
        usuario = st.text_input("Usuario", key="login_usr")
        password = st.text_input("Contraseña", type="password", key="login_pwd")
        if st.button("Ingresar"):
            nombre, rol = autenticar_usuario(usuario, password)
            if nombre:
                st.session_state.logged_in = True
                st.session_state.usuario    = usuario
                st.session_state.nombre     = nombre
                st.session_state.rol        = rol
                st.experimental_rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
    
    else:  # Registrarse
        st.subheader("🆕 Registrarse (solo estudiantes)")
        nuevo_usr = st.text_input("Nombre de usuario", key="reg_usr")
        nom_compl = st.text_input("Nombre completo", key="reg_name")
        pwd_new   = st.text_input("Contraseña", type="password", key="reg_pwd")
        if st.button("Crear Cuenta"):
            if not (nuevo_usr and nom_compl and pwd_new):
                st.warning("Complete todos los campos.")
            else:
                df = cargar_usuarios()
                if nuevo_usr in df['usuario'].values or nuevo_usr==ADMIN_USER:
                    st.error("El nombre de usuario ya existe.")
                else:
                    if registrar_usuario(nuevo_usr, nom_compl, pwd_new, "estudiante"):
                        # marcamos que hubo registro y recargamos
                        st.session_state.registered = True
                        st.experimental_rerun()
    
    # después del form, chequeamos si registramos, mostramos éxito y forzamos volver al login
    if st.session_state.registered:
        st.success("✅ ¡Te has registrado exitosamente!")
        # restaurar el estado de la radio
        st.session_state.opcion = "Iniciar Sesión"
        st.session_state.registered = False
        st.experimental_rerun()

# — Panel tras login —
if st.session_state.logged_in:
    st.sidebar.success(f"{st.session_state.nombre} ({st.session_state.rol})")
    if st.sidebar.button("🔒 Cerrar Sesión"):
        st.session_state.logged_in = False
        st.session_state.usuario   = ""
        st.session_state.nombre    = ""
        st.session_state.rol       = ""
        st.session_state.opcion    = "Iniciar Sesión"
        st.experimental_rerun()

    if st.session_state.rol == "estudiante":
        # ... lógica de asistencia ...
        pass
    else:
        # ... panel administrador ...
        pass
