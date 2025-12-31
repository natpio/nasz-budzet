import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Budżet Pro - Pełna Kontrola", page_icon="🏦", layout="wide")

# --- STYLIZACJA (WYSOKI KONTRAST) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1c1f26; padding: 15px; border-radius: 12px; border: 1px solid #444; }
    .header-wplywy { background-color: #00d4ff; color: black; padding: 12px; border-radius: 8px; font-weight: bold; text-transform: uppercase; margin-top: 10px; }
    .header-wydatki { background-color: #ff4b4b; color: white; padding: 12px; border-radius: 8px; font-weight: bold; text-transform: uppercase; margin-top: 10px; }
    .stExpander { border: 1px solid #555 !important; background-color: #1c1f26 !important; margin-bottom: 8px !important; }
    div[data-testid="stExpander"] p { color: white !important; font-size: 1.1em; font-weight: bold; }
    .shopping-card { background-color: #1c1f26; padding: 15px; border-radius: 10px; border-left: 5px solid #00ff88; margin-bottom: 10px; color: white !important; font-weight: bold; }
    .minus-alert { background-color: #3e0b0b; border: 2px solid #ff4b4b; padding: 15px; border-radius: 10px; color: white; text-align: center; font-weight: bold; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# --- ZARZĄDZANIE DANYMI ---
FILES = {
    "data": "budzet_dynamiczny.json", 
    "shopping": "zakupy_total.json", 
    "raty": "raty_total.json", 
    "sejf": "sejf_total.json", 
    "config": "budzet_config.json"
}

def load_data(key):
    if os.path.exists(FILES[key]):
        with open(FILES[key], "r", encoding='utf-8') as f:
            return json.load(f)
    if key == "config": return {"current_period": datetime.now().strftime("%Y-%m-%d")}
    return []

def save_data(data, key):
    with open(FILES[key], "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Inicjalizacja baz danych
raw_all = load_data("data")
raw_shop = load_data("shopping")
raw_raty = load_data("raty")
raw_sejf = load_data("sejf") if load_data("sejf") else [{"Suma": 0.0}]
config = load_data("config")

# --- IKONY ZAKUPÓW ---
def get_icon(name):
    icons = {"mleko": "🥛", "ser": "🧀", "masło": "🧈", "chleb": "🍞", "buł": "🥖", "jaj": "🥚", "mięs": "🥩", "szynka": "🍖", "piw": "🍺", "wod": "💧", "sok": "🥤", "kawa": "☕", "herbata": "🍵", "pomid": "🍅", "ogór": "🥒", "ziem": "🥔", "owoc": "🍎", "papie": "🧻", "myd": "🧼", "pasta": "🪥", "karma": "🐾", "pieluchy": "👶"}
    for k, v in icons.items():
        if k in name.lower(): return v
    return "🛒"

# --- NAWIGACJA ---
with st.sidebar:
    st.title("🏦 Budżet Piotr & Natalia")
    all_periods = sorted(list(set([x['Okres_Ref'] for x in raw_all] + [config['current_period']])), reverse=True)
    sel_period = st.selectbox("📅 Okres budżetowy (od wypłaty)", all_periods)
    page = st.radio("Menu", ["🏠 Pulpit", "💳 Raty i Stałe", "🛒 Lista Zakupów", "💰 Skarbonki", "⚙️ Zamknij Okres"])
    st.divider()
    st.info(f"Obecnie zarządzasz budżetem od: {sel_period}")

# --- LOGIKA OBLICZEŃ ---
msc_data = [x for x in raw_all if x['Okres_Ref'] == sel_period]
period_start_dt = datetime.strptime(sel_period, "%Y-%m-%d").date()

# Automatyczne 800+ i Raty
auto_800 = sum(800 for d in [date(2018, 8, 1), date(2022, 11, 1)] if period_start_dt < d + relativedelta(years=18))
raty_val = sum(r['Kwota'] for r in raw_raty if datetime.strptime(r['Start'], '%Y-%m-%d').date() <= period_start_dt <= datetime.strptime(r['Koniec'], '%Y-%m-%d').date())

total_in = sum(x['Kwota'] for x in msc_data if x['Typ'] == "Przychod") + auto_800
total_out = sum(x['Kwota'] for x in msc_data if x['Typ'] != "Przychod") + raty_val
wolne = total_in - total_out

# --- STRONA 1: PULPIT ---
if page == "🏠 Pulpit":
    if wolne < 0:
        st.markdown(f"<div class='minus-alert'>🚨 UWAGA: Brakuje {abs(wolne):,.2f} zł do zamknięcia budżetu!</div>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1: st.metric("Saldo do wypłaty", f"{wolne:,.2f} zł", delta=f"In: {total_in:,.0f} | Out: {total_out:,.0f}")
    with c2: st.metric("Sejf (Nienaruszalny)", f"{raw_sejf[0]['Suma']:,.2f} zł")

    st.divider()
    col_add, col_list = st.columns([1, 1.5])

    with col_add:
        st.markdown("<div class='header-wplywy' style='background-color:#00ff88'>➕ DODAJ WPIS</div>", unsafe_allow_html=True)
        with st.form("entry_form", clear_on_submit=True):
            t = st.selectbox("Typ", ["Wydatki Zmienne", "Stałe Opłaty", "Przychod", "Fundusze Celowe"])
            o = st.selectbox("Kto", ["Piotr", "Natalia"])
            kw = st.number_input("Kwota", min_value=0.0)
            op = st.text_input("Opis")
            if st.form_submit_button("ZAPISZ DO HISTORII"):
                raw_all.append({"Id": str(datetime.now().timestamp()), "Data": str(date.today()), "Osoba": o, "Typ": t, "Kwota": kw, "Opis": op, "Okres_Ref": sel_period})
                save_data(raw_all, "data"); st.rerun()

    with col_list:
        # WPŁYWY
        st.markdown(f"<div class='header-wplywy'>💰 WPŁYWY</div>", unsafe_allow_html=True)
        if auto_800 > 0: st.info(f"✨ Automatyczne 800+: {auto_800} zł")
        for x in raw_all[::-1]:
            if x['Okres_Ref'] == sel_period and x['Typ'] == "Przychod":
                with st.expander(f"➕ {x['Kwota']} zł | {x['Opis']}"):
                    c1, c2 = st.columns(2)
                    if c1.button("🗑️ Usuń", key=f"del_{x['Id']}"):
                        raw_all = [i for i in raw_all if i['Id'] != x['Id']]; save_data(raw_all, "data"); st.rerun()
                    if c2.button("✏️ Edytuj", key=f"ed_{x['Id']}"): st.session_state[f"mode_{x['Id']}"] = True
                    if st.session_state.get(f"mode_{x['Id']}"):
                        new_k = st.number_input("Kwota", value=float(x['Kwota']), key=f"k_{x['Id']}")
                        new_o = st.text_input("Opis", value=x['Opis'], key=f"o_{x['Id']}")
                        if st.button("Zapisz", key=f"s_{x['Id']}"):
                            for i in raw_all:
                                if i['Id'] == x['Id']: i['Kwota'], i['Opis'] = new_k, new_o
                            save_data(raw_all, "data"); del st.session_state[f"mode_{x['Id']}"]; st.rerun()

        # WYDATKI
        st.markdown(f"<div class='header-wydatki'>💸 WYDATKI</div>", unsafe_allow_html=True)
        if raty_val > 0: st.warning(f"💳 Aktywne raty: {raty_val} zł")
        for x in raw_all[::-1]:
            if x['Okres_Ref'] == sel_period and x['Typ'] != "Przychod":
                with st.expander(f"➖ {x['Kwota']} zł | {x['Opis']} ({x['Typ']})"):
                    c1, c2 = st.columns(2)
                    if c1.button("🗑️ Usuń", key=f"del_{x['Id']}"):
                        raw_all = [i for i in raw_all if i['Id'] != x['Id']]; save_data(raw_all, "data"); st.rerun()
                    if c2.button("✏️ Edytuj", key=f"ed_{x['Id']}"): st.session_state[f"mode_{x['Id']}"] = True
                    if st.session_state.get(f"mode_{x['Id']}"):
                        new_k = st.number_input("Kwota", value=float(x['Kwota']), key=f"k_{x['Id']}")
                        new_o = st.text_input("Opis", value=x['Opis'], key=f"o_{x['Id']}")
                        if st.button("Zapisz", key=f"s_{x['Id']}"):
                            for i in raw_all:
                                if i['Id'] == x['Id']: i['Kwota'], i['Opis'] = new_k, new_o
                            save_data(raw_all, "data"); del st.session_state[f"mode_{x['Id']}"]; st.rerun()

# --- STRONA 2: RATY ---
elif page == "💳 Raty i Stałe":
    st.header("💳 Twoje Raty")
    with st.form("rata_f"):
        n, k = st.text_input("Nazwa zobowiązania"), st.number_input("Kwota miesięczna", min_value=0.0)
        s, e = st.date_input("Kiedy startuje?"), st.date_input("Kiedy koniec?")
        if st.form_submit_button("DODAJ RATĘ"):
            raw_raty.append({"Id": str(datetime.now().timestamp()), "Nazwa": n, "Kwota": k, "Start": str(s), "Koniec": str(e)})
            save_data(raw_raty, "raty"); st.rerun()
    st.divider()
    for r in raw_raty:
        with st.container():
            st.info(f"📌 **{r['Nazwa']}**: {r['Kwota']} zł (od {r['Start']} do {r['Koniec']})")
            if st.button("Usuń tę ratę", key=f"dr_{r['Id']}"):
                raw_raty = [i for i in raw_raty if i['Id'] != r['Id']]; save_data(raw_raty, "raty"); st.rerun()

# --- STRONA 3: ZAKUPY ---
elif page == "🛒 Lista Zakupów":
    st.header("🛒 Co kupić?")
    new_p = st.text_input("Dodaj produkt na listę...")
    if st.button("Dopisz ➕"):
        if new_p:
            raw_shop.append({"Id": str(datetime.now().timestamp()), "Item": f"{get_icon(new_p)} {new_p}", "Time": datetime.now().strftime("%H:%M")})
            save_data(raw_shop, "shopping"); st.rerun()
    st.divider()
    for p in raw_shop:
        c1, c2 = st.columns([5,1])
        c1.markdown(f"<div class='shopping-card'>{p['Item']} <br><small>Dodano: {p['Time']}</small></div>", unsafe_allow_html=True)
        if c2.button("✅", key=p['Id']):
            raw_shop = [i for i in raw_shop if i['Id'] != p['Id']]; save_data(raw_shop, "shopping"); st.rerun()

# --- STRONA 4: SKARBONKI ---
elif page == "💰 Skarbonki":
    st.header("💰 Sejf i Oszczędności")
    st.markdown("### Stan Sejfu Globalnego")
    nowy_sejf = st.number_input("Wpisz stan oszczędności (ręcznie)", value=float(raw_sejf[0]['Suma']))
    if st.button("Zaktualizuj Sejf"):
        raw_sejf[0]['Suma'] = nowy_sejf; save_data(raw_sejf, "sejf"); st.success("Sejf zaktualizowany!"); st.rerun()
    
    st.divider()
    st.markdown("### Fundusze Celowe")
    cele = {}
    for x in raw_all:
        if x['Typ'] == "Fundusze Celowe":
            cele[x['Opis']] = cele.get(x['Opis'], 0) + x['Kwota']
    if cele:
        for n, k in cele.items(): st.success(f"📂 {n}: **{k:,.2f} zł**")
    else: st.write("Brak funduszy celowych w historii.")

# --- STRONA 5: ZAMKNIJ OKRES ---
elif page == "⚙️ Zamknij Okres":
    st.header("🏁 Zamknięcie okresu wypłatowego")
    st.write(f"Zamykasz okres rozpoczęty: **{config['current_period']}**")
    st.write(f"Saldo końcowe: **{wolne:,.2f} zł**")
    
    st.warning("Pamiętaj: Zamknięcie okresu tylko czyści historię na Pulpicie. Sejf NIE zostanie naruszony bez Twojej zgody.")
    
    if st.button("ZAMKNIJ I ZACZNIJ NOWĄ WYPŁATĘ"):
        new_start = str(date.today())
        config['current_period'] = new_start
        save_data(config, "config")
        st.success(f"Okres zamknięty! Nowy startuje z datą {new_start}")
        st.rerun()
