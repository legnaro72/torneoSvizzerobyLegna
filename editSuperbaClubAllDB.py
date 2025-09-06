import streamlit as st
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# Dati di connessione a MongoDB forniti dall'utente
MONGO_URI_PLAYERS = "mongodb+srv://massimilianoferrando:Legnaro21!$@cluster0.t3750lc.mongodb.net/?retryWrites=true&w=majority"
MONGO_URI_TOURNEMENTS = "mongodb+srv://massimilianoferrando:Legnaro21!$@cluster0.t3750lc.mongodb.net/?retryWrites=true&w=majority"
MONGO_URI_TOURNEMENTS_CH = "mongodb+srv://massimilianoferrando:Legnaro21!$@cluster0.t3750lc.mongodb.net/?retryWrites=true&w=majority"

# Crea tre connessioni separate come richiesto
try:
    client_players = MongoClient(MONGO_URI_PLAYERS, server_api=ServerApi('1'))
    client_italiana = MongoClient(MONGO_URI_TOURNEMENTS, server_api=ServerApi('1'))
    client_svizzera = MongoClient(MONGO_URI_TOURNEMENTS_CH, server_api=ServerApi('1'))
    
    # Invia un ping a ciascun client per confermare le connessioni
    client_players.admin.command('ping')
    client_italiana.admin.command('ping')
    client_svizzera.admin.command('ping')
    st.sidebar.success("✅ Connessioni a MongoDB riuscite!")
except Exception as e:
    st.sidebar.error(f"❌ Errore di connessione a MongoDB: {e}")
    st.stop() # Interrompe l'app se la connessione fallisce

# --- Sezione per la gestione dei giocatori ---
db_players = client_players["giocatori_subbuteo"]
collection_players = db_players["superba_players"]

def carica_dati_da_mongo():
    data = list(collection_players.find())
    if data:
        df = pd.DataFrame(data)
        df = df.drop(columns=["_id"], errors="ignore")
        if "Giocatore" in df.columns:
            return df.sort_values(by="Giocatore").reset_index(drop=True)
    return pd.DataFrame(columns=["Giocatore", "Squadra", "Potenziale"])

def salva_dati_su_mongo(df):
    collection_players.delete_many({})
    collection_players.insert_many(df.to_dict('records'))

# --- Sezione per la gestione dei tornei ---
def carica_tornei_all_italiana():
    """Carica solo i nomi dei tornei all'italiana dalla collezione Superba."""
    db_tornei = client_italiana["TorneiSubbuteo"]
    collection_tornei = db_tornei["Superba"]
    data = list(collection_tornei.find({}, {"nome_torneo": 1}))
    if data:
        df = pd.DataFrame(data)
        df = df.drop(columns=["_id"], errors="ignore")
        if "nome_torneo" in df.columns:
            df.rename(columns={"nome_torneo": "Torneo"}, inplace=True)
            return df.sort_values(by="Torneo").reset_index(drop=True)
    return pd.DataFrame(columns=["Torneo"])

def salva_tornei_all_italiana(df):
    db_tornei = client_italiana["TorneiSubbuteo"]
    collection_tornei = db_tornei["Superba"]
    collection_tornei.delete_many({})
    collection_tornei.insert_many(df.to_dict('records'))
    st.toast("Dati dei tornei all'italiana salvati con successo!")

def carica_tornei_svizzeri():
    """Carica solo i nomi dei tornei svizzeri dalla collezione SuperbaSvizzero."""
    db_tornei = client_svizzera["TorneiSubbuteo"]
    collection_tornei = db_tornei["SuperbaSvizzero"]
    data = list(collection_tornei.find({}, {"nome_torneo": 1}))
    if data:
        df = pd.DataFrame(data)
        df = df.drop(columns=["_id"], errors="ignore")
        if "nome_torneo" in df.columns:
            df.rename(columns={"nome_torneo": "Torneo"}, inplace=True)
            return df.sort_values(by="Torneo").reset_index(drop=True)
    return pd.DataFrame(columns=["Torneo"])

def salva_tornei_svizzeri(df):
    db_tornei = client_svizzera["TorneiSubbuteo"]
    collection_tornei = db_tornei["SuperbaSvizzero"]
    collection_tornei.delete_many({})
    collection_tornei.insert_many(df.to_dict('records'))
    st.toast("Dati dei tornei svizzeri salvati con successo!")


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
if "confirm_delete" not in st.session_state:
    st.session_state.confirm_delete = {"type": None, "data": None, "password_required": False}
if "password_check" not in st.session_state:
    st.session_state.password_check = {"show": False, "password": None, "type": None}


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
            st.toast(f"Giocatore '{giocatore}' aggiunto!")
        else:
            idx = st.session_state.edit_index
            st.session_state.df_giocatori.at[idx, "Giocatore"] = giocatore.strip()
            st.session_state.df_giocatori.at[idx, "Squadra"] = squadra.strip()
            st.session_state.df_giocatori.at[idx, "Potenziale"] = potenziale
            st.toast(f"Giocatore '{giocatore}' aggiornato!")
            
        st.session_state.df_giocatori = st.session_state.df_giocatori.sort_values(by="Giocatore").reset_index(drop=True)
        salva_dati_su_mongo(st.session_state.df_giocatori)
        st.session_state.edit_index = None
        st.rerun()

def modify_player(idx):
    st.session_state.edit_index = idx

def confirm_delete_player(idx, selected_player):
    st.session_state.confirm_delete = {"type": "player", "data": (idx, selected_player), "password_required": True}
    st.rerun()

def confirm_delete_torneo_italiana(selected_tornei):
    st.session_state.confirm_delete = {"type": "tornei_ita", "data": selected_tornei, "password_required": True}
    st.rerun()

def confirm_delete_torneo_svizzero(selected_tornei):
    st.session_state.confirm_delete = {"type": "tornei_svizz", "data": selected_tornei, "password_required": True}
    st.rerun()
    
def confirm_delete_all_tornei_italiana():
    st.session_state.confirm_delete = {"type": "all_ita", "data": None, "password_required": True}
    st.rerun()

def confirm_delete_all_tornei_svizzeri():
    st.session_state.confirm_delete = {"type": "all_svizz", "data": None, "password_required": True}
    st.rerun()

def confirm_delete_all_tornei_all():
    st.session_state.confirm_delete = {"type": "all", "data": None, "password_required": True}
    st.rerun()

def cancel_delete():
    st.session_state.confirm_delete = {"type": None, "data": None, "password_required": False}
    st.session_state.password_check = {"show": False, "password": None, "type": None}
    st.info("Operazione di eliminazione annullata.")
    st.rerun()

def process_deletion_with_password(password, deletion_type, data):
    # Determine password based on deletion type
    if deletion_type in ["player", "tornei_ita", "tornei_svizz"]:
        correct_password = "SuperbaPwd"
    elif deletion_type in ["all_ita", "all_svizz", "all"]:
        correct_password = "Legnaro72"
    else:
        st.error("Tipo di cancellazione non valido.")
        return

    if password == correct_password:
        if deletion_type == "player":
            idx, selected_player = data
            st.session_state.df_giocatori = st.session_state.df_giocatori.drop(idx).reset_index(drop=True)
            salva_dati_su_mongo(st.session_state.df_giocatori)
            st.toast(f"Giocatore '{selected_player}' eliminato!")

        elif deletion_type == "tornei_ita":
            db_tornei = client_italiana["TorneiSubbuteo"]
            collection_tornei = db_tornei["Superba"]
            for torneo in data:
                collection_tornei.delete_one({"nome_torneo": torneo})
                st.session_state.df_tornei_italiana = st.session_state.df_tornei_italiana[st.session_state.df_tornei_italiana["Torneo"] != torneo].reset_index(drop=True)
                st.toast(f"Torneo '{torneo}' eliminato!")

        elif deletion_type == "tornei_svizz":
            db_tornei = client_svizzera["TorneiSubbuteo"]
            collection_tornei = db_tornei["SuperbaSvizzero"]
            for torneo in data:
                collection_tornei.delete_one({"nome_torneo": torneo})
                st.session_state.df_tornei_svizzeri = st.session_state.df_tornei_svizzeri[st.session_state.df_tornei_svizzeri["Torneo"] != torneo].reset_index(drop=True)
                st.toast(f"Torneo '{torneo}' eliminato!")

        elif deletion_type == "all_ita":
            db_tornei = client_italiana["TorneiSubbuteo"]
            collection_tornei = db_tornei["Superba"]
            tornei_da_cancellare = [t["nome_torneo"] for t in collection_tornei.find({}) if "campionato" not in t["nome_torneo"].lower()]
            for torneo in tornei_da_cancellare:
                collection_tornei.delete_one({"nome_torneo": torneo})
            st.session_state.df_tornei_italiana = carica_tornei_all_italiana()
            st.toast("✅ Tutti i tornei all'italiana (esclusi i campionati) sono stati eliminati!")

        elif deletion_type == "all_svizz":
            db_tornei = client_svizzera["TorneiSubbuteo"]
            collection_tornei = db_tornei["SuperbaSvizzero"]
            tornei_da_cancellare = [t["nome_torneo"] for t in collection_tornei.find({}) if "campionato" not in t["nome_torneo"].lower()]
            for torneo in tornei_da_cancellare:
                collection_tornei.delete_one({"nome_torneo": torneo})
            st.session_state.df_tornei_svizzeri = carica_tornei_svizzeri()
            st.toast("✅ Tutti i tornei svizzeri (esclusi i campionati) sono stati eliminati!")

        elif deletion_type == "all":
            # Chiamiamo le funzioni specifiche per applicare il filtro
            db_tornei_ita = client_italiana["TorneiSubbuteo"]
            collection_tornei_ita = db_tornei_ita["Superba"]
            tornei_da_cancellare_ita = [t["nome_torneo"] for t in collection_tornei_ita.find({}) if "campionato" not in t["nome_torneo"].lower()]
            for torneo in tornei_da_cancellare_ita:
                collection_tornei_ita.delete_one({"nome_torneo": torneo})
            
            db_tornei_svizz = client_svizzera["TorneiSubbuteo"]
            collection_tornei_svizz = db_tornei_svizz["SuperbaSvizzero"]
            tornei_da_cancellare_svizz = [t["nome_torneo"] for t in collection_tornei_svizz.find({}) if "campionato" not in t["nome_torneo"].lower()]
            for torneo in tornei_da_cancellare_svizz:
                collection_tornei_svizz.delete_one({"nome_torneo": torneo})
            
            st.session_state.df_tornei_italiana = carica_tornei_all_italiana()
            st.session_state.df_tornei_svizzeri = carica_tornei_svizzeri()
            st.toast("✅ TUTTI i tornei (esclusi i campionati) sono stati eliminati!")

        # Reset state after successful deletion
        st.session_state.confirm_delete = {"type": None, "data": None, "password_required": False}
        st.session_state.password_check = {"show": False, "password": None, "type": None}
        st.rerun()
    else:
        st.error("❌ Password errata. Operazione annullata.")
        st.session_state.password_check["show"] = True # Keep password field open on error

# Logica di visualizzazione basata sullo stato
if st.session_state.edit_index is None and st.session_state.confirm_delete["type"] is None:
    st.header("Gestione Giocatori")
    st.subheader("Lista giocatori")
    df = st.session_state.df_giocatori.copy()
    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nessun giocatore trovato. Aggiungine uno per iniziare!")

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
                    st.button("🗑️ Elimina", on_click=confirm_delete_player, args=(idx, selected), key=f"del_{idx}")

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
        st.button("❌ Cancella tutti i tornei all'italiana", on_click=confirm_delete_all_tornei_italiana)
    with col_del_all_svizz:
        st.button("❌ Cancella tutti i tornei svizzeri", on_click=confirm_delete_all_tornei_svizzeri)
    with col_del_all:
        st.button("❌ Cancella TUTTI i tornei", on_click=confirm_delete_all_tornei_all)

    # Sezione per i tornei all'italiana
    st.subheader("Tornei all'italiana")
    df_tornei_italiana = st.session_state.df_tornei_italiana.copy()
    if not df_tornei_italiana.empty:
        st.dataframe(df_tornei_italiana[["Torneo"]], use_container_width=True)
        tornei = df_tornei_italiana["Torneo"].tolist()
        selected_tornei_italiana = st.multiselect("Seleziona tornei all'italiana da eliminare", options=tornei, key="del_italiana_select")
        
        if selected_tornei_italiana:
            st.button("🗑️ Elimina Tornei selezionati", on_click=confirm_delete_torneo_italiana, args=(selected_tornei_italiana,), key="del_italiana_btn")
    else:
        st.info("Nessun torneo all'italiana trovato.")

    # ---
    st.markdown("---")

    # Sezione per i tornei svizzeri
    st.subheader("Tornei svizzeri")
    df_tornei_svizzeri = st.session_state.df_tornei_svizzeri.copy()
    if not df_tornei_svizzeri.empty:
        st.dataframe(df_tornei_svizzeri[["Torneo"]], use_container_width=True)
        tornei_svizzeri = df_tornei_svizzeri["Torneo"].tolist()
        selected_tornei_svizzeri = st.multiselect("Seleziona tornei svizzeri da eliminare", options=tornei_svizzeri, key="del_svizzero_select")
        
        if selected_tornei_svizzeri:
            st.button("🗑️ Elimina Tornei Svizzeri selezionati", on_click=confirm_delete_torneo_svizzero, args=(selected_tornei_svizzeri,), key="del_svizzero_btn")
    else:
        st.info("Nessun torneo svizzero trovato.")


elif st.session_state.edit_index is not None: # Logica di modifica/aggiunta giocatore
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

elif st.session_state.confirm_delete["type"] is not None:
    # Confirmation and password logic for deletions
    deletion_type = st.session_state.confirm_delete["type"]

    if deletion_type == "player":
        _, selected_player = st.session_state.confirm_delete["data"]
        st.warning(f"Sei sicuro di voler eliminare il giocatore '{selected_player}'?")
    elif deletion_type == "tornei_ita":
        st.warning("Sei sicuro di voler eliminare i tornei all'italiana selezionati?")
    elif deletion_type == "tornei_svizz":
        st.warning("Sei sicuro di voler eliminare i tornei svizzeri selezionati?")
    elif deletion_type == "all_ita":
        st.warning("Sei sicuro di voler eliminare TUTTI i tornei all'italiana? I tornei che contengono la parola 'campionato' nel nome non verranno eliminati.")
    elif deletion_type == "all_svizz":
        st.warning("Sei sicuro di voler eliminare TUTTI i tornei svizzeri? I tornei che contengono la parola 'campionato' nel nome non verranno eliminati.")
    elif deletion_type == "all":
        st.warning("Sei sicuro di voler eliminare TUTTI i tornei? I tornei che contengono la parola 'campionato' nel nome non verranno eliminati.")

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Conferma e procedi"):
            st.session_state.password_check["show"] = True
            st.session_state.password_check["type"] = deletion_type
    with col_cancel:
        st.button("❌ Annulla", on_click=cancel_delete)
    
    if st.session_state.password_check["show"]:
        password = st.text_input("Inserisci la password per confermare", type="password")
        if st.button("Conferma Password"):
            process_deletion_with_password(password, st.session_state.password_check["type"], st.session_state.confirm_delete["data"])

# Footer leggero
st.markdown("---")
st.caption("⚽ Subbuteo Tournament Manager •  Made by Legnaro72")
