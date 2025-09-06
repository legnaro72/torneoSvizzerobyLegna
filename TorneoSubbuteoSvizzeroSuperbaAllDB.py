import streamlit as st
import pandas as pd
from datetime import datetime
import io
from fpdf import FPDF
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId

# -------------------------
# Session state (inizializzazione e aggiornamento nome torneo)
# -------------------------
for key, default in {
    "df_torneo": pd.DataFrame(),
    "df_squadre": pd.DataFrame(),
    "turno_attivo": 0,
    "risultati_temp": {},
    "nuovo_torneo_step": 1,
    "club_scelto": "Superba",
    "giocatori_selezionati_db": [],
    "giocatori_ospiti": [],
    "giocatori_totali": [],
    "torneo_iniziato": False,
    "setup_mode": None,
    "nome_torneo": "Torneo Subbuteo - Sistema Svizzero",
    "torneo_finito": False,
    "edited_df_squadre": pd.DataFrame(),
    "gioc_info": {}
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Aggiornamento del nome del torneo se è finito
if st.session_state.torneo_finito and not st.session_state.nome_torneo.startswith("finito_"):
    st.session_state.nome_torneo = f"finito_{st.session_state.nome_torneo}"

st.set_page_config(page_title=f"⚽ {st.session_state.nome_torneo}", layout="wide")

# -------------------------
# Connessione a MongoDB Atlas
# -------------------------

players_collection = None
tournaments_collection = None
with st.spinner("Connessione a MongoDB..."):
    try:
        MONGO_URI = st.secrets["MONGO_URI"]
        server_api = ServerApi('1')
        client = MongoClient(MONGO_URI, server_api=server_api)
        
        # Connessione per i giocatori
        db_players = client.get_database("giocatori_subbuteo")
        players_collection = db_players.get_collection("superba_players") 
        _ = players_collection.find_one()

        # Connessione per i tornei (nuovo)
        db_tournaments = client.get_database("TorneiSubbuteo")
        tournaments_collection = db_tournaments.get_collection("SuperbaSvizzero")
        _ = tournaments_collection.find_one()

        st.sidebar.success("✅ Connessione a MongoDB Atlas riuscita.")
    except Exception as e:
        st.sidebar.error(f"❌ Errore di connessione a MongoDB: {e}. Non sarà possibile caricare/salvare i dati del database.")

# -------------------------
# Funzioni di utilità
# -------------------------

def autoplay_audio(audio_data: bytes):
    b64 = base64.b64encode(audio_data).decode("utf-8")
    md = f"""
        <audio autoplay="true">
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
        </audio>
        """
    st.markdown(md, unsafe_allow_html=True)
    
def salva_torneo_su_db():
    """Salva o aggiorna lo stato del torneo su MongoDB."""
    if tournaments_collection is None:
        st.error("❌ Connessione a MongoDB non attiva, impossibile salvare.")
        return

    torneo_data = {
        "nome_torneo": st.session_state.nome_torneo,
        "data_salvataggio": datetime.now(),
        "df_torneo": st.session_state.df_torneo.to_dict('records'),
        "df_squadre": st.session_state.df_squadre.to_dict('records'),
        "turno_attivo": st.session_state.turno_attivo,
        "torneo_iniziato": st.session_state.torneo_iniziato,
    }

    try:
        # Cerca un torneo esistente con lo stesso nome
        existing_doc = tournaments_collection.find_one({"nome_torneo": st.session_state.nome_torneo})

        if existing_doc:
            # Aggiorna il documento esistente
            tournaments_collection.update_one(
                {"_id": existing_doc["_id"]},
                {"$set": torneo_data}
            )
            st.success(f"✅ Torneo '{st.session_state.nome_torneo}' aggiornato con successo!")
        else:
            # Crea un nuovo documento
            tournaments_collection.insert_one(torneo_data)
            st.success(f"✅ Nuovo torneo '{st.session_state.nome_torneo}' salvato con successo!")
    except Exception as e:
        st.error(f"❌ Errore durante il salvataggio del torneo: {e}")

@st.cache_data
def carica_nomi_tornei_da_db():
    """Carica i nomi dei tornei disponibili dal DB."""
    if tournaments_collection is None:
        return []
    try:
        tornei = tournaments_collection.find({}, {"nome_torneo": 1}).sort("data_salvataggio", -1)
        return list(t['nome_torneo'] for t in tornei)
    except Exception as e:
        st.error(f"❌ Errore caricamento nomi tornei: {e}")
        return []

def carica_torneo_da_db(nome_torneo):
    """Carica un singolo torneo dal DB e lo ripristina nello stato della sessione."""
    if tournaments_collection is None:
        st.error("❌ Connessione a MongoDB non attiva, impossibile caricare.")
        return False
    try:
        torneo_data = tournaments_collection.find_one({"nome_torneo": nome_torneo})
        if torneo_data:
            st.session_state.nome_torneo = torneo_data.get("nome_torneo", "Torneo Svizzero Caricato")
            st.session_state.df_torneo = pd.DataFrame(torneo_data.get('df_torneo', []))
            st.session_state.df_squadre = pd.DataFrame(torneo_data.get('df_squadre', []))
            st.session_state.turno_attivo = torneo_data.get('turno_attivo', 0)
            st.session_state.torneo_iniziato = torneo_data.get('torneo_iniziato', False)
            st.session_state.setup_mode = None
            st.session_state.risultati_temp = {}
            if not st.session_state.df_torneo.empty:
                init_results_temp_from_df(st.session_state.df_torneo)
            return True
        else:
            st.error(f"❌ Torneo '{nome_torneo}' non trovato nel database.")
            return False
    except Exception as e:
        st.error(f"❌ Errore durante il caricamento del torneo: {e}")
        return False

@st.cache_data
def carica_giocatori_da_db():
    if 'players_collection' in globals() and players_collection is not None:
        try:
            count = players_collection.count_documents({})
            if count == 0:
                st.warning("⚠️ La collection 'superba_players' è vuota o non esiste. Non è stato caricato alcun giocatore.")
                return pd.DataFrame()
            else:
                st.info(f"✅ Trovati {count} giocatori nel database. Caricamento in corso...")
            
            df = pd.DataFrame(list(players_collection.find()))
            
            if '_id' in df.columns:
                df = df.drop(columns=['_id'])
            
            if 'Giocatore' not in df.columns:
                st.error("❌ Errore: la colonna 'Giocatore' non è presente nel database dei giocatori.")
                return pd.DataFrame()
            
            return df
        except Exception as e:
            st.error(f"❌ Errore durante la lettura dalla collection dei giocatori: {e}")
            return pd.DataFrame()
    else:
        st.warning("⚠️ La connessione a MongoDB non è attiva.")
        return pd.DataFrame()

# The @st.cache_data decorator must be removed to fix the TypeError.
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
            pdf.set_text_color(0, 128, 0)
        else:
            pdf.set_text_color(255, 0, 0)

        pdf.cell(0, 8, match_text, ln=True)

    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Classifica attuale", ln=True)
    
    classifica = aggiorna_classifica(df_torneo)
    if not classifica.empty:
        # Aggiungo la classifica in formato tabellare
        pdf.set_font("Arial", "B", 10)
        header = ['Squadra', 'Punti', 'G', 'V', 'N', 'P', 'GF', 'GS', 'DR']
        col_widths = [45, 15, 10, 10, 10, 10, 10, 10, 10]
        
        for i, h in enumerate(header):
            pdf.cell(col_widths[i], 8, h, border=1, ln=0, align='C')
        pdf.ln()

        pdf.set_font("Arial", "", 10)
        for _, row in classifica.iterrows():
            pdf.cell(col_widths[0], 8, str(row['Squadra']).encode("latin-1", "ignore").decode("latin-1"), border=1)
            pdf.cell(col_widths[1], 8, str(row['Punti']), border=1, align='C')
            pdf.cell(col_widths[2], 8, str(row['G']), border=1, align='C')
            pdf.cell(col_widths[3], 8, str(row['V']), border=1, align='C')
            pdf.cell(col_widths[4], 8, str(row['N']), border=1, align='C')
            pdf.cell(col_widths[5], 8, str(row['P']), border=1, align='C')
            pdf.cell(col_widths[6], 8, str(row['GF']), border=1, align='C')
            pdf.cell(col_widths[7], 8, str(row['GS']), border=1, align='C')
            pdf.cell(col_widths[8], 8, str(row['DR']), border=1, align='C')
            pdf.ln()

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

@st.cache_data
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

def init_results_temp_from_df(df):
    for _, row in df.iterrows():
        T = row.get('Turno', 1)
        casa = row['Casa']
        ospite = row['Ospite']
        key_gc = f"gc_{T}_{casa}_{ospite}"
        key_go = f"go_{T}_{casa}_{ospite}"
        key_val = f"val_{T}_{casa}_{ospite}"
        st.session_state.risultati_temp.setdefault(key_gc, int(row.get('GolCasa', 0)))
        st.session_state.risultati_temp.setdefault(key_go, int(row.get('GolOspite', 0)))
        st.session_state.risultati_temp.setdefault(key_val, bool(row.get('Validata', False)))

def visualizza_incontri_attivi(df_turno_corrente, turno_attivo):
    """Visualizza gli incontri del turno attivo e permette di inserire e validare i risultati."""
    for i, riga in df_turno_corrente.iterrows():
        with st.container(border=True):
            casa = riga['Casa']
            ospite = riga['Ospite']
            key_gc = f"gc_{turno_attivo}_{casa}_{ospite}"
            key_go = f"go_{turno_attivo}_{casa}_{ospite}"
            key_val = f"val_{turno_attivo}_{casa}_{ospite}"
            
            valida_key = f"valida_{turno_attivo}_{casa}_{ospite}"
            
            giocatore_casa = st.session_state.df_squadre[st.session_state.df_squadre['Squadra'] == casa]['Giocatore'].iloc[0]
            giocatore_ospite = st.session_state.df_squadre[st.session_state.df_squadre['Squadra'] == ospite]['Giocatore'].iloc[0]
            
            st.markdown(f"<p style='text-align:center; font-size:1.2rem; font-weight:bold;'>⚽ Partita</p>", unsafe_allow_html=True)
            
            # Titolo della partita con giocatori
            st.markdown(f"<p style='text-align:center; font-weight:bold;'>🏠{casa} ({giocatore_casa}) 🆚 {ospite} ({giocatore_ospite})🛫</p>", unsafe_allow_html=True)
        
            
            c_score1, c_score2 = st.columns(2)
            with c_score1:
                st.session_state.risultati_temp[key_gc] = st.number_input(f"Gol {casa}", min_value=0, key=key_gc, disabled=st.session_state.risultati_temp.get(key_val, False))
            with c_score2:
                st.session_state.risultati_temp[key_go] = st.number_input(f"Gol {ospite}", min_value=0, key=key_go, disabled=st.session_state.risultati_temp.get(key_val, False))
            
            if st.button("Valida Risultato ✅", key=valida_key, disabled=st.session_state.risultati_temp.get(key_val, False), use_container_width=True):
                df_turno_corrente.loc[df_turno_corrente['Casa'] == casa, 'GolCasa'] = st.session_state.risultati_temp[key_gc]
                df_turno_corrente.loc[df_turno_corrente['Casa'] == casa, 'GolOspite'] = st.session_state.risultati_temp[key_go]
                df_turno_corrente.loc[df_turno_corrente['Casa'] == casa, 'Validata'] = True
                st.session_state.df_torneo.loc[df_turno_corrente.index, ['GolCasa', 'GolOspite', 'Validata']] = df_turno_corrente.loc[df_turno_corrente.index, ['GolCasa', 'GolOspite', 'Validata']]
                st.session_state.risultati_temp[key_val] = True
                st.success("✅ Risultato validato!")
                st.rerun()
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
    st.markdown("### Scegli azione 📝")
    c1, c2 = st.columns([1,1])
    with c1:
        with st.container(border=True):
            st.markdown(
                """<div style='text-align:center'>
                    <h2>📂 Carica torneo esistente</h2>
                    <p style='margin:0.2rem 0 1rem 0'>Riprendi un torneo salvato (MongoDB)</p>
                    </div>""",
                unsafe_allow_html=True,
            )
            if st.button("Carica torneo (MongoDB) 📂", key="btn_carica", use_container_width=True):
                st.session_state.setup_mode = "carica_db"
                st.session_state.torneo_finito = False
                st.rerun()
    with c2:
        with st.container(border=True):
            st.markdown(
                """<div style='text-align:center'>
                    <h2>✨ Crea nuovo torneo</h2>
                    <p style='margin:0.2rem 0 1rem 0'>Genera primo turno scegliendo giocatori del Club Superba</p>
                    </div>""",
                unsafe_allow_html=True,
            )
            if st.button("Nuovo torneo ✨", key="btn_nuovo", use_container_width=True):
                st.session_state.setup_mode = "nuovo"
                st.session_state.nuovo_torneo_step = 0
                st.session_state.giocatori_selezionati_db = []
                st.session_state.giocatori_ospiti = []
                st.session_state.giocatori_totali = []
                st.session_state.club_scelto = "Superba"
                st.session_state.torneo_finito = False
                st.session_state.edited_df_squadre = pd.DataFrame()
                st.session_state.gioc_info = {} # Reset del dizionario per la nuova grafica
                st.rerun()

    st.markdown("---")

# -------------------------
# Logica di caricamento o creazione torneo
# -------------------------
if st.session_state.setup_mode == "carica_db":
    st.markdown("#### 📥 Carica torneo da MongoDB")
    tornei_disponibili = carica_nomi_tornei_da_db()
    if tornei_disponibili:
        opzione_scelta = st.selectbox("Seleziona il torneo da caricare:", tornei_disponibili)
        if st.button("Carica Torneo Selezionato 📥", type="primary"):
            with st.spinner("Caricamento in corso..."):
                if carica_torneo_da_db(opzione_scelta):
                    st.balloons()
                    st.success("✅ Torneo caricato! Ora puoi continuare da dove eri rimasto.")
                    st.session_state.torneo_finito = False
                    st.rerun()
    else:
        st.warning("⚠️ Nessun torneo trovato nel database.")
    if st.button("↩️ Indietro"):
        st.session_state.setup_mode = None
        st.rerun()

if st.session_state.setup_mode == "nuovo":
    st.markdown("#### ✨ Crea nuovo torneo — passo per passo")
    if st.session_state.nuovo_torneo_step == 0:
        suffisso = st.text_input("Dai un nome al tuo torneo", value="", placeholder="Es. 'Campionato Invernale'")
        if st.button("Prossimo passo ➡️", key="next_step_0", type="primary"):
            st.session_state.nome_torneo = f"Torneo Subbuteo Svizzero - {suffisso.strip()}" if suffisso.strip() else "Torneo Subbuteo - Sistema Svizzero"
            st.session_state.nuovo_torneo_step = 1
            st.rerun()
    elif st.session_state.nuovo_torneo_step == 1:
        st.info(f"**Nome del torneo:** {st.session_state.nome_torneo}")
        st.markdown("### Selezione partecipanti 👥")
        
        col_db, col_num = st.columns([2, 1])
        with col_db:
            df_gioc = carica_giocatori_da_db()
            if not df_gioc.empty:
                st.session_state.giocatori_selezionati_db = st.multiselect(
                    "Seleziona i giocatori che partecipano (dal database):",
                    options=df_gioc['Giocatore'].tolist(),
                    default=st.session_state.giocatori_selezionati_db,
                )
        with col_num:
            num_squadre = st.number_input("Numero totale di partecipanti:", min_value=2, max_value=100, value=max(8, len(st.session_state.giocatori_selezionati_db)), step=1, key="num_partecipanti")

        num_mancanti = num_squadre - len(st.session_state.giocatori_selezionati_db)
        if num_mancanti > 0:
            st.warning(f"⚠️ Mancano **{num_mancanti}** giocatori per raggiungere il numero totale. Aggiungi i nomi dei giocatori ospiti.")
            for i in range(num_mancanti):
                ospite_name = st.text_input(f"Nome Giocatore Ospite {i+1}", key=f"ospite_player_{i}", value=st.session_state.giocatori_ospiti[i] if i < len(st.session_state.giocatori_ospiti) else "")
                if i >= len(st.session_state.giocatori_ospiti):
                    st.session_state.giocatori_ospiti.append(ospite_name)
                else:
                    st.session_state.giocatori_ospiti[i] = ospite_name

        st.session_state.giocatori_totali = st.session_state.giocatori_selezionati_db + [p for p in st.session_state.giocatori_ospiti if p.strip()]
        
        st.markdown(f"**Partecipanti selezionati:** {len(st.session_state.giocatori_totali)} di {num_squadre}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Accetta giocatori ✅", key="next_step_1", use_container_width=True, type="primary"):
                if len(st.session_state.giocatori_totali) != num_squadre:
                    st.error(f"❌ Il numero di giocatori selezionati ({len(st.session_state.giocatori_totali)}) non corrisponde al numero totale di partecipanti ({num_squadre}).")
                else:
                    data_squadre = []
                    giocatori_db_df = carica_giocatori_da_db()
                    for player in st.session_state.giocatori_totali:
                        if player in giocatori_db_df['Giocatore'].tolist():
                            player_info = giocatori_db_df[giocatori_db_df['Giocatore'] == player].iloc[0]
                            squadra = player_info.get('Squadra', player)
                            potenziale = player_info.get('Potenziale', 0)
                            data_squadre.append({'Giocatore': player, 'Squadra': squadra, 'Potenziale': potenziale})
                        else:
                            data_squadre.append({'Giocatore': player, 'Squadra': player, 'Potenziale': 0})
                    
                    st.session_state.df_squadre = pd.DataFrame(data_squadre)
                    st.session_state.nuovo_torneo_step = 2
                    st.rerun()

        with col2:
            if st.button("↩️ Indietro", use_container_width=True):
                st.session_state.nuovo_torneo_step = 1
                st.rerun()

    elif st.session_state.nuovo_torneo_step == 2:
        st.info(f"**Nome del torneo:** {st.session_state.nome_torneo}")
        st.markdown("### Modifica i nomi delle squadre e il potenziale 📝")
        st.info("Utilizza i campi sottostanti per assegnare una squadra e un potenziale a ogni partecipante.")
        
        if 'gioc_info' not in st.session_state:
            st.session_state['gioc_info'] = {}

        for gioc_df in st.session_state.df_squadre.to_dict('records'):
            gioc = gioc_df['Giocatore']
            
            if gioc not in st.session_state['gioc_info']:
                st.session_state['gioc_info'][gioc] = {
                    "Squadra": gioc_df['Squadra'],
                    "Potenziale": int(gioc_df['Potenziale'])
                }

            with st.container(border=True):
                st.markdown(f"**Giocatore**: {gioc}")
                
                squadra_nuova = st.text_input(
                    f"Squadra",
                    value=st.session_state['gioc_info'][gioc]["Squadra"],
                    key=f"squadra_input_{gioc}"
                )
                
                potenziale_nuovo = st.slider(
                    f"Potenziale",
                    min_value=0,
                    max_value=10,
                    value=int(st.session_state['gioc_info'][gioc]["Potenziale"]),
                    key=f"potenziale_slider_{gioc}"
                )
                
                st.session_state['gioc_info'][gioc]["Squadra"] = squadra_nuova
                st.session_state['gioc_info'][gioc]["Potenziale"] = potenziale_nuovo

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Genera calendario ▶️", type="primary", use_container_width=True):
                df_squadre_aggiornato = []
                for gioc, info in st.session_state['gioc_info'].items():
                    df_squadre_aggiornato.append({
                        "Giocatore": gioc,
                        "Squadra": info["Squadra"],
                        "Potenziale": info["Potenziale"]
                    })
                
                st.session_state.df_squadre = pd.DataFrame(df_squadre_aggiornato)
                
                st.session_state.torneo_iniziato = True
                st.session_state.turno_attivo = 1
                
                classifica_iniziale = pd.DataFrame({
                    "Squadra": st.session_state.df_squadre['Squadra'].tolist(),
                    "Punti": [0] * len(st.session_state.df_squadre),
                    "G": [0] * len(st.session_state.df_squadre),
                    "V": [0] * len(st.session_state.df_squadre),
                    "N": [0] * len(st.session_state.df_squadre),
                    "P": [0] * len(st.session_state.df_squadre),
                    "GF": [0] * len(st.session_state.df_squadre),
                    "GS": [0] * len(st.session_state.df_squadre),
                    "DR": [0] * len(st.session_state.df_squadre),
                }).set_index('Squadra')

                precedenti = set()
                df_turno = genera_accoppiamenti(classifica_iniziale.reset_index(), precedenti)
                df_turno["Turno"] = st.session_state.turno_attivo
                st.session_state.df_torneo = pd.concat([st.session_state.df_torneo, df_turno], ignore_index=True)
                st.session_state.setup_mode = None
                init_results_temp_from_df(st.session_state.df_torneo)
                st.rerun()

        with col2:
            if st.button("↩️ Indietro", use_container_width=True):
                st.session_state.nuovo_torneo_step = 1
                st.rerun()

# -------------------------
# Sidebar
# -------------------------
with st.sidebar:
    st.header("Opzioni Torneo")
    if st.session_state.torneo_iniziato:
        st.info(f"Torneo in corso: **{st.session_state.nome_torneo}**")

        st.markdown("---")
        if tournaments_collection is not None:
            if st.button("💾 Salva su DB", use_container_width=True):
                salva_torneo_su_db()
        st.markdown("---")
        
        if st.button("🏁 Termina Torneo", use_container_width=True):
            st.session_state.torneo_iniziato = False
            st.session_state.setup_mode = None
            st.session_state.df_torneo = pd.DataFrame()
            st.session_state.df_squadre = pd.DataFrame()
            st.session_state.turno_attivo = 0
            st.session_state.risultati_temp = {}
            st.session_state.nuovo_torneo_step = 1
            st.session_state.torneo_finito = False
            st.success("✅ Torneo terminato. Dati resettati.")
            st.rerun()

# -------------------------
# Interfaccia Utente Torneo
# -------------------------
if st.session_state.torneo_iniziato and not st.session_state.torneo_finito:
    st.markdown(f"### Turno {st.session_state.turno_attivo}")
    df_turno_corrente = st.session_state.df_torneo[st.session_state.df_torneo['Turno'] == st.session_state.turno_attivo].copy()
    
    if df_turno_corrente.empty:
        st.warning("⚠️ Non ci sono partite in questo turno. Torna indietro per aggiungere giocatori o carica un altro torneo.")
    else:
        visualizza_incontri_attivi(df_turno_corrente, st.session_state.turno_attivo)

    st.markdown("---")
    
    partite_giocate_turno = st.session_state.df_torneo[st.session_state.df_torneo['Turno'] == st.session_state.turno_attivo]
    tutte_validate = partite_giocate_turno['Validata'].all()
    
    col_class, col_next = st.columns([2, 1])
    with col_class:
        st.subheader("Classifica 🏆")
        classifica_attuale = aggiorna_classifica(st.session_state.df_torneo)
        if not classifica_attuale.empty:
            st.dataframe(classifica_attuale, hide_index=True, use_container_width=True)
        else:
            st.info("Nessuna partita giocata per aggiornare la classifica.")
            
    with col_next:
        st.subheader("Prossimo Turno ➡️")
        if tutte_validate:
            precedenti = set(zip(st.session_state.df_torneo['Casa'], st.session_state.df_torneo['Ospite'])) | set(zip(st.session_state.df_torneo['Ospite'], st.session_state.df_torneo['Casa']))
            df_turno_prossimo = genera_accoppiamenti(classifica_attuale, precedenti)

            if not df_turno_prossimo.empty:
                if st.button("▶️ Genera prossimo turno", use_container_width=True, type="primary"):
                    salva_torneo_su_db() # Salva i risultati del turno corrente
                    st.session_state.turno_attivo += 1
                    df_turno_prossimo["Turno"] = st.session_state.turno_attivo
                    st.session_state.df_torneo = pd.concat([st.session_state.df_torneo, df_turno_prossimo], ignore_index=True)
                    st.session_state.risultati_temp = {}
                    init_results_temp_from_df(df_turno_prossimo)
                    st.rerun()
            else:
                st.info("Non ci sono più accoppiamenti possibili. Il torneo è terminato.")
                st.session_state.torneo_finito = True
                st.rerun()
        else:
            st.warning("⚠️ Per generare il prossimo turno, devi validare tutti i risultati.")

# -------------------------
# Esportazione
# -------------------------
if st.session_state.torneo_iniziato and not st.session_state.df_torneo.empty:
    pdf_bytes = esporta_pdf(st.session_state.df_torneo, st.session_state.nome_torneo)
    file_name_pdf = f"{st.session_state.nome_torneo.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    st.sidebar.download_button(
        label="⬇️ Esporta torneo in PDF",
        data=pdf_bytes,
        file_name=file_name_pdf,
        mime="application/pdf"
    )
        
# -------------------------
# Banner vincitore
# -------------------------
if st.session_state.torneo_finito:
    st.subheader("Classifica Finale 🥇")
    df_class = aggiorna_classifica(st.session_state.df_torneo)
    if not df_class.empty:
        st.dataframe(df_class, hide_index=True, use_container_width=True)
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
                🏆 Il vincitore del torneo {st.session_state.nome_torneo} è {vincitore}! 🎉
             </div>
             """, unsafe_allow_html=True)
        st.balloons()
        # we are the champions
        # Codice corretto per scaricare l'audio dall'URL
        audio_url = "https://raw.githubusercontent.com/legnaro72/torneo-Subbuteo-webapp/main/docs/wearethechamp.mp3"
        try:
            response = requests.get(audio_url, timeout=10) # Imposta un timeout
            response.raise_for_status() # Lancia un'eccezione per risposte HTTP errate
            autoplay_audio(response.content)
        except requests.exceptions.RequestException as e:
            st.error(f"Errore durante lo scaricamento dell'audio: {e}")

        # Crea un contenitore vuoto per i messaggi
        placeholder = st.empty()

        # Lancia i palloncini in un ciclo per 3 secondi
        with placeholder.container():
            st.balloons()
            time.sleep(1) # Aspetta 1 secondo
        
        with placeholder.container():
            st.balloons()
            time.sleep(1) # Aspetta 1 secondo
        
        with placeholder.container():
            st.balloons()
            time.sleep(1) # Aspetta 1 secondo
