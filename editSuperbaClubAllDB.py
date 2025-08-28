import streamlit as st
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# Connessione a MongoDB
try:
    # La stringa di connessione è una variabile segreta in Streamlit Cloud
    MONGO_URI = st.secrets["MONGO_URI"]
    client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
    client.admin.command('ping')
    st.sidebar.success("✅ Connessione a MongoDB riuscita!")
except Exception as e:
    st.sidebar.error(f"❌ Errore di connessione a MongoDB: {e}")
    st.stop() # Interrompe l'app se la connessione fallisce

# --- Sezione per la gestione dei giocatori ---
db = client["giocatori_subbuteo"]
collection = db["superba_players"]

def carica_dati_da_mongo():
    data = list(collection.find())
    if data:
        df = pd.DataFrame(data)
        df = df.drop(columns=["_id"], errors="ignore")
        if "Giocatore" in df.columns:
            return df.sort_values(by="Giocatore").reset_index(drop=True)
    return pd.DataFrame(columns=["Giocatore", "Squadra", "Potenziale"])

def salva_dati_su_mongo(df):
    collection.delete_many({})
    collection.insert_many(df.to_dict('records'))

# --- Sezione per la gestione dei tornei ---
def carica_tornei_all_italiana():
    """Carica solo i nomi dei tornei all'italiana dalla collezione Superba."""
    db_tornei = client["TorneiSubbuteo"]
    collection_tornei = db_tornei["Superba"]
    # Richiede solo il campo 'Torneo' per una visualizzazione semplificata
    data = list(collection_tornei.find({}, {"Torneo": 1}))
    if data:
        df = pd.DataFrame(data)
        df = df.drop(columns=["_id"], errors="ignore")
        # Controlla se la colonna esiste prima di ordinarla
        if "Torneo" in df.columns:
            return df.sort_values(by="Torneo").reset_index(drop=True)
    return pd.DataFrame(columns=["Torneo"])

def salva_tornei_all_italiana(df):
    db_tornei = client["TorneiSubbuteo"]
    collection_tornei = db_tornei["Superba"]
    collection_tornei.delete_many({})
    collection_tornei.insert_many(df.to_dict('records'))
    st.success("Dati dei tornei all'italiana salvati con successo!")

def carica_tornei_svizzeri():
    """Carica solo i nomi dei tornei svizzeri dalla collezione SuperbaSvizzero."""
    db_tornei = client["TorneiSubbuteo"]
    collection_tornei = db_tornei["SuperbaSvizzero"]
    # Richiede solo il campo 'Torneo' per una visualizzazione semplificata
    data = list(collection_tornei.find({}, {"Torneo": 1}))
    if data:
        df = pd.DataFrame(data)
        df = df.drop(columns=["_id"], errors="ignore")
        # Controlla se la colonna esiste prima di ordinarla
        if "Torneo" in df.columns:
            return df.sort_values(by="Torneo").reset_index(drop=True)
    return pd.DataFrame(columns=["Torneo"])

def salva_tornei_svizzeri(df):
    db_tornei = client["TorneiSubbuteo"]
    collection_tornei = db_tornei["SuperbaSvizzero"]
    collection_tornei.delete_many({})
    collection_tornei.insert_many(df.to_dict('records'))
    st.success("Dati dei tornei svizzeri salvati con successo!")


st.set_page_config(page_title="Gestione Superba All-in-one", layout="wide")
st.title("🎲 Gestione del Club e dei Tornei")

# Inizializza i dataframe nel session state
if "df_giocatori" not in st.session_state:
    st.session_state.df_giocatori = carica_dati_da_mongo()
if "df_tornei_italiana" not in st.session_state:
    st.session_state.df_tornei_italiana = carica_tornei_all_italiana()
if "df_tornei_svizzeri" not in st.session_state:
    st.session_state.df_tornei_svizzeri = carica_tornei_svizzeri()
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None

# Funzioni per la logica dell'app
def add_player():
    st.session_state.edit_index = -1

def save_player(giocatore, squadra, potenziale):
    if giocatore.strip() == "":
        st.error("Il nome del giocatore non può essere vuoto!")
    else:
        if st.session_state.edit_index == -1:
            nuova_riga = {"Giocatore": giocatore.strip(), "Squadra": squadra.strip(), "Potenziale": potenziale}
            st.session_state.df_giocatori = pd.concat([st.session_state.df_giocatori, pd.DataFrame([nuova_riga])], ignore_index=True)
            st.success(f"Giocatore '{giocatore}' aggiunto!")
        else:
            idx = st.session_state.edit_index
            st.session_state.df_giocatori.at[idx, "Giocatore"] = giocatore.strip()
            st.session_state.df_giocatori.at[idx, "Squadra"] = squadra.strip()
            st.session_state.df_giocatori.at[idx, "Potenziale"] = potenziale
            st.success(f"Giocatore '{giocatore}' aggiornato!")
            
        st.session_state.df_giocatori = st.session_state.df_giocatori.sort_values(by="Giocatore").reset_index(drop=True)
        salva_dati_su_mongo(st.session_state.df_giocatori)
        st.session_state.edit_index = None
        st.rerun()

def modify_player(idx):
    st.session_state.edit_index = idx

def delete_player(idx, selected_player):
    st.session_state.df_giocatori = st.session_state.df_giocatori.drop(idx).reset_index(drop=True)
    st.success(f"Giocatore '{selected_player}' eliminato!")
    st.session_state.df_giocatori = st.session_state.df_giocatori.sort_values(by="Giocatore").reset_index(drop=True)
    salva_dati_su_mongo(st.session_state.df_giocatori)
    st.rerun()

# Funzioni di eliminazione per i tornei
def delete_torneo_italiana(idx, selected_torneo):
    st.session_state.df_tornei_italiana = st.session_state.df_tornei_italiana.drop(idx).reset_index(drop=True)
    st.success(f"Torneo '{selected_torneo}' eliminato!")
    salva_tornei_all_italiana(st.session_state.df_tornei_italiana)
    st.rerun()

def delete_torneo_svizzero(idx, selected_torneo):
    st.session_state.df_tornei_svizzeri = st.session_state.df_tornei_svizzeri.drop(idx).reset_index(drop=True)
    st.success(f"Torneo '{selected_torneo}' eliminato!")
    salva_tornei_svizzeri(st.session_state.df_tornei_svizzeri)
    st.rerun()
    
# Nuove funzioni per la cancellazione totale
def delete_all_tornei_italiana():
    db_tornei = client["TorneiSubbuteo"]
    collection_tornei = db_tornei["Superba"]
    collection_tornei.delete_many({})
    st.session_state.df_tornei_italiana = carica_tornei_all_italiana() # Ricarica il dataframe vuoto
    st.success("✅ Tutti i tornei all'italiana sono stati eliminati!")
    st.rerun()

def delete_all_tornei_svizzeri():
    db_tornei = client["TorneiSubbuteo"]
    collection_tornei = db_tornei["SuperbaSvizzero"]
    collection_tornei.delete_many({})
    st.session_state.df_tornei_svizzeri = carica_tornei_svizzeri() # Ricarica il dataframe vuoto
    st.success("✅ Tutti i tornei svizzeri sono stati eliminati!")
    st.rerun()

def delete_all_tornei_all():
    delete_all_tornei_italiana()
    delete_all_tornei_svizzeri()


# Logica di visualizzazione basata sullo stato
if st.session_state.edit_index is None:
    st.header("Gestione Giocatori")
    st.subheader("Lista giocatori")
    df = st.session_state.df_giocatori.copy()
    st.dataframe(df, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.button("➕ Aggiungi nuovo giocatore", on_click=add_player)
    with col2:
        if not df.empty and "Giocatore" in df.columns:
            giocatori = df["Giocatore"].tolist()
            selected = st.selectbox("Seleziona giocatore per Modifica o Elimina", options=[""] + giocatori)

            if selected:
                idx = df.index[df["Giocatore"] == selected][0]
                mod_col, del_col = st.columns(2)
                with mod_col:
                    st.button("✏️ Modifica", on_click=modify_player, args=(idx,), key=f"mod_{idx}")
                with del_col:
                    st.button("🗑️ Elimina", on_click=delete_player, args=(idx, selected), key=f"del_{idx}")

    csv = st.session_state.df_giocatori.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Scarica CSV giocatori aggiornato",
        data=csv,
        file_name="giocatori_superba_modificato.csv",
        mime="text/csv",
    )

    # ---
    st.markdown("---")
    st.header("Gestione Tornei")

    col_del_all_ita, col_del_all_svizz, col_del_all = st.columns(3)
    with col_del_all_ita:
        st.button("❌ Cancella tutti i tornei all'italiana", on_click=delete_all_tornei_italiana)
    with col_del_all_svizz:
        st.button("❌ Cancella tutti i tornei svizzeri", on_click=delete_all_tornei_svizzeri)
    with col_del_all:
        st.button("❌ Cancella TUTTI i tornei", on_click=delete_all_tornei_all)

    # Sezione per i tornei all'italiana
    st.subheader("Tornei all'italiana")
    df_tornei_italiana = st.session_state.df_tornei_italiana.copy()
    if not df_tornei_italiana.empty:
        st.dataframe(df_tornei_italiana, use_container_width=True)
        tornei = df_tornei_italiana["Torneo"].tolist()
        selected_torneo_italiana = st.selectbox("Seleziona torneo all'italiana da eliminare", options=[""] + tornei, key="del_italiana_select")
        
        if selected_torneo_italiana:
            idx_italiana = df_tornei_italiana.index[df_tornei_italiana["Torneo"] == selected_torneo_italiana][0]
            st.button("🗑️ Elimina Torneo selezionato", on_click=delete_torneo_italiana, args=(idx_italiana, selected_torneo_italiana), key="del_italiana_btn")
    else:
        st.info("Nessun torneo all'italiana trovato.")

    # ---
    st.markdown("---")

    # Sezione per i tornei svizzeri
    st.subheader("Tornei svizzeri")
    df_tornei_svizzeri = st.session_state.df_tornei_svizzeri.copy()
    if not df_tornei_svizzeri.empty:
        st.dataframe(df_tornei_svizzeri, use_container_width=True)
        tornei_svizzeri = df_tornei_svizzeri["Torneo"].tolist()
        selected_torneo_svizzero = st.selectbox("Seleziona torneo svizzero da eliminare", options=[""] + tornei_svizzeri, key="del_svizzero_select")
        
        if selected_torneo_svizzero:
            idx_svizzero = df_tornei_svizzeri.index[df_tornei_svizzeri["Torneo"] == selected_torneo_svizzero][0]
            st.button("🗑️ Elimina Torneo Svizzero selezionato", on_click=delete_torneo_svizzero, args=(idx_svizzero, selected_torneo_svizzero), key="del_svizzero_btn")
    else:
        st.info("Nessun torneo svizzero trovato.")


else: # Logica di modifica/aggiunta giocatore
    st.header("Gestione Giocatori")
    if st.session_state.edit_index == -1:
        st.subheader("➕ Nuovo giocatore")
        default_giocatore = ""
        default_squadra = ""
        default_potenziale = 4
    else:
        st.subheader("✏️ Modifica giocatore")
        idx = st.session_state.edit_index
        default_giocatore = st.session_state.df_giocatori.at[idx, "Giocatore"]
        default_squadra = st.session_state.df_giocatori.at[idx, "Squadra"]
        default_potenziale = st.session_state.df_giocatori.at[idx, "Potenziale"]

    giocatore = st.text_input("Nome Giocatore", value=default_giocatore, key="giocatore_input")
    squadra = st.text_input("Squadra", value=default_squadra, key="squadra_input")
    potenziale = st.slider("Potenziale", 1, 10, default_potenziale, key="potenziale_input")

    col_save, col_cancel = st.columns(2)
    with col_save:
        if st.button("✅ Salva"):
            save_player(giocatore, squadra, potenziale)
    with col_cancel:
        if st.button("❌ Annulla"):
            st.session_state.edit_index = None
            st.rerun()
