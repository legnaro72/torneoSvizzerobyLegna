import streamlit as st
import pandas as pd
import math
import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# =========================
# Config & stile di pagina
# =========================
st.set_page_config(page_title="🇨🇭 Torneo Svizzero x Club", layout="wide")

# =========================
# Funzioni utili
# =========================
def aggiorna_classifica(df):
    """Crea la classifica aggiornata da df partite validate"""
    squadre = pd.unique(df[["Casa", "Ospite"]].values.ravel())
    classifica = {sq: {"Punti":0,"GF":0,"GS":0,"G":0} for sq in squadre}

    for _, r in df.iterrows():
        if not r["Validata"]:
            continue
        casa, ospite = r["Casa"], r["Ospite"]
        gc, go = int(r["GolCasa"]), int(r["GolOspite"])
        classifica[casa]["GF"] += gc
        classifica[casa]["GS"] += go
        classifica[ospite]["GF"] += go
        classifica[ospite]["GS"] += gc
        classifica[casa]["G"] += 1
        classifica[ospite]["G"] += 1
        if gc > go:
            classifica[casa]["Punti"] += 3
        elif gc < go:
            classifica[ospite]["Punti"] += 3
        else:
            classifica[casa]["Punti"] += 1
            classifica[ospite]["Punti"] += 1

    df_class = pd.DataFrame([
        {"Squadra": sq, "Punti": d["Punti"], "GF": d["GF"], "GS": d["GS"], "DR": d["GF"]-d["GS"], "G": d["G"]}
        for sq,d in classifica.items()
    ])
    df_class = df_class.sort_values(by=["Punti","DR","GF"], ascending=[False,False,False]).reset_index(drop=True)
    return df_class

def genera_pdf(df_partite, df_classifica, torneo_completo=True):
    """Genera PDF con calendario e classifica"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()

    titolo = Paragraph(f"<b>{st.session_state.nome_torneo}</b>", styles['Title'])
    story.append(titolo)
    story.append(Spacer(1, 12))

    # Partite
    story.append(Paragraph("<b>Calendario Partite</b>", styles['Heading2']))
    data = [["Turno", "Casa", "Gol", "Ospite", "Gol", "Stato"]]
    for _, r in df_partite.iterrows():
        stato = "✅ Giocata" if r["Validata"] else "⏳ Da giocare"
        colore = colors.black if r["Validata"] else colors.red
        row = [
            str(r["Turno"]),
            Paragraph(f"<font color='{colore.rgb()}'>"+str(r["Casa"])+"</font>", styles['Normal']),
            Paragraph(f"<font color='{colore.rgb()}'>"+str(r["GolCasa"])+"</font>", styles['Normal']),
            Paragraph(f"<font color='{colore.rgb()}'>"+str(r["Ospite"])+"</font>", styles['Normal']),
            Paragraph(f"<font color='{colore.rgb()}'>"+str(r["GolOspite"])+"</font>", styles['Normal']),
            Paragraph(f"<font color='{colore.rgb()}'>"+stato+"</font>", styles['Normal'])
        ]
        data.append(row)

    t = Table(data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('ALIGN', (2,1), (2,-1), 'CENTER'),
        ('ALIGN', (4,1), (4,-1), 'CENTER'),
    ]))
    story.append(t)
    story.append(Spacer(1, 20))

    # Classifica
    if not df_classifica.empty:
        if torneo_completo:
            story.append(Paragraph("<b>Classifica Finale</b>", styles['Heading2']))
            colore = colors.black
        else:
            story.append(Paragraph("<b>Classifica Parziale</b>", styles['Heading2']))
            colore = colors.red

        data_class = [list(df_classifica.columns)] + df_classifica.astype(str).values.tolist()
        data_class_colored = []
        for i, row in enumerate(data_class):
            if i == 0:  
                data_class_colored.append(row)
            else:
                data_class_colored.append([Paragraph(f"<font color='{colore.rgb()}'>"+c+"</font>", styles['Normal']) for c in row])

        t2 = Table(data_class_colored, repeatRows=1)
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ]))
        story.append(t2)

        if torneo_completo:
            vincitore = df_classifica.iloc[0]["Squadra"]
            story.append(Spacer(1, 20))
            story.append(Paragraph(f"🏆 Vincitore del torneo: <b>{vincitore}</b>", styles['Title']))

    doc.build(story)
    buffer.seek(0)
    return buffer

# =========================
# Stato app
# =========================
if "torneo_iniziato" not in st.session_state:
    st.session_state.torneo_iniziato = False
if "df_torneo" not in st.session_state:
    st.session_state.df_torneo = pd.DataFrame()
if "nome_torneo" not in st.session_state:
    st.session_state.nome_torneo = "Torneo Subbuteo"

# =========================
# Creazione torneo demo
# =========================
if not st.session_state.torneo_iniziato:
    st.title("🇨🇭 Torneo Svizzero x Club")
    st.info("Demo avviata con un torneo fittizio (4 squadre, girone unico andata).")
    squadre = ["Milan","Inter","Juve","Roma"]
    partite = []
    turno = 1
    for i in range(len(squadre)):
        for j in range(i+1,len(squadre)):
            partite.append({"Turno": turno,"Casa": squadre[i],"Ospite": squadre[j],
                            "GolCasa":0,"GolOspite":0,"Validata": False})
            turno += 1
    st.session_state.df_torneo = pd.DataFrame(partite)
    st.session_state.torneo_iniziato = True

# =========================
# Vista torneo
# =========================
st.header(st.session_state.nome_torneo)

df = st.session_state.df_torneo
for i, row in df.iterrows():
    col1,col2,col3,col4,col5 = st.columns([2,1,2,1,1])
    with col1: st.write(row["Casa"])
    with col2: g1 = st.number_input(" ", min_value=0, max_value=20, value=int(row["GolCasa"]), key=f"c_{i}")
    with col3: st.write(row["Ospite"])
    with col4: g2 = st.number_input("  ", min_value=0, max_value=20, value=int(row["GolOspite"]), key=f"o_{i}")
    with col5: 
        if st.checkbox("Valida", value=row["Validata"], key=f"v_{i}"):
            df.at[i,"Validata"] = True
        df.at[i,"GolCasa"] = g1
        df.at[i,"GolOspite"] = g2

st.session_state.df_torneo = df

# =========================
# Classifica
# =========================
df_class = aggiorna_classifica(df)
st.subheader("Classifica")
st.dataframe(df_class, hide_index=True, use_container_width=True)

# Vincitore se torneo finito
if all(df["Validata"]) and not df_class.empty:
    vincitore = df_class.iloc[0]["Squadra"]
    st.success(f"🏆 Vincitore del torneo: {vincitore}")

# =========================
# Export in sidebar
# =========================
with st.sidebar:
    st.markdown("### 📂 Esporta Dati")

    # Export CSV
    csv_data = st.session_state.df_torneo.to_csv(index=False).encode('utf-8')
    file_name_csv = f"{st.session_state.nome_torneo.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    st.download_button("⬇️ Scarica CSV", data=csv_data, file_name=file_name_csv, mime="text/csv")

    # Export PDF
    torneo_completo = all(st.session_state.df_torneo["Validata"])
    pdf_buffer = genera_pdf(st.session_state.df_torneo, df_class, torneo_completo)
    file_name_pdf = f"{st.session_state.nome_torneo.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    st.download_button("📄 Esporta PDF", data=pdf_buffer, file_name=file_name_pdf, mime="application/pdf")
