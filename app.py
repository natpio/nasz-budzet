import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Budżet Pro - Naprawa Usuwania", page_icon="🏦", layout="wide")

# --- STYLIZACJA (WYSOKI KONTRAST + CZYTELNOŚĆ) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1c1f26; padding: 15px; border-radius: 12px; border: 1px solid #444; color: #ffffff; }
    .section-header { padding: 10px; border-radius: 8px; font-weight: bold; margin-top: 15px; text-transform: uppercase; font-size: 1.1em; }
    .sub-summary { font-size: 1.05em; font-weight: bold; margin-bottom: 12px; padding: 12px; border-radius: 10px; border: 1px solid #555; color: #ffffff !important; }
    
    /* Poprawa widoczności wpisów */
    .stExpander { border: 1px solid #555 !important; background-color: #1c1f26 !important; margin-bottom: 8px !important; }
    div[data-testid="stExpander"] p { color: white !important; font-size: 1.1em; font-weight: bold; }
    
    /* Kolorowe przyciski dla łatwiejszej obsługi */
    button[kind="primary"] { background-color: #ff4b4b !important; border: none !important; }
    button[kind="secondary"] { background-color: #3e4451 !important; color: white !important; }
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

# Inicjalizacja
df_all = load_data("data", ["Data", "Czas", "Osoba", "Typ", "Kwota", "Opis", "Miesiac_Ref"])
df_raty = load_data("raty", ["Nazwa", "Kwota", "Start", "Koniec"])
df_sejf = load_data("sejf", ["Suma"])
if df_sejf.empty: df_sejf = pd.DataFrame([{"Suma": 0.0}])

# --- NAWIGACJA ---
with st.sidebar:
    st.title("🏦 Menu")
    obecny_msc = datetime.now().strftime("%Y-%m")
    dostepne_miesiace = sorted(list(set(df_all['Miesiac_Ref'].unique().tolist() + [obecny_msc])), reverse=True)
    wybrany_msc = st.selectbox("📅 Miesiąc:", dostepne_miesiace)
    page = st.radio("Idź do:", ["🏠 Pulpit", "💳 Raty", "🛒 Zakupy", "💰 Skarbonki"])

# --- LOGIKA ---
df_current = df_all[df_all['Miesiac_Ref'] == wybrany_msc].copy()

# --- STRONA 1: PULPIT ---
if page == "🏠 Pulpit":
    col_add, col_hist = st.columns([1, 1.5])
    
    with col_add:
        st.markdown("<div style='background-color:#00ff88; color:black;' class='section-header'>➕ Dodaj Wpis</div>", unsafe_allow_html=True)
        with st.form("new_entry_form", clear_on_submit=True):
            t = st.selectbox("Typ", ["Wydatki Zmienne", "Stałe Opłaty", "Przychod", "Fundusze Celowe"])
            o = st.selectbox("Osoba", ["Piotr", "Natalia"])
            kw = st.number_input("Kwota", min_value=0.0)
            op = st.text_input("Opis (co to?)")
            if st.form_submit_button("DODAJ"):
                now = datetime.now()
                new_row = {"Data": str(now.date()), "Czas": now.strftime("%H:%M"), "Osoba": o, "Typ": t, "Kwota": kw, "Opis": op, "Miesiac_Ref": wybrany_msc}
                df_all = pd.concat([df_all, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df_all, "data")
                st.rerun()

    with col_hist:
        # PRZYCHODY (Wpływy)
        st.markdown("<div style='background-color:#00d4ff; color:black;' class='section-header'>💰 Wpływy</div>", unsafe_allow_html=True)
        inc_df = df_current[df_current['Typ'] == "Przychod"]
        for i, row in inc_df.sort_index(ascending=False).iterrows():
            with st.expander(f"➕ {row['Kwota']} zł | {row['Opis']}"):
                c1, c2 = st.columns(2)
                # USUWANIE
                if c1.button("🗑️ USUŃ", key=f"del_inc_{i}", type="primary", use_container_width=True):
                    df_all = df_all.drop(index=i)
                    save_data(df_all, "data")
                    st.rerun()
                # EDYCJA
                if c2.button("✏️ EDYTUJ", key=f"ed_inc_{i}", use_container_width=True):
                    st.session_state[f"edit_mode_{i}"] = True
                
                if st.session_state.get(f"edit_mode_{i}"):
                    new_kw = st.number_input("Nowa kwota", value=float(row['Kwota']), key=f"nk_{i}")
                    new_op = st.text_input("Nowy opis", value=row['Opis'], key=f"no_{i}")
                    if st.button("ZAPISZ ZMIANY", key=f"save_{i}"):
                        df_all.at[i, 'Kwota'] = new_kw
                        df_all.at[i, 'Opis'] = new_op
                        save_data(df_all, "data")
                        del st.session_state[f"edit_mode_{i}"]
                        st.rerun()

        # WYDATKI
        st.markdown("<div style='background-color:#ff4b4b; color:white;' class='section-header'>💸 Wydatki</div>", unsafe_allow_html=True)
        exp_df = df_current[df_current['Typ'] != "Przychod"]
        for i, row in exp_df.sort_index(ascending=False).iterrows():
            with st.expander(f"➖ {row['Kwota']} zł | {row['Opis']} ({row['Typ']})"):
                c1, c2 = st.columns(2)
                # USUWANIE (Naprawione - teraz na pewno usunie z bazy głównej)
                if c1.button("🗑️ USUŃ", key=f"del_exp_{i}", type="primary", use_container_width=True):
                    df_all = df_all.drop(index=i)
                    save_data(df_all, "data")
                    st.rerun()
                # EDYCJA
                if c2.button("✏️ EDYTUJ", key=f"ed_exp_{i}", use_container_width=True):
                    st.session_state[f"edit_mode_{i}"] = True

                if st.session_state.get(f"edit_mode_{i}"):
                    new_kw = st.number_input("Nowa kwota", value=float(row['Kwota']), key=f"nk_{i}")
                    new_op = st.text_input("Nowy opis", value=row['Opis'], key=f"no_{i}")
                    if st.button("ZAPISZ ZMIANY", key=f"save_{i}"):
                        df_all.at[i, 'Kwota'] = new_kw
                        df_all.at[i, 'Opis'] = new_op
                        save_data(df_all, "data")
                        del st.session_state[f"edit_mode_{i}"]
                        st.rerun()

# --- POZOSTAŁE STRONY (UPROSZCZONE DLA CZYTELNOŚCI) ---
elif page == "🛒 Zakupy":
    st.header("🛒 Lista Zakupów")
    # Kod listy zakupów jak poprzednio...
    # (Pamiętaj o dodaniu st.rerun() po usunięciu produktu!)

elif page == "💳 Raty":
    st.header("💳 Raty")
    # Kod rat jak poprzednio...

elif page == "💰 Skarbonki":
    st.header("💰 Skarbonki")
    # Kod skarbonek jak poprzednio...
