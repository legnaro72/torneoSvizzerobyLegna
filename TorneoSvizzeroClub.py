import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io

st.set_page_config(page_title="⚽ Torneo Subbuteo - Sistema Svizzero", layout="wide")

# -------------------------
# Funzioni di utilità
# -------------------------
def aggiorna_classifica(df):
    stats = {}
    for _, r in df.iterrows():
        if not bool(r.get('Validata', False)):
            continue
        for squadra, gol, gol_avv in [(r['Casa'], int(r['GolCasa']), int(r['GolOspite'])),
                                     (r['Ospite'], int(r['GolOspite']), int(r['GolCasa']))]:
            if squadra not in stats:
                stats[squadra] = {'Punti': 0, 'GF': 0, 'GS': 0}
            stats[squadra]['GF'] += gol
            stats[squadra]['GS'] += gol_avv
        # punti (2 vittoria / 1 pareggio)
        if int(r['GolCasa']) > int(r['GolOspite']):
            stats[r['Casa']]['Punti'] += 2
        elif int(r['GolCasa']) < int(r['GolOspite']):
            stats[r['Ospite']]['Punti'] += 2
        else:
            stats[r['Casa']]['Punti'] += 1
            stats[r['Ospite']]['Punti'] += 1

    if not stats:
        return pd.DataFrame(columns=['Squadra', 'Punti', 'GF', 'GS', 'DR'])
    df_class = pd.DataFrame([{'Squadra': s, 'Punti': v['Punti'], 'GF': v['GF'], 'GS': v['GS'],
                              'DR': v['GF'] - v['GS']} for s, v in stats.items()])
    df_class = df_class.sort_values(by=['Punti', 'DR', 'GF'], ascending=False).reset_index(drop=True)
    return df_class

def genera_accoppiamenti(classifica, precedenti):
    # classifica: DataFrame con colonna 'Squadra'
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

def carica_csv_robusto_da_url(url):
    try:
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        text = r.content.decode('latin1')
        return pd.read_csv(io.StringIO(text))
    except Exception as e:
        st.warning(f"Errore caricamento CSV da URL: {e}")
        return pd.DataFrame()

def carica_csv_robusto_da_file(file_buffer):
    try:
        content = file_buffer.read()
        text = content.decode('latin1')
        return pd.read_csv(io.StringIO(text))
    except Exception as e:
        st.warning(f"Errore caricamento CSV da file: {e}")
        return pd.DataFrame()

def init_results_temp_from_df(df):
    # inizializza risultati_temp per ogni riga del df torneo
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
# Inizializzazione session_state
# -------------------------
if "df_torneo" not in st.session_state:
    st.session_state.df_torneo = pd.DataFrame()
if "df_squadre" not in st.session_state:
    st.session_state.df_squadre = pd.DataFrame()
if "turno_attivo" not in st.session_state:
    st.session_state.turno_attivo = 0
if "risultati_temp" not in st.session_state:
    st.session_state.risultati_temp = {}
if "nuovo_torneo_step" not in st.session_state:
    st.session_state.nuovo_torneo_step = 1
if "club_scelto" not in st.session_state:
    st.session_state.club_scelto = None
if "giocatori_scelti" not in st.session_state:
    st.session_state.giocatori_scelti = []
if "squadre_data" not in st.session_state:
    st.session_state.squadre_data = []
if "torneo_iniziato" not in st.session_state:
    st.session_state.torneo_iniziato = False
if "setup_mode" not in st.session_state:
    st.session_state.setup_mode = None  # 'carica' | 'nuovo' | None

# -------------------------
# Dati club (URL giocatori)
# -------------------------
url_club = {
    "Superba": "https://raw.githubusercontent.com/legnaro72/torneoSvizzerobyLegna/refs/heads/main/giocatoriSuperba.csv",
    "PierCrew": "https://raw.githubusercontent.com/legnaro72/torneoSvizzerobyLegna/refs/heads/main/giocatoriPierCrew.csv",
}

# -------------------------
# Header - grande e pulito
# -------------------------
st.markdown("<div style='text-align:center; padding:10px 0'><h1 style='color:#0B5FFF;'>⚽ Torneo Subbuteo - Sistema Svizzero</h1></div>", unsafe_allow_html=True)

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
               <p style='margin:0.2rem 0 1rem 0'>Riprendi un torneo salvato (CSV)</p>
               </div>""",
            unsafe_allow_html=True,
        )
        if st.button("Carica torneo (CSV)", key="btn_carica"):
            st.session_state.setup_mode = "carica"
            st.rerun() # Forza il ricaricamento
    with c2:
        st.markdown(
            """<div style='background:#fff8e6; border-radius:8px; padding:18px; text-align:center'>
               <h2>✨ Crea nuovo torneo</h2>
               <p style='margin:0.2rem 0 1rem 0'>Genera primo turno scegliendo club e giocatori</p>
               </div>""",
            unsafe_allow_html=True,
        )
        if st.button("Nuovo torneo", key="btn_nuovo"):
            st.session_state.setup_mode = "nuovo"
            st.session_state.nuovo_torneo_step = 1
            st.session_state.giocatori_scelti = []
            st.rerun() # Forza il ricaricamento

    st.markdown("---")

# -------------------------
# Logica di caricamento o creazione torneo (fuori dal blocco di scelta)
# -------------------------
# Se scelgo carica
if st.session_state.setup_mode == "carica":
    st.markdown("#### 📥 Carica CSV torneo")
    file = st.file_uploader("Carica file CSV del torneo (es. esportazione dell'app)", type="csv")
    if file:
        df = carica_csv_robusto_da_file(file)
        if not df.empty:
            # validazione colonne minime e normalizzazione
            # assicurati che esistano le colonne attese
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
            # cast appropriati
            df['GolCasa'] = df['GolCasa'].fillna(0).astype(int)
            df['GolOspite'] = df['GolOspite'].fillna(0).astype(int)
            df['Validata'] = df['Validata'].astype(bool)
            if 'Turno' not in df.columns:
                df['Turno'] = 1
            st.session_state.df_torneo = df.reset_index(drop=True)
            st.session_state.turno_attivo = int(st.session_state.df_torneo['Turno'].max())
            init_results_temp_from_df(st.session_state.df_torneo)
            st.session_state.torneo_iniziato = True
            st.session_state.setup_mode = None # Nascondi la sezione di setup dopo il caricamento
            st.success("✅ Torneo caricato! Ora puoi continuare da dove eri rimasto.")
            st.rerun()  # per aggiornare UI e nascondere setup

# Se scelgo nuovo torneo
if st.session_state.setup_mode == "nuovo":
    st.markdown("#### ✨ Crea nuovo torneo — passo per passo")
    # Step 1: scelta club e giocatori
    if st.session_state.nuovo_torneo_step == 1:
        club = st.selectbox("Scegli il Club", list(url_club.keys()), index=0)
        st.session_state.club_scelto = club
        df_gioc = carica_csv_robusto_da_url(url_club[club])
        st.markdown("**Numero partecipanti** (min 2)")
        num_squadre = st.number_input("Numero partecipanti", min_value=2, max_value=100, value=8, step=1, key="num_partecipanti")
        st.markdown("### 👥 Seleziona i giocatori del club")
        giocatori_club = []
        if not df_gioc.empty and 'Giocatore' in df_gioc.columns:
            giocatori_club = df_gioc["Giocatore"].dropna().astype(str).tolist()

        seleziona_tutti = st.checkbox("Seleziona tutti i giocatori del club", key="sel_all")
        giocatori_selezionati_temp = []

        # mostra elenco giocatori del club come checkbox
        if giocatori_club:
            for g in giocatori_club:
                checked = seleziona_tutti
                if st.checkbox(g, value=checked, key=f"chk_{g}"):
                    giocatori_selezionati_temp.append(g)

        # aggiungi ospiti per riempire il numero
        mancanti = num_squadre - len(giocatori_selezionati_temp)
        if mancanti > 0:
            st.markdown(f"### ➕ Aggiungi nuovi giocatori ({mancanti} slot)")
            for i in range(mancanti):
                col1, col2 = st.columns([0.15, 0.85])
                with col1:
                    aggiungi = st.checkbox(f"Aggiungi slot {i+1}", value=True, key=f"aggiungi_{i}")
                with col2:
                    nome = st.text_input(f"Nome mancanti {i+1}", value=f"Ospite{i+1}", key=f"nome_manc_{i}")
                if aggiungi:
                    giocatori_selezionati_temp.append(nome)

        st.markdown("---")
        if st.button("✅ Conferma giocatori", key="conf_gioc"):
            if len(giocatori_selezionati_temp) < 2:
                st.warning("Servono almeno 2 giocatori.")
            else:
                st.session_state.giocatori_scelti = giocatori_selezionati_temp
                st.session_state.nuovo_torneo_step = 2
                st.success("Giocatori confermati — procedi a definire squadre e potenziali.")
                st.rerun() # Forza il ricaricamento

    # Step 2: conferma squadre e potenziale
    elif st.session_state.nuovo_torneo_step == 2:
        st.markdown("### 🏷️ Definisci Squadre e Potenziali")
        df_gioc = carica_csv_robusto_da_url(st.session_state.club_scelto) if st.session_state.club_scelto else pd.DataFrame()
        squadre_data = []
        for i, gioc in enumerate(st.session_state.giocatori_scelti):
            # precompila nome e squadra dal CSV club se presente
            if not df_gioc.empty and 'Giocatore' in df_gioc.columns and gioc in df_gioc['Giocatore'].values:
                riga = df_gioc[df_gioc['Giocatore'] == gioc].iloc[0]
                squadra_default = riga['Squadra'] if 'Squadra' in riga and pd.notna(riga['Squadra']) else f"Squadra{i+1}"
                try:
                    pot_def = int(riga['Potenziale']) if 'Potenziale' in riga and pd.notna(riga['Potenziale']) else 4
                except:
                    pot_def = 4
            else:
                squadra_default = f"Squadra{i+1}"
                pot_def = 4

            nome_gioc = st.text_input(f"Nome giocatore {i+1}", value=gioc, key=f"g_{i}")
            squadra = st.text_input(f"Squadra {i+1}", value=squadra_default, key=f"s_{i}")
            pot = st.slider(f"Potenziale {i+1}", 1, 10, value=pot_def, key=f"p_{i}")
            squadre_data.append({"Giocatore": nome_gioc, "Squadra": squadra, "Potenziale": pot})

        st.markdown("---")
        if st.button("✅ Conferma squadre e genera primo turno", key="gen1"):
            # crea df_squadre organizzato per potenziale
            df_squadre = pd.DataFrame(squadre_data)
            df_squadre["SquadraGiocatore"] = df_squadre.apply(lambda r: f"{r['Squadra']} ({r['Giocatore']})", axis=1)
            df_squadre = df_squadre.sort_values(by="Potenziale", ascending=False).reset_index(drop=True)
            st.session_state.df_squadre = df_squadre

            # classifica iniziale e generazione primo turno
            classifica_iniziale = pd.DataFrame({
                'Squadra': df_squadre['SquadraGiocatore'],
                'Punti': 0, 'GF': 0, 'GS': 0, 'DR': 0
            })
            nuove_partite = genera_accoppiamenti(classifica_iniziale, set())
            st.session_state.turno_attivo = 1
            nuove_partite["Turno"] = st.session_state.turno_attivo
            st.session_state.df_torneo = nuove_partite.reset_index(drop=True)
            init_results_temp_from_df(st.session_state.df_torneo)
            st.session_state.torneo_iniziato = True
            st.session_state.setup_mode = None # Nascondi la sezione di setup dopo la creazione
            st.success("🏁 Primo turno generato! Ora sei nella vista torneo.")
            st.rerun()

# -------------------------
# Vista torneo attivo (solo dopo generazione o caricamento)
# -------------------------
if st.session_state.torneo_iniziato and not st.session_state.df_torneo.empty:
    st.markdown("## 📅 Partite — vista principale (solo torneo in corso)")
    # Mostra partite del turno attivo per default
    turno_corrente = st.session_state.turno_attivo
    st.markdown(f"### 🔷 Turno attivo: {turno_corrente}")

    df_turno = st.session_state.df_torneo[st.session_state.df_torneo['Turno'] == turno_corrente].reset_index()
    if df_turno.empty:
        st.info("Nessuna partita generata per il turno attivo. Premi 'Genera turno successivo' se tutte le partite validate.")
    else:
        for _, row in df_turno.iterrows():
            idx = int(row['index'])
            T = int(row['Turno'])
            casa = row['Casa']
            osp = row['Ospite']
            key_gc = f"gc_{T}_{casa}_{osp}"
            key_go = f"go_{T}_{casa}_{osp}"
            key_val = f"val_{T}_{casa}_{osp}"
            # inizializza se mancanti
            st.session_state.risultati_temp.setdefault(key_gc, int(row.get('GolCasa', 0)))
            st.session_state.risultati_temp.setdefault(key_go, int(row.get('GolOspite', 0)))
            st.session_state.risultati_temp.setdefault(key_val, bool(row.get('Validata', False)))

            c1, c2, c3, c4 = st.columns([3,1,1,0.8])
            with c1:
                st.markdown(f"**{casa}** vs  **{osp}**")
            with c2:
                gol_casa = st.number_input("", min_value=0, max_value=20, value=st.session_state.risultati_temp[key_gc], key=key_gc)
            with c3:
                gol_osp = st.number_input("", min_value=0, max_value=20, value=st.session_state.risultati_temp[key_go], key=key_go)
            with c4:
                validata = st.checkbox("Validata", value=st.session_state.risultati_temp[key_val], key=key_val)
            # persisti in risultati_temp e nel df_torneo
            st.session_state.risultati_temp[key_gc] = int(gol_casa)
            st.session_state.risultati_temp[key_go] = int(gol_osp)
            st.session_state.risultati_temp[key_val] = bool(validata)
            # aggiorna df_torneo (modifica in session_state.df_torneo)
            st.session_state.df_torneo.at[idx, 'GolCasa'] = int(gol_casa)
            st.session_state.df_torneo.at[idx, 'GolOspite'] = int(gol_osp)
            st.session_state.df_torneo.at[idx, 'Validata'] = bool(validata)

    st.markdown("---")
    # Bottone per generare turno successivo
    c_left, c_right = st.columns([1,2])
    with c_left:
        if st.button("⚡ Genera turno successivo"):
            # costruisci set precedenti da partite validate
            partite_validate = st.session_state.df_torneo[st.session_state.df_torneo['Validata'] == True]
            precedenti = set(zip(partite_validate['Casa'], partite_validate['Ospite']))
            classifica_attuale = aggiorna_classifica(st.session_state.df_torneo)
            if classifica_attuale.empty:
                # se classifica vuota e abbiamo df_squadre definito, usalo
                if not st.session_state.df_squadre.empty:
                    classifica_attuale = pd.DataFrame({'Squadra': st.session_state.df_squadre['SquadraGiocatore']})
                else:
                    st.warning("Classifica vuota: assicurati di avere squadre o partite validate.")
                    classifica_attuale = pd.DataFrame({'Squadra': []})
            nuove_partite = genera_accoppiamenti(classifica_attuale, precedenti)
            if nuove_partite.empty:
                st.warning("⚠️ Nessuna nuova partita possibile (controlla partite validate / già giocate).")
            else:
                st.session_state.turno_attivo += 1
                nuove_partite["Turno"] = st.session_state.turno_attivo
                # reset colonne se mancanti
                for col in ['GolCasa','GolOspite','Validata']:
                    if col not in nuove_partite.columns:
                        if col in ['GolCasa','GolOspite']:
                            nuove_partite[col] = 0
                        else:
                            nuove_partite[col] = False
                st.session_state.df_torneo = pd.concat([st.session_state.df_torneo, nuove_partite], ignore_index=True)
                init_results_temp_from_df(nuove_partite)
                st.success(f"🎉 Turno {st.session_state.turno_attivo} generato!")
                st.rerun()
    with c_right:
        st.markdown("### 🏆 Classifica attuale")
        df_class = aggiorna_classifica(st.session_state.df_torneo)
        st.dataframe(df_class, use_container_width=True)

    st.markdown("---")
    # Opzioni aggiuntive: mostra tutte le giornate e esportazione
    with st.expander("Mostra tutte le giornate / Turni"):
        df_visual = st.session_state.df_torneo.copy()
        df_visual = df_visual.sort_values(by="Turno").reset_index(drop=True)
        cols_to_show = ["Turno", "Casa", "GolCasa", "Ospite", "GolOspite", "Validata"]
        for c in cols_to_show:
            if c not in df_visual.columns:
                df_visual[c] = ""
        st.dataframe(df_visual[cols_to_show], use_container_width=True)

    st.markdown("### 💾 Esporta torneo")
    nome_base = st.text_input("Nome file (base)", value="torneo_subbuteo", key="nome_base")
    csv_data = st.session_state.df_torneo.to_csv(index=False).encode('utf-8')
    st.download_button(label="⬇️ Scarica CSV torneo", data=csv_data,
                       file_name=f"{nome_base}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                       mime="text/csv")
