import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

st.set_page_config(page_title="⚽ Torneo Subbuteo - Sistema Svizzero", layout="wide")

# --- Funzioni ---
def aggiorna_classifica(df):
    stats = {}
    for _, r in df.iterrows():
        if not r['Validata']:
            continue
        for squadra, gol, gol_avv in [(r['Casa'], r['GolCasa'], r['GolOspite']),
                                     (r['Ospite'], r['GolOspite'], r['GolCasa'])]:
            if squadra not in stats:
                stats[squadra] = {'Punti': 0, 'GF': 0, 'GS': 0, 'DR': 0}
            stats[squadra]['GF'] += gol
            stats[squadra]['GS'] += gol_avv
            stats[squadra]['DR'] = stats[squadra]['GF'] - stats[squadra]['GS']
        if r['GolCasa'] > r['GolOspite']:
            stats[r['Casa']]['Punti'] += 2
        elif r['GolCasa'] < r['GolOspite']:
            stats[r['Ospite']]['Punti'] += 2
        else:
            stats[r['Casa']]['Punti'] += 1
            stats[r['Ospite']]['Punti'] += 1

    if not stats:
        return pd.DataFrame(columns=['Squadra', 'Punti', 'GF', 'GS', 'DR'])
    df_classifica = pd.DataFrame([{'Squadra': squadra, **dati} for squadra, dati in stats.items()])
    df_classifica = df_classifica.sort_values(by=['Punti', 'DR', 'GF'], ascending=False).reset_index(drop=True)
    return df_classifica

def genera_accoppiamenti(classifica, precedenti):
    accoppiamenti = []
    gia_abbinati = set()
    for i, r1 in classifica.iterrows():
        squadra1 = r1['Squadra']
        if squadra1 in gia_abbinati:
            continue
        for j in range(i + 1, len(classifica)):
            squadra2 = classifica.iloc[j]['Squadra']
            if squadra2 in gia_abbinati:
                continue
            if (squadra1, squadra2) not in precedenti and (squadra2, squadra1) not in precedenti:
                accoppiamenti.append((squadra1, squadra2))
                gia_abbinati.add(squadra1)
                gia_abbinati.add(squadra2)
                break
    df = pd.DataFrame([{"Casa": c, "Ospite": o, "GolCasa": 0, "GolOspite": 0, "Validata": False} for c, o in accoppiamenti])
    return df

def carica_csv_robusto_da_file(file_buffer):
    try:
        content = file_buffer.read()
        text = content.decode('latin1')
        df = pd.read_csv(io.StringIO(text))
        return df
    except Exception as e:
        st.warning(f"Errore caricamento CSV da file: {e}")
        return pd.DataFrame()

# --- Stato sessione ---
if "df_torneo" not in st.session_state:
    st.session_state.df_torneo = pd.DataFrame()
if "df_squadre" not in st.session_state:
    st.session_state.df_squadre = pd.DataFrame()
if "turno_attivo" not in st.session_state:
    st.session_state.turno_attivo = 0
if "risultati_temp" not in st.session_state:
    st.session_state.risultati_temp = {}
if "torneo_iniziato" not in st.session_state:
    st.session_state.torneo_iniziato = False

# --- Header ---
st.markdown("<h1 style='text-align: center; color: #2E86C1;'>⚽ Torneo Subbuteo - Sistema Svizzero ⚽</h1>", unsafe_allow_html=True)

# --- Se il torneo non è iniziato mostro setup ---
if not st.session_state.torneo_iniziato:
    scelta = st.radio("Scegli un'opzione:", ["📂 Carica torneo esistente", "✨ Crea nuovo torneo"])

    if scelta == "📂 Carica torneo esistente":
        file = st.file_uploader("Carica file CSV del torneo", type="csv")
        if file:
            st.session_state.df_torneo = carica_csv_robusto_da_file(file)
            if not st.session_state.df_torneo.empty:
                st.session_state.turno_attivo = st.session_state.df_torneo["Turno"].max()
                st.session_state.torneo_iniziato = True
                st.success("✅ Torneo caricato con successo! Continua da dove eri rimasto.")

    elif scelta == "✨ Crea nuovo torneo":
        giocatori = st.text_area("Inserisci i nomi dei giocatori (uno per riga)").splitlines()
        if st.button("✅ Genera primo turno") and len(giocatori) >= 2:
            st.session_state.df_squadre = pd.DataFrame({"Squadra": giocatori})
            classifica_iniziale = pd.DataFrame({
                'Squadra': giocatori,
                'Punti': 0, 'GF': 0, 'GS': 0, 'DR': 0
            })
            nuove_partite = genera_accoppiamenti(classifica_iniziale, set())
            st.session_state.turno_attivo = 1
            nuove_partite["Turno"] = st.session_state.turno_attivo
            st.session_state.df_torneo = nuove_partite
            st.session_state.torneo_iniziato = True
            st.success("🏁 Primo turno generato!")

# --- Se torneo attivo, mostro solo partite, nuovo turno, classifica ---
if st.session_state.torneo_iniziato and not st.session_state.df_torneo.empty:
    st.markdown("## 📅 Partite in corso")
    for turno in sorted(st.session_state.df_torneo['Turno'].unique()):
        st.markdown(f"### 🔹 Turno {turno}")
        df_turno = st.session_state.df_torneo[st.session_state.df_torneo['Turno'] == turno]
        for idx, row in df_turno.iterrows():
            key_gc = f"gc_{row['Turno']}_{row['Casa']}_{row['Ospite']}"
            key_go = f"go_{row['Turno']}_{row['Casa']}_{row['Ospite']}"
            key_val = f"val_{row['Turno']}_{row['Casa']}_{row['Ospite']}"

            col1, col2, col3, col4 = st.columns([2,1,1,1])
            col1.write(f"**{row['Casa']}** vs **{row['Ospite']}**")
            gol_casa = col2.number_input("", 0, 20, value=int(row['GolCasa']), key=key_gc)
            gol_ospite = col3.number_input("", 0, 20, value=int(row['GolOspite']), key=key_go)
            validata = col4.checkbox("✔️", value=bool(row['Validata']), key=key_val)

            st.session_state.df_torneo.at[idx, 'GolCasa'] = gol_casa
            st.session_state.df_torneo.at[idx, 'GolOspite'] = gol_ospite
            st.session_state.df_torneo.at[idx, 'Validata'] = validata

    # Nuovo turno
    if st.button("⚡ Genera turno successivo"):
        partite_validate = st.session_state.df_torneo[st.session_state.df_torneo['Validata']]
        precedenti = set(zip(partite_validate['Casa'], partite_validate['Ospite']))
        classifica_attuale = aggiorna_classifica(st.session_state.df_torneo)
        nuove_partite = genera_accoppiamenti(classifica_attuale, precedenti)
        if nuove_partite.empty:
            st.warning("⚠️ Nessuna nuova partita possibile.")
        else:
            st.session_state.turno_attivo += 1
            nuove_partite["Turno"] = st.session_state.turno_attivo
            st.session_state.df_torneo = pd.concat([st.session_state.df_torneo, nuove_partite], ignore_index=True)
            st.success(f"🎉 Turno {st.session_state.turno_attivo} generato!")

    # Classifica
    st.markdown("## 🏆 Classifica")
    df_classifica = aggiorna_classifica(st.session_state.df_torneo)
    st.dataframe(df_classifica, use_container_width=True)

    # Esportazione
    st.markdown("## 💾 Esporta torneo")
    nome_base = st.text_input("Nome file", value="torneo_subbuteo")
    st.download_button("⬇️ Scarica CSV torneo", 
                       data=st.session_state.df_torneo.to_csv(index=False), 
                       file_name=f"{nome_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", 
                       mime="text/csv")
