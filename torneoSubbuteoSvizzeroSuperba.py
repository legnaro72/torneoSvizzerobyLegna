import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io
from fpdf import FPDF

st.set_page_config(page_title="⚽ Torneo Subbuteo - Sistema Svizzero", layout="wide")

# -------------------------
# Funzioni di utilità
# -------------------------
def esporta_pdf(df_torneo, nome_torneo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)

    titolo = nome_torneo.encode("latin-1", "ignore").decode("latin-1")
    pdf.cell(0, 10, titolo, ln=True, align="C")

    pdf.set_font("Arial", "", 11)
    turno_corrente = None
    for _, r in df_torneo.sort_values(by="Turno").iterrows():
        if turno_corrente != r["Turno"]:
            turno_corrente = r["Turno"]
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, f"Turno {turno_corrente}", ln=True)
            pdf.set_font("Arial", "", 11)

        casa = str(r["Casa"])
        osp = str(r["Ospite"])
        gc = str(r["GolCasa"])
        go = str(r["GolOspite"])
        match_text = f"{casa} {gc} - {go} {osp}"
        match_text = match_text.encode("latin-1", "ignore").decode("latin-1")

        if bool(r["Validata"]):
            pdf.set_text_color(0, 128, 0)   # verde per partite validate
        else:
            pdf.set_text_color(255, 0, 0)   # rosso per partite da giocare

        pdf.cell(0, 8, match_text, ln=True)

    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Classifica attuale", ln=True)

    classifica = aggiorna_classifica(df_torneo)
    if not classifica.empty:
        pdf.set_font("Arial", "", 11)
        for _, row in classifica.iterrows():
            line = f"{row['Squadra']} - Punti:{row['Punti']} G:{row['G']} V:{row['V']} N:{row['N']} P:{row['P']} GF:{row['GF']} GS:{row['GS']} DR:{row['DR']}"
            line = line.encode("latin-1", "ignore").decode("latin-1")
            pdf.cell(0, 8, line, ln=True)

    return pdf.output(dest="S").encode("latin-1")

def aggiorna_classifica(df):
    stats = {}
    for _, r in df.iterrows():
        if not bool(r.get('Validata', False)):
            continue
        casa, osp = r['Casa'], r['Ospite']
        gc, go = int(r['GolCasa']), int(r['GolOspite'])
        for squadra in [casa, osp]:
            if squadra not in stats:
                stats[squadra] = {'Punti': 0, 'GF': 0, 'GS': 0, 'DR': 0, 'G': 0, 'V': 0, 'N': 0, 'P': 0}
        stats[casa]['G'] += 1
        stats[osp]['G'] += 1
        stats[casa]['GF'] += gc
        stats[casa]['GS'] += go
        stats[osp]['GF'] += go
        stats[osp]['GS'] += gc
        if gc > go:
            stats[casa]['Punti'] += 2
            stats[casa]['V'] += 1
            stats[osp]['P'] += 1
        elif gc < go:
            stats[osp]['Punti'] += 2
            stats[osp]['V'] += 1
            stats[casa]['P'] += 1
        else:
            stats[casa]['Punti'] += 1
            stats[osp]['Punti'] += 1
            stats[casa]['N'] += 1
            stats[osp]['N'] += 1
    if not stats:
        return pd.DataFrame(columns=['Squadra', 'Punti', 'G', 'V', 'N', 'P', 'GF', 'GS', 'DR'])
    df_class = pd.DataFrame([
        {'Squadra': s,
         'Punti': v['Punti'],
         'G': v['G'],
         'V': v['V'],
         'N': v['N'],
         'P': v['P'],
         'GF': v['GF'],
         'GS': v['GS'],
         'DR': v['GF'] - v['GS']}
        for s, v in stats.items()
    ])
    df_class = df_class.sort_values(by=['Punti', 'DR', 'GF'], ascending=False).reset_index(drop=True)
    return df_class

def genera_accoppiamenti(classifica, precedenti):
    accoppiamenti = []
    gia_abbinati = set()
    for i, r1 in classifica.iterrows():
        s1 = r1['Squadra']
        if s1 in gia_abbinati:
            continue
        for j in range(i + 1, len(classifica)):
            s2 = classifica.iloc[j]['Squadra']
            if s2 in gia_abbinati:
                continue
            if (s1, s2) not in precedenti and (s2, s1) not in precedenti:
                accoppiamenti.append((s1, s2))
                gia_abbinati.add(s1)
                gia_abbinati.add(s2)
                break
    df = pd.DataFrame([{"Casa": c, "Ospite": o, "GolCasa": 0, "GolOspite": 0, "Validata": False} for c, o in accoppiamenti])
    return df

def carica_csv_robusto_da_url(url):
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        text = r.content.decode('latin1')
        return pd.read_csv(io.StringIO(text))
    except Exception as e:
        st.warning(f"Errore caricamento CSV da URL: {e}")
        return pd.DataFrame()

def carica_csv_robusto_da_file(file_buffer):
    try:
        content = file_buffer.read()
        text = content.decode('latin1')
        return pd.read_csv(io.StringIO(text))
    except Exception as e:
        st.warning(f"Errore caricamento CSV da file: {e}")
        return pd.DataFrame()

def init_results_temp_from_df(df):
    for _, row in df.iterrows():
        T = row.get('Turno', 1)
        casa = row['Casa']
        osp = row['Ospite']
        key_gc = f"gc_{T}_{casa}_{osp}"
        key_go = f"go_{T}_{casa}_{osp}"
        key_val = f"val_{T}_{casa}_{osp}"
        st.session_state.risultati_temp.setdefault(key_gc, int(row.get('GolCasa', 0)))
        st.session_state.risultati_temp.setdefault(key_go, int(row.get('GolOspite', 0)))
        st.session_state.risultati_temp.setdefault(key_val, bool(row.get('Validata', False)))

# -------------------------
# Session state
# -------------------------
for key, default in {
    "df_torneo": pd.DataFrame(),
    "df_squadre": pd.DataFrame(),
    "turno_attivo": 0,
    "risultati_temp": {},
    "nuovo_torneo_step": 1,
    "club_scelto": "Superba", # Imposta il club di default
    "giocatori_scelti": [],
    "squadre_data": [],
    "torneo_iniziato": False,
    "setup_mode": None,
    "nome_torneo": "Torneo Subbuteo - Sistema Svizzero"
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# -------------------------
# Dati club
# -------------------------
url_club = {
    "Superba": "https://raw.githubusercontent.com/legnaro72/torneoSvizzerobyLegna/refs/heads/main/giocatoriSuperba.csv",
    "PierCrew": "https://raw.githubusercontent.com/legnaro72/torneoSvizzerobyLegna/refs/heads/main/giocatoriPierCrew.csv",
}

# -------------------------
# Header grafico
# -------------------------
st.markdown(f"""
<div style='text-align:center; padding:20px; border-radius:12px; background: linear-gradient(to right, #ffefba, #ffffff);'>
    <h1 style='color:#0B5FFF;'>⚽ {st.session_state.nome_torneo} 🏆</h1>
</div>
""", unsafe_allow_html=True)

# -------------------------
# Se torneo non è iniziato e non è stato ancora selezionato un setup
# -------------------------
if not st.session_state.torneo_iniziato and st.session_state.setup_mode is None:
    st.markdown("### Scegli azione")
    c1, c2 = st.columns([1,1])
    with c1:
        st.markdown(
            """<div style='background:#f5f8ff; border-radius:8px; padding:18px; text-align:center'>
               <h2>📂 Carica torneo esistente</h2>
               <p style='margin:0.2rem 0 1rem 0'>Riprendi un torneo salvato (CSV)</p>
               </div>""",
            unsafe_allow_html=True,
        )
        if st.button("Carica torneo (CSV)", key="btn_carica"):
            st.session_state.setup_mode = "carica"
            st.rerun()
    with c2:
        st.markdown(
            """<div style='background:#fff8e6; border-radius:8px; padding:18px; text-align:center'>
               <h2>✨ Crea nuovo torneo</h2>
               <p style='margin:0.2rem 0 1rem 0'>Genera primo turno scegliendo giocatori del Club Superba</p>
               </div>""",
            unsafe_allow_html=True,
        )
        if st.button("Nuovo torneo", key="btn_nuovo"):
            st.session_state.setup_mode = "nuovo"
            st.session_state.nuovo_torneo_step = 0
            st.session_state.giocatori_scelti = []
            st.session_state.club_scelto = "Superba" # Imposta il club
            st.rerun()

    st.markdown("---")

# -------------------------
# Logica di caricamento o creazione torneo
# -------------------------
if st.session_state.setup_mode == "carica":
    st.markdown("#### 📥 Carica CSV torneo")
    file = st.file_uploader("Carica file CSV del torneo (es. esportazione dell'app)", type="csv")
    if file:
        df = carica_csv_robusto_da_file(file)
        if not df.empty:
            for col in ['Casa','Ospite','GolCasa','GolOspite','Validata','Turno']:
                if col not in df.columns:
                    if col in ['GolCasa','GolOspite']:
                        df[col] = 0
                    elif col == 'Validata':
                        df[col] = False
                    elif col == 'Turno':
                        df['Turno'] = 1
                    else:
                        st.warning(f"Colonna {col} mancante nel CSV; il file potrebbe non contenere le info attese.")
            df['GolCasa'] = df['GolCasa'].fillna(0).astype(int)
            df['GolOspite'] = df['GolOspite'].fillna(0).astype(int)
            df['Validata'] = df['Validata'].astype(bool)
            if 'Turno' not in df.columns:
                df['Turno'] = 1
            st.session_state.df_torneo = df.reset_index(drop=True)
            st.session_state.turno_attivo = int(st.session_state.df_torneo['Turno'].max())
            init_results_temp_from_df(st.session_state.df_torneo)
            st.session_state.torneo_iniziato = True
            st.session_state.setup_mode = None
            st.success("✅ Torneo caricato! Ora puoi continuare da dove eri rimasto.")
            st.rerun()

if st.session_state.setup_mode == "nuovo":
    st.markdown("#### ✨ Crea nuovo torneo — passo per passo")

    if st.session_state.nuovo_torneo_step == 0:
        suffisso = st.text_input("Dai un nome al tuo torneo", value="", placeholder="Es. 'Campionato Invernale'")
        if st.button("Prossimo passo", key="next_step_0"):
            st.session_state.nome_torneo = f"Torneo Subbuteo Svizzero - {suffisso.strip()}" if suffisso.strip() else "Torneo Subbuteo - Sistema Svizzero"
            st.session_state.nuovo_torneo_step = 1
            st.rerun()

    elif st.session_state.nuovo_torneo_step == 1:
        st.markdown(f"**Nome del torneo:** {st.session_state.nome_torneo}")
        
        # Rimozione della scelta del club, ora è cablato su Superba
        st.markdown(f"### Club selezionato: **{st.session_state.club_scelto}**")

        df_gioc = carica_csv_robusto_da_url(url_club[st.session_state.club_scelto])
        st.markdown("**Numero partecipanti** (min 2)")
        num_squadre = st.number_input("Numero partecipanti", min_value=2, max_value=100, value=8, step=1, key="num_partecipanti")
        st.markdown("### 👥 Seleziona i giocatori del club")
        giocatori_club = []
        if not df_gioc.empty and 'Giocatore' in df_gioc.columns:
            giocatori_club = df_gioc["Giocatore"].dropna().astype(str).tolist()

        seleziona_tutti = st.checkbox("Seleziona tutti i giocatori del club", key="sel_all")
        giocatori_selezionati_temp = []
        if giocatori_club:
            for g in giocatori_club:
                checked = seleziona_tutti
                if st.checkbox(g, value=checked, key=f"chk_{g}"):
                    giocatori_selezionati_temp.append(g)

        mancanti = num_squadre - len(giocatori_selezionati_temp)
        if mancanti > 0:
            st.markdown(f"### ➕ Aggiungi nuovi giocatori ({mancanti} slot)")
            for i in range(mancanti):
                col1, col2 = st.columns([0.15, 0.85])
                with col1:
                    aggiungi = st.checkbox(f"Aggiungi slot {i+1}", value=True, key=f"aggiungi_{i}")
                with col2:
                    nome = st.text_input(f"Nome mancanti {i+1}", value=f"Ospite{i+1}", key=f"nome_manc_{i}")
                if aggiungi:
                    giocatori_selezionati_temp.append(nome)

        st.markdown("---")
        if st.button("✅ Conferma giocatori", key="conf_gioc"):
            if len(giocatori_selezionati_temp) < 2:
                st.warning("Servono almeno 2 giocatori.")
            else:
                st.session_state.giocatori_scelti = giocatori_selezionati_temp
                st.session_state.nuovo_torneo_step = 2
                st.success("Giocatori confermati — procedi a definire squadre e potenziali.")
                st.rerun()

    elif st.session_state.nuovo_torneo_step == 2:
        st.markdown("### 🏷️ Definisci Squadre e Potenziali")
        st.markdown(f"**Nome del torneo:** {st.session_state.nome_torneo}")
        df_gioc = carica_csv_robusto_da_url(url_club[st.session_state.club_scelto]) if st.session_state.club_scelto else pd.DataFrame()
        squadre_data = []
        for i, gioc in enumerate(st.session_state.giocatori_scelti):
            if not df_gioc.empty and 'Giocatore' in df_gioc.columns and gioc in df_gioc['Giocatore'].values:
                riga = df_gioc[df_gioc['Giocatore'] == gioc].iloc[0]
                squadra_default = riga['Squadra'] if 'Squadra' in riga and pd.notna(riga['Squadra']) else f"Squadra{i+1}"
                try:
                    pot_def = int(riga['Potenziale']) if 'Potenziale' in riga and pd.notna(riga['Potenziale']) else 4
                except:
                    pot_def = 4
            else:
                squadra_default = f"Squadra{i+1}"
                pot_def = 4

            nome_gioc = st.text_input(f"Nome giocatore {i+1}", value=gioc, key=f"g_{i}")
            squadra = st.text_input(f"Squadra {i+1}", value=squadra_default, key=f"s_{i}")
            pot = st.slider(f"Potenziale {i+1}", 1, 10, value=pot_def, key=f"p_{i}")
            squadre_data.append({"Giocatore": nome_gioc, "Squadra": squadra, "Potenziale": pot})

        st.markdown("---")
        if st.button("✅ Conferma squadre e genera primo turno", key="gen1"):
            df_squadre = pd.DataFrame(squadre_data)
            df_squadre["SquadraGiocatore"] = df_squadre.apply(lambda r: f"{r['Squadra']} ({r['Giocatore']})", axis=1)
            df_squadre = df_squadre.sort_values(by="Potenziale", ascending=False).reset_index(drop=True)
            st.session_state.df_squadre = df_squadre

            classifica_iniziale = pd.DataFrame({
                'Squadra': df_squadre['SquadraGiocatore'],
                'Punti': 0, 'GF': 0, 'GS': 0, 'DR': 0
            })
            nuove_partite = genera_accoppiamenti(classifica_iniziale, set())
            st.session_state.turno_attivo = 1
            nuove_partite["Turno"] = st.session_state.turno_attivo
            st.session_state.df_torneo = pd.concat([st.session_state.df_torneo, nuove_partite], ignore_index=True)
            init_results_temp_from_df(nuove_partite)
            st.session_state.torneo_iniziato = True
            st.session_state.setup_mode = None
            st.success("🏁 Primo turno generato! Ora sei nella vista torneo.")
            st.rerun()

# -------------------------
# Vista torneo attivo
# -------------------------
if st.session_state.torneo_iniziato and not st.session_state.df_torneo.empty:
    modo_vista = st.radio(
        "Seleziona modalità di visualizzazione turni:",
        options=["Menu a tendina", "Bottoni"],
        index=0
    )

    turni_disponibili = sorted(st.session_state.df_torneo['Turno'].unique())

    if modo_vista == "Menu a tendina":
        turno_corrente = st.selectbox(
            "🔹 Seleziona turno", 
            turni_disponibili, 
            index=len(turni_disponibili)-1
        )
    else:
        st.markdown("🔹 Seleziona turno:")
        col_btns = st.columns(len(turni_disponibili))
        turno_corrente = turni_disponibili[-1]
        for i, T in enumerate(turni_disponibili):
            if col_btns[i].button(f"Turno {T}"):
                turno_corrente = T

    st.markdown(f"### 🔷 Turno selezionato: {turno_corrente}")

    df_turno = st.session_state.df_torneo[st.session_state.df_torneo['Turno'] == turno_corrente].reset_index()

    if df_turno.empty:
        st.info("Nessuna partita generata per questo turno. Premi 'Genera turno successivo' se tutte le partite validate.")
    else:
        for _, row in df_turno.iterrows():
            idx = int(row['index'])
            T = int(row['Turno'])
            casa = row['Casa']
            osp = row['Ospite']
            key_gc = f"gc_{T}_{casa}_{osp}"
            key_go = f"go_{T}_{casa}_{osp}"
            key_val = f"val_{T}_{casa}_{osp}"

            st.session_state.risultati_temp.setdefault(key_gc, int(row.get('GolCasa', 0)))
            st.session_state.risultati_temp.setdefault(key_go, int(row.get('GolOspite', 0)))
            st.session_state.risultati_temp.setdefault(key_val, bool(row.get('Validata', False)))

            c1, c2, c3, c4 = st.columns([3,1,1,0.8])
            with c1:
                st.markdown(f"**{casa}** vs **{osp}**")

            key_gc_input = f"gc_input_{T}_{casa}_{osp}"
            key_go_input = f"go_input_{T}_{casa}_{osp}"
            key_val_input = f"val_input_{T}_{casa}_{osp}"

            if key_gc not in st.session_state:
                st.session_state[key_gc] = int(row.get('GolCasa', 0))
            if key_go not in st.session_state:
                st.session_state[key_go] = int(row.get('GolOspite', 0))
            if key_val not in st.session_state:
                st.session_state[key_val] = bool(row.get('Validata', False))

            with c2:
                st.number_input("", min_value=0, max_value=20, step=1, key=key_gc_input)
                st.session_state[key_gc] = st.session_state[key_gc_input]
            with c3:
                st.number_input("", min_value=0, max_value=20, step=1, key=key_go_input)
                st.session_state[key_go] = st.session_state[key_go_input]
            with c4:
                st.checkbox("Validata", key=key_val_input)
                st.session_state[key_val] = st.session_state[key_val_input]

            st.session_state.df_torneo.at[idx, 'GolCasa'] = st.session_state[key_gc]
            st.session_state.df_torneo.at[idx, 'GolOspite'] = st.session_state[key_go]
            st.session_state.df_torneo.at[idx, 'Validata'] = st.session_state[key_val]

    st.markdown("---")
    c_left, c_right = st.columns([1,2])
    with c_left:
        if st.button("⚡ Genera turno successivo"):
            partite_validate = st.session_state.df_torneo[st.session_state.df_torneo['Validata'] == True]
            precedenti = set(zip(partite_validate['Casa'], partite_validate['Ospite']))
            classifica_attuale = aggiorna_classifica(st.session_state.df_torneo)
            if classifica_attuale.empty:
                if not st.session_state.df_squadre.empty:
                    classifica_attuale = pd.DataFrame({'Squadra': st.session_state.df_squadre['SquadraGiocatore']})
                else:
                    st.warning("Classifica vuota: assicurati di avere squadre o partite validate.")
                    classifica_attuale = pd.DataFrame({'Squadra': []})
            nuove_partite = genera_accoppiamenti(classifica_attuale, precedenti)
            if nuove_partite.empty:
                st.warning("⚠️ Nessuna nuova partita possibile (controlla partite validate / già giocate).")
            else:
                st.session_state.turno_attivo += 1
                nuove_partite["Turno"] = st.session_state.turno_attivo
                for col in ['GolCasa','GolOspite','Validata']:
                    if col not in nuove_partite.columns:
                        if col in ['GolCasa','GolOspite']:
                            nuove_partite[col] = 0
                        else:
                            nuove_partite[col] = False
                st.session_state.df_torneo = pd.concat([st.session_state.df_torneo, nuove_partite], ignore_index=True)
                init_results_temp_from_df(nuove_partite)
                st.success(f"🎉 Turno {st.session_state.turno_attivo} generato!")
                st.rerun()
    with c_right:
        st.markdown("### 🏆 Classifica attuale")
        df_class = aggiorna_classifica(st.session_state.df_torneo)
        st.dataframe(df_class, use_container_width=True)

    st.markdown("---")
    with st.expander("Mostra tutte le giornate / Turni"):
        df_visual = st.session_state.df_torneo.copy()
        df_visual = df_visual.sort_values(by="Turno").reset_index(drop=True)
        cols_to_show = ["Turno", "Casa", "GolCasa", "Ospite", "GolOspite", "Validata"]
        for c in cols_to_show:
            if c not in df_visual.columns:
                df_visual[c] = ""
        st.dataframe(df_visual[cols_to_show], use_container_width=True)

    # -------------------------
    # Sezione esportazione (ora in sidebar)
    # -------------------------
    st.sidebar.markdown("### 💾 Esporta torneo")
    csv_data = st.session_state.df_torneo.to_csv(index=False).encode('utf-8')
    file_name_csv = f"{st.session_state.nome_torneo.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    st.sidebar.download_button(label="⬇️ Scarica CSV torneo", data=csv_data,
                               file_name=file_name_csv,
                               mime="text/csv")
    
    if st.sidebar.button("⬇️ Esporta torneo in PDF"):
        pdf_bytes = esporta_pdf(st.session_state.df_torneo, st.session_state.nome_torneo)
        file_name_pdf = f"{st.session_state.nome_torneo.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        st.sidebar.download_button(
            label="📄 Download PDF torneo",
            data=pdf_bytes,
            file_name=file_name_pdf,
            mime="application/pdf"
        )
        
# -------------------------
# Banner vincitore
# -------------------------
if st.session_state.torneo_iniziato and not st.session_state.df_torneo.empty:
    tutte_validate = st.session_state.df_torneo['Validata'].all()

    if tutte_validate:
        df_class = aggiorna_classifica(st.session_state.df_torneo)
        if not df_class.empty:
            vincitore = df_class.iloc[0]['Squadra']

            st.markdown(
                f"""
                <div style='background:linear-gradient(90deg, gold, orange); 
                            padding:20px; 
                            border-radius:12px; 
                            text-align:center; 
                            color:black; 
                            font-size:28px; 
                            font-weight:bold;
                            margin-top:20px;'>
                    🏆 Vincitore del torneo: {vincitore} 🏆
                </div>
                """,
                unsafe_allow_html=True
            )
