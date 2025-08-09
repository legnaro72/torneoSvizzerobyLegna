import streamlit as st
import pandas as pd
import requests
from io import StringIO

URL_CSV = "https://raw.githubusercontent.com/legnaro72/torneoSvizzerobyLegna/refs/heads/main/giocatoriPierCrew.csv"

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
if "show_new_player_form" not in st.session_state:
    st.session_state.show_new_player_form = False
if "edit_index" not in st.session_state:
    st.session_state.edit_index = None  # tiene traccia del giocatore da modificare

def toggle_new_player_form():
    st.session_state.show_new_player_form = not st.session_state.show_new_player_form
    st.session_state.edit_index = None

def start_edit(index):
    st.session_state.edit_index = index
    st.session_state.show_new_player_form = False

def stop_edit():
    st.session_state.edit_index = None

def delete_player(index):
    df = st.session_state.df_giocatori.copy()
    df = df.drop(index).reset_index(drop=True)
    st.session_state.df_giocatori = df
    # Se si stava modificando quel giocatore, resetta il form
    if st.session_state.edit_index == index:
        stop_edit()

st.button("➕ Aggiungi nuovo giocatore", on_click=toggle_new_player_form)

# Form Aggiungi Nuovo Giocatore
if st.session_state.show_new_player_form:
    with st.form("form_nuovo_giocatore", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        nuovo_giocatore = col1.text_input("Nome Giocatore", placeholder="Nome nuovo giocatore")
        nuova_squadra = col2.text_input("Squadra", placeholder="Squadra")
        nuovo_potenziale = col3.slider("Potenziale", 1, 10, 4)
        submitted = st.form_submit_button("✅ Aggiungi")
        if submitted:
            if nuovo_giocatore.strip() == "":
                st.error("Il nome del giocatore non può essere vuoto!")
            else:
                nuova_riga = {
                    "Giocatore": nuovo_giocatore.strip(),
                    "Squadra": nuova_squadra.strip(),
                    "Potenziale": nuovo_potenziale,
                }
                st.session_state.df_giocatori = pd.concat(
                    [st.session_state.df_giocatori, pd.DataFrame([nuova_riga])],
                    ignore_index=True
                )
                st.success(f"Giocatore '{nuovo_giocatore}' aggiunto!")
                st.session_state.show_new_player_form = False

st.markdown("### Lista giocatori attuali")

df = st.session_state.df_giocatori.copy()

# Mostra tabella con pulsante modifica e cancellazione
for i, row in df.iterrows():
    col_gioc, col_squad, col_pot, col_edit, col_del = st.columns([3,3,2,1,1])
    col_gioc.write(row["Giocatore"])
    col_squad.write(row["Squadra"])
    col_pot.write(row["Potenziale"])
    if col_edit.button("✏️", key=f"edit_{i}"):
        start_edit(i)
    if col_del.button("🗑️", key=f"del_{i}"):
        delete_player(i)
        st.experimental_rerun()  # Per aggiornare subito la lista dopo la cancellazione

# Form modifica giocatore
if st.session_state.edit_index is not None:
    idx = st.session_state.edit_index
    gioc = st.session_state.df_giocatori.at[idx, "Giocatore"]
    squadra = st.session_state.df_giocatori.at[idx, "Squadra"]
    pot = st.session_state.df_giocatori.at[idx, "Potenziale"]

    st.markdown("---")
    st.markdown(f"### Modifica giocatore: {gioc}")

    with st.form("form_modifica_giocatore"):
        col1, col2, col3 = st.columns(3)
        giocatore_mod = col1.text_input("Nome Giocatore", value=gioc)
        squadra_mod = col2.text_input("Squadra", value=squadra)
        potenziale_mod = col3.slider("Potenziale", 1, 10, pot)
        submitted = st.form_submit_button("✅ Salva modifiche")
        if submitted:
            if giocatore_mod.strip() == "":
                st.error("Il nome del giocatore non può essere vuoto!")
            else:
                st.session_state.df_giocatori.at[idx, "Giocatore"] = giocatore_mod.strip()
                st.session_state.df_giocatori.at[idx, "Squadra"] = squadra_mod.strip()
                st.session_state.df_giocatori.at[idx, "Potenziale"] = potenziale_mod
                st.success(f"Giocatore '{giocatore_mod}' aggiornato!")
                stop_edit()

st.divider()

csv = st.session_state.df_giocatori.to_csv(index=False).encode("utf-8")
st.download_button(
    "📥 Scarica CSV aggiornato",
    data=csv,
    file_name="giocatori_superba_modificato.csv",
    mime="text/csv",
)
