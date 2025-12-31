import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
import calendar
from dateutil.relativedelta import relativedelta
import plotly.express as px

# --- KONFIGURACJA I STYLE ---
st.set_page_config(page_title="Budżet Rodzinny 3.2", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    .stMetric { background-color: #1c1f26; padding: 15px; border-radius: 10px; border: 1px solid #333; }
    .shopping-item { background-color: #1c1f26; padding: 10px; border-radius: 5px; border-left: 5px solid #00ff88; margin-bottom: 5px; }
    .minus-alert { background-color: #3e0b0b; border: 1px solid #ff4b4b; padding: 15px; border-radius: 10px; margin-bottom: 20px; text-align: center; }
    div[data-testid="stExpander"] { border: 1px solid #444; border-radius: 8px; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- ZARZĄDZANIE BAZĄ DANYCH ---
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

# Inicjalizacja danych
transakcje = load_db("transakcje", [])
oplaty_stale = load_db("stale", [])
raty = load_db("raty", [])
kasa_oszcz = load_db("kasa", {"nadwyzki": 0.0, "historia_zamkniec": []})
lista_zakupow = load_db("zakupy", [])

# --- LOGIKA 800+ (Punkt 11) ---
def oblicz_800plus(data_widoku):
    laura = date(2018, 8, 1)
    zosia = date(2022, 11, 1)
    suma = 0
    if data_widoku < laura + relativedelta(years=18): suma += 800
    if data_widoku < zosia + relativedelta(years=18): suma += 800
    return suma

# --- NAWIGACJA ---
with st.sidebar:
    st.title("🏦 Menu Główne")
    wybrany_miesiac = st.selectbox("Wybierz Okres", 
        pd.date_range(start="2024-01-01", periods=36, freq='MS').strftime("%Y-%m").tolist(),
        index=pd.date_range(start="2024-01-01", periods=36, freq='MS').strftime("%Y-%m").tolist().index(datetime.now().strftime("%Y-%m"))
    )
    menu = st.radio("Idź do:", ["🏠 Pulpit", "⚙️ Wydatki Stałe i Raty", "🛒 Lista Zakupów", "📊 Statystyki i Archiwum"])

sel_dt = datetime.strptime(wybrany_miesiac, "%Y-%m").date()

# --- OBLICZENIA BILANSU ---
suma_800 = oblicz_800plus(sel_dt)
msc_dochody = sum(t['kwota'] for t in transakcje if t['miesiac'] == wybrany_miesiac and t['typ'] == "Wynagrodzenie") + suma_800
msc_zmienne = sum(t['kwota'] for t in transakcje if t['miesiac'] == wybrany_miesiac and t['typ'] == "Wydatek Zmienny")
msc_stale = sum(s['kwota'] for s in oplaty_stale)
msc_raty = sum(r['kwota'] for r in raty if datetime.strptime(r['start'], "%Y-%m-%d").date() <= sel_dt <= datetime.strptime(r['koniec'], "%Y-%m-%d").date())
msc_oszcz_celowe = sum(t['kwota'] for t in transakcje if t['miesiac'] == wybrany_miesiac and t['typ'] == "Oszczędność Celowa")

dostepne_środki = msc_dochody - (msc_zmienne + msc_stale + msc_raty + msc_oszcz_celowe)
# Kasa Oszczędnościowa (Punkt 6) = Nadwyżki z zamknięć + Wszystkie wpłacone oszczędności celowe
total_oszcz_celowe = sum(t['kwota'] for t in transakcje if t['typ'] == "Oszczędność Celowa")
aktualna_kasa = kasa_oszcz['nadwyzki'] + total_oszcz_celowe

# --- STRONA 1: PULPIT ---
if menu == "🏠 Pulpit":
    # Wskaźniki
    c1, c2, c3 = st.columns(3)
    c1.metric("Dostępne Środki", f"{dostepne_środki:,.2f} zł")
    c2.metric("Kasa Oszczędnościowa", f"{aktualna_kasa:,.2f} zł")
    
    dni_w_msc = calendar.monthrange(sel_dt.year, sel_dt.month)[1]
    dzis = datetime.now()
    poz_dni = (dni_w_msc - dzis.day + 1) if dzis.strftime("%Y-%m") == wybrany_miesiac else dni_w_msc
    c3.metric("Zostało dziennie", f"{max(0, dostepne_środki/max(1, poz_dni)):,.2f} zł")

    # Życie pod kreską (Punkt 9)
    if dostepne_środki < 0:
        st.markdown(f"<div class='minus-alert'>🚨 BRAKUJE PIENIĘDZY: {abs(dostepne_środki):,.2f} zł</div>", unsafe_allow_html=True)
        if st.button("🆘 Pobierz brakującą kwotę z Kasy Oszczędnościowej"):
            kwota_ratunku = abs(dostepne_środki)
            kasa_oszcz['nadwyzki'] -= kwota_ratunku
            transakcje.append({
                "id": str(datetime.now().timestamp()), 
                "miesiac": wybrany_miesiac, 
                "typ": "Wynagrodzenie", 
                "kwota": kwota_ratunku, 
                "opis": "🆘 Ratunek z Kasy", 
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            save_db("kasa", kasa_oszcz); save_db("transakcje", transakcje); st.rerun()

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("➕ Nowa Operacja")
        with st.form("trans_form", clear_on_submit=True):
            t_typ = st.selectbox("Typ", ["Wydatek Zmienny", "Wynagrodzenie", "Oszczędność Celowa"])
            t_kw = st.number_input("Kwota", min_value=0.0, step=10.0)
            t_op = st.text_input("Opis")
            if st.form_submit_button("Dodaj"):
                transakcje.append({
                    "id": str(datetime.now().timestamp()), 
                    "miesiac": wybrany_miesiac, 
                    "typ": t_typ, 
                    "kwota": t_kw, 
                    "opis": t_op, 
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                save_db("transakcje", transakcje); st.rerun()
    
    with col_b:
        st.subheader("🏁 Zamknięcie Miesiąca") # (Punkt 7)
        if st.button("Zamknij miesiąc i przesuń saldo do Kasy"):
            if dostepne_środki > 0:
                kwota_transferu = dostepne_środki
                kasa_oszcz['nadwyzki'] += kwota_transferu
                kasa_oszcz.setdefault('historia_zamkniec', []).append({"data": datetime.now().strftime("%Y-%m-%d %H:%M"), "miesiac": wybrany_miesiac, "kwota": kwota_transferu})
                transakcje.append({
                    "id": str(datetime.now().timestamp()), 
                    "miesiac": wybrany_miesiac, 
                    "typ": "Wydatek Zmienny", 
                    "kwota": kwota_transferu, 
                    "opis": "🏁 Zamknięcie (transfer do kasy)", 
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                save_db("kasa", kasa_oszcz); save_db("transakcje", transakcje); st.success("Pieniądze przelane!"); st.rerun()

    st.subheader("📋 Historia Wpisów")
    for t in [x for x in transakcje if x['miesiac'] == wybrany_miesiac][::-1]:
        with st.expander(f"{t['typ']} | {t['kwota']} zł | {t['opis']} (Dodano: {t.get('timestamp', '---')})"):
            nk = st.number_input("Kwota", value=float(t['kwota']), key=f"k_{t['id']}")
            no = st.text_input("Opis", value=t['opis'], key=f"o_{t['id']}")
            c_e1, c_e2 = st.columns(2)
            if c_e1.button("💾 Zapisz", key=f"s_{t['id']}"):
                t['kwota'], t['opis'] = nk, no
                save_db("transakcje", transakcje); st.rerun()
            if c_e2.button("🗑️ Usuń", key=f"d_{t['id']}"):
                transakcje = [x for x in transakcje if x['id'] != t['id']]
                save_db("transakcje", transakcje); st.rerun()

# --- STRONA: LISTA ZAKUPÓW (Punkt 12) ---
elif menu == "🛒 Lista Zakupów":
    st.header("🛒 Lista Zakupów")
    with st.form("shop_form", clear_on_submit=True):
        prod = st.text_input("Nazwa produktu")
        if st.form_submit_button("Dodaj do listy"):
            if prod:
                lista_zakupow.append({"id": str(datetime.now().timestamp()), "nazwa": prod, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M")})
                save_db("zakupy", lista_zakupow); st.rerun()
    st.divider()
    for p in lista_zakupow[::-1]:
        col_p1, col_p2 = st.columns([5, 1])
        with col_p1:
            with st.expander(f"🛒 {p['nazwa']} (Dodano: {p['timestamp']})"):
                en = st.text_input("Edytuj nazwę", value=p['nazwa'], key=f"en_{p['id']}")
                if st.button("💾 Zapisz", key=f"es_{p['id']}"):
                    p['nazwa'] = en
                    save_db("zakupy", lista_zakupow); st.rerun()
        if col_p2.button("🗑️", key=f"dp_{p['id']}"):
            lista_zakupow = [x for x in lista_zakupow if x['id'] != p['id']]
            save_db("zakupy", lista_zakupow); st.rerun()

# --- STRONA: STATYSTYKI (Punkt 10) ---
elif menu == "📊 Statystyki i Archiwum":
    st.header("📊 Statystyki i Archiwum Zamknięć")
    
    # Archiwum transferów
    st.subheader("📁 Archiwum Zamknięć Miesięcy")
    if kasa_oszcz.get('historia_zamkniec'):
        st.table(pd.DataFrame(kasa_oszcz['historia_zamkniec']))
    else: st.info("Brak historii zamknięć.")

    st.divider()
    df = pd.DataFrame(transakcje)
    if not df.empty:
        c1, c2 = st.columns(2)
        fig_pie = px.pie(df[df['typ'] != "Wynagrodzenie"], values='kwota', names='typ', title="Twoje Wydatki")
        c1.plotly_chart(fig_pie)
        
        fig_bar = px.bar(df, x='miesiac', y='kwota', color='typ', title="Przepływy w Czasie")
        c2.plotly_chart(fig_bar)

# --- STRONA: STAŁE I RATY (Punkt 3 i 4) ---
elif menu == "⚙️ Wydatki Stałe i Raty":
    st.header("⚙️ Zarządzanie Stałymi Wydatkami")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Stałe Opłaty")
        with st.form("st_form", clear_on_submit=True):
            sn, sk = st.text_input("Nazwa"), st.number_input("Kwota", min_value=0.0)
            if st.form_submit_button("Dodaj"):
                oplaty_stale.append({"id": str(datetime.now().timestamp()), "nazwa": sn, "kwota": sk})
                save_db("stale", oplaty_stale); st.rerun()
        for s in oplaty_stale:
            st.info(f"📌 {s['nazwa']}: {s['kwota']} zł")
            if st.button("Usuń", key=f"ds_{s['id']}"):
                oplaty_stale = [x for x in oplaty_stale if x['id'] != s['id']]
                save_db("stale", oplaty_stale); st.rerun()
    with col2:
        st.subheader("Raty")
        with st.form("rt_form", clear_on_submit=True):
            rn, rk = st.text_input("Nazwa"), st.number_input("Rata", min_value=0.0)
            rs, re = st.date_input("Od kiedy"), st.date_input("Do kiedy")
            if st.form_submit_button("Dodaj"):
                raty.append({"id": str(datetime.now().timestamp()), "nazwa": rn, "kwota": rk, "start": str(rs), "koniec": str(re)})
                save_db("raty", raty); st.rerun()
        for r in raty:
            st.warning(f"💳 {r['nazwa']}: {r['kwota']} zł (Do: {r['koniec']})")
            if st.button("Usuń", key=f"dr_{r['id']}"):
                raty = [x for x in raty if x['id'] != r['id']]
                save_db("raty", raty); st.rerun()
