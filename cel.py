import streamlit as st
import numpy as np
import cv2
from datetime import datetime
import psycopg2

# Configuración de página
st.set_page_config(page_title="Escáner QR", page_icon="📸", layout="centered")

st.title("📸 Escáner QR de Asistencia")
st.markdown("Escanea un código QR para registrar la asistencia en la base de datos.")

# Función para conectar a Supabase (PostgreSQL)
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

# Interfaz de escaneo QR
img = st.camera_input("Escanea el código QR")

if img:
    # Procesar imagen de QR
    img_array = np.frombuffer(img.getvalue(), np.uint8)
    frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    qr_detector = cv2.QRCodeDetector()
    data, _, _ = qr_detector.detectAndDecode(frame)

    if data:
        st.success(f"📦 QR Detectado: `{data}`")
        now = datetime.now()

        # Conectar y registrar en base de datos
        conn = conectar_bd()
        if conn:
            try:
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO asistencias (nombre, id_materia, materia, fecha, hora, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    "QR_SinUsuario",  # Nombre ficticio
                    data,            # El ID leído desde el QR
                    "Desconocida",   # Puedes ajustar esto si codificas el nombre en el QR
                    now.date().isoformat(),
                    now.strftime("%H:%M:%S"),
                    now.strftime("%Y-%m-%d %H:%M:%S")
                ))
                conn.commit()
                st.success("✅ Asistencia registrada correctamente.")
            except Exception as e:
                st.error(f"❌ Error al registrar asistencia: {e}")
            finally:
                conn.close()
    else:
        st.error("⚠️ No se pudo leer ningún código QR.")
