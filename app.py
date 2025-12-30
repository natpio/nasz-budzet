import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import calendar

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Nasz Budżet Ultra Pro + Edycja", page_icon="🏦", layout="wide")

# --- STYLIZACJA ---
st.markdown("""
    <style>
    .main { background-color: #1a1a1a; color: #ffffff; }
    .stMetric { background-color: #262626; padding: 15px; border-radius: 12px; border: 1px solid #444; }
    .limit-box { background-color: #0e1117; border: 2px solid #00d4ff; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .saving-box { background: linear-gradient(135deg, #ffd700, #b8860b); color: black; padding: 20px; border-radius: 15px; text-align: center; font-weight: bold; }
    .section-header { padding: 10px; border-radius: 5px; font-weight: bold; margin-bottom: 10px; text-transform: uppercase; }
    .edit-container { background-color: #2b2b2b; padding: 15px; border-radius: 10px; border: 1px solid #ffd700; margin-bottom: 10px; }
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
    
    # Wybór aktywnego miesiąca
    obecny_msc_str = datetime.now().strftime("%Y-%m")
    if not df_all.empty:
        dostepne_miesiace = sorted(list(set(df_all['Miesiac_Ref'].unique().tolist() + [obecny_msc_str])), reverse=True)
    else:
        dostepne_miesiace = [obecny_msc_str]
    
    wybrany_msc = st.selectbox("📅 Przeglądaj miesiąc:", dostepne_miesiace)
    page = st.radio("Menu", ["🏠 Pulpit", "💳 Raty i Stałe", "🛒 Lista Zakupów", "💰 Skarbonki"])
    
    st.divider()
    st.info(f"Oszczędności: {df_sejf.iloc[0]['Suma'] + df_all[df_all['Typ'] == 'Fundusze Celowe']['Kwota'].sum():,.2f} zł")

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

# OBLICZENIA LIMITU
dzis_dt = datetime.now()
rok_sel, msc_sel = map(int, wybrany_msc.split("-"))
dni_w_msc = calendar.monthrange(rok_sel, msc_sel)[1]
dni_do_konca = (dni_w_msc - dzis_dt.day + 1) if wybrany_msc == dzis_dt.strftime("%Y-%m") else 1

dochody = df_current[df_current['Typ'] == "Przychod"]['Kwota'].sum() + auto_800
oplaty = df_current[df_current['Typ'] == "Stałe Opłaty"]['Kwota'].sum() + raty_val
fundusze = df_current[df_current['Typ'] == "Fundusze Celowe"]['Kwota'].sum()
zmienne = df_current[df_current['Typ'] == "Wydatki Zmienne"]['Kwota'].sum()

wolne_srodki = dochody - oplaty - fundusze - zmienne
limit_dzienny = wolne_srodki / dni_do_konca if dni_do_konca > 0 else 0

# --- STRONA 1: PULPIT ---
if page == "🏠 Pulpit":
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f'<div class="limit-box"><p style="color:#00d4ff;">Limit na dziś:</p><h1>{max(0, limit_dzienny):,.2f} zł</h1></div>', unsafe_allow_html=True)
    with c2:
        total_sav = df_sejf.iloc[0]['Suma'] + df_all[df_all['Typ'] == "Fundusze Celowe"]['Kwota'].sum()
        st.markdown(f'<div class="saving-box"><p>SEJF GLOBALNY:</p><h1>{total_sav:,.2f} zł</h1></div>', unsafe_allow_html=True)

    st.divider()
    col_add, col_hist = st.columns([1, 1.5])
    
    with col_add:
        st.markdown("<div style='color:#00ff88;' class='section-header'>➕ Dodaj Wpis</div>", unsafe_allow_html=True)
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
        st.markdown("<div class='section-header'>📜 Historia i Edycja</div>", unsafe_allow_html=True)
        for i, row in df_current.sort_index(ascending=False).iterrows():
            with st.expander(f"{row['Data']} | {row['Opis']} | {row['Kwota']} zł"):
                edit_col, del_col = st.columns(2)
                if del_col.button("Usuń", key=f"del_{i}"):
                    df_all = df_all.drop(i)
                    save_data(df_all, "data"); st.rerun()
                
                if edit_col.button("Edytuj", key=f"edit_btn_{i}"):
                    st.session_state[f"editing_{i}"] = True
                
                if st.session_state.get(f"editing_{i}", False):
                    with st.container(border=True):
                        new_kw = st.number_input("Nowa kwota", value=float(row['Kwota']), key=f"kw_{i}")
                        new_op = st.text_input("Nowy opis", value=row['Opis'], key=f"op_{i}")
                        if st.button("Zapisz zmiany", key=f"save_{i}"):
                            df_all.at[i, 'Kwota'] = new_kw
                            df_all.at[i, 'Opis'] = new_op
                            save_data(df_all, "data")
                            del st.session_state[f"editing_{i}"]
                            st.rerun()

# --- STRONA 2: RATY I STAŁE ---
elif page == "💳 Raty i Stałe":
    st.header("💳 Zarządzanie Ratami")
    with st.form("add_rata"):
        n, kw = st.text_input("Nazwa raty"), st.number_input("Kwota miesięczna", min_value=0.0)
        s, k = st.date_input("Start"), st.date_input("Koniec")
        if st.form_submit_button("DODAJ RATĘ"):
            df_raty = pd.concat([df_raty, pd.DataFrame([{"Nazwa": n, "Kwota": kw, "Start": str(s), "Koniec": str(k)}])], ignore_index=True)
            save_data(df_raty, "raty"); st.rerun()
    
    st.divider()
    for i, r in df_raty.iterrows():
        with st.expander(f"Rata: {r['Nazwa']} - {r['Kwota']} zł"):
            ec, dc = st.columns(2)
            if dc.button("Usuń ratę", key=f"del_r_{i}"):
                df_raty = df_raty.drop(i)
                save_data(df_raty, "raty"); st.rerun()
            
            if ec.button("Edytuj ratę", key=f"ed_r_{i}"):
                st.session_state[f"ed_rata_{i}"] = True
            
            if st.session_state.get(f"ed_rata_{i}", False):
                new_r_kw = st.number_input("Nowa kwota", value=float(r['Kwota']), key=f"r_kw_{i}")
                if st.button("Zaktualizuj", key=f"up_r_{i}"):
                    df_raty.at[i, 'Kwota'] = new_r_kw
                    save_data(df_raty, "raty")
                    del st.session_state[f"ed_rata_{i}"]
                    st.rerun()

# --- STRONA 3: ZAKUPY ---
elif page == "🛒 Lista Zakupów":
    st.header("🛒 Zakupy")
    p = st.text_input("Dopisz...")
    if st.button("Dodaj"):
        df_s = pd.concat([df_s, pd.DataFrame([{"Produkt": p, "Czas": datetime.now().strftime("%Y-%m-%d %H:%M")}])], ignore_index=True)
        save_data(df_s, "shopping"); st.rerun()
    for i, row in df_s.iterrows():
        c1, c2 = st.columns([4,1])
        c1.write(f"🔹 {row['Produkt']} ({row['Czas']})")
        if c2.button("❌", key=i): df_s = df_s.drop(i); save_data(df_s, "shopping"); st.rerun()

# --- STRONA 4: SKARBONKI ---
elif page == "💰 Skarbonki":
    st.header("💰 Oszczędności")
    st.metric("SEJF TOTAL", f"{df_sejf.iloc[0]['Suma'] + df_all[df_all['Typ'] == 'Fundusze Celowe']['Kwota'].sum():,.2f} zł")
    sk = df_all[df_all['Typ'] == "Fundusze Celowe"].groupby("Opis")["Kwota"].sum().reset_index()
    for _, s in sk.iterrows(): st.info(f"**{s['Opis']}**: {s['Kwota']:,.2f} zł")
