import streamlit as st
import pandas as pd
import random
import os
from fpdf import FPDF
import base64

# =========================
# Config & stile di pagina
# =========================
st.set_page_config(page_title="🇨🇭 Torneo Svizzero x Club", layout="wide")

# =========================
# Funzione PDF
# =========================
def genera_pdf(df_partite, df_classifica):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    # Titolo
    pdf.cell(200, 10, txt="Calendario Torneo Svizzero", ln=True, align='C')
    pdf.ln(10)

    # Partite
    pdf.set_font("Arial", size=10)
    for _, row in df_partite.iterrows():
        testo = f"{row['Turno']} - {row['Casa']} {row['GolCasa']} : {row['GolOspite']} {row['Ospite']}"
        pdf.cell(200, 8, txt=testo, ln=True)

    pdf.ln(10)

    # Classifica
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Classifica", ln=True, align='C')
    pdf.ln(8)

    pdf.set_font("Arial", size=10)
    for _, row in df_classifica.iterrows():
        testo = f"{row['Squadra']} - Pt: {row['Punti']} - GF: {row['GF']} - GS: {row['GS']} - DR: {row['DR']}"
        pdf.cell(200, 8, txt=testo, ln=True)

    # Scarta caratteri non supportati da latin1
    return pdf.output(dest='S').encode('latin1', 'ignore')


# =========================
# Inizializza sessione
# =========================
if "df_torneo" not in st.session_state:
    st.session_state.df_torneo = pd.DataFrame(columns=["Turno","Casa","GolCasa","Ospite","GolOspite","Validata"])

if "df_classifica" not in st.session_state:
    st.session_state.df_classifica = pd.DataFrame(columns=["Squadra","Punti","GF","GS","DR"])


# =========================
# UI App
# =========================
st.title("🇨🇭 Torneo Svizzero x Club")

st.subheader("📅 Calendario Partite")
st.dataframe(st.session_state.df_torneo)

st.subheader("📊 Classifica")
st.dataframe(st.session_state.df_classifica)

# =========================
# Download PDF
# =========================
if not st.session_state.df_torneo.empty and not st.session_state.df_classifica.empty:
    pdf_data = genera_pdf(st.session_state.df_torneo, st.session_state.df_classifica)
    st.download_button(
        label="⬇️ Scarica PDF Torneo",
        data=pdf_data,
        file_name="torneo_svizzero.pdf",
        mime="application/pdf"
    )

