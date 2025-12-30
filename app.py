import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Nasz Budżet Premium", page_icon="💰", layout="wide")

# --- STYLIZACJA CSS ---
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); border: 1px solid #eee; }
    .header-text { text-align: center; color: #1e1e1e; font-family: 'Segoe UI', sans-serif; }
    .balance-card { background: linear-gradient(135deg, #007bff, #00d4ff); color: white; padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
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
df_all = load_data(BUDGET_FILE, ["Data", "Osoba", "Kategoria", "Typ", "Kwota", "Opis"])
df_shopping = load_data(SHOPPING_FILE, ["Produkt", "Czas"])

# --- NAWIGACJA ---
with st.sidebar:
    st.title("💎 Menu")
    page = st.radio("Wybierz:", ["📊 Portfel & Statystyki", "🛒 Lista Zakupów"])
    st.divider()
    st.write("Witajcie, Piotr i Natalia! 👋")

# --- SEKCJA 1: PORTFEL ---
if page == "📊 Portfel & Statystyki":
    st.markdown("<h1 class='header-text'>💎 Nasz Sejf Finansowy</h1>", unsafe_allow_html=True)
    
    # OBLICZENIA SALDA
    if not df_all.empty:
        dochody = df_all[df_all['Typ'] == "Dochód"]['Kwota'].sum()
        wydatki = df_all[df_all['Typ'] == "Wydatek"]['Kwota'].sum()
    else:
        dochody, wydatki = 0, 0
    saldo = dochody - wydatki

    # PANEL GŁÓWNY (SALDO)
    st.markdown(f"""
        <div class="balance-card">
            <h2 style='margin:0;'>Aktualne Saldo</h2>
            <h1 style='margin:0; font-size: 3em;'>{saldo:,.2f} zł</h1>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1: st.metric("Łączne Dochody", f"{dochody:,.2f} zł", delta_color="normal")
    with col2: st.metric("Łączne Wydatki", f"-{wydatki:,.2f} zł", delta_color="inverse")

    st.divider()

    left, right = st.columns([1, 2])

    with left:
        st.subheader("➕ Nowy Wpis")
        with st.form("finance_form", clear_on_submit=True):
            typ = st.radio("Co dodajemy?", ["Wydatek", "Dochód"])
            data = st.date_input("Data", datetime.now())
            osoba = st.selectbox("Kto?", ["Piotr", "Natalia"])
            
            if typ == "Wydatek":
                kat = st.selectbox("Kategoria", ["🏠 Dom", "🛒 Jedzenie", "🚗 Transport", "🎭 Rozrywka", "✨ Inne"])
            else:
                kat = st.selectbox("Kategoria", ["💰 Wypłata", "🎁 Prezent", "📈 Inne"])
                
            kwota = st.number_input("Kwota (zł)", min_value=0.0)
            opis = st.text_input("Notatka")
            
            if st.form_submit_button("Zatwierdź ✅"):
                new_row = {"Data": str(data), "Osoba": osoba, "Kategoria": kat, "Typ": typ, "Kwota": kwota, "Opis": opis}
                df_all = pd.concat([df_all, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df_all, BUDGET_FILE)
                st.success("Zapisano!")
                st.rerun()

    with right:
        st.subheader("📈 Historia Ruchów")
        if not df_all.empty:
            st.dataframe(df_all.sort_values("Data", ascending=False), use_container_width=True, hide_index=True)
            st.bar_chart(df_all[df_all['Typ'] == "Wydatek"].groupby("Kategoria")["Kwota"].sum())
        else:
            st.info("Brak danych do wyświetlenia.")

# --- SEKCJA 2: LISTA ZAKUPÓW ---
elif page == "🛒 Lista Zakupów":
    st.markdown("<h1 class='header-text'>🛒 Lista Zakupów</h1>", unsafe_allow_html=True)
    with st.container(border=True):
        new_item = st.text_input("Co dopisać?")
        if st.button("Dodaj ➕"):
            if new_item:
                new_entry = {"Produkt": new_item, "Czas": datetime.now().strftime("%d.%m | %H:%M")}
                df_shopping = pd.concat([df_shopping, pd.DataFrame([new_entry])], ignore_index=True)
                save_data(df_shopping, SHOPPING_FILE)
                st.rerun()
    
    for index, row in df_shopping.iterrows():
        c1, c2 = st.columns([4, 1])
        with c1: st.write(f"**{row['Produkt']}** (Dodano: {row['Czas']})")
        with c2: 
            if st.button("✅", key=f"s_{index}"):
                df_shopping = df_shopping.drop(index)
                save_data(df_shopping, SHOPPING_FILE)
                st.rerun()
