
import streamlit as st
import pandas as pd
from datetime import datetime
import io
from fpdf import FPDF
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from bson.objectid import ObjectId
import requests
import base64
import time
import urllib.parse
import os

# Import auth utilities
import auth_utils as auth
from auth_utils import verify_write_access

# Mostra la schermata di autenticazione se non si è già autenticati
if not st.session_state.get('authenticated', False):
    auth.show_auth_screen(club="Superba")
    st.stop()

# -------------------------
# Configurazione della pagina
# -------------------------
st.set_page_config(
    page_title="Torneo Subbuteo - Svizzero",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

def reset_app_state():
    """Resetta lo stato dell'applicazione"""
    keys_to_reset = [
        "df_torneo", "df_squadre", "turno_attivo", "risultati_temp",
        "nuovo_torneo_step", "club_scelto", "giocatori_selezionati_db",
        "giocatori_ospiti", "giocatori_totali", "torneo_iniziato",
        "setup_mode", "torneo_finito", "edited_df_squadre",
        "gioc_info", "modalita_visualizzazione"
    ]
    for key in keys_to_reset:
        if key in st.session_state:
            del st.session_state[key]

# Inizializza lo stato della sessione
if st.session_state.get('sidebar_state_reset', False):
    reset_app_state()
    st.session_state['sidebar_state_reset'] = False
    st.rerun()


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
    "gioc_info": {},
    "modalita_visualizzazione": "Squadre"
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Aggiornamento del nome del torneo se è finito
if st.session_state.torneo_finito and not st.session_state.nome_torneo.startswith("finito_"):
    st.session_state.nome_torneo = f"finito_{st.session_state.nome_torneo}"

# -------------------------
# CSS personalizzato
# -------------------------
st.markdown("""
<style>
.stButton>button { 
    background: linear-gradient(90deg, #457b9d, #1d3557); 
    color: white; 
    border-radius: 10px; 
    padding: 0.55em 1.0em; 
    font-weight: 700; 
    border: 0; 
    box-shadow: 0 4px 14px #00000022;
}
.stButton>button:hover { 
    transform: translateY(-1px); 
    box-shadow: 0 6px 18px #00000033; 
}
.stDownloadButton>button { 
    background: linear-gradient(90deg, #457b9d, #1d3557); 
    color: white; 
    border-radius: 10px; 
    font-weight: 700; 
    border: 0; 
    box-shadow: 0 4px 14px #00000022;
}
.stDownloadButton>button:hover { 
    transform: translateY(-1px); 
    box-shadow: 0 6px 18px #00000033; 
}
        
        /* Stile per il link button nella sidebar sia per tema chiaro che scuro */
        [data-testid="stSidebar"] .stLinkButton a {
            color: white !important;
            background: linear-gradient(90deg, #457b9d, #1d3557) !important;
            border-radius: 10px !important;
            padding: 0.55em 1.0em !important;
            font-weight: 700 !important;
            text-decoration: none !important;
            transition: all 0.2s ease !important;
            display: inline-block !important;
            width: 100% !important;
            text-align: center !important;
            border: none !important;
            box-shadow: 0 4px 14px #00000022 !important;
        }
        
        [data-testid="stSidebar"] .stLinkButton a:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 18px #00000033 !important;
            color: white !important;
        }
        
        [data-testid="stSidebar"] .stLinkButton a:active {
            transform: translateY(0) !important;
        }
        
        /* Override per il tema scuro */
        .stApp[data-theme="dark"] [data-testid="stSidebar"] .stLinkButton a,
        html[data-theme="dark"] [data-testid="stSidebar"] .stLinkButton a,
        body[data-theme="dark"] [data-testid="stSidebar"] .stLinkButton a {
            color: white !important;
        }
/* Main content h3 styling - solo per contenuto principale */
.main .block-container h3 { 
    color: white; 
    font-weight: 700;
    background: linear-gradient(90deg, #457b9d, #1d3557);
    border-radius: 10px;
    box-shadow: 0 4px 14px #00000022;
    padding: 10px;
    text-align: center;
}
/* Sidebar h3 styling - mantiene stile normale */
.css-1d391kg h3, [data-testid="stSidebar"] h3 {
    color: #1d3557;
    font-weight: 700;
    background: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
    text-align: left !important;
}

/* Tema scuro - sidebar subheaders bianchi con selettori più specifici */
@media (prefers-color-scheme: dark) {
    [data-testid="stSidebar"] h3,
    .css-1d391kg h3,
    [data-testid="stSidebar"] .element-container h3,
    .css-1d391kg .element-container h3 {
        color: #ffffff !important;
        background: none !important;
    }
}

/* Streamlit dark theme - sidebar subheaders bianchi con priorità massima */
.stApp[data-theme="dark"] [data-testid="stSidebar"] h3,
.stApp[data-theme="dark"] .css-1d391kg h3,
.stApp[data-theme="dark"] [data-testid="stSidebar"] .element-container h3,
.stApp[data-theme="dark"] .css-1d391kg .element-container h3,
.stApp[data-theme="dark"] [data-testid="stSidebar"] div h3,
.stApp[data-theme="dark"] .css-1d391kg div h3 {
    color: #ffffff !important;
    background: none !important;
}

/* Selettori ancora più specifici per forzare il bianco sui subheader */
html[data-theme="dark"] [data-testid="stSidebar"] h3,
html[data-theme="dark"] .css-1d391kg h3,
body[data-theme="dark"] [data-testid="stSidebar"] h3,
body[data-theme="dark"] .css-1d391kg h3 {
    color: #ffffff !important;
}

/* Override per tutti i possibili selettori di subheader nella sidebar */
[data-testid="stSidebar"] h3[class*="css"],
.css-1d391kg h3[class*="css"] {
    color: #ffffff !important;
}

/* CSS con massima specificità per tema scuro */
.stApp[data-theme="dark"] [data-testid="stSidebar"] * h3,
.stApp[data-theme="dark"] .css-1d391kg * h3 {
    color: #ffffff !important;
}

/* Approccio universale - forza bianco su TUTTI gli h3 della sidebar nel tema scuro */
@media (prefers-color-scheme: dark) {
    [data-testid="stSidebar"] h3 {
        color: white !important;
    }
}

.stApp[data-theme="dark"] [data-testid="stSidebar"] h3 {
    color: white !important;
}

/* Selettore CSS universale per tutti gli elementi h3 nella sidebar */
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] .stMarkdown h3,
[data-testid="stSidebar"] div h3 {
    color: white !important;
}

/* Forza il colore blu per i subheader della sidebar in entrambi i temi */
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h3[class*="st-emotion-cache"],
[data-testid="stSidebar"] h3[class*="css"],
[data-testid="stSidebar"] h3[class*="element-container"],
[data-testid="stSidebar"] h3[class*="stMarkdown"],
[data-testid="stSidebar"] h3[class*="stSubheader"],
[data-testid="stSidebar"] h3[class*="stHeadingContainer"],
[data-testid="stSidebar"] h3[class*="stTitle"],
[data-testid="stSidebar"] .stMarkdown h3,
[data-testid="stSidebar"] .element-container h3,
[data-testid="stSidebar"] .stSubheader h3,
[data-testid="stSidebar"] .stHeadingContainer h3,
[data-testid="stSidebar"] .stTitle h3,
.stApp[data-theme="light"] [data-testid="stSidebar"] h3,
.stApp[data-theme="dark"] [data-testid="stSidebar"] h3,
html[data-theme="light"] [data-testid="stSidebar"] h3,
html[data-theme="dark"] [data-testid="stSidebar"] h3,
body[data-theme="light"] [data-testid="stSidebar"] h3,
body[data-theme="dark"] [data-testid="stSidebar"] h3 {
    color: #0078D4 !important;
    font-weight: 700;
    background: none !important;
    border-radius: 0 !important;
    box-shadow: none !important;
    padding: 0 !important;
    text-align: left !important;
}

/* Rimuovi eventuali stili di hover o focus che potrebbero sovrascrivere */
[data-testid="stSidebar"] h3:hover,
[data-testid="stSidebar"] h3:focus,
[data-testid="stSidebar"] h3:active {
    color: #0078D4 !important;
}

/* Forza il colore anche per i temi personalizzati */
[data-testid="stSidebar"] h3[style*="color"],
[data-testid="stSidebar"] h3[style*="color"]:hover,
[data-testid="stSidebar"] h3[style*="color"]:focus {
    color: #0078D4 !important;
}
""", unsafe_allow_html=True)

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

        #st.sidebar.toast("✅ Connessione a MongoDB Atlas riuscita.")
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
    if not verify_write_access():
        st.error("⛔ Accesso in sola lettura. Non è possibile salvare le modifiche.")
        return False
        
    if tournaments_collection is None:
        st.error("❌ Connessione a MongoDB non attiva, impossibile salvare.")
        return False

    torneo_data = {
        "nome_torneo": st.session_state.nome_torneo,
        "data_salvataggio": datetime.now(),
        "df_torneo": st.session_state.df_torneo.to_dict('records'),
        "df_squadre": st.session_state.df_squadre.to_dict('records'),
        "turno_attivo": st.session_state.turno_attivo,
        "torneo_iniziato": st.session_state.torneo_iniziato,
    }

    try:
        # Se abbiamo un ID torneo nella sessione, aggiorniamo quel documento specifico
        if 'tournament_id' in st.session_state and st.session_state.tournament_id:
            tournaments_collection.update_one(
                {"_id": ObjectId(st.session_state.tournament_id)},
                {"$set": torneo_data}
            )
            st.success(f"✅ Torneo '{st.session_state.nome_torneo}' aggiornato con successo!")
        else:
            # Altrimenti cerchiamo un torneo esistente con lo stesso nome
            existing_doc = tournaments_collection.find_one({"nome_torneo": st.session_state.nome_torneo})
            
            if existing_doc:
                # Aggiorna il documento esistente e salva l'ID nella sessione
                tournaments_collection.update_one(
                    {"_id": existing_doc["_id"]},
                    {"$set": torneo_data}
                )
                st.session_state.tournament_id = str(existing_doc["_id"])
                st.success(f"✅ Torneo esistente '{st.session_state.nome_torneo}' aggiornato con successo!")
            else:
                # Crea un nuovo documento e salva l'ID nella sessione
                result = tournaments_collection.insert_one(torneo_data)
                st.session_state.tournament_id = str(result.inserted_id)
                st.success(f"✅ Nuovo torneo '{st.session_state.nome_torneo}' salvato con successo!")
    except Exception as e:
        st.error(f"❌ Errore durante il salvataggio del torneo: {e}")

@st.cache_data(ttl=300)  # Cache per 5 minuti
def carica_nomi_tornei_da_db():
    """Carica i nomi dei tornei disponibili dal DB."""
    if tournaments_collection is None:
        return []
    try:
        # Usiamo distinct per ottenere direttamente la lista dei nomi senza duplicati
        return sorted(tournaments_collection.distinct("nome_torneo"))
    except Exception as e:
        st.error(f"❌ Errore caricamento tornei: {e}")
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
            # Salva l'ID del torneo nella sessione
            st.session_state.tournament_id = str(torneo_data['_id'])
            # 💡 AGGIUNGI QUESTA RIGA 💡
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
    try:
        pdf = FPDF()
        pdf.add_page()
        
        # Titolo del torneo
        pdf.set_font("Arial", "B", 16)
        titolo = nome_torneo.encode("latin-1", "ignore").decode("latin-1")
        pdf.cell(0, 15, titolo, ln=True, align="C")
        
        # Data di generazione
        pdf.set_font("Arial", "I", 10)
        pdf.cell(0, 8, f"Generato il: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align="C")
        pdf.ln(10)

        # Sezione Partite
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Partite", ln=True)
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
            
            # Gestione caratteri speciali
            casa = casa.encode("latin-1", "ignore").decode("latin-1")
            osp = osp.encode("latin-1", "ignore").decode("latin-1")
            
            match_text = f"{casa} {gc} - {go} {osp}"
            
            # Colore in base allo stato della partita
            if bool(r.get("Validata", False)):
                pdf.set_text_color(0, 100, 0)  # Verde scuro per partite validate
            else:
                pdf.set_text_color(128, 128, 128)  # Grigio per partite non validate
            
            pdf.cell(0, 8, match_text, ln=True)

        # Sezione Classifica
        pdf.ln(15)
        pdf.set_text_color(0, 0, 0)  # Ripristina il colore nero
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Classifica", ln=True)
        
        classifica = aggiorna_classifica(df_torneo)
        if not classifica.empty:
            # Intestazione tabella
            pdf.set_font("Arial", "B", 10)
            header = ['Pos', 'Squadra', 'Punti', 'G', 'V', 'N', 'P', 'GF', 'GS', 'DR']
            col_widths = [12, 50, 12, 8, 8, 8, 8, 8, 8, 8]
            
            # Intestazione con bordi
            for i, h in enumerate(header):
                pdf.cell(col_widths[i], 8, h, border=1, align='C')
            pdf.ln()

            # Dettagli classifica
            pdf.set_font("Arial", "", 10)
            for idx, (_, row) in enumerate(classifica.iterrows(), 1):
                pdf.cell(col_widths[0], 8, str(idx), border=1, align='C')
                pdf.cell(col_widths[1], 8, str(row['Squadra']).encode("latin-1", "ignore").decode("latin-1"), border=1)
                pdf.cell(col_widths[2], 8, str(row['Punti']), border=1, align='C')
                pdf.cell(col_widths[3], 8, str(row['G']), border=1, align='C')
                pdf.cell(col_widths[4], 8, str(row['V']), border=1, align='C')
                pdf.cell(col_widths[5], 8, str(row['N']), border=1, align='C')
                pdf.cell(col_widths[6], 8, str(row['P']), border=1, align='C')
                pdf.cell(col_widths[7], 8, str(row['GF']), border=1, align='C')
                pdf.cell(col_widths[8], 8, str(row['GS']), border=1, align='C')
                pdf.cell(col_widths[9], 8, str(row['DR']), border=1, align='C')
                pdf.ln()

        # Genera il PDF in memoria
        return pdf.output(dest='S').encode('latin-1')
        
    except Exception as e:
        st.error(f"Errore durante la generazione del PDF: {str(e)}")
        return None


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

def visualizza_incontri_attivi(df_turno_corrente, turno_attivo, modalita_visualizzazione):
    """Visualizza gli incontri del turno attivo e permette di inserire e validare i risultati."""
    for i, riga in df_turno_corrente.iterrows():
        with st.container(border=True):
            casa = riga['Casa']
            ospite = riga['Ospite']
            key_gc = f"gc_{turno_attivo}_{casa}_{ospite}"
            key_go = f"go_{turno_attivo}_{casa}_{ospite}"
            key_val = f"val_{turno_attivo}_{casa}_{ospite}"
            valida_key = f"valida_{turno_attivo}_{casa}_{ospite}"

            # Recupera i dati di squadra e giocatore per la visualizzazione
            info_casa = st.session_state.df_squadre[st.session_state.df_squadre['Squadra'] == casa].iloc[0]
            info_ospite = st.session_state.df_squadre[st.session_state.df_squadre['Squadra'] == ospite].iloc[0]

            nome_squadra_casa = info_casa['Squadra']
            nome_giocatore_casa = info_casa['Giocatore']
            nome_squadra_ospite = info_ospite['Squadra']
            nome_giocatore_ospite = info_ospite['Giocatore']
            
            st.markdown(f"<p style='text-align:center; font-size:1.2rem; font-weight:bold;'>⚽ Partita</p>", unsafe_allow_html=True)
            
            match_string = ""
            if modalita_visualizzazione == 'Squadre':
                match_string = f"{nome_squadra_casa} 🆚 {nome_squadra_ospite}"
            elif modalita_visualizzazione == 'Giocatori':
                match_string = f"{nome_giocatore_casa} 🆚 {nome_giocatore_ospite}"
            elif modalita_visualizzazione == 'Completa':
                match_string = f"{nome_squadra_casa} ({nome_giocatore_casa}) 🆚 {nome_squadra_ospite} ({nome_giocatore_ospite})"
                
            st.markdown(f"<p style='text-align:center; font-weight:bold;'>🏠{match_string}🛫</p>", unsafe_allow_html=True)

            # 💡 MODIFICA QUI 💡
            # Usa il valore del DataFrame per inizializzare l'input se non è già nello stato temporaneo
            gol_casa_iniziale = riga.get('GolCasa', 0)
            gol_ospite_iniziale = riga.get('GolOspite', 0)
            validata_iniziale = bool(riga.get('Validata', False))

            if key_gc not in st.session_state.risultati_temp:
                st.session_state.risultati_temp[key_gc] = gol_casa_iniziale
            if key_go not in st.session_state.risultati_temp:
                st.session_state.risultati_temp[key_go] = gol_ospite_iniziale
            if key_val not in st.session_state.risultati_temp:
                st.session_state.risultati_temp[key_val] = validata_iniziale
            
            c_score1, c_score2 = st.columns(2)
            with c_score1:
                st.session_state.risultati_temp[key_gc] = st.number_input(
                    f"Gol {casa}",
                    min_value=0,
                    value=st.session_state.risultati_temp[key_gc], # Usa il valore salvato in session_state
                    key=key_gc,
                    disabled=st.session_state.risultati_temp.get(key_val, False)
                )
            with c_score2:
                st.session_state.risultati_temp[key_go] = st.number_input(
                    f"Gol {ospite}",
                    min_value=0,
                    value=st.session_state.risultati_temp[key_go], # Usa il valore salvato in session_state
                    key=key_go,
                    disabled=st.session_state.risultati_temp.get(key_val, False)
                )
            
            st.markdown("---")
            validata_checkbox = st.checkbox(
                "✅ Valida Risultato",
                value=st.session_state.risultati_temp.get(key_val, False),
                key=valida_key
            )
            
            # Aggiorna il risultato quando la checkbox cambia stato
            if validata_checkbox != st.session_state.risultati_temp.get(key_val, False):
                st.session_state.risultati_temp[key_val] = validata_checkbox
                if validata_checkbox:
                    # Salva i risultati nel DataFrame quando viene validato
                    df_turno_corrente.loc[df_turno_corrente['Casa'] == casa, 'GolCasa'] = st.session_state.risultati_temp[key_gc]
                    df_turno_corrente.loc[df_turno_corrente['Casa'] == casa, 'GolOspite'] = st.session_state.risultati_temp[key_go]
                    df_turno_corrente.loc[df_turno_corrente['Casa'] == casa, 'Validata'] = True
                    st.session_state.df_torneo.loc[df_turno_corrente.index, ['GolCasa', 'GolOspite', 'Validata']] = df_turno_corrente.loc[df_turno_corrente.index, ['GolCasa', 'GolOspite', 'Validata']]
                    st.success("✅ Risultato validato!")
                else:
                    # Rimuovi la validazione se deselezionata
                    df_turno_corrente.loc[df_turno_corrente['Casa'] == casa, 'Validata'] = False
                    st.session_state.df_torneo.loc[df_turno_corrente.index, 'Validata'] = False
                    st.info("⚠️ Validazione rimossa")
                st.rerun()
            
            # Mostra stato validazione
            if st.session_state.risultati_temp.get(key_val, False):
                st.success("✅ Partita validata!")
            else:
                st.warning("⚠️ Partita non ancora validata.")

# -------------------------
# Header grafico
# -------------------------
st.markdown(f"""
<div style='text-align:center; padding:20px; border-radius:10px; background: linear-gradient(90deg, #457b9d, #1d3557); box-shadow: 0 4px 14px #00000022;'>
    <h1 style='color:white; font-weight:700; margin:0;'>🇨🇭⚽ {st.session_state.nome_torneo} 🏆🇨🇭</h1>
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
            # Convert NumPy boolean to Python boolean for the disabled state
            is_disabled_new = bool(not verify_write_access())
            if st.button("Nuovo torneo ✨", key="btn_nuovo", use_container_width=True, disabled=is_disabled_new):
                if verify_write_access():
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
                else:
                    st.error("⛔ Accesso in sola lettura. Non è possibile creare nuovi tornei.")
                st.session_state.gioc_info = {} # Reset del dizionario per la nuova grafica
                st.rerun()

    st.markdown("---")

if "mostra_incontri_disputati" not in st.session_state:
    st.session_state["mostra_incontri_disputati"] = False

# -------------------------
# Logica di caricamento o creazione torneo
# -------------------------
if st.session_state.setup_mode == "carica_db":
    st.markdown("#### 📥 Carica torneo da MongoDB")
    with st.spinner("Caricamento elenco tornei..."):
        tornei_disponibili = carica_nomi_tornei_da_db()
    
    if tornei_disponibili:
        st.success(f"✅ Trovati {len(tornei_disponibili)} tornei disponibili")
        opzione_scelta = st.selectbox(
            "Seleziona il torneo da caricare:", 
            tornei_disponibili,
            index=0,
            key="torneo_selezionato"
        )
        
        col1, col2 = st.columns(2)
        with col1:
            # Mostra un avviso se in modalità sola lettura
            if not verify_write_access():
                st.info("🔒 Modalità di sola lettura attiva. Puoi visualizzare ma non modificare i tornei.")
                
            # Convert NumPy boolean to Python boolean for the disabled state
            is_disabled_load = bool(not verify_write_access() and not opzione_scelta)
            if st.button("🔄 Carica Torneo", 
                        type="primary", 
                        use_container_width=True,
                        disabled=is_disabled_load,
                        help="Carica il torneo selezionato" + ("" if verify_write_access() else " (accesso in sola lettura)")):
                with st.spinner(f"Caricamento di '{opzione_scelta}' in corso..."):
                    if carica_torneo_da_db(opzione_scelta):
                        st.balloons()
                        st.success(f"✅ Torneo '{opzione_scelta}' caricato con successo!")
                        st.session_state.torneo_finito = False
                        st.rerun()
            
            # Pulsante per la visualizzazione in sola lettura
            if not verify_write_access() and opzione_scelta:
                if st.button("👁️ Visualizza Torneo (Sola Lettura)", 
                           use_container_width=True,
                           type="secondary"):
                    with st.spinner(f"Caricamento in modalità di sola lettura di '{opzione_scelta}'..."):
                        if carica_torneo_da_db(opzione_scelta):
                            st.balloons()
                            st.success(f"✅ Torneo '{opzione_scelta}' caricato in modalità di sola lettura!")
                            st.session_state.torneo_finito = False
                            st.rerun()
        with col2:
            if st.button("↩️ Torna indietro", use_container_width=True):
                st.session_state.setup_mode = None
                st.rerun()
    else:
        st.warning("⚠️ Nessun torneo trovato nel database.")
        if st.button("↩️ Torna indietro"):
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
# Debug: mostra utente autenticato e ruolo
if st.session_state.get("authenticated"):
    user = st.session_state.get("user", {})
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**👤 Utente:** {user.get('username', '??')}")
    st.sidebar.markdown(f"**🔑 Ruolo:** {user.get('role', '??')}")
    st.sidebar.markdown("---")

# ✅ 1. 🕹️ Gestione Rapida (in cima)
st.sidebar.subheader("🕹️ Gestione Rapida")
st.sidebar.link_button("➡️ Vai a Hub Tornei", "https://farm-tornei-subbuteo-superba-all-db.streamlit.app/", use_container_width=True)
st.sidebar.markdown("---")

if st.session_state.torneo_iniziato:
    #st.sidebar.info(f"Torneo in corso: **{st.session_state.nome_torneo}**")
    
    # ✅ 2. ⚙️ Opzioni Torneo
    st.sidebar.subheader("⚙️ Opzioni Torneo")
    if tournaments_collection is not None:
        # Convert NumPy boolean to Python boolean for the disabled state
        is_disabled_save = bool(not verify_write_access())
        if st.sidebar.button("💾 Salva Torneo", 
                            use_container_width=True, 
                            type="primary",
                            disabled=is_disabled_save,
                            help="Salva il torneo" + ("" if verify_write_access() else " (accesso in sola lettura)")):
            if verify_write_access():
                salva_torneo_su_db()
            else:
                st.error("⛔ Accesso in sola lettura. Non è possibile salvare le modifiche.")
        st.sidebar.success("✅ Torneo salvato su DB!")

    # Convert NumPy boolean to Python boolean for the disabled state
    is_disabled_finish = bool(not verify_write_access())
    if st.sidebar.button("🏁 Termina Torneo", 
                        key="reset_app", 
                        use_container_width=True,
                        disabled=is_disabled_finish,
                        help="Termina il torneo corrente" + ("" if verify_write_access() else " (accesso in sola lettura)")):
        if verify_write_access():
            salva_torneo_su_db()
            st.session_state.torneo_iniziato = False
            st.session_state.setup_mode = None
            st.session_state.df_torneo = pd.DataFrame()
            st.session_state.df_squadre = pd.DataFrame()
            st.session_state.turno_attivo = 0
            st.session_state.risultati_temp = {}
            st.session_state.nuovo_torneo_step = 1
            st.rerun()
        else:
            st.error("⛔ Accesso in sola lettura. Non è possibile terminare il torneo.")
        st.session_state.torneo_finito = False
        st.sidebar.success("✅ Torneo terminato. Dati resettati.")
        st.rerun()

    st.sidebar.markdown("---")

    # ✅ 3. 🔧 Utility (sezione principale con sottosezioni)
    st.sidebar.subheader("🔧 Utility")
    
    # 🔎 Visualizzazione incontri
    with st.sidebar.expander("🔎 Visualizzazione incontri", expanded=False):
        st.session_state.modalita_visualizzazione = st.radio(
            "Formato incontri:",
            options=["Squadre", "Giocatori", "Completa"],
            index=["Squadre", "Giocatori", "Completa"].index(st.session_state.modalita_visualizzazione),
            key="radio_sidebar"
        )
    
    # 📅 Visualizzazione incontri giocati
    with st.sidebar.expander("📅 Visualizzazione incontri giocati", expanded=False):
        if st.button("📋 Mostra tutti gli incontri disputati", key="btn_mostra_tutti_incontri", use_container_width=True):
            st.session_state["mostra_incontri_disputati"] = True
            st.rerun()

    st.sidebar.markdown("---")

    # ✅ 4. 📤 Esportazione (in fondo)
    st.sidebar.subheader("📤 Esportazione")
    if st.sidebar.button("📄 Prepara PDF", key="prepare_pdf", use_container_width=True):
        with st.spinner("Generazione PDF in corso..."):
            pdf_bytes = esporta_pdf(st.session_state.df_torneo, st.session_state.nome_torneo)
            if pdf_bytes:
                st.sidebar.success("✅ PDF pronto per il download!")
                st.sidebar.download_button(
                    label="📥 Scarica PDF Torneo",
                    data=pdf_bytes,
                    file_name=f"{st.session_state.nome_torneo}.pdf".replace(" ", "_"),
                    mime="application/octet-stream",
                    use_container_width=True
                )
            else:
                st.sidebar.error("❌ Errore durante la generazione del PDF")
else:
    st.sidebar.info("ℹ️ Nessun torneo attivo. Avvia un torneo per generare il PDF.")

# -------------------------
# Interfaccia Utente Torneo
# -------------------------
if st.session_state.torneo_iniziato and not st.session_state.torneo_finito:
    if st.session_state["mostra_incontri_disputati"]:
        st.markdown("## 🏟️ Tutti gli incontri disputati")
        df_giocati = st.session_state.df_torneo[st.session_state.df_torneo['Validata'] == True]
        
        if not df_giocati.empty:
            # Add some CSS for the table
            st.markdown("""
            <style>
            .compact-table {
                font-size: 0.9em;
                width: auto !important;
                border-collapse: collapse;
            }
            .compact-table th, .compact-table td {
                padding: 2px 6px !important;
                text-align: center !important;
                white-space: nowrap;
                border: none;
            }
            .compact-table th {
                color: #333 !important;
                font-weight: bold;
                border-bottom: 1px solid #ddd;
            }
            .compact-table tr {
                border-bottom: 1px solid #eee;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Generate the HTML table
            table_html = "<table class='compact-table'><thead><tr>"
            headers = ["📅", "🏠", "⚽️", "⚽️", "🛫"]
            for header in headers:
                table_html += f"<th>{header}</th>"
            table_html += "</tr></thead><tbody>"
            
            # Add table rows
            for _, match in df_giocati.iterrows():
                table_html += "<tr>"
                # Column 1: Round with number emoji
                turno_num = match['Turno']
                # Map numbers to emojis
                num_to_emoji = {
                    0: "0️⃣", 1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 
                    4: "4️⃣", 5: "5️⃣", 6: "6️⃣", 
                    7: "7️⃣", 8: "8️⃣", 9: "9️⃣"
                }
                # Get emoji for the turn number, default to 🔵 if not a single digit
                if isinstance(turno_num, (int, float)) and 0 <= turno_num <= 9:
                    turno_emoji = num_to_emoji[int(turno_num)]
                else:
                    turno_emoji = "🔵"  # Default for unknown turn numbers
                table_html += f"<td style='font-weight: bold; text-align: center;'>{turno_emoji}</td>"
                
                # Column 2: Home team
                table_html += f"<td style='text-align: right;'>{match['Casa']}</td>"
                
                # Column 3: Home goals
                gol_casa = match['GolCasa'] if pd.notna(match['GolCasa']) else "-"
                table_html += f"<td style='font-weight: bold; text-align: center;'>{gol_casa}</td>"
                
                # Column 4: Away goals
                gol_ospite = match['GolOspite'] if pd.notna(match['GolOspite']) else "-"
                table_html += f"<td style='font-weight: bold; text-align: center;'>{gol_ospite}</td>"
                
                # Column 5: Away team
                table_html += f"<td style='text-align: left;'>{match['Ospite']}</td>"
                
                table_html += "</tr>"
                
            table_html += "</tbody></table>"
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.info("Nessun incontro validato al momento.")
            
        # Pulsante per chiudere la tabella e tornare alla vista classica
        if st.button("🔙 Torna alla vista classica", key="btn_chiudi_incontri", use_container_width=True):
            st.session_state["mostra_incontri_disputati"] = False
            st.rerun()
    else:
        st.markdown(f"### Turno {st.session_state.turno_attivo}")
    
    
    df_turno_corrente = st.session_state.df_torneo[st.session_state.df_torneo['Turno'] == st.session_state.turno_attivo].copy()
    
    if df_turno_corrente.empty:
        st.warning("⚠️ Non ci sono partite in questo turno. Torna indietro per aggiungere giocatori o carica un altro torneo.")
    else:
        # Passa il nuovo parametro alla funzione
        visualizza_incontri_attivi(df_turno_corrente, st.session_state.turno_attivo, st.session_state.modalita_visualizzazione)

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
                # Convert NumPy boolean to Python boolean for the disabled state
                is_disabled = bool(
                    (st.session_state.turno_attivo >= st.session_state.df_torneo['Turno'].max().item() 
                     if not st.session_state.df_torneo.empty else True) or 
                    not verify_write_access()
                )
                if st.button("🔄 Genera Prossimo Turno", 
                            disabled=is_disabled,
                            help="Genera il prossimo turno in base alla classifica attuale" + ("" if verify_write_access() else " (accesso in sola lettura)")):
                    if verify_write_access():
                        genera_prossimo_turno()
                    else:
                        st.error("⛔ Accesso in sola lettura. Non è possibile generare nuovi turni.")
                # Convert NumPy boolean to Python boolean for the disabled state
                is_disabled_next = bool(not verify_write_access())
                if st.button("▶️ Genera prossimo turno", 
                    use_container_width=True, 
                    type="primary",
                    disabled=is_disabled_next,
                    help="Genera il prossimo turno" + ("" if verify_write_access() else " (accesso in sola lettura)")):
                    if verify_write_access():
                        salva_torneo_su_db() # Salva i risultati del turno corrente
                        st.session_state.turno_attivo += 1
                        df_turno_prossimo["Turno"] = st.session_state.turno_attivo
                        st.session_state.df_torneo = pd.concat([st.session_state.df_torneo, df_turno_prossimo], ignore_index=True)
                        st.session_state.risultati_temp = {}
                        init_results_temp_from_df(df_turno_prossimo)
                        st.rerun()
                    else:
                        st.error("⛔ Accesso in sola lettura. Non è possibile generare nuovi turni.")
            else:
                st.info("Non ci sono più accoppiamenti possibili. Il torneo è terminato.")
                st.session_state.torneo_finito = True
                st.rerun()
        else:
            st.warning("⚠️ Per generare il prossimo turno, devi validare tutti i risultati.")

    
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
        #audio_url = "./wearethechamp.mp3"
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
# Footer leggero
st.markdown("---")
st.caption("⚽ Subbuteo Tournament Manager •  Made by Legnaro72")

# Non è necessario il blocco if __name__ == "__main__" in un'app Streamlit