import streamlit as st
import pandas as pd
import math
import os
from datetime import datetime
from fpdf import FPDF

# =========================
# Config pagina
# =========================
st.set_page_config(page_title="🇨🇭 Torneo Svizzero x Club", layout="wide")

# =========================
# Inizializza session_state
# =========================
if "torneo_iniziato" not in st.session_state:
    st.session_state.torneo_iniziato = False
if "df_torneo" not in st.session_state:
    st.session_state.df_torneo = pd.DataFrame()
if "nome_torneo" not in st.session_state:
    st.session_state.nome_torneo = "Torneo Svizzero x Club"

# =========================
# Funzioni di utilità
# =========================
def aggiorna_classifica(df):
    classifica = {}
    for _, r in df[df["Validata"] == True].iterrows():
        casa, ospite = r["Casa"], r["Ospite"]
        golc, golo = int(r["GolCasa"]), int(r["GolOspite"])
        for squadra in [casa, ospite]:
            if squadra not in classifica:
                classifica[squadra] = {"Punti": 0, "GF": 0, "GS": 0, "DR": 0}
        classifica[casa]["GF"] += golc
        classifica[casa]["GS"] += golo
        classifica[casa]["DR"] = classifica[casa]["GF"] - classifica[casa]["GS"]
        classifica[ospite]["GF"] += golo
        classifica[ospite]["GS"] += golc
        classifica[ospite]["DR"] = classifica[ospite]["GF"] - classifica[ospite]["GS"]
        if golc > golo:
            classifica[casa]["Punti"] += 3
        elif golo > golc:
            classifica[ospite]["Punti"] += 3
        else:
            classifica[casa]["Punti"] += 1
            classifica[ospite]["Punti"] += 1
    df_classifica = pd.DataFrame([
        {"Squadra": s, **vals} for s, vals in classifica.items()
    ])
    if not df_classifica.empty:
        df_classifica = df_classifica.sort_values(
            by=["Punti", "DR", "GF"], ascending=[False, False, False]
        ).reset_index(drop=True)
    return df_classifica

def genera_pdf(df_torneo, df_classifica):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, st.session_state.nome_torneo, ln=True, align='C')
    pdf.ln(5)

    # Classifica
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "📊 Classifica", ln=True)
    pdf.set_font("Arial", '', 12)
    for _, r in df_classifica.iterrows():
        pdf.cell(0, 8, f"{r['Squadra']} - Punti: {r['Punti']} GF: {r['GF']} GS: {r['GS']} DR: {r['DR']}", ln=True)
    pdf.ln(5)

    # Partite
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "📅 Partite", ln=True)
    pdf.set_font("Arial", '', 12)
    for _, r in df_torneo.iterrows():
        validata = r.get("Validata", False)
        status = "✅" if validata else "❌"
        if validata:
            pdf.set_text_color(0, 0, 0)
        else:
            pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 8, f"Turno {r['Turno']}: {r['Casa']} {r['GolCasa']} - {r['GolOspite']} {r['Ospite']}  {status}", ln=True)
    pdf.set_text_color(0, 0, 0)

    return pdf.output(dest='S').encode('latin1', 'ignore')

# =========================
# Sidebar esportazioni
# =========================
with st.sidebar:
    st.markdown("## 💾 Esporta / Download")

    if st.session_state.torneo_iniziato and not st.session_state.df_torneo.empty:
        # CSV
        csv_data = st.session_state.df_torneo.to_csv(index=False).encode('utf-8')
        file_name = f"{st.session_state.nome_torneo.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        st.download_button(label="⬇️ Scarica CSV torneo", data=csv_data, file_name=file_name, mime="text/csv")

        # PDF
        df_class = aggiorna_classifica(st.session_state.df_torneo)
        pdf_data = genera_pdf(st.session_state.df_torneo, df_class)
        pdf_file_name = f"{st.session_state.nome_torneo.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        st.download_button(label="⬇️ Scarica PDF torneo", data=pdf_data, file_name=pdf_file_name, mime="application/pdf")

# =========================
# Vista torneo attivo
# =========================
if st.session_state.torneo_iniziato:
    st.subheader("📅 Partite in programma")
    df_visual = st.session_state.df_torneo.copy()
    st.dataframe(df_visual[["Turno", "Casa", "GolCasa", "Ospite", "GolOspite", "Validata"]])

    st.subheader("📊 Classifica")
    df_classifica = aggiorna_classifica(st.session_state.df_torneo)
    st.dataframe(df_classifica)

    # Banner vincitore se torneo concluso
    df_non_validate = st.session_state.df_torneo[st.session_state.df_torneo['Validata']==False]
    if df_non_validate.empty and not df_classifica.empty:
        vincitore = df_classifica.iloc[0]['Squadra']
        st.markdown(
            f"<div style='text-align:center; background:#ffd700; padding:15px; border-radius:10px; font-size:22px; color:#000;'>🏆 Torneo concluso! Vincitore: {vincitore} 🏆</div>",
            unsafe_allow_html=True
        )
