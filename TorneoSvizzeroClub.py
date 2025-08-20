import streamlit as st
import pandas as pd
import os
from fpdf import FPDF
import base64

# =========================
# Config & stile di pagina
# =========================
st.set_page_config(page_title="🇨🇭 Torneo Svizzero x Club", layout="wide")

# =========================
# Funzioni di supporto
# =========================
def calcola_classifica(partite):
    classifica = {}
    for _, row in partite.iterrows():
        if row["Validata"]:
            casa, trasf = row["Squadra Casa"], row["Squadra Trasferta"]
            gol_casa, gol_trasf = row["Gol Casa"], row["Gol Trasferta"]

            for squadra in [casa, trasf]:
                if squadra not in classifica:
                    classifica[squadra] = {"Punti": 0, "GF": 0, "GS": 0, "Diff": 0}

            classifica[casa]["GF"] += gol_casa
            classifica[casa]["GS"] += gol_trasf
            classifica[casa]["Diff"] = classifica[casa]["GF"] - classifica[casa]["GS"]

            classifica[trasf]["GF"] += gol_trasf
            classifica[trasf]["GS"] += gol_casa
            classifica[trasf]["Diff"] = classifica[trasf]["GF"] - classifica[trasf]["GS"]

            if gol_casa > gol_trasf:
                classifica[casa]["Punti"] += 3
            elif gol_casa < gol_trasf:
                classifica[trasf]["Punti"] += 3
            else:
                classifica[casa]["Punti"] += 1
                classifica[trasf]["Punti"] += 1

    df = pd.DataFrame(classifica).T.reset_index()
    df = df.rename(columns={"index": "Squadra"})
    df = df.sort_values(by=["Punti", "Diff", "GF"], ascending=[False, False, False]).reset_index(drop=True)
    return df

def torneo_concluso(partite):
    return partite["Validata"].all()

def genera_pdf(partite, classifica, concluso):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    pdf.cell(0, 10, "Calendario & Classifica Torneo Svizzero", ln=True, align="C")

    # Sezione partite
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 10, "Partite:", ln=True)

    for _, row in partite.iterrows():
        if row["Validata"]:
            pdf.set_text_color(0, 0, 0)  # nero
        else:
            pdf.set_text_color(255, 0, 0)  # rosso

        testo = f"{row['Squadra Casa']} {row['Gol Casa']} - {row['Gol Trasferta']} {row['Squadra Trasferta']}"
        pdf.set_font("Arial", "", 11)
        pdf.cell(0, 8, testo, ln=True)

    # Sezione classifica
    if not classifica.empty:
        pdf.ln(5)
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 10, "Classifica:", ln=True)

        if concluso:
            pdf.set_text_color(0, 0, 0)  # nero
        else:
            pdf.set_text_color(255, 0, 0)  # rosso

        for _, row in classifica.iterrows():
            testo = f"{row['Squadra']} - Punti: {row['Punti']} | Diff: {row['Diff']} | GF: {row['GF']} | GS: {row['GS']}"
            pdf.set_font("Arial", "", 11)
            pdf.cell(0, 8, testo, ln=True)

        # Vincitore se concluso
        if concluso:
            vincitore = classifica.iloc[0]["Squadra"]
            pdf.ln(10)
            pdf.set_font("Arial", "B", 14)
            pdf.set_text_color(0, 128, 0)  # verde
            pdf.cell(0, 12, f"🏆 Vincitore del torneo: {vincitore}", ln=True, align="C")

    return pdf

def scarica_pdf(pdf, filename="torneo.pdf"):
    file_path = f"/tmp/{filename}"
    pdf.output(file_path)
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    href = f'<a href="data:application/octet-stream;base64,{b64}" download="{filename}">📥 Scarica PDF</a>'
    st.sidebar.markdown(href, unsafe_allow_html=True)

# =========================
# Demo partite
# =========================
if "partite" not in st.session_state:
    st.session_state.partite = pd.DataFrame([
        {"Squadra Casa": "Milan", "Gol Casa": 2, "Squadra Trasferta": "Inter", "Gol Trasferta": 1, "Validata": True},
        {"Squadra Casa": "Juve", "Gol Casa": 0, "Squadra Trasferta": "Roma", "Gol Trasferta": 0, "Validata": False},
    ])

partite = st.session_state.partite
classifica = calcola_classifica(partite)
concluso = torneo_concluso(partite)

# =========================
# UI
# =========================
st.title("🇨🇭 Torneo Svizzero x Club")

st.subheader("📋 Calendario")
st.dataframe(partite)

st.subheader("📊 Classifica")
if concluso:
    st.dataframe(classifica)
    vincitore = classifica.iloc[0]["Squadra"]
    st.success(f"🏆 Vincitore del torneo: **{vincitore}** 🎉")
else:
    st.error("Classifica provvisoria (torneo non concluso)")
    st.dataframe(classifica)

# =========================
# PDF Export
# =========================
st.sidebar.title("📤 Esporta")
pdf = genera_pdf(partite, classifica, concluso)
scarica_pdf(pdf, "torneo.pdf")
