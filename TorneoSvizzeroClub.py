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
for key, default in [("df_torneo", pd.DataFrame()), ("df_squadre", pd.DataFrame()),
                     ("turno_attivo", 0), ("risultati_temp", {}), ("nuovo_torneo_step", 1),
                     ("club_scelto", None), ("giocatori_scelti", []), ("squadre_data", []),
                     ("torneo_iniziato", False), ("setup_mode", None),
                     ("nome_torneo", "Torneo Subbuteo - Sistema Svizzero")]:
    if key not in st.session_state:
        st.session_state[key] = default

# -------------------------
# Dati club (URL giocatori)
# -------------------------
url_club = {
    "Superba": "https://raw.githubusercontent.com/legnaro72/torneoSvizzerobyLegna/refs/heads/main/giocatoriSuperba.csv",
    "PierCrew": "https://raw.githubusercontent.com/legnaro72/torneoSvizzerobyLegna/refs/heads/main/giocatoriPierCrew.csv",
}

# -------------------------
# Header
# -------------------------
st.markdown(f"<div style='text-align:center; padding:10px 0'><h1 style='color:#0B5FFF;'>⚽ {st.session_state.nome_torneo}</h1></div>", unsafe_allow_html=True)

# -------------------------
# Scelta azione setup
# -------------------------
if not st.session_state.torneo_iniziato and st.session_state.setup_mode is None:
    st.markdown("### Scegli azione")
    c1, c2 = st.columns([1,1])
    with c1:
        st.markdown("""<div style='background:#f5f8ff; border-radius:8px; padding:18px; text-align:center'>
                       <h2>📂 Carica torneo esistente</h2></div>""", unsafe_allow_html=True)
        if st.button("Carica torneo (CSV)"):
            st.session_state.setup_mode = "carica"
            st.rerun()
    with c2:
        st.markdown("""<div style='background:#fff8e6; border-radius:8px; padding:18px; text-align:center'>
                       <h2>✨ Crea nuovo torneo</h2></div>""", unsafe_allow_html=True)
        if st.button("Nuovo torneo"):
            st.session_state.setup_mode = "nuovo"
            st.session_state.nuovo_torneo_step = 0
            st.session_state.giocatori_scelti = []
            st.rerun()
    st.markdown("---")

# -------------------------
# Carica CSV torneo
# -------------------------
if st.session_state.setup_mode == "carica":
    st.markdown("#### 📥 Carica CSV torneo")
    file = st.file_uploader("Carica file CSV del torneo", type="csv")
    if file:
        df = carica_csv_robusto_da_file(file)
        if not df.empty:
            for col in ['Casa','Ospite','GolCasa','GolOspite','Validata','Turno']:
                if col not in df.columns:
                    df[col] = 0 if 'Gol' in col else (False if col=='Validata' else 1)
            df['GolCasa'] = df['GolCasa'].astype(int)
            df['GolOspite'] = df['GolOspite'].astype(int)
            df['Validata'] = df['Validata'].astype(bool)
            df['Turno'] = df['Turno'].astype(int)
            st.session_state.df_torneo = df.reset_index(drop=True)
            st.session_state.turno_attivo = int(st.session_state.df_torneo['Turno'].max())
            init_results_temp_from_df(st.session_state.df_torneo)
            st.session_state.torneo_iniziato = True
            st.session_state.setup_mode = None
            st.success("✅ Torneo caricato!")
            st.rerun()

# -------------------------
# Nuovo torneo passo-passo
# -------------------------
if st.session_state.setup_mode == "nuovo":
    st.markdown("#### ✨ Crea nuovo torneo — passo per passo")

    if st.session_state.nuovo_torneo_step == 0:
        suffisso = st.text_input("Dai un nome al tuo torneo")
        if st.button("Prossimo passo"):
            st.session_state.nome_torneo = f"Torneo Subbuteo Svizzero - {suffisso.strip()}" if suffisso.strip() else "Torneo Subbuteo - Sistema Svizzero"
            st.session_state.nuovo_torneo_step = 1
            st.rerun()

    elif st.session_state.nuovo_torneo_step == 1:
        club = st.selectbox("Scegli il Club", list(url_club.keys()))
        st.session_state.club_scelto = club
        df_gioc = carica_csv_robusto_da_url(url_club[club])
        num_squadre = st.number_input("Numero partecipanti", min_value=2, max_value=100, value=8)
        st.markdown("### 👥 Seleziona i giocatori")
        giocatori_club = df_gioc["Giocatore"].dropna().astype(str).tolist() if not df_gioc.empty and 'Giocatore' in df_gioc.columns else []
        seleziona_tutti = st.checkbox("Seleziona tutti", key="sel_all")
        giocatori_selezionati_temp = [g for g in giocatori_club if seleziona_tutti]
        for g in giocatori_club:
            if st.checkbox(g, value=(g in giocatori_selezionati_temp), key=f"chk_{g}"):
                if g not in giocatori_selezionati_temp:
                    giocatori_selezionati_temp.append(g)
        mancanti = num_squadre - len(giocatori_selezionati_temp)
        for i in range(mancanti):
            nome = st.text_input(f"Nome mancanti {i+1}", value=f"Ospite{i+1}", key=f"nome_manc_{i}")
            giocatori_selezionati_temp.append(nome)
        if st.button("✅ Conferma giocatori"):
            if len(giocatori_selezionati_temp) < 2:
                st.warning("Servono almeno 2 giocatori.")
            else:
                st.session_state.giocatori_scelti = giocatori_selezionati_temp
                st.session_state.nuovo_torneo_step = 2
                st.rerun()

    elif st.session_state.nuovo_torneo_step == 2:
        st.markdown("### 🏷️ Definisci Squadre e Potenziali")
        squadre_data = []
        df_gioc = carica_csv_robusto_da_url(url_club[st.session_state.club_scelto]) if st.session_state.club_scelto else pd.DataFrame()
        for i, gioc in enumerate(st.session_state.giocatori_scelti):
            if not df_gioc.empty and 'Giocatore' in df_gioc.columns and gioc in df_gioc['Giocatore'].values:
                riga = df_gioc[df_gioc['Giocatore']==gioc].iloc[0]
                squadra_default = riga['Squadra'] if 'Squadra' in riga and pd.notna(riga['Squadra']) else f"Squadra{i+1}"
                pot_def = int(riga['Potenziale']) if 'Potenziale' in riga and pd.notna(riga['Potenziale']) else 4
            else:
                squadra_default = f"Squadra{i+1}"
                pot_def = 4
            nome_gioc = st.text_input(f"Nome giocatore {i+1}", value=gioc, key=f"g_{i}")
            squadra = st.text_input(f"Squadra {i+1}", value=squadra_default, key=f"s_{i}")
            pot = st.slider(f"Potenziale {i+1}", 1, 10, value=pot_def, key=f"p_{i}")
            squadre_data.append({"Giocatore": nome_gioc, "Squadra": squadra, "Potenziale": pot})
        if st.button("✅ Conferma squadre e genera primo turno"):
            df_squadre = pd.DataFrame(squadre_data)
            df_squadre["SquadraGiocatore"] = df_squadre.apply(lambda r: f"{r['Squadra']} ({r['Giocatore']})", axis=1)
            df_squadre = df_squadre.sort_values(by="Potenziale", ascending=False).reset_index(drop=True)
            st.session_state.df_squadre = df_squadre
            classifica_iniziale = pd.DataFrame({'Squadra': df_squadre['SquadraGiocatore'], 'Punti': 0, 'GF':0,'GS':0,'DR':0})
            nuove_partite = genera_accoppiamenti(classifica_iniziale, set())
            st.session_state.turno_attivo = 1
            nuove_partite["Turno"] = st.session_state.turno_attivo
            st.session_state.df_torneo = pd.concat([st.session_state.df_torneo, nuove_partite], ignore_index=True)
            init_results_temp_from_df(nuove_partite)
            st.session_state.torneo_iniziato = True
            st.session_state.setup_mode = None
            st.rerun()

# -------------------------
# Vista torneo attivo
# -------------------------
if st.session_state.torneo_iniziato and not st.session_state.df_torneo.empty:
    st.markdown("## 📅 Partite - Turno in corso")
    turno_corrente = st.session_state.turno_attivo
    st.markdown(f"### 🔷 Turno attivo: {turno_corrente}")
    df_turno = st.session_state.df_torneo[st.session_state.df_torneo['Turno']==turno_corrente].reset_index()
    if df_turno.empty:
        st.info("Nessuna partita generata per il turno attivo.")
    else:
        for _, row in df_turno.iterrows():
            idx = int(row['index']); T = int(row['Turno']); casa=row['Casa']; osp=row['Ospite']
            key_gc, key_go, key_val = f"gc_{T}_{casa}_{osp}", f"go_{T}_{casa}_{osp}", f"val_{T}_{casa}_{osp}"
            st.session_state.risultati_temp.setdefault(key_gc,int(row.get('GolCasa',0)))
            st.session_state.risultati_temp.setdefault(key_go,int(row.get('GolOspite',0)))
            st.session_state.risultati_temp.setdefault(key_val,bool(row.get('Validata',False)))
            c1,c2,c3,c4 = st.columns([3,1,1,0.8])
            with c1: st.markdown(f"**{casa}** vs **{osp}**")
            with c2: gol_casa = st.number_input("", min_value=0, max_value=20, value=st.session_state.risultati_temp[key_gc], key=key_gc)
            with c3: gol_osp = st.number_input("", min_value=0, max_value=20, value=st.session_state.risultati_temp[key_go], key=key_go)
            with c4: validata = st.checkbox("Validata", value=st.session_state.risultati_temp[key_val], key=key_val)
            st.session_state.risultati_temp[key_gc]=gol_casa
            st.session_state.risultati_temp[key_go]=gol_osp
            st.session_state.risultati_temp[key_val]=validata
            st.session_state.df_torneo.at[idx,'GolCasa']=gol_casa
            st.session_state.df_torneo.at[idx,'GolOspite']=gol_osp
            st.session_state.df_torneo.at[idx,'Validata']=validata

    st.markdown("---")
    c_left,c_right = st.columns([1,2])
    with c_left:
        if st.button("⚡ Genera turno successivo"):
            partite_validate = st.session_state.df_torneo[st.session_state.df_torneo['Validata']==True]
            precedenti = set(zip(partite_validate['Casa'],partite_validate['Ospite']))
            classifica_attuale = aggiorna_classifica(st.session_state.df_torneo)
            if classifica_attuale.empty and not st.session_state.df_squadre.empty:
                classifica_attuale = pd.DataFrame({'Squadra': st.session_state.df_squadre['SquadraGiocatore']})
            nuove_partite = genera_accoppiamenti(classifica_attuale, precedenti)
            if nuove_partite.empty:
                st.warning("⚠️ Nessuna nuova partita possibile.")
            else:
                st.session_state.turno_attivo+=1
                nuove_partite["Turno"]=st.session_state.turno_attivo
                for col in ['GolCasa','GolOspite','Validata']:
                    if col not in nuove_partite.columns:
                        nuove_partite[col]=0 if 'Gol' in col else False
                st.session_state.df_torneo=pd.concat([st.session_state.df_torneo, nuove_partite], ignore_index=True)
                init_results_temp_from_df(nuove_partite)
                st.rerun()
    with c_right:
        st.markdown("### 🏆 Classifica attuale")
        df_class = aggiorna_classifica(st.session_state.df_torneo)
        st.dataframe(df_class,use_container_width=True)

    st.markdown("---")
    with st.expander("Mostra tutte le giornate / Turni"):
        df_visual = st.session_state.df_torneo.sort_values(by="Turno").reset_index(drop=True)
        for col in ["Turno","Casa","GolCasa","Ospite","GolOspite","Validata"]:
            if col not in df_visual.columns:
                df_visual[col]=""
        st.dataframe(df_visual[["Turno","Casa","GolCasa","Ospite","
