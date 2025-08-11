import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

st.set_page_config(page_title="Torneo Subbuteo - Sistema Svizzero", layout="wide")

# --- Funzioni ---

def aggiorna_classifica(df):
    stats = {}
    for _, r in df.iterrows():
        if not r['Validata']:
            continue
        for squadra, gol, gol_avv in [(r['Casa'], r['GolCasa'], r['GolOspite']),
                                     (r['Ospite'], r['GolOspite'], r['GolCasa'])]:
            if squadra not in stats:
                stats[squadra] = {'Punti': 0, 'GF': 0, 'GS': 0, 'DR': 0}
            stats[squadra]['GF'] += gol
            stats[squadra]['GS'] += gol_avv
            stats[squadra]['DR'] = stats[squadra]['GF'] - stats[squadra]['GS']
        if r['GolCasa'] > r['GolOspite']:
            stats[r['Casa']]['Punti'] += 2
        elif r['GolCasa'] < r['GolOspite']:
            stats[r['Ospite']]['Punti'] += 2
        else:
            stats[r['Casa']]['Punti'] += 1
            stats[r['Ospite']]['Punti'] += 1

    if not stats:
        return pd.DataFrame(columns=['Squadra', 'Punti', 'GF', 'GS', 'DR'])
    df_classifica = pd.DataFrame([{'Squadra': squadra, **dati} for squadra, dati in stats.items()])
    df_classifica = df_classifica.sort_values(by=['Punti', 'DR', 'GF'], ascending=False).reset_index(drop=True)
    return df_classifica

def genera_accoppiamenti(classifica, precedenti):
    accoppiamenti = []
    gia_abbinati = set()
    for i, r1 in classifica.iterrows():
        squadra1 = r1['Squadra']
        if squadra1 in gia_abbinati:
            continue
        for j in range(i + 1, len(classifica)):
            squadra2 = classifica.iloc[j]['Squadra']
            if squadra2 in gia_abbinati:
                continue
            if (squadra1, squadra2) not in precedenti and (squadra2, squadra1) not in precedenti:
                accoppiamenti.append((squadra1, squadra2))
                gia_abbinati.add(squadra1)
                gia_abbinati.add(squadra2)
                break
    df = pd.DataFrame([{"Casa": c, "Ospite": o, "GolCasa": 0, "GolOspite": 0, "Validata": False} for c, o in accoppiamenti])
    return df

def carica_csv_robusto_da_url(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        text = response.content.decode('latin1')
        df = pd.read_csv(io.StringIO(text))
        return df
    except Exception as e:
        st.warning(f"Errore caricamento CSV da URL: {e}")
        return pd.DataFrame()

def carica_csv_robusto_da_file(file_buffer):
    try:
        content = file_buffer.read()
        text = content.decode('latin1')
        df = pd.read_csv(io.StringIO(text))
        return df
    except Exception as e:
        st.warning(f"Errore caricamento CSV da file: {e}")
        return pd.DataFrame()

# --- Stato sessione ---
if "df_torneo" not in st.session_state:
    st.session_state.df_torneo = pd.DataFrame()
if "df_squadre" not in st.session_state:
    st.session_state.df_squadre = pd.DataFrame()
if "turno_attivo" not in st.session_state:
    st.session_state.turno_attivo = 0
if "risultati_temp" not in st.session_state:
    st.session_state.risultati_temp = {}
if "nuovo_torneo_step" not in st.session_state:
    st.session_state.nuovo_torneo_step = 1
if "club_scelto" not in st.session_state:
    st.session_state.club_scelto = None
if "giocatori_scelti" not in st.session_state:
    st.session_state.giocatori_scelti = []
if "squadre_data" not in st.session_state:
    st.session_state.squadre_data = []

# --- Interfaccia ---
st.markdown("<h1 style='text-align: center; color: #4B8BBE;'>⚽ Torneo Subbuteo - Sistema Svizzero ⚽</h1>", unsafe_allow_html=True)

scelta = st.radio("Scegli un'opzione:", ["📂 Carica torneo esistente", "✨ Crea nuovo torneo"])

url_club = {
    "Superba": "https://raw.githubusercontent.com/legnaro72/torneoSvizzerobyLegna/refs/heads/main/giocatoriSuperba.csv",
    "PierCrew": "https://raw.githubusercontent.com/legnaro72/torneoSvizzerobyLegna/refs/heads/main/giocatoriPierCrew.csv",
}

if scelta == "📂 Carica torneo esistente":
    file = st.file_uploader("Carica file CSV del torneo", type="csv")
    if file:
        st.session_state.df_torneo = carica_csv_robusto_da_file(file)
        st.success("✅ Torneo caricato!")

elif scelta == "✨ Crea nuovo torneo":
    if st.session_state.nuovo_torneo_step == 1:
        club = st.selectbox("Scegli il Club", ["Superba", "PierCrew"], index=0)
        st.session_state.club_scelto = club

        df_giocatori_csv = carica_csv_robusto_da_url(url_club[club])

        num_squadre = st.number_input("Numero partecipanti", min_value=2, max_value=100, step=1)

        st.markdown("### 👥 Amici del Club")
        giocatori_club = df_giocatori_csv["Giocatore"].dropna().unique().tolist()

        seleziona_tutti = st.checkbox("Seleziona tutti i giocatori del club")
        giocatori_selezionati_temp = []

        if seleziona_tutti:
            giocatori_selezionati_temp = giocatori_club.copy()
            for g in giocatori_club:
                st.checkbox(g, value=True, disabled=True)
        else:
            for g in giocatori_club:
                if st.checkbox(g):
                    giocatori_selezionati_temp.append(g)

        mancanti = num_squadre - len(giocatori_selezionati_temp)
        if mancanti > 0:
            st.markdown(f"### ➕ Aggiungi nuovi giocatori ({mancanti} slot)")
            for i in range(mancanti):
                col1, col2 = st.columns([0.2, 0.8])
                with col1:
                    aggiungi = st.checkbox(f"G{i+1}", value=True, key=f"nuovo_chk_{i}")
                with col2:
                    nome = st.text_input(f"Nome giocatore {i+1}", value=f"Ospite{i+1}", key=f"nuovo_nome_{i}")
                if aggiungi:
                    giocatori_selezionati_temp.append(nome)

        if st.button("✅ Conferma giocatori"):
            st.session_state.giocatori_scelti = giocatori_selezionati_temp
            st.session_state.nuovo_torneo_step = 2

    elif st.session_state.nuovo_torneo_step == 2:
        st.markdown(f"**Club scelto:** 🏟️ {st.session_state.club_scelto}")

        df_giocatori_csv = carica_csv_robusto_da_url(url_club[st.session_state.club_scelto])

        squadre_data = []
        for i, gioc in enumerate(st.session_state.giocatori_scelti):
            if gioc not in df_giocatori_csv["Giocatore"].values:
                nome_giocatore = st.text_input(f"Nome giocatore {i+1}", value=gioc, key=f"new_giocatore_{i}")
                squadra_default = f"SquadraOspite{i+1}"
                potenziale_default = 4
            else:
                nome_giocatore = st.text_input(f"Nome giocatore {i+1}", value=gioc, key=f"giocatore_nome_{i}")
                riga = df_giocatori_csv[df_giocatori_csv["Giocatore"] == gioc]
                squadra_default = riga["Squadra"].values[0] if not riga.empty and pd.notna(riga["Squadra"].values[0]) else f"SquadraOspite{i+1}"
                try:
                    potenziale_default = int(riga["Potenziale"].values[0]) if not riga.empty and pd.notna(riga["Potenziale"].values[0]) else 4
                except:
                    potenziale_default = 4

            squadra = st.text_input(f"Squadra giocatore {i+1}", value=squadra_default, key=f"squadra_{i}")
            potenziale = st.slider(f"Potenziale giocatore {i+1}", 1, 10, value=potenziale_default, key=f"potenziale_{i}")

            squadre_data.append({
                "Giocatore": nome_giocatore,
                "Squadra": squadra,
                "Potenziale": potenziale
            })

        if st.button("✅ Conferma squadre e genera primo turno"):
            df_squadre = pd.DataFrame(squadre_data)
            df_squadre["SquadraGiocatore"] = df_squadre.apply(lambda r: f"{r['Squadra']} ({r['Giocatore']})", axis=1)
            df_squadre = df_squadre.sort_values(by="Potenziale", ascending=False).reset_index(drop=True)
            st.session_state.df_squadre = df_squadre
            st.session_state.turno_attivo = 1

            classifica_iniziale = pd.DataFrame({
                'Squadra': df_squadre['SquadraGiocatore'],
                'Punti': 0,
                'GF': 0,
                'GS': 0,
                'DR': 0
            })
            nuove_partite = genera_accoppiamenti(classifica_iniziale, set())
            nuove_partite["Turno"] = st.session_state.turno_attivo
            st.session_state.df_torneo = nuove_partite

            for idx, row in nuove_partite.iterrows():
                key_gc = f"gc_{row['Turno']}_{row['Casa']}_{row['Ospite']}"
                key_go = f"go_{row['Turno']}_{row['Casa']}_{row['Ospite']}"
                key_val = f"val_{row['Turno']}_{row['Casa']}_{row['Ospite']}"
                st.session_state.risultati_temp[key_gc] = 0
                st.session_state.risultati_temp[key_go] = 0
                st.session_state.risultati_temp[key_val] = False

            st.success("🏁 Primo turno generato! Puoi ora inserire i risultati.")

# --- Nuovo turno ---
st.subheader("⚡ Genera turno successivo")
if st.button("▶ Nuovo turno"):
    partite_validate = st.session_state.df_torneo[st.session_state.df_torneo['Validata']]
    precedenti = set(zip(partite_validate['Casa'], partite_validate['Ospite']))
    classifica_attuale = aggiorna_classifica(st.session_state.df_torneo)
    nuove_partite = genera_accoppiamenti(classifica_attuale, precedenti)
    if nuove_partite.empty:
        st.warning("⚠️ Nessuna nuova partita possibile.")
    else:
        st.session_state.turno_attivo += 1
        nuove_partite["Turno"] = st.session_state.turno_attivo
        st.session_state.df_torneo = pd.concat([st.session_state.df_torneo, nuove_partite], ignore_index=True)
        for idx, row in nuove_partite.iterrows():
            key_gc = f"gc_{row['Turno']}_{row['Casa']}_{row['Ospite']}"
            key_go = f"go_{row['Turno']}_{row['Casa']}_{row['Ospite']}"
            key_val = f"val_{row['Turno']}_{row['Casa']}_{row['Ospite']}"
            st.session_state.risultati_temp[key_gc] = 0
            st.session_state.risultati_temp[key_go] = 0
            st.session_state.risultati_temp[key_val] = False
        st.success(f"🎉 Turno {st.session_state.turno_attivo} generato!")

# --- Inserimento risultati ---
if not st.session_state.df_torneo.empty:
    st.subheader("📝 Inserisci / Modifica risultati")
    for turno in sorted(st.session_state.df_torneo['Turno'].unique()):
        st.markdown(f"### Turno {turno}")
        container = st.container()
        df_turno = st.session_state.df_torneo[st.session_state.df_torneo['Turno'] == turno]
        for idx, row in df_turno.iterrows():
            with container:
                key_gc = f"gc_{row['Turno']}_{row['Casa']}_{row['Ospite']}"
                key_go = f"go_{row['Turno']}_{row['Casa']}_{row['Ospite']}"
                key_val = f"val_{row['Turno']}_{row['Casa']}_{row['Ospite']}"

                if key_gc not in st.session_state.risultati_temp:
                    st.session_state.risultati_temp[key_gc] = row['GolCasa']
                if key_go not in st.session_state.risultati_temp:
                    st.session_state.risultati_temp[key_go] = row['GolOspite']
                if key_val not in st.session_state.risultati_temp:
                    st.session_state.risultati_temp[key_val] = row['Validata']

                col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
                col1.markdown(f"**{row['Casa']}** vs **{row['Ospite']}**")
                gol_casa = col2.number_input("", 0, 20, value=st.session_state.risultati_temp[key_gc], key=key_gc)
                gol_ospite = col3.number_input("", 0, 20, value=st.session_state.risultati_temp[key_go], key=key_go)
                validata = col4.checkbox("Validata", value=st.session_state.risultati_temp[key_val], key=key_val)

                st.session_state.risultati_temp[key_gc] = gol_casa
                st.session_state.risultati_temp[key_go] = gol_ospite
                st.session_state.risultati_temp[key_val] = validata

    for idx, row in st.session_state.df_torneo.iterrows():
        key_gc = f"gc_{row['Turno']}_{row['Casa']}_{row['Ospite']}"
        key_go = f"go_{row['Turno']}_{row['Casa']}_{row['Ospite']}"
        key_val = f"val_{row['Turno']}_{row['Casa']}_{row['Ospite']}"
        st.session_state.df_torneo.at[idx, 'GolCasa'] = st.session_state.risultati_temp[key_gc]
        st.session_state.df_torneo.at[idx, 'GolOspite'] = st.session_state.risultati_temp[key_go]
        st.session_state.df_torneo.at[idx, 'Validata'] = st.session_state.risultati_temp[key_val]

# --- Classifica ---
if not st.session_state.df_torneo.empty:
    st.subheader("🏆 Classifica")
    df_classifica = aggiorna_classifica(st.session_state.df_torneo)
    st.dataframe(df_classifica, use_container_width=True)

# --- Tutte le giornate ---
if not st.session_state.df_torneo.empty:
    st.subheader("📅 Tutte le giornate / turni")
    df_visual = st.session_state.df_torneo.copy()
    df_visual = df_visual.sort_values(by="Turno").reset_index(drop=True)
    df_visual_display = df_visual[["Turno", "Casa", "GolCasa", "Ospite", "GolOspite", "Validata"]]
    st.dataframe(df_visual_display, use_container_width=True)

# --- Scarica torneo ---
st.subheader("💾 Esporta CSV")
nome_base = st.text_input("Nome torneo per salvataggio", value="torneo_subbuteo")
if st.button("⬇️ Scarica CSV torneo"):
    csv_data = st.session_state.df_torneo.to_csv(index=False)
    nome_file = f"{nome_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    st.download_button(label="⬇️ Scarica torneo", data=csv_data, file_name=nome_file, mime="text/csv")
if st.button("⬇️ Scarica classifica"):
    csv_classifica = df_classifica.to_csv(index=False)
    nome_file_classifica = f"{nome_base}_classifica_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    st.download_button(label="⬇️ Scarica classifica", data=csv_classifica, file_name=nome_file_classifica, mime="text/csv")


from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from io import BytesIO
import urllib.request

# --- EXPORT PDF ---
if not st.session_state.df_torneo.empty:
    st.subheader("📄 Esporta PDF calendario + classifica (grafica rivista)")

    if st.button("📤 Genera PDF"):
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
        elements = []

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='CenterTitle', alignment=1, fontSize=18, spaceAfter=12))
        styles.add(ParagraphStyle(name='CenterSubtitle', alignment=1, fontSize=10, textColor=colors.grey))

        # LOGO (opzionale)
        try:
            logo_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6e/Football_%28soccer_ball%29.svg/240px-Football_%28soccer_ball%29.svg.png"
            with urllib.request.urlopen(logo_url) as img_file:
                img_data = img_file.read()
            logo = Image(BytesIO(img_data), width=40, height=40)
            elements.append(logo)
        except:
            pass

        # Titolo torneo
        elements.append(Paragraph(f"Torneo Subbuteo - {nome_base}", styles['CenterTitle']))
        elements.append(Paragraph(f"Generato il {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['CenterSubtitle']))
        elements.append(Spacer(1, 10))

        # --- CLASSIFICA ---
        elements.append(Paragraph("🏆 Classifica", styles['Heading2']))
        df_classifica_display = df_classifica.copy()
        df_classifica_display.index = df_classifica_display.index + 1  # Posizioni

        classifica_data = [["Pos"] + df_classifica_display.columns.tolist()]
        for i, row in df_classifica_display.iterrows():
            classifica_data.append([i] + list(row.values))

        table_classifica = Table(classifica_data, repeatRows=1)
        table_classifica.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1f497d")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
        ]))
        # Righe alternate
        for r in range(1, len(classifica_data)):
            bg_color = colors.whitesmoke if r % 2 == 0 else colors.lightgrey
            table_classifica.setStyle(TableStyle([('BACKGROUND', (0, r), (-1, r), bg_color)]))

        elements.append(table_classifica)
        elements.append(Spacer(1, 15))

        # --- CALENDARIO ---
        elements.append(Paragraph("📅 Calendario", styles['Heading2']))
        df_visual = st.session_state.df_torneo.copy()
        df_visual = df_visual.sort_values(by=["Turno"]).reset_index(drop=True)
        df_visual_display = df_visual[["Turno", "Casa", "GolCasa", "Ospite", "GolOspite", "Validata"]]

        calendario_data = [df_visual_display.columns.tolist()] + df_visual_display.values.tolist()
        table_calendario = Table(calendario_data, repeatRows=1)
        table_calendario.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4B8BBE")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
        ]))
        # Righe alternate
        for r in range(1, len(calendario_data)):
            bg_color = colors.whitesmoke if r % 2 == 0 else colors.lightgrey
            table_calendario.setStyle(TableStyle([('BACKGROUND', (0, r), (-1, r), bg_color)]))

        elements.append(table_calendario)

        # --- Genera e scarica ---
        doc.build(elements)
        buffer.seek(0)

        st.download_button(
            label="📥 Scarica PDF",
            data=buffer,
            file_name=f"{nome_base}_torneo.pdf",
            mime="application/pdf"
        )

