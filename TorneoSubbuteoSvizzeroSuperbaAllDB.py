import streamlit as st
import pandas as pd
from datetime import datetime
import io
from fpdf import FPDF
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId

st.set_page_config(page_title="⚽ Torneo Subbuteo - Sistema Svizzero", layout="wide")

# -------------------------
# Connessione a MongoDB Atlas
# -------------------------

players_collection = None
tournaments_collection = None
st.info("Tentativo di connessione a MongoDB...")
try:
    MONGO_URI=st.secrets["MONGO_URI"]
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

    st.success("✅ Connessione a MongoDB Atlas riuscita.")
except Exception as e:
    st.error(f"❌ Errore di connessione a MongoDB: {e}. Non sarà possibile caricare/salvare i dati del database.")

# -------------------------
# Funzioni di utilità
# -------------------------

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

def carica_nomi_tornei_da_db():
    """Carica i nomi dei tornei disponibili dal DB."""
    if tournaments_collection is None:
        return []
    try:
        tornei = tournaments_collection.find({}, {"nome_torneo": 1}).sort("data_salvataggio", -1)
        return list(tornei)
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
    "club_scelto": "Superba",
    "giocatori_scelti": [],
    "squadre_data": [],
    "torneo_iniziato": False,
    "setup_mode": None,
    "nome_torneo": "Torneo Subbuteo - Sistema Svizzero"
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

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
                <p style='margin:0.2rem 0 1rem 0'>Riprendi un torneo salvato (MongoDB)</p>
                </div>""",
            unsafe_allow_html=True,
        )
        if st.button("Carica torneo (MongoDB)", key="btn_carica"):
            st.session_state.setup_mode = "carica_db"
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
            st.session_state.club_scelto = "Superba"
            st.rerun()

    st.markdown("---")

# -------------------------
# Logica di caricamento o creazione torneo
# -------------------------
if st.session_state.setup_mode == "carica_db":
    st.markdown("#### 📥 Carica torneo da MongoDB")
    tornei_disponibili = carica_nomi_tornei_da_db()
    if tornei_disponibili:
        nomi_tornei = [t['nome_torneo'] for t in tornei_disponibili]
        opzione_scelta = st.selectbox("Seleziona il torneo da caricare:", nomi_tornei)
        if st.button("Carica Torneo Selezionato"):
            if carica_torneo_da_db(opzione_scelta):
                st.success("✅ Torneo caricato! Ora puoi continuare da dove eri rimasto.")
                st.rerun()
    else:
        st.warning("⚠️ Nessun torneo trovato nel database.")
    if st.button("Indietro"):
        st.session_state.setup_mode = None
        st.rerun()


if st.session_state.setup_mode == "carica_csv":
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
        st.markdown(f"### Club selezionato: **{st.session_state.club_scelto}**")
        # Legge i giocatori da MongoDB
        df_gioc = carica_giocatori_da_db()
        st.markdown("**Numero partecipanti** (min 2)")
        num_squadre = st.number_input("Numero partecipanti", min_value=2, max_value=100, value=8, step=1, key="num_partecipanti")

        if not df_gioc.empty:
            giocatori_df = df_gioc
            st.session_state.giocatori_scelti = st.multiselect(
                "Seleziona i giocatori che partecipano al torneo",
                options=giocatori_df['Giocatore'].tolist(),
                default=st.session_state.giocatori_scelti,
            )
        else:
            st.warning("⚠️ Impossibile caricare i giocatori dal database. Aggiungi i giocatori manualmente.")
            if 'giocatori_temp' not in st.session_state:
                st.session_state.giocatori_temp = [""] * num_squadre
            for i in range(num_squadre):
                st.session_state.giocatori_temp[i] = st.text_input(f"Nome Giocatore {i+1}", key=f"manual_player_{i}", value=st.session_state.giocatori_temp[i])

            st.session_state.giocatori_scelti = [p for p in st.session_state.giocatori_temp if p.strip()]

        if st.session_state.giocatori_scelti and st.button("Prossimo passo", key="next_step_1"):
            if len(st.session_state.giocatori_scelti) < 2:
                st.error("Devi selezionare almeno 2 giocatori per iniziare il torneo.")
            else:
                st.session_state.squadre_data = st.session_state.giocatori_scelti
                st.session_state.nuovo_torneo_step = 2
                st.rerun()
        if st.button("Indietro"):
            st.session_state.nuovo_torneo_step = 0
            st.rerun()

    elif st.session_state.nuovo_torneo_step == 2:
        st.markdown(f"**Nome del torneo:** {st.session_state.nome_torneo}")
        st.markdown(f"**Giocatori selezionati:** {', '.join(st.session_state.squadre_data)}")
        st.markdown("### Conferma giocatori e inizia torneo")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Inizia Torneo", type="primary"):
                squadre_shuffled = pd.DataFrame({'Squadra': st.session_state.squadre_data}).sample(frac=1).reset_index(drop=True)
                st.session_state.df_squadre = squadre_shuffled
                st.session_state.torneo_iniziato = True
                st.session_state.turno_attivo = 1
                
                classifica_iniziale = pd.DataFrame({
                    "Squadra": st.session_state.squadre_data,
                    "Punti": [0] * len(st.session_state.squadre_data),
                    "G": [0] * len(st.session_state.squadre_data),
                    "V": [0] * len(st.session_state.squadre_data),
                    "N": [0] * len(st.session_state.squadre_data),
                    "P": [0] * len(st.session_state.squadre_data),
                    "GF": [0] * len(st.session_state.squadre_data),
                    "GS": [0] * len(st.session_state.squadre_data),
                    "DR": [0] * len(st.session_state.squadre_data),
                }).set_index('Squadra')

                precedenti = set()
                df_turno = genera_accoppiamenti(classifica_iniziale.reset_index(), precedenti)
                df_turno["Turno"] = st.session_state.turno_attivo
                st.session_state.df_torneo = df_turno
                st.session_state.setup_mode = None
                init_results_temp_from_df(st.session_state.df_torneo)
                st.rerun()

        with col2:
            if st.button("Indietro"):
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
            if st.button("💾 Salva su DB"):
                salva_torneo_su_db()
        st.markdown("---")
        
        if st.button("🏁 Termina Torneo"):
            st.session_state.torneo_iniziato = False
            st.session_state.setup_mode = None
            st.session_state.df_torneo = pd.DataFrame()
            st.session_state.df_squadre = pd.DataFrame()
            st.session_state.turno_attivo = 0
            st.session_state.risultati_temp = {}
            st.session_state.nuovo_torneo_step = 1
            st.success("✅ Torneo terminato. Dati resettati.")
            st.rerun()

# -------------------------
# Interfaccia Utente Torneo
# -------------------------
if st.session_state.torneo_iniziato:
    st.markdown(f"### Turno {st.session_state.turno_attivo}")
    df_turno_corrente = st.session_state.df_torneo[st.session_state.df_torneo['Turno'] == st.session_state.turno_attivo].copy()
    
    col_matches = st.columns(len(df_turno_corrente))
    
    for i, riga in df_turno_corrente.iterrows():
        with col_matches[i]:
            with st.container(border=True):
                st.markdown(f"<p style='text-align:center; font-size:1.2rem; font-weight:bold;'>⚽ Partita {i+1}</p>", unsafe_allow_html=True)
                casa = riga['Casa']
                ospite = riga['Ospite']
                key_gc = f"gc_{st.session_state.turno_attivo}_{casa}_{ospite}"
                key_go = f"go_{st.session_state.turno_attivo}_{casa}_{ospite}"
                key_val = f"val_{st.session_state.turno_attivo}_{casa}_{ospite}"
                
                valida_key = f"valida_{st.session_state.turno_attivo}_{casa}_{ospite}"
                
                st.markdown(f"<p style='text-align:center; font-weight:bold;'>{casa} - {ospite}</p>", unsafe_allow_html=True)
                
                c_score1, c_score2 = st.columns(2)
                with c_score1:
                    st.session_state.risultati_temp[key_gc] = st.number_input(f"Gol {casa}", min_value=0, key=key_gc, disabled=st.session_state.risultati_temp.get(key_val, False))
                with c_score2:
                    st.session_state.risultati_temp[key_go] = st.number_input(f"Gol {ospite}", min_value=0, key=key_go, disabled=st.session_state.risultati_temp.get(key_val, False))
                
                if st.button("Valida Risultato", key=valida_key, disabled=st.session_state.risultati_temp.get(key_val, False)):
                    df_turno_corrente.loc[df_turno_corrente['Casa'] == casa, 'GolCasa'] = st.session_state.risultati_temp[key_gc]
                    df_turno_corrente.loc[df_turno_corrente['Casa'] == casa, 'GolOspite'] = st.session_state.risultati_temp[key_go]
                    df_turno_corrente.loc[df_turno_corrente['Casa'] == casa, 'Validata'] = True
                    st.session_state.df_torneo.loc[df_turno_corrente.index, ['GolCasa', 'GolOspite', 'Validata']] = df_turno_corrente.loc[df_turno_corrente.index, ['GolCasa', 'GolOspite', 'Validata']]
                    st.session_state.risultati_temp[key_val] = True
                    st.success("✅ Risultato validato!")
                    st.rerun()

    st.markdown("---")
    
    partite_giocate_turno = st.session_state.df_torneo[st.session_state.df_torneo['Turno'] == st.session_state.turno_attivo]
    tutte_validate = partite_giocate_turno['Validata'].all()
    
    col_class, col_next = st.columns([2, 1])
    with col_class:
        st.subheader("Classifica")
        classifica_attuale = aggiorna_classifica(st.session_state.df_torneo)
        if not classifica_attuale.empty:
            st.dataframe(classifica_attuale, hide_index=True, use_container_width=True)
        else:
            st.info("Nessuna partita giocata per aggiornare la classifica.")
            
    with col_next:
        st.subheader("Prossimo Turno")
        if tutte_validate:
            if st.button("▶️ Genera prossimo turno", use_container_width=True, type="primary"):
                st.session_state.turno_attivo += 1
                precedenti = set(zip(st.session_state.df_torneo['Casa'], st.session_state.df_torneo['Ospite'])) | set(zip(st.session_state.df_torneo['Ospite'], st.session_state.df_torneo['Casa']))
                df_turno_prossimo = genera_accoppiamenti(classifica_attuale, precedenti)
                df_turno_prossimo["Turno"] = st.session_state.turno_attivo
                st.session_state.df_torneo = pd.concat([st.session_state.df_torneo, df_turno_prossimo], ignore_index=True)
                st.session_state.risultati_temp = {}
                init_results_temp_from_df(df_turno_prossimo)
                st.rerun()
        else:
            st.warning("⚠️ Per generare il prossimo turno, devi validare tutti i risultati.")

# -------------------------
# Esportazione
# -------------------------
if st.session_state.torneo_iniziato and not st.session_state.df_torneo.empty:
    df_torneo_csv = st.session_state.df_torneo.to_csv(index=False)
    st.sidebar.download_button(
        label="⬇️ Esporta torneo in CSV",
        data=df_torneo_csv,
        file_name=f"{st.session_state.nome_torneo.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )
    
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
                    🏆 Il vincitore del torneo {st.session_state.nome_torneo} è {vincitore}! 🎉
                 </div>
                 """, unsafe_allow_html=True)
