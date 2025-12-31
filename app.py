import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar

# --- KONFIGURACJA ---
st.set_page_config(page_title="Budżet Pro Piotr & Natalia", page_icon="🏦", layout="wide")

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
    </style>
    """, unsafe_allow_html=True)

# --- ZARZĄDZANIE DANYMI (Niezawodne ID) ---
FILES = {"data": "budzet_total.json", "shopping": "zakupy_total.json", "raty": "raty_total.json", "sejf": "sejf_total.json"}

def load_data(key):
    if os.path.exists(FILES[key]):
        with open(FILES[key], "r", encoding='utf-8') as f:
            return json.load(f)
    return []

def save_data(data, key):
    with open(FILES[key], "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Inicjalizacja
raw_all = load_data("data")
raw_shop = load_data("shopping")
raw_raty = load_data("raty")
raw_sejf = load_data("sejf") if load_data("sejf") else [{"Suma": 0.0}]

# --- IKONY ZAKUPÓW ---
def get_icon(name):
    icons = {"mleko": "🥛", "ser": "🧀", "masło": "🧈", "chleb": "🍞", "buł": "🥖", "jaj": "🥚", "mięs": "🥩", "szynka": "🍖", "piw": "🍺", "wod": "💧", "sok": "🥤", "kawa": "☕", "herbata": "🍵", "pomid": "🍅", "ogór": "🥒", "ziem": "🥔", "owoc": "🍎", "papie": "🧻", "myd": "🧼", "płyn": "🧴", "pasta": "🪥", "karma": "🐾", "pieluchy": "👶"}
    for k, v in icons.items():
        if k in name.lower(): return v
    return "🛒"

# --- NAWIGACJA ---
with st.sidebar:
    st.title("🏦 Budżet Pro")
    curr_msc = datetime.now().strftime("%Y-%m")
    all_months = sorted(list(set([x['Miesiac_Ref'] for x in raw_all] + [curr_msc])), reverse=True)
    sel_msc = st.selectbox("📅 Wybierz miesiąc", all_months)
    page = st.radio("Menu", ["🏠 Pulpit", "💳 Raty i Stałe", "🛒 Lista Zakupów", "💰 Skarbonki"])

# --- LOGIKA OBLICZEŃ ---
msc_data = [x for x in raw_all if x['Miesiac_Ref'] == sel_msc]
target_dt = datetime.strptime(sel_msc, "%Y-%m").date()

# 800+
dzieci = [date(2018, 8, 1), date(2022, 11, 1)]
auto_800 = sum(800 for d in dzieci if target_dt < d + relativedelta(years=18))

# Raty
raty_msc = 0
for r in raw_raty:
    try:
        s = datetime.strptime(r['Start'], '%Y-%m-%d').date()
        k = datetime.strptime(r['Koniec'], '%Y-%m-%d').date()
        if s.replace(day=1) <= target_dt <= k.replace(day=1):
            raty_msc += r['Kwota']
    except: continue

# Sumy
total_in = sum(x['Kwota'] for x in msc_data if x['Typ'] == "Przychod") + auto_800
total_out = sum(x['Kwota'] for x in msc_data if x['Typ'] != "Przychod") + raty_msc
wolne = total_in - total_out

# Limit dzienny
days_in_m = calendar.monthrange(target_dt.year, target_dt.month)[1]
days_left = (days_in_m - datetime.now().day + 1) if sel_msc == curr_msc else 1
limit_dzienny = wolne / max(days_left, 1)

# --- STRONA 1: PULPIT ---
if page == "🏠 Pulpit":
    c1, c2 = st.columns(2)
    c1.metric("Limit na dziś", f"{max(0, limit_dzienny):,.2f} zł")
    c2.metric("Oszczędności Razem", f"{raw_sejf[0]['Suma'] + sum(x['Kwota'] for x in raw_all if x['Typ'] == 'Fundusze Celowe'):,.2f} zł")

    st.divider()
    col_add, col_list = st.columns([1, 1.5])

    with col_add:
        st.subheader("➕ Dodaj Wpis")
        with st.form("add_form", clear_on_submit=True):
            t = st.selectbox("Typ", ["Wydatki Zmienne", "Stałe Opłaty", "Przychod", "Fundusze Celowe"])
            o = st.selectbox("Kto", ["Piotr", "Natalia"])
            kw = st.number_input("Kwota", min_value=0.0)
            op = st.text_input("Opis")
            if st.form_submit_button("ZAPISZ"):
                raw_all.append({"Id": str(datetime.now().timestamp()), "Data": str(date.today()), "Osoba": o, "Typ": t, "Kwota": kw, "Opis": op, "Miesiac_Ref": sel_msc})
                save_data(raw_all, "data"); st.rerun()

    with col_list:
        # SEKCA WPŁYWÓW
        st.markdown(f"<div class='header-wplywy'>💰 WPŁYWY: {total_in:,.2f} zł</div>", unsafe_allow_html=True)
        if auto_800 > 0: st.info(f"✨ Automatyczne 800+: {auto_800} zł")
        for x in raw_all[::-1]:
            if x['Miesiac_Ref'] == sel_msc and x['Typ'] == "Przychod":
                with st.expander(f"➕ {x['Kwota']} zł | {x['Opis']}"):
                    c1, c2 = st.columns(2)
                    if c1.button("🗑️ Usuń", key=f"del_{x['Id']}"):
                        raw_all = [i for i in raw_all if i['Id'] != x['Id']]
                        save_data(raw_all, "data"); st.rerun()
                    if c2.button("✏️ Edytuj", key=f"ed_{x['Id']}"):
                        st.session_state[f"mode_{x['Id']}"] = True
                    if st.session_state.get(f"mode_{x['Id']}"):
                        new_k = st.number_input("Kwota", value=float(x['Kwota']), key=f"k_{x['Id']}")
                        new_o = st.text_input("Opis", value=x['Opis'], key=f"o_{x['Id']}")
                        if st.button("Zapisz", key=f"s_{x['Id']}"):
                            for item in raw_all:
                                if item['Id'] == x['Id']: item['Kwota'], item['Opis'] = new_k, new_o
                            save_data(raw_all, "data"); del st.session_state[f"mode_{x['Id']}"]; st.rerun()

        # SEKCJA WYDATKÓW
        st.markdown(f"<div class='header-wydatki'>💸 WYDATKI: {total_out:,.2f} zł</div>", unsafe_allow_html=True)
        if raty_msc > 0: st.warning(f"💳 Raty: {raty_msc} zł")
        for x in raw_all[::-1]:
            if x['Miesiac_Ref'] == sel_msc and x['Typ'] != "Przychod":
                with st.expander(f"➖ {x['Kwota']} zł | {x['Opis']} ({x['Typ']})"):
                    c1, c2 = st.columns(2)
                    if c1.button("🗑️ Usuń", key=f"del_{x['Id']}"):
                        raw_all = [i for i in raw_all if i['Id'] != x['Id']]
                        save_data(raw_all, "data"); st.rerun()
                    if c2.button("✏️ Edytuj", key=f"ed_{x['Id']}"):
                        st.session_state[f"mode_{x['Id']}"] = True
                    if st.session_state.get(f"mode_{x['Id']}"):
                        new_k = st.number_input("Kwota", value=float(x['Kwota']), key=f"k_{x['Id']}")
                        new_o = st.text_input("Opis", value=x['Opis'], key=f"o_{x['Id']}")
                        if st.button("Zapisz", key=f"s_{x['Id']}"):
                            for item in raw_all:
                                if item['Id'] == x['Id']: item['Kwota'], item['Opis'] = new_k, new_o
                            save_data(raw_all, "data"); del st.session_state[f"mode_{x['Id']}"]; st.rerun()

# --- STRONA 2: RATY ---
elif page == "💳 Raty i Stałe":
    st.subheader("💳 Harmonogram Rat")
    with st.form("rata_f"):
        n, k = st.text_input("Nazwa raty"), st.number_input("Kwota miesięczna")
        s, e = st.date_input("Start"), st.date_input("Koniec")
        if st.form_submit_button("DODAJ RATĘ"):
            raw_raty.append({"Id": str(datetime.now().timestamp()), "Nazwa": n, "Kwota": k, "Start": str(s), "Koniec": str(e)})
            save_data(raw_raty, "raty"); st.rerun()
    for r in raw_raty:
        st.info(f"📌 **{r['Nazwa']}**: {r['Kwota']} zł (do {r['Koniec']})")
        if st.button("Usuń", key=f"dr_{r['Id']}"):
            raw_raty = [i for i in raw_raty if i['Id'] != r['Id']]
            save_data(raw_raty, "raty"); st.rerun()

# --- STRONA 3: ZAKUPY ---
elif page == "🛒 Lista Zakupów":
    st.subheader("🛒 Zakupy")
    new_p = st.text_input("Co kupić?")
    if st.button("Dodaj ➕"):
        raw_shop.append({"Id": str(datetime.now().timestamp()), "Item": f"{get_icon(new_p)} {new_p}", "Time": datetime.now().strftime("%H:%M")})
        save_data(raw_shop, "shopping"); st.rerun()
    for p in raw_shop:
        c1, c2 = st.columns([5,1])
        c1.markdown(f"<div class='shopping-card'>{p['Item']} <br><small>Dodano: {p['Time']}</small></div>", unsafe_allow_html=True)
        if c2.button("✅", key=p['Id']):
            raw_shop = [i for i in raw_shop if i['Id'] != p['Id']]
            save_data(raw_shop, "shopping"); st.rerun()

# --- STRONA 4: SKARBONKI ---
elif page == "💰 Skarbonki":
    st.subheader("💰 Twój Sejf i Cele")
    nowy_sejf = st.number_input("Sejf Globalny (gotówka/konto)", value=float(raw_sejf[0]['Suma']))
    if st.button("Aktualizuj Sejf"):
        raw_sejf[0]['Suma'] = nowy_sejf
        save_data(raw_sejf, "sejf"); st.rerun()
    
    st.divider()
    cele = {}
    for x in raw_all:
        if x['Typ'] == "Fundusze Celowe":
            cele[x['Opis']] = cele.get(x['Opis'], 0) + x['Kwota']
    for n, k in cele.items():
        st.success(f"📂 {n}: **{k:,.2f} zł**")
