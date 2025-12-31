import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
import calendar
from dateutil.relativedelta import relativedelta
import plotly.express as px

# --- KONFIGURACJA I OSTATECZNA NAPRAWA KONTRASTU (v3.8) ---
st.set_page_config(page_title="Budżet Rodzinny 3.8", layout="wide")

st.markdown("""
    <style>
    /* Informacja dla przeglądarki o trybie ciemnym - to naprawia kalendarz i systemowe okna */
    :root { color-scheme: dark; }
    
    .main { background-color: #0e1117; color: white; }
    
    /* Wyraźne kafelki Metric */
    [data-testid="stMetric"] {
        background-color: #1c1f26;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #333;
    }
    [data-testid="stMetricLabel"] > div { color: #ffffff !important; opacity: 1 !important; font-size: 1rem !important; }
    [data-testid="stMetricValue"] > div { color: #00ff88 !important; font-weight: bold !important; }

    /* TOTALNA NAPRAWA PÓL FORMULARZA */
    /* Tło dla wszystkich pól wprowadzania, aby uniknąć białego na białym */
    input, select, textarea, div[data-baseweb="input"], div[data-baseweb="select"] {
        background-color: #262730 !important;
        color: #ffffff !important;
    }

    /* Specyficzna poprawka dla pól daty (Date Input) */
    input[type="date"] {
        color: #ffffff !important;
        background-color: #262730 !important;
    }
    
    /* Wymuszenie jasnej ikony kalendarza w polu daty */
    ::-webkit-calendar-picker-indicator {
        filter: invert(1);
        cursor: pointer;
    }

    /* Czytelne etykiety nad polami (np. 'Nazwa raty') */
    label p {
        color: #00ff88 !important; 
        font-weight: bold !important;
        font-size: 1.1rem !important;
    }

    /* Stylizacja przycisków - duże, zielone, czytelne na telefonie */
    .stButton>button {
        width: 100%;
        background-color: #00ff88 !important;
        color: #0e1117 !important;
        font-weight: bold !important;
        border: none !important;
        height: 3em;
        margin-top: 10px;
    }
    
    .stButton>button:active {
        background-color: #00cc6e !important;
    }

    /* Alert deficytu/minusowego salda */
    .minus-alert { 
        background-color: #3e0b0b; 
        border: 2px solid #ff4b4b; 
        padding: 15px; 
        border-radius: 10px; 
        text-align: center; 
        font-weight: bold;
        color: white;
        margin-bottom: 20px;
    }

    /* Poprawa widoczności tekstu w historii (expanderach) */
    .st-ae { color: white !important; }
    </style>
    """, unsafe_allow_html=True)

# --- ZARZĄDZANIE BAZĄ DANYCH (JSON) ---
FILES = {
    "transakcje": "db_transakcje.json",
    "stale": "db_stale.json",
    "raty": "db_raty.json",
    "kasa": "db_kasa.json",
    "zakupy": "db_zakupy.json"
}

def load_db(key, default):
    if os.path.exists(FILES[key]):
        try:
            with open(FILES[key], "r", encoding='utf-8') as f: return json.load(f)
        except: return default
    return default

def save_db(key, data):
    with open(FILES[key], "w", encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)

# Wczytanie danych na start
transakcje = load_db("transakcje", [])
oplaty_stale = load_db("stale", [])
raty = load_db("raty", [])
kasa_oszcz = load_db("kasa", {"nadwyzki": 0.0, "historia_zamkniec": []})
lista_zakupow = load_db("zakupy", [])

# --- LOGIKA ŚWIADCZEŃ 800+ ---
def oblicz_800plus(data_widoku):
    laura_ur, zosia_ur = date(2018, 8, 1), date(2022, 11, 1)
    suma = 0
    if data_widoku < laura_ur + relativedelta(years=18): suma += 800
    if data_widoku < zosia_ur + relativedelta(years=18): suma += 800
    return suma

# --- SIDEBAR (MENU BOCZNE) ---
with st.sidebar:
    st.title("🏦 Budżet 3.8")
    wybrany_miesiac = st.selectbox("Wybierz Miesiąc", 
        pd.date_range(start="2024-01-01", periods=36, freq='MS').strftime("%Y-%m").tolist(),
        index=pd.date_range(start="2024-01-01", periods=36, freq='MS').strftime("%Y-%m").tolist().index(datetime.now().strftime("%Y-%m"))
    )
    menu = st.radio("Nawigacja", ["🏠 Pulpit", "⚙️ Stałe i Raty", "🛒 Lista Zakupów", "📊 Statystyki"])

sel_dt = datetime.strptime(wybrany_miesiac, "%Y-%m").date()
suma_800 = oblicz_800plus(sel_dt)

# --- OBLICZENIA MIESIĘCZNE ---
msc_dochody = sum(t['kwota'] for t in transakcje if t['miesiac'] == wybrany_miesiac and t['typ'] == "Wynagrodzenie") + suma_800
msc_zmienne = sum(t['kwota'] for t in transakcje if t['miesiac'] == wybrany_miesiac and t['typ'] == "Wydatek Zmienny")
msc_stale = sum(s['kwota'] for s in oplaty_stale)
msc_raty = sum(r['kwota'] for r in raty if datetime.strptime(r['start'], "%Y-%m-%d").date() <= sel_dt <= datetime.strptime(r['koniec'], "%Y-%m-%d").date())
msc_oszcz_celowe = sum(t['kwota'] for t in transakcje if t['miesiac'] == wybrany_miesiac and t['typ'] == "Oszczędność Celowa")

portfel_saldo = msc_dochody - (msc_zmienne + msc_stale + msc_raty + msc_oszcz_celowe)
kasa_total = kasa_oszcz['nadwyzki'] + sum(t['kwota'] for t in transakcje if t['typ'] == "Oszczędność Celowa")

# --- SEKCJA 1: PULPIT ---
if menu == "🏠 Pulpit":
    c1, c2 = st.columns(2)
    c1.metric("Portfel (Miesiąc)", f"{portfel_saldo:,.2f} zł")
    c2.metric("Sejf (Oszczędności)", f"{kasa_total:,.2f} zł")
    
    if portfel_saldo < 0:
        st.markdown(f"<div class='minus-alert'>🚨 Deficyt: {abs(portfel_saldo):,.2f} zł</div>", unsafe_allow_html=True)
        if st.button("🆘 Ratuj budżet z Sejfu"):
            kasa_oszcz['nadwyzki'] -= abs(portfel_saldo)
            transakcje.append({
                "id": str(datetime.now().timestamp()), 
                "miesiac": wybrany_miesiac, 
                "typ": "Wynagrodzenie", 
                "kwota": abs(portfel_saldo), 
                "opis": "🆘 Ratunek z Sejfu", 
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            save_db("kasa", kasa_oszcz); save_db("transakcje", transakcje); st.rerun()

    st.divider()
    with st.form("dodaj_wpis", clear_on_submit=True):
        st.subheader("➕ Nowa Operacja")
        t_typ = st.selectbox("Kategoria", ["Wydatek Zmienny", "Wynagrodzenie", "Oszczędność Celowa"])
        t_kw = st.number_input("Kwota (zł)", min_value=0.0, step=10.0)
        t_op = st.text_input("Opis / Notatka")
        if st.form_submit_button("ZAPISZ"):
            transakcje.append({
                "id": str(datetime.now().timestamp()), 
                "miesiac": wybrany_miesiac, 
                "typ": t_typ, 
                "kwota": t_kw, 
                "opis": t_op, 
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            save_db("transakcje", transakcje); st.rerun()

    if st.button("🏁 Zamknij miesiąc (Przenieś saldo do Sejfu)"):
        if portfel_saldo > 0:
            kasa_oszcz['nadwyzki'] += portfel_saldo
            transakcje.append({
                "id": str(datetime.now().timestamp()), 
                "miesiac": wybrany_miesiac, 
                "typ": "Wydatek Zmienny", 
                "kwota": portfel_saldo, 
                "opis": "🏁 Zamknięcie (transfer)", 
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            save_db("kasa", kasa_oszcz); save_db("transakcje", transakcje); st.rerun()

    st.subheader("📋 Historia wpisów")
    for t in [x for x in transakcje if x['miesiac'] == wybrany_miesiac][::-1]:
        with st.expander(f"{t['typ']} | {t['kwota']} zł | {t['opis']}"):
            if st.button("🗑️ Usuń ten wpis", key=f"del_{t['id']}"):
                transakcje = [x for x in transakcje if x['id'] != t['id']]
                save_db("transakcje", transakcje); st.rerun()

# --- SEKCJA 2: STAŁE I RATY ---
elif menu == "⚙️ Stałe i Raty":
    st.header("⚙️ Zarządzanie obciążeniami")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📌 Opłaty Stałe")
        with st.form("stale_f", clear_on_submit=True):
            sn = st.text_input("Nazwa (np. Czynsz)")
            sk = st.number_input("Kwota miesięczna", min_value=0.0)
            if st.form_submit_button("DODAJ OPŁATĘ"):
                oplaty_stale.append({"id": str(datetime.now().timestamp()), "nazwa": sn, "kwota": sk})
                save_db("stale", oplaty_stale); st.rerun()
        for s in oplaty_stale:
            st.write(f"• {s['nazwa']}: **{s['kwota']} zł**")
            if st.button("Usuń", key=f"ds_{s['id']}"):
                oplaty_stale = [x for x in oplaty_stale if x['id'] != s['id']]
                save_db("stale", oplaty_stale); st.rerun()
    with col2:
        st.subheader("💳 Raty i Kredyty")
        with st.form("raty_f", clear_on_submit=True):
            rn = st.text_input("Nazwa (np. Rata za auto)")
            rk = st.number_input("Kwota raty", min_value=0.0)
            rs = st.date_input("Miesiąc początkowy")
            re = st.date_input("Miesiąc końcowy")
            if st.form_submit_button("DODAJ RATĘ"):
                raty.append({"id": str(datetime.now().timestamp()), "nazwa": rn, "kwota": rk, "start": str(rs), "koniec": str(re)})
                save_db("raty", raty); st.rerun()
        for r in raty:
            st.write(f"• {r['nazwa']}: **{r['kwota']} zł** (do {r['koniec']})")
            if st.button("Usuń", key=f"dr_{r['id']}"):
                raty = [x for x in raty if x['id'] != r['id']]
                save_db("raty", raty); st.rerun()

# --- SEKCJA 3: ZAKUPY ---
elif menu == "🛒 Lista Zakupów":
    st.header("🛒 Lista Zakupów")
    with st.form("zak_f", clear_on_submit=True):
        p = st.text_input("Co dopisać?")
        if st.form_submit_button("DODAJ DO LISTY"):
            lista_zakupow.append({"id": str(datetime.now().timestamp()), "nazwa": p})
            save_db("zakupy", lista_zakupow); st.rerun()
    for p in lista_zakupow[::-1]:
        c_p1, c_p2 = st.columns([4, 1])
        c_p1.info(f"🛒 **{p['nazwa']}**")
        if c_p2.button("Usuń", key=f"dz_{p['id']}"):
            lista_zakupow = [x for x in lista_zakupow if x['id'] != p['id']]
            save_db("zakupy", lista_zakupow); st.rerun()

# --- SEKCJA 4: STATYSTYKI ---
elif menu == "📊 Statystyki":
    st.header(f"📊 Analiza Roku {sel_dt.year}")
    df = pd.DataFrame(transakcje)
    if not df.empty:
        dzis = datetime.now()
        # Logika liczenia miesięcy bez prognozowania w przód
        if sel_dt.year == dzis.year: ile_msc = dzis.month
        elif sel_dt.year < dzis.year: ile_msc = 12
        else: ile_msc = 0

        suma_800_rok = oblicz_800plus(sel_dt) * ile_msc
        dochody_rok = df[(df['typ']=="Wynagrodzenie") & (~df['opis'].str.contains("Ratunek", na=False)) & (df['miesiac'].str.startswith(str(sel_dt.year)))]['kwota'].sum() + suma_800_rok
        
        st.metric(f"Realne Dochody (rok {sel_dt.year})", f"{dochody_rok:,.2f} zł", help="Wynagrodzenia + 800plus za miesiące, które już minęły.")
        
        # Wykres struktury wydatków (bez transferów do sejfu)
        df_wydatki = df[~df['opis'].str.contains("Zamknięcie", na=False) & (df['typ'] != "Wynagrodzenie") & (df['miesiac'].str.startswith(str(sel_dt.year)))]
        if not df_wydatki.empty:
            fig = px.pie(df_wydatki, values='kwota', names='typ', title="Gdzie idą pieniądze?")
            st.plotly_chart(fig)
        else:
            st.write("Brak wydatków do wyświetlenia wykresu.")
