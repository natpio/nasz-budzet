import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
import calendar

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Nasz Budżet Pro", page_icon="📈", layout="wide")

# --- STYLIZACJA (Dark Mode & Professional UI) ---
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
FILES = {"data": "budzet_pro_data.json", "shopping": "zakupy_data.json"}

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

# --- LOGIKA KALENDARZA I LIMITU ---
dzis = date.today()
dni_w_miesiacu = calendar.monthrange(dzis.year, dzis.month)[1]
dni_do_konca = dni_w_miesiacu - dzis.day + 1

# Obliczenia finansowe
dochody = df[df['Typ'] == "Przychod"]['Kwota'].sum()
stale = df[df['Typ'] == "Stałe Opłaty"]['Kwota'].sum()
fundusze = df[df['Typ'] == "Fundusze Celowe"]['Kwota'].sum()
zmienne = df[df['Typ'] == "Wydatki Zmienne"]['Kwota'].sum()

# KASA OSZCZĘDNOŚCIOWA (Suma wszystkich funduszy celowych)
kasa_oszczednosciowa = fundusze

# LIMIT DZIENNY: (Przychod - Stale - Fundusze - Zmienne_z_poprzednich_dni) / dni_do_konca
wolne_srodki = dochody - stale - fundusze - zmienne
limit_dzienny = wolne_srodki / dni_do_konca if dni_do_konca > 0 else 0

# --- MENU BOCZNE ---
with st.sidebar:
    st.title("💎 Budżet Pro v3.5")
    page = st.radio("Nawigacja", ["🏠 Pulpit Sterowniczy", "🛒 Lista Zakupów", "💰 Moje Skarbonki", "📜 Pełna Historia"])
    st.divider()
    if st.button("🗑️ Resetuj Miesiąc"):
        if st.checkbox("Potwierdzam reset"):
            save_data(pd.DataFrame(columns=["Data", "Osoba", "Kategoria", "Typ", "Kwota", "Opis"]), "data")
            st.rerun()

# --- STRONA 1: PULPIT ---
if page == "🏠 Pulpit Sterowniczy":
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown(f"""<div class="limit-box">
            <p style='color: #00d4ff; margin:0; font-size: 1.2em;'>Limit na dziś:</p>
            <h1 style='margin:0; font-size: 3.5em;'>{max(0, limit_dzienny):,.2f} zł</h1>
            <p style='margin:0; color: gray;'>Dni do końca miesiąca: {dni_do_konca}</p>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""<div class="saving-box">
            <p style='margin:0; font-size: 1.2em;'>KASA OSZCZĘDNOŚCIOWA</p>
            <h1 style='margin:0; font-size: 3.5em;'>{kasa_oszczednosciowa:,.2f} zł</h1>
            <p style='margin:0;'>Suma wszystkich funduszy</p>
        </div>""", unsafe_allow_html=True)

    st.divider()

    # Statystyki w pigułce
    m1, m2, m3 = st.columns(3)
    m1.metric("Wpływy", f"{dochody:,.2f} zł")
    m2.metric("Opłaty stałe", f"{stale:,.2f} zł")
    m3.metric("Pozostało w portfelu", f"{wolne_srodki:,.2f} zł")

    st.divider()

    # Formularz dodawania
    l_col, r_col = st.columns([1, 1])
    with l_col:
        st.markdown("<div style='color:#00ff88;' class='section-header'>➕ Nowy Wpis</div>", unsafe_allow_html=True)
        with st.form("main_form", clear_on_submit=True):
            typ = st.selectbox("Co to za ruch?", ["Wydatki Zmienne", "Stałe Opłaty", "Przychod", "Fundusze Celowe"])
            osoba = st.selectbox("Kto?", ["Piotr", "Natalia"])
            kwota = st.number_input("Kwota (zł)", min_value=0.0, step=0.01)
            opis = st.text_input("Nazwa / Opis (np. Mieszkanie, Bonus, Paliwo)")
            if st.form_submit_button("ZATWIERDŹ"):
                nowy = {"Data": str(dzis), "Osoba": osoba, "Typ": typ, "Kwota": kwota, "Opis": opis}
                df = pd.concat([df, pd.DataFrame([nowy])], ignore_index=True)
                save_data(df, "data")
                st.rerun()

    with r_col:
        st.markdown("<div style='color:#ffaa00;' class='section-header'>📊 Wydatki wg Typu</div>", unsafe_allow_html=True)
        if not df.empty:
            wykres_data = df.groupby("Typ")["Kwota"].sum()
            st.bar_chart(wykres_data)
        else:
            st.info("Brak danych do wykresu.")

# --- STRONA 2: ZAKUPY ---
elif page == "🛒 Lista Zakupów":
    st.markdown("<h1 class='header-text'>🛒 Lista Zakupów</h1>", unsafe_allow_html=True)
    c_in, _ = st.columns([2, 1])
    with c_in:
        nowy_p = st.text_input("Dopisz do listy...")
        if st.button("Dodaj ➕"):
            if nowy_p:
                nowy_wpis_s = {"Produkt": nowy_p, "Czas": datetime.now().strftime("%H:%M")}
                df_s = pd.concat([df_s, pd.DataFrame([nowy_wpis_s])], ignore_index=True)
                save_data(df_s, "shopping"); st.rerun()

    st.divider()
    for i, row in df_s.iterrows():
        c1, c2 = st.columns([4, 1])
        c1.write(f"🔹 **{row['Produkt']}** (Dodano: {row['Czas']})")
        if c2.button("✅ Kupione", key=f"s_{i}"):
            df_s = df_s.drop(i); save_data(df_s, "shopping"); st.rerun()

# --- STRONA 3: SKARBONKI ---
elif page == "💰 Moje Skarbonki":
    st.markdown("<h1 class='header-text'>💰 Fundusze Celowe</h1>", unsafe_allow_html=True)
    if not df[df['Typ'] == "Fundusze Celowe"].empty:
        skarbonki = df[df['Typ'] == "Fundusze Celowe"].groupby("Opis")["Kwota"].sum().reset_index()
        for _, s in skarbonki.iterrows():
            st.markdown(f"""
                <div style='background-color:#262626; padding:15px; border-radius:10px; border-left: 5px solid #ffd700; margin-bottom:10px;'>
                    <span style='font-size:1.2em;'>{s['Opis']}</span>: <b style='font-size:1.5em; color:#ffd700;'>{s['Kwota']:,.2f} zł</b>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Nie masz jeszcze żadnych skarbonek. Dodaj je w Pulpicie jako 'Fundusze Celowe'.")

# --- STRONA 4: HISTORIA ---
elif page == "📜 Pełna Historia":
    st.markdown("<h1 class='header-text'>📜 Historia Transakcji</h1>", unsafe_allow_html=True)
    st.dataframe(df.sort_values("Data", ascending=False), use_container_width=True, hide_index=True)
