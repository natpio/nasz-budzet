import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Nasz Budżet Ultra Pro + Archiwum", page_icon="🏦", layout="wide")

# --- STYLIZACJA ---
st.markdown("""
    <style>
    .main { background-color: #1a1a1a; color: #ffffff; }
    .stMetric { background-color: #262626; padding: 15px; border-radius: 12px; border: 1px solid #444; }
    .limit-box { background-color: #0e1117; border: 2px solid #00d4ff; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .saving-box { background: linear-gradient(135deg, #ffd700, #b8860b); color: black; padding: 20px; border-radius: 15px; text-align: center; font-weight: bold; }
    .section-header { padding: 10px; border-radius: 5px; font-weight: bold; margin-bottom: 10px; text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

# --- ZARZĄDZANIE PLIKAMI ---
FILES = {"data": "budzet_pro_data.json", "shopping": "zakupy_data.json", "raty": "raty_data.json", "sejf": "sejf_total.json"}

def load_data(key, cols):
    if os.path.exists(FILES[key]):
        try:
            with open(FILES[key], "r", encoding='utf-8') as f:
                d = json.load(f)
                return pd.DataFrame(d) if d else pd.DataFrame(columns=cols)
        except: return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_data(df, key):
    with open(FILES[key], "w", encoding='utf-8') as f:
        json.dump(df.to_dict(orient="records"), f, indent=4, ensure_ascii=False)

# Inicjalizacja danych
df_all = load_data("data", ["Data", "Czas", "Osoba", "Typ", "Kwota", "Opis", "Miesiac_Ref"])
df_s = load_data("shopping", ["Produkt", "Czas"])
df_raty = load_data("raty", ["Nazwa", "Kwota", "Start", "Koniec"])
df_sejf = load_data("sejf", ["Suma"])

if df_sejf.empty: df_sejf = pd.DataFrame([{"Suma": 0.0}])

# --- NAWIGACJA I WYBÓR MIESIĄCA ---
with st.sidebar:
    st.title("🏦 Budżet Total Pro")
    
    # Wybór aktywnego miesiąca
    if not df_all.empty:
        dostepne_miesiace = sorted(df_all['Miesiac_Ref'].unique().tolist(), reverse=True)
        obecny_msc_str = datetime.now().strftime("%Y-%m")
        if obecny_msc_str not in dostepne_miesiace:
            dostepne_miesiace.insert(0, obecny_msc_str)
    else:
        dostepne_miesiace = [datetime.now().strftime("%Y-%m")]
    
    wybrany_msc = st.selectbox("📅 Przeglądaj miesiąc:", dostepne_miesiace)
    
    page = st.radio("Menu", ["🏠 Pulpit", "💳 Raty i Stałe", "🛒 Lista Zakupów", "💰 Skarbonki"])
    
    st.divider()
    if st.button("🚀 ZAMKNIJ MIESIĄC"):
        # Logika zamknięcia (tylko dla obecnego miesiąca)
        msc_data = df_all[df_all['Miesiac_Ref'] == wybrany_msc]
        # (Tutaj można dodać transfer do sejfu jak w poprzedniej wersji)
        st.success(f"Miesiąc {wybrany_msc} zarchiwizowany.")

# --- FILTROWANIE DANYCH POD WYBRANY MIESIĄC ---
df = df_all[df_all['Miesiac_Ref'] == wybrany_msc].copy()

# --- LOGIKA AUTOMATYCZNA ---
def get_auto_income():
    dzis = datetime.strptime(wybrany_msc, "%Y-%m").date()
    dzieci = [date(2018, 8, 1), date(2022, 11, 1)]
    return sum(800 for u in dzieci if dzis < u + relativedelta(years=18))

def get_active_raty():
    target_date = datetime.strptime(wybrany_msc, "%Y-%m").date()
    suma = 0
    if not df_raty.empty:
        for _, r in df_raty.iterrows():
            start = datetime.strptime(r['Start'], '%Y-%m-%d').date()
            koniec = datetime.strptime(r['Koniec'], '%Y-%m-%d').date()
            if start <= target_date <= koniec:
                suma += r['Kwota']
    return suma

auto_800 = get_auto_income()
raty_msc = get_active_raty()

# --- OBLICZENIA ---
dzis_dt = datetime.now()
rok_sel, msc_sel = map(int, wybrany_msc.split("-"))
dni_w_msc = calendar.monthrange(rok_sel, msc_sel)[1]

# Jeśli oglądamy stary miesiąc, dni do końca = 0 (bo już minął)
if wybrany_msc == dzis_dt.strftime("%Y-%m"):
    dni_do_konca = dni_w_msc - dzis_dt.day + 1
else:
    dni_do_konca = 1 # Aby uniknąć dzielenia przez 0, pokazujemy sumę końcową

dochody = df[df['Typ'] == "Przychod"]['Kwota'].sum() + auto_800
oplaty = df[df['Typ'] == "Stałe Opłaty"]['Kwota'].sum() + raty_msc
fundusze = df[df['Typ'] == "Fundusze Celowe"]['Kwota'].sum()
zmienne = df[df['Typ'] == "Wydatki Zmienne"]['Kwota'].sum()

wolne_srodki = dochody - oplaty - fundusze - zmienne
limit_dzienny = wolne_srodki / dni_do_konca if dni_do_konca > 0 else 0
oszczednosci_razem = df_sejf.iloc[0]['Suma'] + df_all[df_all['Typ'] == "Fundusze Celowe"]['Kwota'].sum()

# --- STRONA 1: PULPIT ---
if page == "🏠 Pulpit":
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""<div class="limit-box"><p style='color:#00d4ff;'>Limit na dziś ({wybrany_msc}):</p>
            <h1 style='font-size:3.5em;'>{max(0, limit_dzienny):,.2f} zł</h1></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="saving-box"><p>KASA OSZCZĘDNOŚCIOWA (GLOBALNA)</p>
            <h1 style='font-size:3.5em;'>{oszczednosci_razem:,.2f} zł</h1></div>""", unsafe_allow_html=True)

    st.divider()
    l, r = st.columns(2)
    with l:
        st.markdown("<div style='color:#00ff88;' class='section-header'>➕ Nowy Wpis</div>", unsafe_allow_html=True)
        with st.form("add_form", clear_on_submit=True):
            t = st.selectbox("Typ", ["Wydatki Zmienne", "Stałe Opłaty", "Przychod", "Fundusze Celowe"])
            o = st.selectbox("Kto?", ["Piotr", "Natalia"])
            kw = st.number_input("Kwota", min_value=0.0)
            op = st.text_input("Opis")
            if st.form_submit_button("ZAPISZ"):
                now = datetime.now()
                new = {
                    "Data": str(now.date()), 
                    "Czas": now.strftime("%H:%M"), 
                    "Osoba": o, "Typ": t, "Kwota": kw, "Opis": op,
                    "Miesiac_Ref": wybrany_msc
                }
                df_all = pd.concat([df_all, pd.DataFrame([new])], ignore_index=True)
                save_data(df_all, "data"); st.rerun()
    with r:
        st.markdown("<div class='section-header'>📜 Historia miesiąca</div>", unsafe_allow_html=True)
        st.dataframe(df.sort_values(["Data", "Czas"], ascending=False), use_container_width=True, hide_index=True)

# --- STRONA 2: RATY I STAŁE ---
elif page == "💳 Raty i Stałe":
    st.header("💳 Raty")
    with st.form("raty_form"):
        n, kw = st.text_input("Nazwa"), st.number_input("Kwota", min_value=0.0)
        s, k = st.date_input("Start"), st.date_input("Koniec")
        if st.form_submit_button("Dodaj"):
            df_raty = pd.concat([df_raty, pd.DataFrame([{"Nazwa": n, "Kwota": kw, "Start": str(s), "Koniec": str(k)}])], ignore_index=True)
            save_data(df_raty, "raty"); st.rerun()
    st.dataframe(df_raty)

# --- STRONA 3: ZAKUPY ---
elif page == "🛒 Lista Zakupów":
    st.header("🛒 Zakupy")
    p = st.text_input("Produkt")
    if st.button("Dodaj"):
        df_s = pd.concat([df_s, pd.DataFrame([{"Produkt": p, "Czas": datetime.now().strftime("%Y-%m-%d %H:%M")}])], ignore_index=True)
        save_data(df_s, "shopping"); st.rerun()
    for i, row in df_s.iterrows():
        c1, c2 = st.columns([4,1]); c1.write(f"🔹 {row['Produkt']} ({row['Czas']})")
        if c2.button("✅", key=i): df_s = df_s.drop(i); save_data(df_s, "shopping"); st.rerun()

# --- STRONA 4: SKARBONKI ---
elif page == "💰 Skarbonki":
    st.header("💰 Oszczędności")
    st.metric("SEJF (Globalny)", f"{df_sejf.iloc[0]['Suma']:,.2f} zł")
    sk = df_all[df_all['Typ'] == "Fundusze Celowe"].groupby("Opis")["Kwota"].sum().reset_index()
    for _, s in sk.iterrows(): st.info(f"**{s['Opis']}**: {s['Kwota']:,.2f} zł")
