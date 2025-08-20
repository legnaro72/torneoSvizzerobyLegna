import streamlit as st
import pandas as pd
import requests
from io import StringIO

URL_CSV = "https://drive.google.com/file/d/1d9HJVNhbE4QCLjYDsFjp5hUJhs9d5IjQ/view?usp=sharing"

st.set_page_config(page_title="Gestione Giocatori PierCrew", layout="wide")
st.title("🎲 Gestione Giocatori PierCrew")

def carica_csv_da_url(url):
    try:
        r = requests.get(url)
        r.raise_for_status()
        df = pd.read_csv(StringIO(r.text))
        for col in ["Giocatore", "Squadra", "Potenziale"]:
            if col not in df.columns:
                df[col] = ""
        df["Potenziale"] = pd.to_numeric(df["Potenziale"], errors='coerce').fillna(4).astype(int)
        return df[["Giocatore", "Squadra", "Potenziale"]]
    except Exception as e:
        st.warning(f"Non è stato possibile caricare il file CSV dal link: {e}")
        return pd.DataFrame(columns=["Giocatore", "Squadra", "Potenziale"])

if "df_giocatori" not in st.session_state:
    st.session_state.df_giocatori = carica_csv_da_url(URL_CSV)
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None  # tiene traccia del giocatore da modificare

# Pulsante aggiungi nuovo giocatore
if st.button("➕ Aggiungi nuovo giocatore"):
    st.session_state.edit_index = -1  # segnale per form aggiunta

# Form aggiunta/modifica giocatore
if st.session_state.edit_index is not None:
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

    giocatore = st.text_input("Nome Giocatore", value=default_giocatore)
    squadra = st.text_input("Squadra", value=default_squadra)
    potenziale = st.slider("Potenziale", 1, 10, default_potenziale)

    if st.button("✅ Salva"):
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
            st.session_state.edit_index = None

    if st.button("❌ Annulla"):
        st.session_state.edit_index = None

else:
    st.subheader("Lista giocatori")

    df = st.session_state.df_giocatori.copy()
    st.dataframe(df, use_container_width=True)

    giocatori = df["Giocatore"].tolist()
    selected = st.selectbox("Seleziona giocatore per Modifica o Elimina", options=[""] + giocatori)

    if selected:
        idx = df.index[df["Giocatore"] == selected][0]
        col1, col2 = st.columns(2)
        if col1.button("✏️ Modifica", key=f"mod_{idx}"):
            st.session_state.edit_index = idx
        if col2.button("🗑️ Elimina", key=f"del_{idx}"):
            st.session_state.df_giocatori = df.drop(idx).reset_index(drop=True)
            st.success(f"Giocatore '{selected}' eliminato!")

csv = st.session_state.df_giocatori.to_csv(index=False).encode("utf-8")
st.download_button(
    "📥 Scarica CSV aggiornato",
    data=csv,
    file_name="giocatori_piercrew_modificato.csv",
    mime="text/csv",
)
