import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Nasz Budżet Pro + Raty", page_icon="📈", layout="wide")

# --- STYLIZACJA ---
st.markdown("""
    <style>
    .main { background-color: #1a1a1a; color: #ffffff; }
    .stMetric { background-color: #262626; padding: 15px; border-radius: 12px; border: 1px solid #444; }
    .limit-box { background-color: #0e1117; border: 2px solid #00d4ff; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .saving-box { background: linear-gradient(135deg, #ffd700, #b8860b); color: black; padding: 20px; border-radius: 15px; text-align: center; font-weight: bold; }
    .section-header { padding: 10px; border-radius: 5px; font-weight: bold; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }
    </style>
    """, unsafe_allow_html=True)

# --- ZARZĄDZANIE PLIKAMI ---
FILES = {"data": "budzet_pro_data.json", "shopping": "zakupy_data.json", "raty": "raty_data.json"}

def load_data(key, cols):
    if os.path.exists(FILES[key]):
        try:
            with open(FILES[key], "r", encoding='utf-8') as f:
                d = json.load(f)
                return pd.DataFrame(d) if d else pd.DataFrame(columns=cols)
        except:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_data(df, key):
    with open(FILES[key], "w", encoding='utf-8') as f:
        json.dump(df.to_dict(orient="records"), f, indent=4, ensure_ascii=False)

# Inicjalizacja danych
df = load_data("data", ["Data", "Osoba", "Kategoria", "Typ", "Kwota", "Opis"])
df_s = load_data("shopping", ["Produkt", "Czas"])
df_raty = load_data("raty", ["Nazwa", "Kwota", "Start", "Koniec"])

# --- LOGIKA 800+ (AUTOMATYCZNA) ---
def oblicz_800_plus():
    dzis = date.today()
    dzieci = [
        date(2018, 8, 1),  # Córka 1
        date(2022, 11, 1)  # Córka 2
    ]
    suma = 0
    for urodziny in dzieci:
        koniec_swiadczenia = urodziny + relativedelta(years=18)
        if dzis < koniec_swiadczenia:
            suma += 800
    return suma

auto_800 = oblicz_800_plus()

# --- LOGIKA RAT (AUTOMATYCZNA) ---
def oblicz_raty_na_dzis():
    dzis = date.today()
    suma_rat = 0
    if not df_raty.empty:
        for _, r in df_raty.iterrows():
            start = datetime.strptime(r['Start'], '%Y-%m-%d').date()
            koniec = datetime.strptime(r['Koniec'], '%Y-%m-%d').date()
            if start <= dzis <= koniec:
                suma_rat += r['Kwota']
    return suma_rat

raty_na_miesiac = oblicz_raty_na_dzis()

# --- OBLICZENIA LIMITU ---
dzis_dt = date.today()
dni_w_miesiacu = calendar.monthrange(dzis_dt.year, dzis_dt.month)[1]
dni_do_konca = dni_w_miesiacu - dzis_dt.day + 1

dochody_wpisane = df[df['Typ'] == "Przychod"]['Kwota'].sum()
dochody_total = dochody_wpisane + auto_800

stale_wpisane = df[df['Typ'] == "Stałe Opłaty"]['Kwota'].sum()
stale_total = stale_wpisane + raty_na_miesiac

fundusze = df[df['Typ'] == "Fundusze Celowe"]['Kwota'].sum()
zmienne = df[df['Typ'] == "Wydatki Zmienne"]['Kwota'].sum()

wolne_srodki = dochody_total - stale_total - fundusze - zmienne
limit_dzienny = wolne_srodki / dni_do_konca if dni_do_konca > 0 else 0

# --- MENU BOCZNE ---
with st.sidebar:
    st.title("💎 Budżet Ultra Pro")
    page = st.radio("Nawigacja", ["🏠 Pulpit", "💳 Raty i Stałe", "🛒 Lista Zakupów", "💰 Skarbonki"])
    st.divider()
    st.info(f"✨ Auto 800+: {auto_800} zł")
    st.info(f"📅 Raty w tym msc: {raty_na_miesiac} zł")

# --- STRONA 1: PULPIT ---
if page == "🏠 Pulpit":
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""<div class="limit-box"><p style='color:#00d4ff;'>Limit na dziś:</p>
            <h1 style='font-size:3.5em;'>{max(0, limit_dzienny):,.2f} zł</h1>
            <p>Dni do końca: {dni_do_konca}</p></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="saving-box"><p>KASA OSZCZĘDNOŚCIOWA</p>
            <h1 style='font-size:3.5em;'>{fundusze:,.2f} zł</h1><p>Suma funduszy</p></div>""", unsafe_allow_html=True)

    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("Wpływy (z 800+)", f"{dochody_total:,.2f} zł")
    m2.metric("Opłaty + Raty", f"{stale_total:,.2f} zł")
    m3.metric("Zostało w portfelu", f"{wolne_srodki:,.2f} zł")

    st.divider()
    l, r = st.columns(2)
    with l:
        st.markdown("<div style='color:#00ff88;' class='section-header'>➕ Dodaj Wydatek/Przychód</div>", unsafe_allow_html=True)
        with st.form("main_form", clear_on_submit=True):
            t = st.selectbox("Typ", ["Wydatki Zmienne", "Stałe Opłaty", "Przychod", "Fundusze Celowe"])
            o = st.selectbox("Kto?", ["Piotr", "Natalia"])
            kw = st.number_input("Kwota", min_value=0.0)
            op = st.text_input("Opis")
            if st.form_submit_button("ZAPISZ"):
                new = {"Data": str(dzis_dt), "Osoba": o, "Typ": t, "Kwota": kw, "Opis": op}
                df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                save_data(df, "data"); st.rerun()

# --- STRONA 2: RATY I STAŁE ---
elif page == "💳 Raty i Stałe":
    st.header("💳 Zarządzanie Ratami")
    with st.form("raty_form", clear_on_submit=True):
        n = st.text_input("Nazwa raty (np. Telefon)")
        kw = st.number_input("Kwota miesięczna", min_value=0.0)
        s = st.date_input("Start spłaty", date.today())
        k = st.date_input("Koniec spłaty", date.today() + relativedelta(years=1))
        if st.form_submit_button("DODAJ RATĘ"):
            new_r = {"Nazwa": n, "Kwota": kw, "Start": str(s), "Koniec": str(k)}
            df_raty = pd.concat([df_raty, pd.DataFrame([new_r])], ignore_index=True)
            save_data(df_raty, "raty"); st.rerun()
    
    st.subheader("Twoje aktywne raty:")
    st.dataframe(df_raty, use_container_width=True)
    if st.button("Wyczyść wszystkie raty"):
        save_data(pd.DataFrame(columns=["Nazwa", "Kwota", "Start", "Koniec"]), "raty"); st.rerun()

# --- STRONY 3 i 4 (LISTA I SKARBONKI - bez zmian w logice) ---
elif page == "🛒 Lista Zakupów":
    st.header("🛒 Zakupy")
    p = st.text_input("Co kupić?")
    if st.button("Dodaj"):
        df_s = pd.concat([df_s, pd.DataFrame([{"Produkt": p, "Czas": datetime.now().strftime("%H:%M")}])], ignore_index=True)
        save_data(df_s, "shopping"); st.rerun()
    for i, row in df_s.iterrows():
        c1, c2 = st.columns([4,1]); c1.write(f"🔹 {row['Produkt']}"); 
        if c2.button("✅", key=i): df_s = df_s.drop(i); save_data(df_s, "shopping"); st.rerun()

elif page == "💰 Skarbonki":
    st.header("💰 Twoje Fundusze")
    if not df[df['Typ'] == "Fundusze Celowe"].empty:
        sk = df[df['Typ'] == "Fundusze Celowe"].groupby("Opis")["Kwota"].sum().reset_index()
        for _, s in sk.iterrows():
            st.warning(f"**{s['Opis']}**: {s['Kwota']:,.2f} zł")
    else: st.info("Brak funduszy.")
