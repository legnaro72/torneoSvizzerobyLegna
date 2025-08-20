import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io
from fpdf import FPDF

st.set_page_config(page_title="⚽ Torneo Subbuteo - Sistema Svizzero", layout="wide")

# -------------------------
# Funzioni di utilità
# -------------------------
def aggiorna_classifica(df):
    stats = {}
    for _, r in df.iterrows():
        if not bool(r.get('Validata', False)):
            continue
        casa, osp = r['Casa'], r['Ospite']
        gc, go = int(r['GolCasa']), int(r['GolOspite'])
        for squadra in [casa, osp]:
            if squadra not in stats:
                stats[squadra] = {'Punti':0,'GF':0,'GS':0,'DR':0,'G':0,'V':0,'N':0,'P':0}
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
        return pd.DataFrame(columns=['Squadra','Punti','G','V','N','P','GF','GS','DR'])
    df_class = pd.DataFrame([{'Squadra':s,'Punti':v['Punti'],'G':v['G'],'V':v['V'],
                              'N':v['N'],'P':v['P'],'GF':v['GF'],'GS':v['GS'],
                              'DR':v['GF']-v['GS']} for s,v in stats.items()])
    return df_class.sort_values(by=['Punti','DR','GF'],ascending=False).reset_index(drop=True)

def genera_accoppiamenti(classifica, precedenti):
    accoppiamenti = []
    gia_abbinati = set()
    for i, r1 in classifica.iterrows():
        s1 = r1['Squadra']
        if s1 in gia_abbinati: continue
        for j in range(i+1,len(classifica)):
            s2 = classifica.iloc[j]['Squadra']
            if s2 in gia_abbinati: continue
            if (s1,s2) not in precedenti and (s2,s1) not in precedenti:
                accoppiamenti.append((s1,s2))
                gia_abbinati.update([s1,s2])
                break
    df = pd.DataFrame([{"Casa":c,"Ospite":o,"GolCasa":0,"GolOspite":0,"Validata":False} for c,o in accoppiamenti])
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
        T = row.get('Turno',1)
        casa, osp = row['Casa'], row['Ospite']
        key_gc = f"gc_{T}_{casa}_{osp}"
        key_go = f"go_{T}_{casa}_{osp}"
        key_val = f"val_{T}_{casa}_{osp}"
        st.session_state.risultati_temp.setdefault(key_gc,int(row.get('GolCasa',0)))
        st.session_state.risultati_temp.setdefault(key_go,int(row.get('GolOspite',0)))
        st.session_state.risultati_temp.setdefault(key_val,bool(row.get('Validata',False)))

def esporta_pdf(df_torneo, nome_torneo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",14)
    titolo = nome_torneo.encode("latin-1","ignore").decode("latin-1")
    pdf.cell(0,10,titolo,ln=True,align="C")
    pdf.set_font("Arial","",11)
    turno_corrente = None
    for _, r in df_torneo.sort_values(by="Turno").iterrows():
        if turno_corrente != r["Turno"]:
            turno_corrente = r["Turno"]
            pdf.ln(5)
            pdf.set_font("Arial","B",12)
            pdf.cell(0,8,f"Turno {turno_corrente}",ln=True)
            pdf.set_font("Arial","",11)
        casa, osp = str(r["Casa"]), str(r["Ospite"])
        gc, go = str(r["GolCasa"]), str(r["GolOspite"])
        match_text = f"{casa} {gc} - {go} {osp}"
        match_text = match_text.encode("latin-1","ignore").decode("latin-1")
        pdf.set_text_color(0,0,0) if bool(r["Validata"]) else pdf.set_text_color(255,0,0)
        pdf.cell(0,8,match_text,ln=True)
    # classifica
    pdf.ln(10)
    pdf.set_text_color(0,0,0)
    pdf.set_font("Arial","B",12)
    pdf.cell(0,8,"Classifica attuale",ln=True)
    classifica = aggiorna_classifica(df_torneo)
    if not classifica.empty:
        pdf.set_font("Arial","",11)
        for _, row in classifica.iterrows():
            line = f"{row['Squadra']} - Punti:{row['Punti']} GF:{row['GF']} GS:{row['GS']} DR:{row['DR']}"
            line = line.encode("latin-1","ignore").decode("latin-1")
            pdf.cell(0,8,line,ln=True)
    return pdf.output(dest="S").encode("latin-1")

# -------------------------
# Session state
# -------------------------
if "df_torneo" not in st.session_state: st.session_state.df_torneo = pd.DataFrame()
if "df_squadre" not in st.session_state: st.session_state.df_squadre = pd.DataFrame()
if "turno_attivo" not in st.session_state: st.session_state.turno_attivo = 0
if "risultati_temp" not in st.session_state: st.session_state.risultati_temp = {}
if "nuovo_torneo_step" not in st.session_state: st.session_state.nuovo_torneo_step = 1
if "club_scelto" not in st.session_state: st.session_state.club_scelto = None
if "giocatori_scelti" not in st.session_state: st.session_state.giocatori_scelti = []
if "squadre_data" not in st.session_state: st.session_state.squadre_data = []
if "torneo_iniziato" not in st.session_state: st.session_state.torneo_iniziato = False
if "setup_mode" not in st.session_state: st.session_state.setup_mode = None
if "nome_torneo" not in st.session_state: st.session_state.nome_torneo = "Torneo Subbuteo - Sistema Svizzero"

# -------------------------
# Dati club
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
# Setup torneo
# -------------------------
if not st.session_state.torneo_iniziato and st.session_state.setup_mode is None:
    st.markdown("### Scegli azione")
    c1,c2 = st.columns([1,1])
    with c1:
        st.markdown("<div style='background:#f5f8ff; border-radius:8px; padding:18px; text-align:center'><h2>📂 Carica torneo esistente</h2></div>", unsafe_allow_html=True)
        if st.button("Carica torneo (CSV)"):
            st.session_state.setup_mode = "carica"
            st.rerun()
    with c2:
        st.markdown("<div style='background:#fff8e6; border-radius:8px; padding:18px; text-align:center'><h2>✨ Crea nuovo torneo</h2></div>", unsafe_allow_html=True)
        if st.button("Nuovo torneo"):
            st.session_state.setup_mode = "nuovo"
            st.session_state.nuovo_torneo_step = 0
            st.session_state.giocatori_scelti = []
            st.rerun()
    st.markdown("---")

# -------------------------
# Carica CSV
# -------------------------
if st.session_state.setup_mode == "carica":
    file = st.file_uploader("Carica file CSV", type="csv")
    if file:
        df = carica_csv_robusto_da_file(file)
        if not df.empty:
            for col in ['Casa','Ospite','GolCasa','GolOspite','Validata','Turno']:
                if col not in df.columns:
                    if col in ['GolCasa','GolOspite']: df[col]=0
                    elif col=='Validata': df[col]=False
                    elif col=='Turno': df[col]=1
            df['GolCasa']=df['GolCasa'].fillna(0).astype(int)
            df['GolOspite']=df['GolOspite'].fillna(0).astype(int)
            df['Validata']=df['Validata'].astype(bool)
            st.session_state.df_torneo = df.reset_index(drop=True)
            st.session_state.turno_attivo = int(st.session_state.df_torneo['Turno'].max())
            init_results_temp_from_df(st.session_state.df_torneo)
            st.session_state.torneo_iniziato = True
            st.session_state.setup_mode = None
            st.success("✅ Torneo caricato!")
            st.rerun()

# -------------------------
# Nuovo torneo
# -------------------------
if st.session_state.setup_mode == "nuovo":
    st.markdown("#### ✨ Crea nuovo torneo")
    # Step 0: nome torneo
    if st.session_state.nuovo_torneo_step==0:
        suffisso = st.text_input("Dai un nome al tuo torneo")
        if st.button("Prossimo passo"):
            st.session_state.nome_torneo = f"Torneo Subbuteo Svizzero - {suffisso.strip()}" if suffisso.strip() else "Torneo Subbuteo - Sistema Svizzero"
            st.session_state.nuovo_torneo_step=1
            st.rerun()
    # Step 1: scegli club e giocatori
    elif st.session_state.nuovo_torneo_step==1:
        club = st.selectbox("Scegli il Club", list(url_club.keys()), index=0)
        st.session_state.club_scelto = club
        df_gioc = carica_csv_robusto_da_url(url_club[club])
        num_squadre = st.number_input("Numero partecipanti", min_value=2, max_value=100, value=8, step=1)
        giocatori_club = df_gioc["Giocatore"].dropna().astype(str).tolist() if not df_gioc.empty else []
        seleziona_tutti = st.checkbox("Seleziona tutti i giocatori")
        giocatori_selezionati_temp=[]
        for g in giocatori_club:
            checked=seleziona_tutti
            if st.checkbox(g,value=checked,key=f"chk_{g}"): giocatori_selezionati_temp.append(g)
        mancanti = num_squadre - len(giocatori_selezionati_temp)
        if mancanti>0:
            for i in range(mancanti):
                col1,col2 = st.columns([0.15,0.85])
                with col1: aggiungi=st.checkbox(f"Aggiungi slot {i+1}",value=True,key=f"aggiungi_{i}")
                with col2: nome=st.text_input(f"Nome mancanti {i+1}", value=f"Ospite{i+1}", key=f"nome_manc_{i}")
                if aggiungi: giocatori_selezionati_temp.append(nome)
        if st.button("✅ Conferma giocatori"):
            if len(giocatori_selezionati_temp)<2: st.warning("Servono almeno 2 giocatori.")
            else:
                st.session_state.giocatori_scelti = giocatori_selezionati_temp
                st.session_state.nuovo_torneo_step=2
                st.success("Giocatori confermati.")
                st.rerun()
    # Step 2: conferma squadre e potenziale
    elif st.session_state.nuovo_torneo_step==2:
        st.markdown("### 🏷️ Definisci Squadre e Potenziali")
        df_gioc = carica_csv_robusto_da_url(url_club[st.session_state.club_scelto]) if st.session_state.club_scelto else pd.DataFrame()
        squadre_data=[]
        for i,gioc in enumerate(st.session_state.giocatori_scelti):
            if not df_gioc.empty and gioc in df_gioc['Giocatore'].values:
                riga = df_gioc[df_gioc['Giocatore']==gioc].iloc[0]
                squadra_default = riga['Squadra'] if 'Squadra' in riga and pd.notna(riga['Squadra']) else f"Squadra{i+1}"
                pot_def = int(riga['Potenziale']) if 'Potenziale' in riga and pd.notna(riga['Potenziale']) else 4
            else:
                squadra_default=f"Squadra{i+1}"; pot_def=4
            nome_gioc = st.text_input(f"Nome giocatore {i+1}",value=gioc,key=f"g_{i}")
            squadra = st.text_input(f"Squadra {i+1}", value=squadra_default,key=f"s_{i}")
            pot = st.slider(f"Potenziale {i+1}",1,10,value=pot_def,key=f"p_{i}")
            squadre_data.append({"Giocatore":nome_gioc,"Squadra":squadra,"Potenziale":pot})
        if st.button("✅ Conferma squadre e genera primo turno"):
            df_squadre = pd.DataFrame(squadre_data)
            df_squadre["SquadraGiocatore"]=df_squadre.apply(lambda r: f"{r['Squadra']} ({r['Giocatore']})",axis=1)
            df_squadre=df_squadre.sort_values(by="Potenziale",ascending=False).reset_index(drop=True)
            st.session_state.df_squadre=df_squadre
            classifica_iniziale = pd.DataFrame({'Squadra':df_squadre['SquadraGiocatore'],'Punti':0,'GF':0,'GS':0,'DR':0})
            nuove_partite = genera_accoppiamenti(classifica_iniziale,set())
            st.session_state.turno_attivo=1
            nuove_partite["Turno"]=st.session_state.turno_attivo
            st.session_state.df_torneo = pd.concat([st.session_state.df_torneo, nuove_partite], ignore_index=True)
            init_results_temp_from_df(nuove_partite)
            st.session_state.torneo_iniziato=True
            st.session_state.setup_mode=None
            st.success("🏁 Primo turno generato!")
            st.rerun()

# -------------------------
# Vista torneo attivo
# -------------------------
if st.session_state.torneo_iniziato and not st.session_state.df_torneo.empty:
    # Turni disponibili
    turni_disponibili = sorted(st.session_state.df_torneo['Turno'].unique())
    turno = st.selectbox("Seleziona Turno", turni_disponibili, index=len(turni_disponibili)-1)
    st.markdown(f"### Turno {turno}")
    df_turno = st.session_state.df_torneo[st.session_state.df_torneo['Turno']==turno].copy()
    # Inserimento risultati
    for idx,r in df_turno.iterrows():
        casa, osp = r['Casa'], r['Ospite']
        key_gc = f"gc_{turno}_{casa}_{osp}"
        key_go = f"go_{turno}_{casa}_{osp}"
        key_val = f"val_{turno}_{casa}_{osp}"
        col1,col2,col3,col4=st.columns([2,1,1,1])
        with col1: st.markdown(f"**{casa} vs {osp}**")
        with col2: gc = st.number_input("Gol Casa", min_value=0, max_value=20, value=st.session_state.risultati_temp.get(key_gc,0), key=key_gc)
        with col3: go = st.number_input("Gol Ospite", min_value=0, max_value=20, value=st.session_state.risultati_temp.get(key_go,0), key=key_go)
        with col4: val = st.checkbox("Validata", value=st.session_state.risultati_temp.get(key_val,False), key=key_val)
        st.session_state.risultati_temp[key_gc]=gc
        st.session_state.risultati_temp[key_go]=go
        st.session_state.risultati_temp[key_val]=val
    # Salva risultati nel df principale
    for idx,r in df_turno.iterrows():
        casa, osp = r['Casa'], r['Ospite']
        key_gc = f"gc_{turno}_{casa}_{osp}"
        key_go = f"go_{turno}_{casa}_{osp}"
        key_val = f"val_{turno}_{casa}_{osp}"
        st.session_state.df_torneo.loc[(st.session_state.df_torneo['Turno']==turno)&
                                        (st.session_state.df_torneo['Casa']==casa)&
                                        (st.session_state.df_torneo['Ospite']==osp),'GolCasa']=st.session_state.risultati_temp[key_gc]
        st.session_state.df_torneo.loc[(st.session_state.df_torneo['Turno']==turno)&
                                        (st.session_state.df_torneo['Casa']==casa)&
                                        (st.session_state.df_torneo['Ospite']==osp),'GolOspite']=st.session_state.risultati_temp[key_go]
        st.session_state.df_torneo.loc[(st.session_state.df_torneo['Turno']==turno)&
                                        (st.session_state.df_torneo['Casa']==casa)&
                                        (st.session_state.df_torneo['Ospite']==osp),'Validata']=st.session_state.risultati_temp[key_val]
    # Classifica attuale
    st.markdown("### 📊 Classifica attuale")
    classifica = aggiorna_classifica(st.session_state.df_torneo)
    st.dataframe(classifica)

    # Genera turno successivo
    st.markdown("---")
    if st.button("➡️ Genera prossimo turno (Sistema Svizzero)"):
        precedenti = set([(r['Casa'],r['Ospite']) for _,r in st.session_state.df_torneo.iterrows() if bool(r.get('Validata',False))])
        nuove_partite = genera_accoppiamenti(classifica,precedenti)
        if nuove_partite.empty: st.warning("Non ci sono più accoppiamenti possibili!"); st.stop()
        st.session_state.turno_attivo = st.session_state.df_torneo['Turno'].max()+1
        nuove_partite["Turno"]=st.session_state.turno_attivo
        st.session_state.df_torneo=pd.concat([st.session_state.df_torneo, nuove_partite], ignore_index=True)
        init_results_temp_from_df(nuove_partite)
        st.success(f"Turno {st.session_state.turno_attivo} generato!")
        st.rerun()

    # Export CSV e PDF
    st.markdown("---")
    col1,col2=st.columns(2)
    with col1:
        csv_data = st.session_state.df_torneo.to_csv(index=False).encode("utf-8")
        st.download_button("💾 Esporta CSV", data=csv_data, file_name=f"{st.session_state.nome_torneo}.csv", mime="text/csv")
    with col2:
        pdf_bytes = esporta_pdf(st.session_state.df_torneo, st.session_state.nome_torneo)
        st.download_button("📄 Esporta PDF", data=pdf_bytes, file_name=f"{st.session_state.nome_torneo}.pdf", mime="application/pdf")

    # Banner vincitore
    if st.session_state.df_torneo['Validata'].all():
        vincitore = classifica.iloc[0]['Squadra'] if not classifica.empty else "Nessuno"
        st.markdown(f"<h2 style='text-align:center; color:gold; background:black; padding:10px'>🏆 VINCITORE: {vincitore}</h2>", unsafe_allow_html=True)
