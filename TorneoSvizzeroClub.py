import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Torneo Subbuteo - Sistema Svizzero", layout="wide")

# --- Funzioni ---
def formatta_nome(squadra, giocatore):
    return f"{squadra} ({giocatore})"

def aggiorna_classifica(df_torneo):
    stats = {}
    for _, r in df_torneo.iterrows():
        if not r['Validata']:
            continue
        for team_col, gol, gol_avv in [('Casa', 'GolCasa', 'GolOspite'), ('Ospite', 'GolOspite', 'GolCasa')]:
            squadra_gioc = r[team_col]
            if squadra_gioc not in stats:
                stats[squadra_gioc] = {'Punti': 0, 'GF': 0, 'GS': 0, 'DR': 0}
            stats[squadra_gioc]['GF'] += r[gol]
            stats[squadra_gioc]['GS'] += r[gol_avv]
            stats[squadra_gioc]['DR'] = stats[squadra_gioc]['GF'] - stats[squadra_gioc]['GS']

        if r['GolCasa'] > r['GolOspite']:
            stats[r['Casa']]['Punti'] += 2
        elif r['GolCasa'] < r['GolOspite']:
            stats[r['Ospite']]['Punti'] += 2
        else:
            stats[r['Casa']]['Punti'] += 1
            stats[r['Ospite']]['Punti'] += 1

    if not stats:
        df_classifica = pd.DataFrame(columns=['Squadra', 'Punti', 'GF', 'GS', 'DR'])
    else:
        df_classifica = pd.DataFrame([
            {'Squadra': squadra, **dati} for squadra, dati in stats.items()
        ])
        df_classifica = df_classifica.sort_values(by=['Punti', 'DR', 'GF'], ascending=False).reset_index(drop=True)
    return df_classifica

def genera_accoppiamenti(classifica, precedenti):
    accoppiamenti = []
    già_abbinati = set()
    for i, r1 in classifica.iterrows():
        squadra1 = r1['Squadra']
        if squadra1 in già_abbinati:
            continue
        for j in range(i + 1, len(classifica)):
            squadra2 = classifica.iloc[j]['Squadra']
            if squadra2 in già_abbinati:
                continue
            if (squadra1, squadra2) not in precedenti and (squadra2, squadra1) not in precedenti:
                accoppiamenti.append((squadra1, squadra2))
                già_abbinati.add(squadra1)
                già_abbinati.add(squadra2)
                break
    df = pd.DataFrame([{"Casa": c, "Ospite": o, "GolCasa": 0, "GolOspite": 0, "Validata": False} for c, o in accoppiamenti])
    return df

def genera_nome_ospite_esistente(lista_squadre, prefisso="Ospite"):
    idx = 1
    while True:
        nome_ospite = f"{prefisso}{idx}"
        squadra_ospite = f"Squadra{nome_ospite}"
        full_name = formatta_nome(squadra_ospite, nome_ospite)
        if full_name not in lista_squadre:
            return nome_ospite, squadra_ospite
        idx += 1

# --- Stato sessione ---
if "df_torneo" not in st.session_state:
    st.session_state.df_torneo = pd.DataFrame()
if "df_squadre" not in st.session_state:
    st.session_state.df_squadre = pd.DataFrame()
if "turno_attivo" not in st.session_state:
    st.session_state.turno_attivo = 0
if "risultati_temp" not in st.session_state:
    st.session_state.risultati_temp = {}
if "url_giocatori" not in st.session_state:
    st.session_state.url_giocatori = "https://raw.githubusercontent.com/legnaro72/torneoSvizzerobyLegna/refs/heads/main/giocatoriSuperba.csv"

# --- Interfaccia ---
st.title("🏆 Torneo Subbuteo - Sistema Svizzero")
scelta = st.radio("Scegli:", ["📂 Carica torneo esistente", "🆕 Crea nuovo torneo"])

if scelta == "📂 Carica torneo esistente":
    file = st.file_uploader("Carica file CSV del torneo", type="csv")
    if file:
        df_caricato = pd.read_csv(file)
        st.session_state.df_torneo = df_caricato
        st.success("✅ Torneo caricato!")

else:
    club = st.selectbox("Scegli Club per la lista giocatori:", ["Superba", "PierCrew"])
    if club == "Superba":
        st.session_state.url_giocatori = "https://raw.githubusercontent.com/legnaro72/torneoSvizzerobyLegna/refs/heads/main/giocatoriSuperba.csv"
    else:
        st.session_state.url_giocatori = "https://raw.githubusercontent.com/legnaro72/torneoSvizzerobyLegna/refs/heads/main/giocatoriPierCrew.csv"

    try:
        df_giocatori_csv = pd.read_csv(st.session_state.url_giocatori)
        lista_giocatori_csv = df_giocatori_csv["Giocatore"].dropna().unique().tolist()
    except Exception as e:
        st.warning(f"Impossibile caricare lista giocatori da GitHub: {e}")
        df_giocatori_csv = pd.DataFrame(columns=["Giocatore", "Squadra", "Potenziale"])
        lista_giocatori_csv = []

    num_squadre = st.number_input("Numero squadre", min_value=2, max_value=100, step=1)
    col1, col2, col3 = st.columns([3, 3, 2])  # colonne più larghe per mobile
    squadre_input = []

    with st.form("form_squadre"):
        squadre_giocatori_usati = set()

        for i in range(int(num_squadre)):
            giocatore_scelto = col2.selectbox(
                f"Giocatore {i+1}",
                options=["(Nuovo giocatore)"] + lista_giocatori_csv,
                key=f"giocatore_sel_{i}"
            )

            if giocatore_scelto == "(Nuovo giocatore)":
                nome_ospite, squadra_ospite = genera_nome_ospite_esistente(squadre_giocatori_usati)
                giocatore = col2.text_input(f"Nome nuovo giocatore {i+1}", value=nome_ospite, key=f"giocatore_{i}")
                squadra = col1.text_input(f"Squadra {i+1}", value=squadra_ospite, key=f"squadra_{i}")
                potenziale = col3.slider(f"Potenziale {i+1}", 1, 10, 4, key=f"potenziale_{i}")
            else:
                giocatore = giocatore_scelto
                riga = df_giocatori_csv[df_giocatori_csv["Giocatore"] == giocatore]
                if not riga.empty:
                    squadra_predefinita = riga["Squadra"].values[0] if pd.notna(riga["Squadra"].values[0]) else ""
                    potenziale_default = int(riga["Potenziale"].values[0]) if pd.notna(riga["Potenziale"].values[0]) else 5
                else:
                    squadra_predefinita = ""
                    potenziale_default = 5
                squadra = col1.text_input(f"Squadra {i+1}", value=squadra_predefinita, key=f"squadra_{i}")
                potenziale = col3.slider(f"Potenziale {i+1}", 1, 10, potenziale_default, key=f"potenziale_{i}")

            nome_completo = formatta_nome(squadra, giocatore)
            squadre_giocatori_usati.add(nome_completo)
            squadre_input.append((squadra, giocatore, potenziale))

        submitted = st.form_submit_button("✅ Conferma squadre e genera primo turno")

    if submitted:
        df_squadre = pd.DataFrame(squadre_input, columns=["Squadra", "Giocatore", "Potenziale"])
        df_squadre["SquadraGiocatore"] = df_squadre.apply(lambda r: formatta_nome(r["Squadra"], r["Giocatore"]), axis=1)
        df_squadre = df_squadre.sort_values(by="Potenziale", ascending=False).reset_index(drop=True)
        st.session_state.df_squadre = df_squadre

        st.session_state.turno_attivo = 1
        classifica_iniziale = pd.DataFrame({'Squadra': df_squadre['SquadraGiocatore'], 'Punti': 0, 'GF': 0, 'GS': 0, 'DR': 0})
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

# --- Nuovo turno ---
st.subheader("🔁 Genera turno successivo")
if st.button("➕ Nuovo turno"):
    partite_validate = st.session_state.df_torneo[st.session_state.df_torneo['Validata']]
    precedenti = set(zip(partite_validate['Casa'], st.session_state.df_torneo['Ospite']))
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
        st.success(f"Turno {st.session_state.turno_attivo} generato!")

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

                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                col1.markdown(f"**{row['Casa']}**  vs  **{row['Ospite']}**")
                gol_casa = col2.number_input("Gol casa", 0, 20, value=st.session_state.risultati_temp[key_gc], key=key_gc)
                gol_ospite = col3.number_input("Gol ospite", 0, 20, value=st.session_state.risultati_temp[key_go], key=key_go)
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
    st.subheader("📊 Classifica")
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
st.subheader("📥 Esporta CSV")
nome_base = st.text_input("Nome torneo per salvataggio", value="torneo_subbuteo")
if st.button("📤 Scarica CSV torneo"):
    csv_data = st.session_state.df_torneo.to_csv(index=False)
    nome_file = f"{nome_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    st.download_button(label="📥 Scarica torneo", data=csv_data, file_name=nome_file, mime="text/csv")
if st.button("📤 Scarica classifica"):
    csv_classifica = df_classifica.to_csv(index=False)
    nome_file_classifica = f"{nome_base}_classifica_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    st.download_button(label="📥 Scarica classifica", data=csv_classifica, file_name=nome_file_classifica, mime="text/csv")
