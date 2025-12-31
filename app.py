import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Nasz Budżet v6.1 - High Contrast", page_icon="🏦", layout="wide")

# --- STYLIZACJA (POPRAWIONY KONTRAST) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1c1f26; padding: 15px; border-radius: 12px; border: 1px solid #444; color: #ffffff; }
    
    /* Główne boksy z limitami */
    .limit-box { background-color: #000000; border: 2px solid #00d4ff; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .limit-box h1 { color: #ffffff !important; }
    
    .saving-box { background: linear-gradient(135deg, #ffd700, #b8860b); color: #000000 !important; padding: 20px; border-radius: 15px; text-align: center; font-weight: bold; }
    .saving-box h1 { color: #000000 !important; }

    /* Nagłówki sekcji */
    .section-header { padding: 10px; border-radius: 8px; font-weight: bold; margin-top: 15px; margin-bottom: 8px; text-transform: uppercase; font-size: 1.1em; }
    
    /* Podsumowania nad listami */
    .sub-summary { font-size: 1.05em; font-weight: bold; margin-bottom: 12px; padding: 12px; border-radius: 10px; border: 1px solid #555; color: #ffffff !important; }

    /* Kafelki wpisów w historii i zakupach - MAKSYMALNY KONTRAST */
    .stExpander { border: 1px solid #444 !important; background-color: #1c1f26 !important; border-radius: 8px !important; margin-bottom: 5px !important; }
    .stExpander p, .stExpander span, .stExpander label { color: #ffffff !important; font-weight: 500; }
    
    .shopping-item { background-color: #1c1f26; padding: 15px; border-radius: 10px; border: 1px solid #00ff88; margin-bottom: 10px; color: #ffffff !important; font-size: 1.1em; font-weight: bold; }
    .shopping-time { color: #00ff88; font-size: 0.75em; font-weight: normal; }
    
    /* Naprawa szarego tekstu w Streamlit */
    div[data-testid="stExpander"] p { color: white !important; font-size: 1.05em; }
    small { color: #cccccc !important; }
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

# --- FUNKCJA IKON DLA ZAKUPÓW ---
def pobierz_ikone(produkt):
    p = produkt.lower()
    ikony = {
        "mleko": "🥛", "ser": "🧀", "masło": "🧈", "jajka": "🥚", "chleb": "🍞", "bułki": "🥖",
        "szynka": "🥩", "mięso": "🍖", "kurczak": "🍗", "ryba": "🐟", "parówki": "🌭",
        "pomidor": "🍅", "ogórek": "🥒", "ziemniaki": "🥔", "marchew": "🥕", "cebula": "🧅", "czosnek": "🧄",
        "jabłka": "🍎", "banany": "🍌", "cytryna": "🍋", "owoce": "🍉",
        "woda": "💧", "sok": "🥤", "piwo": "🍺", "wino": "🍷", "kawa": "☕", "herbata": "🍵",
        "papier": "🧻", "mydło": "🧼", "płyn": "🧴", "proszek": "🧺", "pasta": "🪥",
        "słodycze": "🍬", "czekolada": "🍫", "chipsy": "🍿", "lody": "🍦",
        "karma": "🐾", "pies": "🐶", "kot": "🐱", "pieluchy": "👶"
    }
    for klucz, emoji in ikony.items():
        if klucz in p: return emoji
    return "🛒"

# Inicjalizacja danych
df_all = load_data("data", ["Data", "Czas", "Osoba", "Typ", "Kwota", "Opis", "Miesiac_Ref"])
df_s = load_data("shopping", ["Produkt", "Czas"])
df_raty = load_data("raty", ["Nazwa", "Kwota", "Start", "Koniec"])
df_sejf = load_data("sejf", ["Suma"])

if df_sejf.empty: df_sejf = pd.DataFrame([{"Suma": 0.0}])

# --- NAWIGACJA ---
with st.sidebar:
    st.title("🏦 Budżet Total Pro")
    obecny_msc_str = datetime.now().strftime("%Y-%m")
    dostepne_miesiace = sorted(list(set(df_all['Miesiac_Ref'].unique().tolist() + [obecny_msc_str])), reverse=True)
    wybrany_msc = st.selectbox("📅 Wybierz miesiąc:", dostepne_miesiace)
    page = st.radio("Menu", ["🏠 Pulpit", "💳 Raty i Stałe", "🛒 Lista Zakupów", "💰 Skarbonki"])
    st.divider()
    total_sav = df_sejf.iloc[0]['Suma'] + df_all[df_all['Typ'] == "Fundusze Celowe"]['Kwota'].sum()
    st.info(f"Oszczędności: {total_sav:,.2f} zł")

# --- FILTROWANIE I LOGIKA ---
df_current = df_all[df_all['Miesiac_Ref'] == wybrany_msc].copy()

def get_auto_income():
    target_date = datetime.strptime(wybrany_msc, "%Y-%m").date()
    dzieci = [date(2018, 8, 1), date(2022, 11, 1)]
    return sum(800 for u in dzieci if target_date < u + relativedelta(years=18))

def get_active_raty():
    target_date = datetime.strptime(wybrany_msc, "%Y-%m").date()
    suma = 0
    if not df_raty.empty:
        for _, r in df_raty.iterrows():
            start = datetime.strptime(r['Start'], '%Y-%m-%d').date()
            koniec = datetime.strptime(r['Koniec'], '%Y-%m-%d').date()
            if start.replace(day=1) <= target_date <= koniec.replace(day=1):
                suma += r['Kwota']
    return suma

auto_800 = get_auto_income()
raty_val = get_active_raty()

# OBLICZENIA
dzis_dt = datetime.now()
rok_sel, msc_sel = map(int, wybrany_msc.split("-"))
dni_w_msc = calendar.monthrange(rok_sel, msc_sel)[1]
dni_do_konca = (dni_w_msc - dzis_dt.day + 1) if wybrany_msc == dzis_dt.strftime("%Y-%m") else 1

dochody_razem = df_current[df_current['Typ'] == "Przychod"]['Kwota'].sum() + auto_800
wydatki_razem = df_current[df_current['Typ'] != "Przychod"]['Kwota'].sum() + raty_val
wolne_srodki = dochody_razem - wydatki_razem
limit_dzienny = wolne_srodki / dni_do_konca if dni_do_konca > 0 else 0

# --- STRONA 1: PULPIT ---
if page == "🏠 Pulpit":
    c1, c2 = st.columns(2)
    with c1: st.markdown(f'<div class="limit-box"><p style="color:#00d4ff;">Limit na dziś:</p><h1>{max(0, limit_dzienny):,.2f} zł</h1></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="saving-box"><p>SEJF GLOBALNY:</p><h1>{total_sav:,.2f} zł</h1></div>', unsafe_allow_html=True)

    st.divider()
    col_add, col_hist = st.columns([1, 1.5])
    
    with col_add:
        st.markdown("<div style='background-color:#00ff88; color:black;' class='section-header'>➕ Dodaj Wpis</div>", unsafe_allow_html=True)
        with st.form("new_entry_form", clear_on_submit=True):
            t = st.selectbox("Typ", ["Wydatki Zmienne", "Stałe Opłaty", "Przychod", "Fundusze Celowe"])
            o = st.selectbox("Kto?", ["Piotr", "Natalia"])
            kw = st.number_input("Kwota", min_value=0.0)
            op = st.text_input("Opis")
            if st.form_submit_button("ZAPISZ"):
                now = datetime.now()
                new_row = {"Data": str(now.date()), "Czas": now.strftime("%H:%M"), "Osoba": o, "Typ": t, "Kwota": kw, "Opis": op, "Miesiac_Ref": wybrany_msc}
                df_all = pd.concat([df_all, pd.DataFrame([new_row])], ignore_index=True)
                save_data(df_all, "data"); st.rerun()

    with col_hist:
        # PRZYCHODY
        st.markdown("<div style='background-color:#00d4ff; color:black;' class='section-header'>💰 Wpływy</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='sub-summary' style='border-color:#00d4ff; background-color:#102030;'>SUMA: {dochody_razem:,.2f} zł</div>", unsafe_allow_html=True)
        
        inc_df = df_current[df_current['Typ'] == "Przychod"]
        for i, row in inc_df.sort_index(ascending=False).iterrows():
            with st.expander(f"➕ {row['Kwota']} zł | {row['Opis']}"):
                ec, dc = st.columns(2)
                if dc.button("Usuń", key=f"d_{i}"):
                    df_all = df_all.drop(i); save_data(df_all, "data"); st.rerun()
                if ec.button("Edytuj", key=f"e_{i}"): st.session_state[f"ed_{i}"] = True
                if st.session_state.get(f"ed_{i}", False):
                    n_kw = st.number_input("Kwota", value=float(row['Kwota']), key=f"nk_{i}")
                    n_op = st.text_input("Opis", value=row['Opis'], key=f"no_{i}")
                    if st.button("Zapisz", key=f"s_{i}"):
                        df_all.at[i, 'Kwota'], df_all.at[i, 'Opis'] = n_kw, n_op
                        save_data(df_all, "data"); del st.session_state[f"ed_{i}"]; st.rerun()

        # WYDATKI
        st.markdown("<div style='background-color:#ff4b4b; color:white;' class='section-header'>💸 Wydatki</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='sub-summary' style='border-color:#ff4b4b; background-color:#301010;'>SUMA (z ratami): {wydatki_razem:,.2f} zł</div>", unsafe_allow_html=True)
        
        exp_df = df_current[df_current['Typ'] != "Przychod"]
        for i, row in exp_df.sort_index(ascending=False).iterrows():
            with st.expander(f"➖ {row['Kwota']} zł | {row['Opis']} ({row['Typ']})"):
                ec, dc = st.columns(2)
                if dc.button("Usuń", key=f"d_{i}"):
                    df_all = df_all.drop(i); save_data(df_all, "data"); st.rerun()
                if ec.button("Edytuj", key=f"e_{i}"): st.session_state[f"ed_{i}"] = True
                if st.session_state.get(f"ed_{i}", False):
                    n_kw = st.number_input("Kwota", value=float(row['Kwota']), key=f"nk_{i}")
                    n_op = st.text_input("Opis", value=row['Opis'], key=f"no_{i}")
                    if st.button("Zapisz", key=f"s_{i}"):
                        df_all.at[i, 'Kwota'], df_all.at[i, 'Opis'] = n_kw, n_op
                        save_data(df_all, "data"); del st.session_state[f"ed_{i}"]; st.rerun()

# --- STRONA 3: ZAKUPY ---
elif page == "🛒 Lista Zakupów":
    st.header("🛒 Lista Zakupów")
    p_in = st.text_input("Co kupić?", placeholder="np. mleko, chleb...")
    if st.button("Dodaj do listy ➕", use_container_width=True):
        if p_in:
            ikona = pobierz_ikone(p_in)
            df_s = pd.concat([df_s, pd.DataFrame([{"Produkt": f"{ikona} {p_in}", "Czas": datetime.now().strftime("%Y-%m-%d %H:%M")}])], ignore_index=True)
            save_data(df_s, "shopping"); st.rerun()
    st.divider()
    for i, row in df_s.iterrows():
        c1, c2 = st.columns([5,1])
        with c1: st.markdown(f"<div class='shopping-item'>{row['Produkt']}<br><span class='shopping-time'>Dodano: {row['Czas']}</span></div>", unsafe_allow_html=True)
        if c2.button("✅", key=f"c_{i}"):
            df_s = df_s.drop(i); save_data(df_s, "shopping"); st.rerun()

# --- STRONY RATY I SKARBONKI (Analogicznie poprawione style) ---
elif page == "💳 Raty i Stałe":
    st.header("💳 Raty")
    # Kod zarządzania ratami (zgodny z poprzednim)
    for i, r in df_raty.iterrows():
        with st.expander(f"Rata: {r['Nazwa']} | {r['Kwota']} zł"):
            st.write(f"Koniec spłaty: {r['Koniec']}")
            if st.button("Usuń", key=f"dr_{i}"):
                df_raty = df_raty.drop(i); save_data(df_raty, "raty"); st.rerun()

elif page == "💰 Skarbonki":
    st.header("💰 Oszczędności")
    st.metric("SEJF GLOBALNY", f"{total_sav:,.2f} zł")
    sk = df_all[df_all['Typ'] == "Fundusze Celowe"].groupby("Opis")["Kwota"].sum().reset_index()
    for _, s in sk.iterrows(): st.success(f"**{s['Opis']}**: {s['Kwota']:,.2f} zł")
