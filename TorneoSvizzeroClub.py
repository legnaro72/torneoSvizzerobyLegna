import streamlit as st
import pandas as pd
from datetime import datetime
import requests
import io
from fpdf import FPDF

st.set_page_config(page_title="⚽ Torneo Subbuteo - Sistema Svizzero", layout="wide")

# -------------------------
# Funzioni
# -------------------------

def esporta_pdf(df_torneo, nome_torneo):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    titolo = nome_torneo.encode("latin-1", "ignore").decode("latin-1")
    pdf.cell(0, 10, titolo, ln=True, align="C")
    pdf.set_font("Arial", "", 11)
    turno_corrente = None
    for _, r in df_torneo.sort_values(by="Turno").iterrows():
        if turno_corrente != r["Turno"]:
            turno_corrente = r["Turno"]
            pdf.ln(5)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 8, f"Turno {turno_corrente}", ln=True)
            pdf.set_font("Arial", "", 11)
        casa, osp = str(r["Casa"]), str(r["Ospite"])
        gc, go = str(r["GolCasa"]), str(r["GolOspite"])
        match_text = f"{casa} {gc} - {go} {osp}".encode("latin-1", "ignore").decode("latin-1")
        pdf.set_text_color(0, 0, 0) if bool(r["Validata"]) else pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 8, match_text, ln=True)
    # Classifica
    pdf.ln(10)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Classifica attuale", ln=True)
    classifica = aggiorna_classifica(df_torneo)
    if not classifica.empty:
        pdf.set_font("Arial", "", 11)
        for _, row in classifica.iterrows():
            line = f"{row['Squadra']} - Punti:{row['Punti']} GF:{row['GF']} GS:{row['GS']} DR:{row['DR']}"
            line = line.encode("latin-1", "ignore").decode("latin-1")
            pdf.cell(0, 8, line, ln=True)
    return pdf.output(dest="S").encode("latin-1")

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
        stats[casa]['G'] += 1; stats[osp]['G'] += 1
        stats[casa]['GF'] += gc; stats[casa]['GS'] += go
        stats[osp]['GF'] += go; stats[osp]['GS'] += gc
        if gc > go:
            stats[casa]['Punti'] += 2; stats[casa]['V'] += 1; stats[osp]['P'] += 1
        elif gc < go:
            stats[osp]['Punti'] += 2; stats[osp]['V'] += 1; stats[casa]['P'] += 1
        else:
            stats[casa]['Punti'] += 1; stats[osp]['Punti'] += 1; stats[casa]['N'] += 1; stats[osp]['N'] += 1
    if not stats:
        return pd.DataFrame(columns=['Squadra','Punti','G','V','N','P','GF','GS','DR'])
    df_class = pd.DataFrame([{'Squadra':s,'Punti':v['Punti'],'G':v['G'],'V':v['V'],'N':v['N'],'P':v['P'],'GF':v['GF'],'GS':v['GS'],'DR':v['GF']-v['GS']} for s,v in stats.items()])
    return df_class.sort_values(by=['Punti','DR','GF'],ascending=False).reset_index(drop=True)

def genera_accoppiamenti(classifica, precedenti):
    accoppiamenti, gia_abbinati = [], set()
    for i, r1 in classifica.iterrows():
        s1 = r1['Squadra']
        if s1 in gia_abbinati: continue
        for j in range(i+1,len(classifica)):
            s2 = classifica.iloc[j]['Squadra']
            if s2 in gia_abbinati: continue
            if (s1,s2) not in precedenti and (s2,s1) not in precedenti:
                accoppiamenti.append((s1,s2))
                gia_abbinati.add(s1); gia_abbinati.add(s2)
                break
    df = pd.DataFrame([{"Casa":c,"Ospite":o,"GolCasa":0,"GolOspite":0,"Validata":False} for c,o in accoppiamenti])
    return df

def carica_csv_robusto_da_url(url):
    try: r=requests.get(url,timeout=8); r.raise_for_status(); return pd.read_csv(io.StringIO(r.content.decode('latin1')))
    except Exception as e: st.warning(f"Errore caricamento CSV da URL: {e}"); return pd.DataFrame()

def carica_csv_robusto_da_file(file_buffer):
    try: return pd.read_csv(io.StringIO(file_buffer.read().decode('latin1')))
    except Exception as e: st.warning(f"Errore caricamento CSV da file: {e}"); return pd.DataFrame()

def init_results_temp_from_df(df):
    for _, row in df.iterrows():
        T=row.get('Turno',1); casa=row['Casa']; osp=row['Ospite']
        key_gc=f"gc_{T}_{casa}_{osp}"; key_go=f"go_{T}_{casa}_{osp}"; key_val=f"val_{T}_{casa}_{osp}"
        st.session_state.risultati_temp.setdefault(key_gc,int(row.get('GolCasa',0)))
        st.session_state.risultati_temp.setdefault(key_go,int(row.get('GolOspite',0)))
        st.session_state.risultati_temp.setdefault(key_val,bool(row.get('Validata',False)))

# -------------------------
# Inizializzazione session_state
# -------------------------
if "df_torneo" not in st.session_state: st.session_state.df_torneo=pd.DataFrame()
if "df_squadre" not in st.session_state: st.session_state.df_squadre=pd.DataFrame()
if "turno_attivo" not in st.session_state: st.session_state.turno_attivo=0
if "risultati_temp" not in st.session_state: st.session_state.risultati_temp={}
if "nuovo_torneo_step" not in st.session_state: st.session_state.nuovo_torneo_step=1
if "club_scelto" not in st.session_state: st.session_state.club_scelto=None
if "giocatori_scelti" not in st.session_state: st.session_state.giocatori_scelti=[]
if "squadre_data" not in st.session_state: st.session_state.squadre_data=[]
if "torneo_iniziato" not in st.session_state: st.session_state.torneo_iniziato=False
if "setup_mode" not in st.session_state: st.session_state.setup_mode=None
if "nome_torneo" not in st.session_state: st.session_state.nome_torneo="Torneo Subbuteo - Sistema Svizzero"

# -------------------------
# Dati club
# -------------------------
url_club={
    "Superba":"https://raw.githubusercontent.com/legnaro72/torneoSvizzerobyLegna/refs/heads/main/giocatoriSuperba.csv",
    "PierCrew":"https://raw.githubusercontent.com/legnaro72/torneoSvizzerobyLegna/refs/heads/main/giocatoriPierCrew.csv"
}

# -------------------------
# Header
# -------------------------
st.markdown(f"<h1 style='text-align:center;color:#0B5FFF;'>⚽ {st.session_state.nome_torneo}</h1>", unsafe_allow_html=True)

# -------------------------
# Gestione torneo
# -------------------------
if st.session_state.torneo_iniziato and not st.session_state.df_torneo.empty:
    turni_disponibili = sorted(st.session_state.df_torneo['Turno'].unique())
    st.session_state.turno_attivo = turni_disponibili[-1] if turni_disponibili else 1
    turno_selezionato = st.selectbox("Seleziona Turno", turni_disponibili, index=turni_disponibili.index(st.session_state.turno_attivo))
    df_turno = st.session_state.df_torneo[st.session_state.df_torneo['Turno']==turno_selezionato].copy()

    if df_turno.empty:
        st.info("Nessuna partita in questo turno.")
    else:
        for _, row in df_turno.iterrows():
            idx=int(row.name); T=int(row['Turno']); casa=row['Casa']; osp=row['Ospite']
            key_gc=f"gc_{T}_{casa}_{osp}"; key_go=f"go_{T}_{casa}_{osp}"; key_val=f"val_{T}_{casa}_{osp}"
            st.session_state.risultati_temp.setdefault(key_gc,int(row.get('GolCasa',0)))
            st.session_state.risultati_temp.setdefault(key_go,int(row.get('GolOspite',0)))
            st.session_state.risultati_temp.setdefault(key_val,bool(row.get('Validata',False)))
            c1,c2,c3,c4=st.columns([3,1,1,0.8])
            with c1: st.markdown(f"**{casa}** vs  **{osp}**")
            with c2: st.number_input("", min_value=0,max_value=20,step=1,key=f"gc_input_{T}_{casa}_{osp}"); st.session_state[key_gc]=st.session_state[f"gc_input_{T}_{casa}_{osp}"]
            with c3: st.number_input("", min_value=0,max_value=20,step=1,key=f"go_input_{T}_{casa}_{osp}"); st.session_state[key_go]=st.session_state[f"go_input_{T}_{casa}_{osp}"]
            with c4: st.checkbox("Validata", key=f"val_input_{T}_{casa}_{osp}"); st.session_state[key_val]=st.session_state[f"val_input_{T}_{casa}_{osp}"]
            st.session_state.df_torneo.at[idx,'GolCasa']=st.session_state[key_gc]; st.session_state.df_torneo.at[idx,'GolOspite']=st.session_state[key_go]; st.session_state.df_torneo.at[idx,'Validata']=st.session_state[key_val]

    # Classifica e esportazioni
    st.markdown("---")
    c_left,c_right=st.columns([1,2])
    with c_left:
        if st.button("⚡ Genera turno successivo"):
            partite_validate=st.session_state.df_torneo[st.session_state.df_torneo['Validata']==True]
            precedenti=set(zip(partite_validate['Casa'],partite_validate['Ospite']))
            classifica_attuale=aggiorna_classifica(st.session_state.df_torneo)
            if classifica_attuale.empty and not st.session_state.df_squadre.empty:
                classifica_attuale=pd.DataFrame({'Squadra':st.session_state.df_squadre['SquadraGiocatore']})
            nuove_partite=genera_accoppiamenti(classifica_attuale,precedenti)
            if nuove_partite.empty: st.warning("⚠️ Nessuna nuova partita possibile")
            else:
                st.session_state.turno_attivo+=1; nuove_partite["Turno"]=st.session_state.turno_attivo
                for col in ['GolCasa','GolOspite','Validata']:
                    if col not in nuove_partite.columns: nuove_partite[col]=0 if 'Gol' in col else False
                st.session_state.df_torneo=pd.concat([st.session_state.df_torneo,nuove_partite],ignore_index=True)
                init_results_temp_from_df(nuove_partite)
                st.success(f"🎉 Turno {st.session_state.turno_attivo} generato!")
    with c_right: st.dataframe(aggiorna_classifica(st.session_state.df_torneo),use_container_width=True)

    st.markdown("---")
    st.sidebar.markdown("### 💾 Esporta torneo")
    csv_data=st.session_state.df_torneo.to_csv(index=False).encode('utf-8')
    file_name_csv=f"{st.session_state.nome_torneo.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    st.sidebar.download_button(label="⬇️ Scarica CSV torneo", data=csv_data,file_name=file_name_csv,mime="text/csv")
    if st.sidebar.button("⬇️ Esporta torneo in PDF"):
        pdf_bytes=esporta_pdf(st.session_state.df_torneo,st.session_state.nome_torneo)
        file_name_pdf=f"{st.session_state.nome_torneo.replace(' ','_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        st.sidebar.download_button(label="📄 Download PDF torneo", data=pdf_bytes, file_name=file_name_pdf, mime="application/pdf")

    # Banner vincitore
    tutte_validate=st.session_state.df_torneo['Validata'].all()
    if tutte_validate:
        df_class=aggiorna_classifica(st.session_state.df_torneo)
        if not df_class.empty:
            vincitore=df_class.iloc[0]['Squadra']
            st.markdown(f"<div style='background:linear-gradient(90deg,gold,orange);padding:20px;border-radius:12px;text-align:center;color:black;font-size:28px;font-weight:bold;margin-top:20px;'>🏆 Vincitore del torneo: {vincitore} 🏆</div>", unsafe_allow_html=True)
