import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
import calendar
from dateutil.relativedelta import relativedelta
import plotly.express as px

# --- KONFIGURACJA I STYLE ---
st.set_page_config(page_title="Budżet Rodzinny 2.0", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1c1f26; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    .header-box { background-color: #262730; padding: 20px; border-radius: 10px; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- SYSTEM PLIKÓW ---
FILES = {
    "transakcje": "db_transakcje.json",
    "stale": "db_stale.json",
    "raty": "db_raty.json",
    "kasa": "db_kasa.json"
}

def load_db(key, default):
    if os.path.exists(FILES[key]):
        with open(FILES[key], "r", encoding='utf-8') as f: return json.load(f)
    return default

def save_db(key, data):
    with open(FILES[key], "w", encoding='utf-8') as f: json.dump(data, f, indent=4)

# Inicjalizacja danych
transakcje = load_db("transakcje", []) # (Punkty 1, 2, 5)
oplaty_stale = load_db("stale", [])     # (Punkt 3)
raty = load_db("raty", [])             # (Punkt 4)
kasa_oszcz = load_db("kasa", {"nadwyzki": 0.0}) # (Punkty 6, 7)

# --- LOGIKA 800+ (Punkt 11) ---
def oblicz_800plus(data_widoku):
    laura = date(2018, 8, 1)
    zosia = date(2022, 11, 1)
    suma = 0
    if data_widoku < laura + relativedelta(years=18): suma += 800
    if data_widoku < zosia + relativedelta(years=18): suma += 800
    return suma

# --- NAWIGACJA (Sidebar) ---
with st.sidebar:
    st.title("🏦 Panel Sterowania")
    wybrany_miesiac = st.selectbox("Miesiąc", 
        pd.date_range(start="2024-01-01", periods=36, freq='MS').strftime("%Y-%m").tolist(),
        index=pd.date_range(start="2024-01-01", periods=36, freq='MS').strftime("%Y-%m").tolist().index(datetime.now().strftime("%Y-%m"))
    )
    menu = st.radio("Nawigacja", ["🏠 Pulpit", "⚙️ Wydatki Stałe i Raty", "📊 Statystyki (Rok)"])

sel_dt = datetime.strptime(wybrany_miesiac, "%Y-%m").date()

# --- PRZELICZENIA MIESIĘCZNE ---
# Dochody (Punkt 1 + 11)
msc_dochody = sum(t['kwota'] for t in transakcje if t['miesiac'] == wybrany_miesiac and t['typ'] == "Wynagrodzenie")
suma_800 = oblicz_800plus(sel_dt)
total_dochody = msc_dochody + suma_800

# Wydatki Zmienne (Punkt 2)
msc_zmienne = sum(t['kwota'] for t in transakcje if t['miesiac'] == wybrany_miesiac and t['typ'] == "Wydatek Zmienny")

# Wydatki Stałe i Raty (Punkty 3 + 4)
msc_stale = sum(s['kwota'] for s in oplaty_stale)
msc_raty = sum(r['kwota'] for r in raty if datetime.strptime(r['start'], "%Y-%m-%d").date() <= sel_dt <= datetime.strptime(r['koniec'], "%Y-%m-%d").date())

# Oszczędności Celowe (Punkt 5)
msc_oszcz_celowe = sum(t['kwota'] for t in transakcje if t['miesiac'] == wybrany_miesiac and t['typ'] == "Oszczędność Celowa")

# Bilans (Punkt 8 + 9)
suma_wydatkow = msc_zmienne + msc_stale + msc_raty + msc_oszcz_celowe
dostepne_środki = total_dochody - suma_wydatkow

# Kasa Oszczędnościowa (Punkt 6)
wszystkie_oszcz_celowe = sum(t['kwota'] for t in transakcje if t['typ'] == "Oszczędność Celowa")
aktualna_kasa = kasa_oszcz['nadwyzki'] + wszystkie_oszcz_celowe

# --- STRONA 1: PULPIT ---
if menu == "🏠 Pulpit":
    # Wskaźniki górne
    c1, c2, c3 = st.columns(3)
    c1.metric("Portfel (Miesiąc)", f"{dostepne_środki:,.2f} zł")
    c2.metric("Kasa Oszczędnościowa", f"{aktualna_kasa:,.2f} zł") # (Punkt 6)
    
    # Punkt 8: Ile dziennie
    dni_w_msc = calendar.monthrange(sel_dt.year, sel_dt.month)[1]
    dzis = datetime.now()
    pozostalo_dni = (dni_w_msc - dzis.day + 1) if dzis.strftime("%Y-%m") == wybrany_miesiac else dni_w_msc
    dzienny_limit = dostepne_środki / max(1, pozostalo_dni)
    c3.metric("Limit dzienny", f"{max(0, dzienny_limit):,.2f} zł")

    # Punkt 9: Życie pod kreską
    if dostepne_środki < 0:
        st.error(f"⚠️ Brakuje Ci {abs(dostepne_środki):,.2f} zł do końca miesiąca!")
        if st.button("🆘 Pobierz brakującą kwotę z Kasy Oszczędnościowej"):
            kasa_oszcz['nadwyzki'] -= abs(dostepne_środki)
            transakcje.append({"id": str(datetime.now().timestamp()), "miesiac": wybrany_miesiac, "typ": "Wynagrodzenie", "kwota": abs(dostepne_środki), "opis": "Ratunek z Kasy"})
            save_db("kasa", kasa_oszcz); save_db("transakcje", transakcje); st.rerun()

    # Formularze dodawania (Punkty 1, 2, 5)
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📝 Nowy wpis")
        with st.form("trans_form", clear_on_submit=True):
            t_typ = st.selectbox("Typ", ["Wynagrodzenie", "Wydatek Zmienny", "Oszczędność Celowa"])
            t_kwota = st.number_input("Kwota", min_value=0.0)
            t_opis = st.text_input("Opis")
            if st.form_submit_button("Dodaj"):
                transakcje.append({"id": str(datetime.now().timestamp()), "miesiac": wybrany_miesiac, "typ": t_typ, "kwota": t_kwota, "opis": t_opis})
                save_db("transakcje", transakcje); st.rerun()
    
    with col2:
        st.subheader("🏁 Zamknięcie miesiąca") # (Punkt 7)
        if st.button("Zamknij miesiąc i przesuń nadwyżkę do Kasy"):
            if dostepne_środki > 0:
                kasa_oszcz['nadwyzki'] += dostepne_środki
                transakcje.append({"id": str(datetime.now().timestamp()), "miesiac": wybrany_miesiac, "typ": "Wydatek Zmienny", "kwota": dostepne_środki, "opis": "Zamknięcie miesiąca (przesunięcie)"})
                save_db("kasa", kasa_oszcz); save_db("transakcje", transakcje); st.success("Pieniądze przelane do kasy!"); st.rerun()

    # Tabela edycji (Punkty 1, 2, 5 - edycja i usuwanie)
    st.subheader("📋 Historia okresu")
    for i, t in enumerate([x for x in transakcje if x['miesiac'] == wybrany_miesiac]):
        with st.expander(f"{t['typ']} | {t['kwota']} zł | {t['opis']}"):
            new_kwota = st.number_input("Kwota", value=float(t['kwota']), key=f"k_{t['id']}")
            new_opis = st.text_input("Opis", value=t['opis'], key=f"o_{t['id']}")
            c_e1, c_e2 = st.columns(2)
            if c_e1.button("Zapisz zmiany", key=f"s_{t['id']}"):
                t['kwota'], t['opis'] = new_kwota, new_opis
                save_db("transakcje", transakcje); st.rerun()
            if c_e2.button("Usuń", key=f"d_{t['id']}"):
                transakcje = [x for x in transakcje if x['id'] != t['id']]
                save_db("transakcje", transakcje); st.rerun()

# --- STRONA 2: STAŁE I RATY (Punkty 3 + 4) ---
elif menu == "⚙️ Wydatki Stałe i Raty":
    st.header("⚙️ Zarządzanie stałymi elementami")
    c_s1, c_s2 = st.columns(2)
    
    with c_s1:
        st.subheader("🏠 Wydatki Stałe")
        with st.form("stale_f"):
            s_n = st.text_input("Nazwa")
            s_k = st.number_input("Kwota", min_value=0.0)
            if st.form_submit_button("Dodaj stały"):
                oplaty_stale.append({"id": str(datetime.now().timestamp()), "nazwa": s_n, "kwota": s_k})
                save_db("stale", oplaty_stale); st.rerun()
        for s in oplaty_stale:
            st.write(f"📌 {s['nazwa']}: {s['kwota']} zł")
            if st.button("Usuń", key=f"ds_{s['id']}"):
                oplaty_stale = [x for x in oplaty_stale if x['id'] != s['id']]
                save_db("stale", oplaty_stale); st.rerun()

    with c_s2:
        st.subheader("💳 Raty")
        with st.form("raty_f"):
            r_n = st.text_input("Nazwa")
            r_k = st.number_input("Rata", min_value=0.0)
            r_s = st.date_input("Start")
            r_e = st.date_input("Koniec")
            if st.form_submit_button("Dodaj ratę"):
                raty.append({"id": str(datetime.now().timestamp()), "nazwa": r_n, "kwota": r_k, "start": str(r_s), "koniec": str(r_e)})
                save_db("raty", raty); st.rerun()
        for r in raty:
            st.write(f"📊 {r['nazwa']}: {r['kwota']} zł (do {r['koniec']})")
            if st.button("Usuń", key=f"dr_{r['id']}"):
                raty = [x for x in raty if x['id'] != r['id']]
                save_db("raty", raty); st.rerun()

# --- STRONA 3: STATYSTYKI (Punkt 10) ---
elif menu == "📊 Statystyki (Rok)":
    st.header("📊 Statystyki Roczne")
    df = pd.DataFrame(transakcje)
    if not df.empty:
        c_r1, c_r2 = st.columns(2)
        # Sumy roczne
        suma_doch_rok = df[df['typ'] == "Wynagrodzenie"]['kwota'].sum() + (suma_800 * 12)
        suma_wyd_rok = df[df['typ'] != "Wynagrodzenie"]['kwota'].sum() + (msc_stale * 12) + (msc_raty * 12)
        c_r1.metric("Łączne Dochody (Rok)", f"{suma_doch_rok:,.2f} zł")
        c_r2.metric("Łączne Wydatki (Rok)", f"{suma_wyd_rok:,.2f} zł")
        
        # Wykres typów (Punkt 10)
        fig_pie = px.pie(df[df['typ'] != "Wynagrodzenie"], values='kwota', names='typ', title="Na co idą pieniądze?")
        st.plotly_chart(fig_pie)
        
        # Wykres słupkowy miesięczny
        fig_bar = px.bar(df, x='miesiac', y='kwota', color='typ', barmode='group', title="Przepływy miesięczne")
        st.plotly_chart(fig_bar)
