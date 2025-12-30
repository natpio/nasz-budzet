import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Nasz Budżet Premium", page_icon="💰", layout="wide")

# --- STYLIZACJA CSS (Efekt Wow) ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #eee; }
    .stButton>button { width: 100%; border-radius: 10px; font-weight: bold; }
    .shopping-item { background-color: #ffffff; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #007bff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .time-text { color: #888; font-size: 0.8em; font-style: italic; }
    .header-text { text-align: center; color: #1e1e1e; font-family: 'Segoe UI', sans-serif; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNKCJE DANYCH ---
BUDGET_FILE = "budzet_data.json"
SHOPPING_FILE = "zakupy_data.json"

def load_data(file, columns):
    if os.path.exists(file):
        try:
            with open(file, "r", encoding='utf-8') as f:
                data = json.load(f)
                return pd.DataFrame(data) if data else pd.DataFrame(columns=columns)
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_data(df, file):
    with open(file, "w", encoding='utf-8') as f:
        json.dump(df.to_dict(orient="records"), f, indent=4, ensure_ascii=False)

# Inicjalizacja danych
df_budget = load_data(BUDGET_FILE, ["Data", "Osoba", "Kategoria", "Kwota", "Opis"])
df_shopping = load_data(SHOPPING_FILE, ["Produkt", "Czas"])

# --- NAWIGACJA (SIDEBAR) ---
with st.sidebar:
    st.title("💎 Panel Sterowania")
    page = st.radio("Dokąd idziemy?", ["💰 Wydatki & Analiza", "🛒 Lista Zakupów"])
    st.markdown("---")
    st.info("Aplikacja Piotra i Natalii v2.0")

# --- SEKCJA 1: WYDATKI & ANALIZA ---
if page == "💰 Wydatki & Analiza":
    st.markdown("<h1 class='header-text'>📊 Nasz Sejf Finansowy</h1>", unsafe_allow_html=True)
    
    # KARTY PODSUMOWANIA
    total_spent = df_budget['Kwota'].sum() if not df_budget.empty else 0
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="Suma Wszystkich Wydatków", value=f"{total_spent:,.2f} zł".replace(',', ' '))
    with col2:
        st.metric(label="Liczba Transakcji", value=len(df_budget))
    with col3:
        top_cat = df_budget['Kategoria'].mode()[0] if not df_budget.empty else "-"
        st.metric(label="Główny Koszt", value=top_cat)

    st.divider()

    # LAYOUT: FORMULARZ + WYKRES
    left, right = st.columns([1, 2], gap="large")

    with left:
        st.subheader("➕ Dodaj Wydatek")
        with st.form("new_expense", clear_on_submit=True):
            data = st.date_input("Kiedy?", datetime.now())
            osoba = st.selectbox("Kto?", ["Piotr", "Natalia"])
            kat = st.selectbox("Kategoria", ["🏠 Dom", "🛒 Jedzenie", "🚗 Transport", "🎭 Rozrywka", "💊 Zdrowie", "✨ Inne"])
            kwota = st.number_input("Kwota (zł)", min_value=0.0, step=0.01)
            opis = st.text_input("Na co dokładnie?")
            
            if st.form_submit_button("Zapisz w bazie 🔒"):
                new_row = {"Data": str(data), "Osoba": osoba, "Kategoria": kat, "Kwota": kwota, "Opis": opis}
                df_budget = pd.concat([df_budget, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df_budget, BUDGET_FILE)
                st.success("Dodano!")
                st.rerun()

    with right:
        st.subheader("📈 Gdzie uciekają pieniądze?")
        if not df_budget.empty:
            # Wykres
            chart_data = df_budget.groupby("Kategoria")["Kwota"].sum()
            st.bar_chart(chart_data, color="#007bff")
            
            # Tabela
            st.write("Ostatnie 10 wpisów:")
            st.dataframe(df_budget.sort_values("Data", ascending=False).head(10), use_container_width=True, hide_index=True)
        else:
            st.info("Zacznij dodawać wydatki, aby zobaczyć analizę.")

# --- SEKCJA 2: LISTA ZAKUPÓW ---
elif page == "🛒 Lista Zakupów":
    st.markdown("<h1 class='header-text'>🛒 Wspólna Lista Zakupów</h1>", unsafe_allow_html=True)
    
    # Dodawanie produktu
    c_add, _ = st.columns([2, 1])
    with c_add:
        with st.container(border=True):
            new_item = st.text_input("Co dopisać do listy?", placeholder="np. Mleko 2%, płatki owsiane...")
            if st.button("Dodaj do listy ➕"):
                if new_item:
                    now = datetime.now().strftime("%d.%m | %H:%M")
                    new_entry = {"Produkt": new_item, "Czas": now}
                    df_shopping = pd.concat([df_shopping, pd.DataFrame([new_entry])], ignore_index=True)
                    save_data(df_shopping, SHOPPING_FILE)
                    st.rerun()

    st.markdown("---")
    
    # Wyświetlanie listy produktów
    if df_shopping.empty:
        st.success("Wszystko kupione! Lodówka pełna. 🍏")
    else:
        for index, row in df_shopping.iterrows():
            with st.container():
                # Stylizowany element listy
                st.markdown(f"""
                <div class="shopping-item">
                    <div>
                        <b style="font-size: 1.2em;">{row['Produkt']}</b><br>
                        <span class="time-text">Dodano: {row['Czas']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Przycisk usuwania pod elementem
                if st.button(f"✅ Kupione / Usuń", key=f"del_{index}"):
                    df_shopping = df_shopping.drop(index)
                    save_data(df_shopping, SHOPPING_FILE)
                    st.rerun()
                st.markdown("<br>", unsafe_allow_html=True)

# --- GLOBALNY RESET (W Sidebarku na samym dole) ---
if st.sidebar.button("🗑️ Resetuj Wszystkie Dane"):
    if st.sidebar.checkbox("Tak, chcę wyczyścić wszystko"):
        save_data(pd.DataFrame(columns=["Data", "Osoba", "Kategoria", "Kwota", "Opis"]), BUDGET_FILE)
        save_data(pd.DataFrame(columns=["Produkt", "Czas"]), SHOPPING_FILE)
        st.rerun()
