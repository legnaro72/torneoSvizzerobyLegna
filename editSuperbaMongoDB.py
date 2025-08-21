import streamlit as st
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

# Passo 3.1: Connessione a MongoDB
# La stringa di connessione è una variabile segreta in Streamlit Cloud
# Per un test locale, puoi inserirla direttamente qui:
#MONGO_URI = "mongodb+srv://massimilianoferrando:Legnaro21!$@cluster0.t3750lc.mongodb.net/?retryWrites=true&w=majority"

MONGO_URI = st.secrets["MONGO_URI"]


# Crea una connessione al client
try:
    client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
    # Invia un ping al server per confermare la connessione
    client.admin.command('ping')
    st.sidebar.success("✅ Connessione a MongoDB riuscita!")
except Exception as e:
    st.sidebar.error(f"❌ Errore di connessione a MongoDB: {e}")
    st.stop() # Interrompe l'app se la connessione fallisce

# Seleziona il database e la collezione
db = client["giocatori_subbuteo"]
collection = db["superba_players"]

def carica_dati_da_mongo():
    """Carica tutti i giocatori dalla collezione MongoDB e li ordina alfabeticamente."""
    data = list(collection.find())
    if data:
        df = pd.DataFrame(data)
        # Rimuovi la colonna _id che viene aggiunta automaticamente da Mongo
        df = df.drop(columns=["_id"], errors="ignore")
        # Ordina i giocatori in base al nome
        df = df.sort_values(by="Giocatore").reset_index(drop=True)
        return df[["Giocatore", "Squadra", "Potenziale"]]
    return pd.DataFrame(columns=["Giocatore", "Squadra", "Potenziale"])

def salva_dati_su_mongo(df):
    """Sostituisce tutti i dati nella collezione con il dataframe corrente."""
    # Prima svuota la collezione
    collection.delete_many({})
    # Poi inserisci i nuovi dati
    collection.insert_many(df.to_dict('records'))

st.set_page_config(page_title="Gestione Giocatori Superba", layout="wide")
st.title("🎲 Gestione Giocatori Superba")

# Inizializza il dataframe nel session state caricando i dati da Mongo
if "df_giocatori" not in st.session_state:
    st.session_state.df_giocatori = carica_dati_da_mongo()
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
            
        # Ordina il dataframe dopo ogni salvataggio
        st.session_state.df_giocatori = st.session_state.df_giocatori.sort_values(by="Giocatore").reset_index(drop=True)
        
        # CHIAMATA AL DATABASE PER SALVARE
        salva_dati_su_mongo(st.session_state.df_giocatori)
        
        st.session_state.edit_index = None
        st.rerun()

def modify_player(idx):
    st.session_state.edit_index = idx

def delete_player(idx, selected_player):
    st.session_state.df_giocatori = st.session_state.df_giocatori.drop(idx).reset_index(drop=True)
    st.success(f"Giocatore '{selected_player}' eliminato!")
    
    # Ordina il dataframe dopo ogni eliminazione
    st.session_state.df_giocatori = st.session_state.df_giocatori.sort_values(by="Giocatore").reset_index(drop=True)
    
    # CHIAMATA AL DATABASE PER SALVARE
    salva_dati_su_mongo(st.session_state.df_giocatori)
    
    st.rerun()

# Logica di visualizzazione basata sullo stato
if st.session_state.edit_index is None:
    st.subheader("Lista giocatori")
    df = st.session_state.df_giocatori.copy()
    st.dataframe(df, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.button("➕ Aggiungi nuovo giocatore", on_click=add_player)
    with col2:
        if not df.empty:
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
        "📥 Scarica CSV aggiornato",
        data=csv,
        file_name="giocatori_superba_modificato.csv",
        mime="text/csv",
    )

else:
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
