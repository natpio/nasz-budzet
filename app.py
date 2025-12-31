import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
import calendar
from dateutil.relativedelta import relativedelta
import plotly.express as px

# --- KONFIGURACJA I TOTALNA POPRAWKA WIDOCZNOŚCI (v3.7) ---
st.set_page_config(page_title="Budżet Rodzinny 3.7", layout="wide")

st.markdown("""
    <style>
    /* Tło i ogólny tekst */
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

    /* NAPRAWA FORMULARZY I KALENDARZA */
    /* Wymuszenie ciemnego tła i jasnego tekstu w polach input */
    input, select, textarea {
        color: white !important;
        background-color: #262730 !important;
    }
    
    /* Naprawa pól daty (Date Input) */
    div[data-baseweb="input"] {
        background-color: #262730 !important;
        border-radius: 5px !important;
    }

    /* Poprawa widoczności etykiet w formularzach */
    label p {
        color: #ffffff !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
    }

    /* Stylizacja przycisków, żeby były bardziej widoczne */
    .stButton>button {
        width: 100%;
        background-color: #00ff88 !important;
        color: #0e1117 !important;
        font-weight: bold !important;
        border: none !important;
        padding: 10px !important;
    }
    
    .stButton>button:hover {
        background-color: #00cc6e !important;
    }

    /* Alert deficytu */
    .minus-alert { 
        background-color: #3e0b0b; 
        border: 1px solid #ff4b4b; 
        padding: 15px; 
        border-radius: 10px; 
        margin-bottom: 20px; 
        text-align: center; 
        font-weight: bold;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BAZA DANYCH ---
FILES = {"transakcje": "db_transakcje.json", "stale": "db_stale.json", "raty": "db_raty.json", "kasa": "db_kasa.json", "zakupy": "db_zakupy.json"}

def load_db(key, default):
    if os.path.exists(FILES[key]):
        try:
            with open(FILES[key], "r", encoding='utf-8') as f: return json.load(f)
        except: return default
    return default

def save_db(key, data):
    with open(FILES[key], "w", encoding='utf-8') as f: json.dump(data, f, indent=4, ensure_ascii=False)

transakcje = load_db("transakcje", [])
oplaty_stale = load_db("stale", [])
raty = load_db("raty", [])
kasa_oszcz = load_db("kasa", {"nadwyzki": 0.0, "historia_zamkniec": []})
lista_zakupow = load_db("zakupy", [])

# --- LOGIKA ŚWIADCZEŃ ---
def oblicz_800plus(data_widoku):
    laura, zosia = date(2018, 8, 1), date(2022, 11, 1)
    suma = 0
    if data_widoku < laura + relativedelta(years=18): suma += 800
    if data_widoku < zosia + relativedelta(years=18): suma += 800
    return suma

# --- NAWIGACJA ---
with st.sidebar:
    st.title("🏦 Budżet Domowy")
    wybrany_miesiac = st.selectbox("Wybierz Miesiąc", 
        pd.date_range(start="2024-01-01", periods=36, freq='MS').strftime("%Y-%m").tolist(),
        index=pd.date_range(start="2024-01-01", periods=36, freq='MS').strftime("%Y-%m").tolist().index(datetime.now().strftime("%Y-%m"))
    )
    menu = st.radio("Menu:", ["🏠 Pulpit", "⚙️ Stałe i Raty", "🛒 Lista Zakupów", "📊 Statystyki i Kasa"])

sel_dt = datetime.strptime(wybrany_miesiac, "%Y-%m").date()
suma_800 = oblicz_800plus(sel_dt)

# --- OBLICZENIA ---
msc_dochody_total = sum(t['kwota'] for t in transakcje if t['miesiac'] == wybrany_miesiac and t['typ'] == "Wynagrodzenie") + suma_800
msc_zmienne = sum(t['kwota'] for t in transakcje if t['miesiac'] == wybrany_miesiac and t['typ'] == "Wydatek Zmienny")
msc_stale = sum(s['kwota'] for s in oplaty_stale)
msc_raty = sum(r['kwota'] for r in raty if datetime.strptime(r['start'], "%Y-%m-%d").date() <= sel_dt <= datetime.strptime(r['koniec'], "%Y-%m-%d").date())
msc_oszcz_celowe = sum(t['kwota'] for t in transakcje if t['miesiac'] == wybrany_miesiac and t['typ'] == "Oszczędność Celowa")

dostepne_środki = msc_dochody_total - (msc_zmienne + msc_stale + msc_raty + msc_oszcz_celowe)
aktualna_kasa = kasa_oszcz['nadwyzki'] + sum(t['kwota'] for t in transakcje if t['typ'] == "Oszczędność Celowa")

# --- STRONA 1: PULPIT ---
if menu == "🏠 Pulpit":
    c1, c2, c3 = st.columns(3)
    c1.metric("Portfel (Miesiąc)", f"{dostepne_środki:,.2f} zł")
    c2.metric("Kasa Oszczędnościowa", f"{aktualna_kasa:,.2f} zł")
    
    dni_w_msc = calendar.monthrange(sel_dt.year, sel_dt.month)[1]
    dzis = datetime.now()
    poz_dni = (dni_w_msc - dzis.day + 1) if dzis.strftime("%Y-%m") == wybrany_miesiac else dni_w_msc
    c3.metric("Limit dzienny", f"{max(0, dostepne_środki/max(1, poz_dni)):,.2f} zł")

    if dostepne_środki < 0:
        st.markdown(f"<div class='minus-alert'>🚨 Deficyt: {abs(dostepne_środki):,.2f} zł</div>", unsafe_allow_html=True)
        if st.button("🆘 Ratuj budżet z Kasy"):
            kasa_oszcz['nadwyzki'] -= abs(dostepne_środki)
            transakcje.append({"id": str(datetime.now().timestamp()), "miesiac": wybrany_miesiac, "typ": "Wynagrodzenie", "kwota": abs(dostepne_środki), "opis": "🆘 Ratunek z Kasy", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")})
            save_db("kasa", kasa_oszcz); save_db("transakcje", transakcje); st.rerun()

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("➕ Dodaj wpis")
        with st.form("add_f", clear_on_submit=True):
            t_typ = st.selectbox("Typ", ["Wydatek Zmienny", "Wynagrodzenie", "Oszczędność Celowa"])
            t_kw, t_op = st.number_input("Kwota", min_value=0.0), st.text_input("Opis")
            if st.form_submit_button("Zapisz wpis"):
                transakcje.append({"id": str(datetime.now().timestamp()), "miesiac": wybrany_miesiac, "typ": t_typ, "kwota": t_kw, "opis": t_op, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")})
                save_db("transakcje", transakcje); st.rerun()
    with col_b:
        st.subheader("🏁 Zamknij miesiąc")
        if st.button("Transfer nadwyżki do Kasy"):
            if dostepne_środki > 0:
                kasa_oszcz['nadwyzki'] += dostepne_środki
                kasa_oszcz['historia_zamkniec'].append({"data": datetime.now().strftime("%Y-%m-%d %H:%M"), "typ": "ZAMKNIĘCIE", "kwota": dostepne_środki, "opis": f"Miesiąc {wybrany_miesiac}"})
                transakcje.append({"id": str(datetime.now().timestamp()), "miesiac": wybrany_miesiac, "typ": "Wydatek Zmienny", "kwota": dostepne_środki, "opis": "🏁 Zamknięcie (transfer)", "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")})
                save_db("kasa", kasa_oszcz); save_db("transakcje", transakcje); st.rerun()

    st.subheader("📋 Historia okresu")
    for t in [x for x in transakcje if x['miesiac'] == wybrany_miesiac][::-1]:
        with st.expander(f"{t['typ']} | {t['kwota']} zł | {t['opis']}"):
            nk, no = st.number_input("Kwota", value=float(t['kwota']), key=f"k_{t['id']}"), st.text_input("Opis", value=t['opis'], key=f"o_{t['id']}")
            if st.button("💾 Zapisz zmiany", key=f"s_{t['id']}"):
                t['kwota'], t['opis'] = nk, no
                save_db("transakcje", transakcje); st.rerun()
            if st.button("🗑️ Usuń wpis", key=f"d_{t['id']}"):
                transakcje = [x for x in transakcje if x['id'] != t['id']]; save_db("transakcje", transakcje); st.rerun()

# --- STRONA: STATYSTYKI I KASA ---
elif menu == "📊 Statystyki i Kasa":
    st.header("📊 Analiza i Sejf")
    df = pd.DataFrame(transakcje)
    
    if not df.empty:
        dzis = datetime.now()
        ile_msc = dzis.month if sel_dt.year == dzis.year else (12 if sel_dt.year < dzis.year else 0)
        suma_800_rok = oblicz_800plus(sel_dt) * ile_msc
        realne_dochody = df[(df['typ'] == "Wynagrodzenie") & (~df['opis'].str.contains("Ratunek", na=False)) & (df['miesiac'].str.startswith(str(sel_dt.year)))]['kwota'].sum() + suma_800_rok
        realne_wydatki = df[(df['typ'] == "Wydatek Zmienny") & (~df['opis'].str.contains("Zamknięcie", na=False)) & (df['miesiac'].str.startswith(str(sel_dt.year)))]['kwota'].sum() + (msc_stale * ile_msc)
        
        c_st1, c_st2 = st.columns(2)
        c_st1.metric(f"Dochody ({sel_dt.year})", f"{realne_dochody:,.2f} zł")
        c_st2.metric(f"Wydatki ({sel_dt.year})", f"{realne_wydatki:,.2f} zł")
        
        fig_pie = px.pie(df[~df['opis'].str.contains("Zamknięcie", na=False) & (df['typ'] != "Wynagrodzenie")], values='kwota', names='typ', title="Twoje Wydatki")
        st.plotly_chart(fig_pie)

    st.subheader("🛠️ Korekta Kasy")
    with st.expander("Skoryguj stan Sejfu"):
        ck1, ck2, ck3 = st.columns([2, 2, 3])
        k_kw, k_ak, k_po = ck1.number_input("Kwota korekty", min_value=0.0), ck2.selectbox("Akcja", ["Odejmij", "Dodaj"]), ck3.text_input("Powód")
        if st.button("Wykonaj"):
            val = k_kw if k_ak == "Dodaj" else -k_kw
            kasa_oszcz['nadwyzki'] += val
            kasa_oszcz['historia_zamkniec'].append({"data": datetime.now().strftime("%Y-%m-%d %H:%M"), "typ": "KOREKTA", "kwota": val, "opis": k_po})
            save_db("kasa", kasa_oszcz); st.rerun()

    if kasa_oszcz['historia_zamkniec']:
        st.subheader("📁 Historia operacji na Kasie")
        st.table(pd.DataFrame(kasa_oszcz['historia_zamkniec']).sort_values(by="data", ascending=False))

# --- RESZTA (Lista Zakupów, Stałe) ---
elif menu == "🛒 Lista Zakupów":
    st.header("🛒 Lista Zakupów")
    with st.form("sh", clear_on_submit=True):
        p = st.text_input("Co kupić?")
        if st.form_submit_button("Dodaj do listy"):
            lista_zakupow.append({"id": str(datetime.now().timestamp()), "nazwa": p, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")})
            save_db("zakupy", lista_zakupow); st.rerun()
    for p in lista_zakupow[::-1]:
        cp1, cp2 = st.columns([5, 1])
        cp1.write(f"🛒 **{p['nazwa']}** ({p['timestamp']})")
        if cp2.button("🗑️", key=f"dp_{p['id']}"):
            lista_zakupow = [x for x in lista_zakupow if x['id'] != p['id']]; save_db("zakupy", lista_zakupow); st.rerun()

elif menu == "⚙️ Stałe i Raty":
    st.header("⚙️ Stałe i Raty")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Opłaty Stałe")
        with st.form("s", clear_on_submit=True):
            sn, sk = st.text_input("Nazwa (np. Czynsz)"), st.number_input("Kwota")
            if st.form_submit_button("Dodaj Stały Wydatek"):
                oplaty_stale.append({"id": str(datetime.now().timestamp()), "nazwa": sn, "kwota": sk}); save_db("stale", oplaty_stale); st.rerun()
        for s in oplaty_stale:
            st.write(f"📌 {s['nazwa']}: {s['kwota']} zł")
            if st.button("Usuń", key=f"ds_{s['id']}"):
                oplaty_stale = [x for x in oplaty_stale if x['id'] != s['id']]; save_db("stale", oplaty_stale); st.rerun()
    with col2:
        st.subheader("Raty")
        with st.form("r", clear_on_submit=True):
            rn, rk = st.text_input("Nazwa (np. Auto)"), st.number_input("Kwota Raty")
            rs, re = st.date_input("Miesiąc START"), st.date_input("Miesiąc KONIEC")
            if st.form_submit_button("Zatwierdź Ratę"):
                raty.append({"id": str(datetime.now().timestamp()), "nazwa": rn, "kwota": rk, "start": str(rs), "koniec": str(re)}); save_db("raty", raty); st.rerun()
        for r in raty:
            st.write(f"💳 {r['nazwa']}: {r['kwota']} zł")
            if st.button("Usuń", key=f"dr_{r['id']}"):
                raty = [x for x in raty if x['id'] != r['id']]; save_db("raty", raty); st.rerun()
