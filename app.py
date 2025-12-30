import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
import calendar

# --- KONFIGURACJA ---
st.set_page_config(page_title="Nasz Budżet Pro", page_icon="📈", layout="wide")

# --- STYLIZACJA (Dark Mode & Colors) ---
st.markdown("""
    <style>
    .main { background-color: #1a1a1a; color: #ffffff; }
    .stMetric { background-color: #262626; padding: 15px; border-radius: 12px; border: 1px solid #444; }
    .limit-box { background-color: #0e1117; border: 2px solid #00d4ff; padding: 20px; border-radius: 15px; text-align: center; }
    .section-header { padding: 10px; border-radius: 5px; font-weight: bold; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- LOGIKA DANYCH ---
FILES = {"data": "budzet_pro_data.json", "shopping": "zakupy_data.json"}

def load_data(key, cols):
    if os.path.exists(FILES[key]):
        with open(FILES[key], "r", encoding='utf-8') as f:
            d = json.load(f)
            return pd.DataFrame(d) if d else pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)

def save_data(df, key):
    with open(FILES[key], "w", encoding='utf-8') as f:
        json.dump(df.to_dict(orient="records"), f, indent=4, ensure_ascii=False)

# Inicjalizacja
df = load_data("data", ["Data", "Osoba", "Kategoria", "Typ", "Kwota", "Opis"])
df_s = load_data("shopping", ["Produkt", "Czas"])

# --- OBLICZENIA BUDŻETOWE ---
dzis = date.today()
dni_w_miesiacu = calendar.monthrange(dzis.year, dzis.month)[1]
dni_do_konca = dni_w_miesiacu - dzis.day + 1

dochody = df[df['Typ'] == "Przychod"]['Kwota'].sum()
stale = df[df['Typ'] == "Stałe Opłaty"]['Kwota'].sum()
fundusze = df[df['Typ'] == "Fundusze Celowe"]['Kwota'].sum()
zmienne = df[df['Typ'] == "Wydatki Zmienne"]['Kwota'].sum()

# Magia limitu dziennego
dostepna_kasa = dochody - stale - fundusze - zmienne
limit_dzienny = dostepna_kasa / dni_do_konca if dni_do_konca > 0 else 0

# --- INTERFEJS ---
st.sidebar.title("💎 Budżet Pro v3")
page = st.sidebar.radio("Nawigacja", ["🏠 Panel Sterowania", "🛒 Lista Zakupów", "📜 Historia"])

if page == "🏠 Panel Sterowania":
    # GÓRNY PANEL (LIMIT)
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f"""<div class="limit-box">
            <p style='color: #00d4ff; margin:0;'>Dziś możecie wydać:</p>
            <h1 style='margin:0; font-size: 2.5em;'>{max(0, limit_dzienny):,.2f} zł</h1>
            <small>Dni do końca miesiąca: {dni_do_konca}</small>
        </div>""", unsafe_allow_html=True)
    
    with c2:
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Przychody", f"{dochody:,.0f} zł")
        col_b.metric("Stałe/Fundusze", f"{stale+fundusze:,.0f} zł", delta_color="inverse")
        col_b.write(f"Zostało: {dostepna_kasa:,.2f} zł")

    st.divider()

    # SEKCJE DODAWANIA
    col_l, col_r = st.columns(2)
    
    with col_l:
        st.markdown("<div style='color:#00ff88;' class='section-header'>➕ DODAJ WPIS</div>", unsafe_allow_html=True)
        with st.form("main_form", clear_on_submit=True):
            t = st.selectbox("Typ wpisu", ["Wydatki Zmienne", "Stałe Opłaty", "Przychod", "Fundusze Celowe"])
            o = st.selectbox("Kto?", ["Piotr", "Natalia"])
            kw = st.number_input("Kwota", min_value=0.0)
            op = st.text_input("Opis / Nazwa")
            if st.form_submit_button("ZATWIERDŹ"):
                new = {"Data": str(dzis), "Osoba": o, "Typ": t, "Kwota": kw, "Opis": op}
                df = pd.concat([df, pd.DataFrame([new])], ignore_index=True)
                save_data(df, "data")
                st.rerun()

    with col_r:
        st.markdown("<div style='color:#ffaa00;' class='section-header'>📊 STRUKTURA MIESIĄCA</div>", unsafe_allow_html=True)
        if not df.empty:
            summary = df.groupby("Typ")["Kwota"].sum()
            st.bar_chart(summary)
        else:
            st.info("Dodaj pierwszy przychód lub wydatek!")

elif page == "🛒 Lista Zakupów":
    st.title("🛒 Zakupy")
    new_s = st.text_input("Dopisz produkt...")
    if st.button("Dodaj"):
        df_s = pd.concat([df_s, pd.DataFrame([{"Produkt": new_s, "Czas": datetime.now().strftime("%H:%M")}])], ignore_index=True)
        save_data(df_s, "shopping"); st.rerun()
    
    for i, row in df_s.iterrows():
        c1, c2 = st.columns([4, 1])
        c1.write(f"**{row['Produkt']}** ({row['Czas']})")
        if c2.button("✅", key=f"s_{i}"):
            df_s = df_s.drop(i); save_data(df_s, "shopping"); st.rerun()

elif page == "📜 Historia":
    st.title("📜 Wszystkie operacje")
    st.dataframe(df.sort_values("Data", ascending=False), use_container_width=True)
