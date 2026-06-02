import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- CONFIGURAZIONE INTERFACCIA ---
st.set_page_config(page_title="Diario Alimentare Palestra", page_icon="💪", layout="centered")

st.title("Diario alimentare")
st.write("Aggiungi i tuoi alimenti, salva il giorno e rivedi tutto quando vuoi.")

# --- CONNESSIONE DIRETTA A GOOGLE SHEETS ---
URL_FOGLIO = "https://docs.google.com/spreadsheets/d/1-3PcrFzKhnokd6FQwLRKXxnyHoA9IJGIxPY9ALsmhDY/edit?usp=sharing"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("Errore di connessione a Google Fogli. Verifica la configurazione nei Secrets.")
    st.stop()

# --- LOGIN UTENTE PER PRIVACY ---
if 'utente' not in st.session_state:
    st.session_state.utente = ""

if not st.session_state.utente:
    st.subheader("Accedi per iniziare")
    nome_utente = st.text_input("Inserisci il tuo nome o email per caricare il tuo diario:").strip().lower()
    if st.button("Entra nell'app", type="primary"):
        if nome_utente:
            st.session_state.utente = nome_utente
            st.rerun()
        else:
            st.error("Inserisci un nome valido per accedere.")
    st.stop()

st.sidebar.write(f"Loggato come: **{st.session_state.utente.capitalize()}**")
if st.sidebar.button("Disconnetti"):
    st.session_state.utente = ""
    st.session_state.elementi_oggi = []
    st.rerun()

# --- CARICAMENTO DATI DAL FOGLIO GOOGLE ---
@st.cache_data(ttl=5)
def scarica_dati(nome_scheda):
    try:
        df = conn.read(spreadsheet=URL_FOGLIO, worksheet=nome_scheda)
        return df.dropna(how='all')
    except Exception:
        return pd.DataFrame()

df_alimenti_tutti = scarica_dati("Alimenti")
df_diario_tutti = scarica_dati("Diario")

if not df_alimenti_tutti.empty and 'Utente' in df_alimenti_tutti.columns:
    df_alimenti = df_alimenti_tutti[df_alimenti_tutti['Utente'] == st.session_state.utente]
else:
    df_alimenti = pd.DataFrame(columns=['Utente', 'Nome', 'Unita', 'Kcal', 'Proteine', 'Carbo', 'Grassi', 'Zuccheri'])

if not df_diario_tutti.empty and 'Utente' in df_diario_tutti.columns:
    df_diario = df_diario_tutti[df_diario_tutti['Utente'] == st.session_state.utente]
else:
    df_diario = pd.DataFrame(columns=['Utente', 'Data', 'Nome', 'Quantita', 'Kcal', 'Proteine', 'Carbo', 'Grassi', 'Zuccheri'])

if 'elementi_oggi' not in st.session_state:
    st.session_state.elementi_oggi = []

# --- SCHERMATA: DIARIO DI OGGI ---
st.subheader("Giorno attivo")
data_selezionata = st.date_input("Seleziona Data", datetime.now()).strftime("%Y-%m-%d")

tot_kcal = sum(int(x['Kcal']) for x in st.session_state.elementi_oggi)
tot_pro = sum(float(x['Proteine']) for x in st.session_state.elementi_oggi)
tot_carbo = sum(float(x['Carbo']) for x in st.session_state.elementi_oggi)
tot_grassi = sum(float(x['Grassi']) for x in st.session_state.elementi_oggi)
tot_zuccheri = sum(float(x['Zuccheri']) for x in st.session_state.elementi_oggi)

if st.button("Salva giorno", use_container_width=True, type="primary"):
    if st.session_state.elementi_oggi:
        nuove_righe = []
        for item in st.session_state.elementi_oggi:
            nuove_righe.append({
                "Utente": st.session_state.utente,
                "Data": data_selezionata,
                "Nome": item['Nome'],
                "Quantita": item['Quantita'],
                "Kcal": item['Kcal'],
                "Proteine": item['Proteine'],
                "Carbo": item['Carbo'],
                "Grassi": item['Grassi'],
                "Zuccheri": item['Zuccheri']
            })
        df_da_salvare = pd.concat([df_diario_tutti, pd.DataFrame(nuove_righe)], ignore_index=True)
        conn.update(spreadsheet=URL_FOGLIO, worksheet="Diario", data=df_da_salvare)
        st.session_state.elementi_oggi = []
        st.success("Giornata salvata sul cloud con successo!")
        st.rerun()
    else:
        st.warning("Aggiungi almeno un alimento prima di salvare la giornata.")

st.markdown(f"""
<div style="background-color: #0d6154; padding: 20px; border-radius: 15px; color: white; margin-bottom: 15px;">
    <p style="margin: 0; font-size: 14px;">Calorie odierne inserite</p>
    <h2 style="margin: 0; font-size: 32px;">{tot_kcal} kcal</h2>
</div>
""", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Proteine", f"{round(tot_pro, 1)} g")
m2.metric("Carbo", f"{round(tot_carbo, 1)} g")
m3.metric("Grassi", f"{round(tot_grassi, 1)} g")
m4.metric("Zuccheri", f"{round(tot_zuccheri, 1)} g")

# --- SEZIONE: AGGIUNGI AL GIORNO ---
st.write("---")
st.subheader("Aggiungi al giorno")

if not df_alimenti.empty:
    lista_nomi_alimenti = df_alimenti['Nome'].tolist()
    alimento_scelto = st.selectbox("Seleziona alimento dalla tua dispensa", lista_nomi_alimenti)
    quantita = st.number_input("Quantità / Moltiplicatore porzione", min_value=0.1, value=1.0, step=0.1)

    if st.button("Aggiungi al giorno"):
        riga_cibo = df_alimenti[df_alimenti['Nome'] == alimento_scelto].iloc[0]
        st.session_state.elementi_oggi.append({
            "Nome": alimento_scelto,
            "Quantita": quantita,
            "Kcal": int(riga_cibo['Kcal'] * quantita),
            "Proteine": round(float(riga_cibo['Proteine']) * quantita, 1),
            "Carbo": round(float(riga_cibo['Carbo']) * quantita, 1),
            "Grassi": round(float(riga_cibo['Grassi']) * quantita, 1),
            "Zuccheri": round(float(riga_cibo['Zuccheri']) * quantita, 1),
        })
        st.rerun()
else:
    st.info("La tua dispensa è vuota. Crea un alimento personalizzato qui sotto per iniziare.")

st.subheader("Elenco del giorno (Temporaneo)")
if not st.session_state.elementi_oggi:
    st.info("Nessun alimento aggiunto per ora. Clicca su 'Aggiungi al giorno'.")
else:
    for idx, item in enumerate(st.session_state.elementi_oggi):
        with st.expander(f"➔ {item['Nome']} (x{item['Quantita']})"):
            st.write(f"🔥 {item['Kcal']} kcal | 🍗 P: {item['Proteine']}g | 🍞 C: {item['Carbo']}g | 🥑 G: {item['Grassi']}g")
            if st.button("Rimuovi", key=f"rimuovi_{idx}"):
                st.session_state.elementi_oggi.pop(idx)
                st.rerun()

# --- SEZIONE: AGGIUNGI ALIMENTO PERSONALIZZATO ---
st.write("---")
st.subheader("Aggiungi alimento personalizzato")
nuovo_nome = st.text_input("Nome alimento", placeholder="Es. uovo sodo")
nuova_unita = st.text_input("Unità/porzione", placeholder="Es. 1 pezzo o 100g")

c1, c2 = st.columns(2)
with c1:
    nuovo_kcal = st.number_input("Kcal", min_value=0, value=0)
    nuovo_carbo = st.number_input("Carbo (g)", min_value=0.0, value=0.0, step=0.1)
    nuovo_zuccheri = st.number_input("Zuccheri (g)", min_value=0.0, value=0.0, step=0.1)
with c2:
    nuovo_pro = st.number_input("Proteine (g)", min_value=0.0, value=0.0, step=0.1)
    nuovo_grassi = st.number_input("Grassi (g)", min_value=0.0, value=0.0, step=0.1)

if st.button("Salva alimento in dispensa"):
    if nuovo_nome:
        # Controllo di sicurezza per le colonne
        if 'Nome' in df_alimenti_tutti.columns and 'Utente' in df_alimenti_tutti.columns:
            controllo_esiste = df_alimenti_tutti[(df_alimenti_tutti['Nome'].str.lower() == nuovo_nome.lower()) & (df_alimenti_tutti['Utente'] == st.session_state.utente)]
            if not controllo_esiste.empty:
                st.error("Questo alimento esiste già nella tua dispensa!")
                st.stop()
        else:
            st.warning(f"Nota: Impossibile verificare i duplicati. Le colonne trovate nel file sono: {df_alimenti_tutti.columns.tolist()}")
        
        # Creazione del nuovo cibo da salvare
        nuovo_cibo = pd.DataFrame([{
            "Utente": st.session_state.utente,
            "Nome": nuovo_nome,
            "Unita": nuova_unita,
            "Kcal": nuovo_kcal,
            "Proteine": nuovo_pro,
            "Carbo": nuovo_carbo,
            "Grassi": nuovo_grassi,
            "Zuccheri": nuovo_zuccheri
        }])
        
        df_alimenti_aggiornato = pd.concat([df_alimenti_tutti, nuovo_cibo], ignore_index=True)
        conn.update(spreadsheet=URL_FOGLIO, worksheet="Alimenti", data=df_alimenti_aggiornato)
        st.success(f"'{nuovo_nome}' salvato per sempre nella tua dispensa!")
        st.rerun()
    else:
        st.error("Inserisci un nome valido per l'alimento.")

# --- SEZIONE: STORICO ---
st.write("---")
st.subheader("Storico giorni salvati")
if not df_diario.empty:
    giorni_unici = df_diario['Data'].unique()
    for g in sorted(giorni_unici, reverse=True):
        dati_giorno = df_diario[df_diario['Data'] == g]
        tot_kcal_g = dati_giorno['Kcal'].sum()
        with st.expander(f"📅 Giorno {g} ➔ Totale: {tot_kcal_g} kcal"):
            st.dataframe(dati_giorno[['Nome', 'Quantita', 'Kcal', 'Proteine', 'Carbo', 'Grassi']], use_container_width=True, hide_index=True)
else:
    st.info("Non ci sono ancora giorni salvati nello storico del cloud.")
