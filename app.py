import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Budżet Pro Piotr & Natalia", page_icon="🏦", layout="wide")

# --- STYLIZACJA ---
st.markdown("""
    <style>
    .main { background-color: #1a1a1a; color: #ffffff; }
    .stMetric { background-color: #262626; padding: 15px; border-radius: 12px; border: 1px solid #444; }
    .limit-box { background-color: #0e1117; border: 2px solid #00d4ff; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .saving-box { background: linear-gradient(135deg, #ffd700, #b8860b); color: black; padding: 20px; border-radius: 15px; text-align: center; font-weight: bold; }
    .section-header { padding: 8px; border-radius: 5px; font-weight: bold; margin-top: 15px; margin-bottom: 5px; text-transform: uppercase; }
    .sub-summary { font-size: 0.95em; font-weight: bold; margin-bottom: 10px; padding: 10px; border-radius: 8px; border-left: 5px solid; }
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

# --- NAWIGACJA ---
with st.sidebar:
    st.title("🏦 Budżet Total Pro")
    obecny_msc_str = datetime.now().strftime("%Y-%m")
    dostepne_miesiace = sorted(list(set(df_all['Miesiac_Ref'].unique().tolist() + [obecny_msc_str])), reverse=True)
    wybrany_msc = st.selectbox("📅 Wybierz miesiąc:", dostepne_miesiace)
    page = st.radio("Menu", ["🏠 Pulpit", "💳 Raty i Stałe", "🛒 Lista Zakupów", "💰 Skarbonki"])
    
    st.divider()
    # Kasa oszczędnościowa = Sejf + Fundusze celowe ze wszystkich miesięcy
    suma_funduszy_all = df_all[df_all['Typ'] == "Fundusze Celowe"]['Kwota'].sum()
    total_sav = df_sejf.iloc[0]['Suma'] + suma_funduszy_all
    st.info(f"Oszczędności: {total_sav:,.2f} zł")

# --- FILTROWANIE ---
df_current = df_all[df_all['Miesiac_Ref'] == wybrany_msc].copy()

# --- LOGIKA AUTOMATYCZNA ---
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

dochody_reczne = df_current[df_current['Typ'] == "Przychod"]['Kwota'].sum()
dochody_razem = dochody_reczne + auto_800

koszty_reczne = df_current[df_current['Typ'] != "Przychod"]['Kwota'].sum()
wydatki_razem = koszty_reczne + raty_val

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
        # --- SEKCJA PRZYCHODÓW ---
        st.markdown("<div style='background-color:#00d4ff; color:black;' class='section-header'>💰 Wpływy i Przychod</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='sub-summary' style='border-color:#00d4ff; background-color:#102030;'>Razem wpływy: {dochody_razem:,.2f} zł</div>", unsafe_allow_html=True)
        
        if auto_800 > 0: st.info(f"✨ Automatyczne 800+: {auto_800:,.2f} zł")
        
        inc_df = df_current[df_current['Typ'] == "Przychod"]
        for i, row in inc_df.sort_index(ascending=False).iterrows():
            with st.expander(f"➕ {row['Kwota']} zł | {row['Opis']} ({row['Czas']})"):
                ec, dc = st.columns(2)
                if dc.button("Usuń", key=f"del_{i}"):
                    df_all = df_all.drop(i); save_data(df_all, "data"); st.rerun()
                if ec.button("Edytuj", key=f"ed_{i}"): st.session_state[f"editing_{i}"] = True
                if st.session_state.get(f"editing_{i}", False):
                    new_kw = st.number_input("Kwota", value=float(row['Kwota']), key=f"k_{i}")
                    new_op = st.text_input("Opis", value=row['Opis'], key=f"o_{i}")
                    if st.button("Zapisz", key=f"s_{i}"):
                        df_all.at[i, 'Kwota'], df_all.at[i, 'Opis'] = new_kw, new_op
                        save_data(df_all, "data"); del st.session_state[f"editing_{i}"]; st.rerun()

        # --- SEKCJA WYDATKÓW ---
        st.markdown("<div style='background-color:#ff4b4b; color:white;' class='section-header'>💸 Wydatki i Koszty</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='sub-summary' style='border-color:#ff4b4b; background-color:#301010;'>Razem wydatki (z ratami): {wydatki_razem:,.2f} zł</div>", unsafe_allow_html=True)
        
        if raty_val > 0: st.warning(f"💳 Aktywne raty w tym msc: {raty_val:,.2f} zł")
        
        exp_df = df_current[df_current['Typ'] != "Przychod"]
        for i, row in exp_df.sort_index(ascending=False).iterrows():
            with st.expander(f"➖ {row['Kwota']} zł | {row['Opis']} ({row['Typ']})"):
                ec, dc = st.columns(2)
                if dc.button("Usuń", key=f"del_{i}"):
                    df_all = df_all.drop(i); save_data(df_all, "data"); st.rerun()
                if ec.button("Edytuj", key=f"ed_{i}"): st.session_state[f"editing_{i}"] = True
                if st.session_state.get(f"editing_{i}", False):
                    new_kw = st.number_input("Kwota", value=float(row['Kwota']), key=f"k_{i}")
                    new_op = st.text_input("Opis", value=row['Opis'], key=f"o_{i}")
                    if st.button("Zapisz", key=f"s_{i}"):
                        df_all.at[i, 'Kwota'], df_all.at[i, 'Opis'] = new_kw, new_op
                        save_data(df_all, "data"); del st.session_state[f"editing_{i}"]; st.rerun()

# --- STRONA 2: RATY I STAŁE ---
elif page == "💳 Raty i Stałe":
    st.header("💳 Zarządzanie Ratami")
    with st.form("add_rata"):
        n, kw = st.text_input("Nazwa raty"), st.number_input("Kwota miesięczna", min_value=0.0)
        s, k = st.date_input("Start spłaty"), st.date_input("Koniec spłaty")
        if st.form_submit_button("DODAJ RATĘ"):
            df_raty = pd.concat([df_raty, pd.DataFrame([{"Nazwa": n, "Kwota": kw, "Start": str(s), "Koniec": str(k)}])], ignore_index=True)
            save_data(df_raty, "raty"); st.rerun()
    
    st.divider()
    for i, r in df_raty.iterrows():
        with st.expander(f"Rata: {r['Nazwa']} | {r['Kwota']} zł | Zakres: {r['Start']} do {r['Koniec']}"):
            ec, dc = st.columns(2)
            if dc.button("Usuń ratę", key=f"dr_{i}"):
                df_raty = df_raty.drop(i); save_data(df_raty, "raty"); st.rerun()
            if ec.button("Edytuj", key=f"er_{i}"): st.session_state[f"edr_{i}"] = True
            if st.session_state.get(f"edr_{i}", False):
                new_n = st.text_input("Nazwa", value=r['Nazwa'], key=f"rn_{i}")
                new_kw = st.number_input("Kwota", value=float(r['Kwota']), key=f"rk_{i}")
                new_s = st.date_input("Start", value=datetime.strptime(r['Start'], '%Y-%m-%d').date(), key=f"rs_{i}")
                new_k = st.date_input("Koniec", value=datetime.strptime(r['Koniec'], '%Y-%m-%d').date(), key=f"re_{i}")
                if st.button("Zapisz zmiany", key=f"rb_{i}"):
                    df_raty.loc[i] = [new_n, new_kw, str(new_s), str(new_k)]
                    save_data(df_raty, "raty"); del st.session_state[f"edr_{i}"]; st.rerun()

# --- POZOSTAŁE STRONY ---
elif page == "🛒 Lista Zakupów":
    st.header("🛒 Zakupy")
    p = st.text_input("Dodaj produkt...")
    if st.button("Dodaj"):
        df_s = pd.concat([df_s, pd.DataFrame([{"Produkt": p, "Czas": datetime.now().strftime("%Y-%m-%d %H:%M")}])], ignore_index=True)
        save_data(df_s, "shopping"); st.rerun()
    st.divider()
    for i, row in df_s.iterrows():
        c1, c2 = st.columns([4,1]); c1.write(f"🔹 {row['Produkt']} ({row['Czas']})")
        if c2.button("✅ Kupione", key=i): df_s = df_s.drop(i); save_data(df_s, "shopping"); st.rerun()

elif page == "💰 Skarbonki":
    st.header("💰 Twoje Skarbonki")
    st.metric("ŁĄCZNIE W SEJFIE", f"{total_sav:,.2f} zł")
    sk = df_all[df_all['Typ'] == "Fundusze Celowe"].groupby("Opis")["Kwota"].sum().reset_index()
    for _, s in sk.iterrows(): st.success(f"**{s['Opis']}**: {s['Kwota']:,.2f} zł")
