import streamlit as st
import json
import os
import calendar
from datetime import datetime, date
import pandas as pd

# Konfiguracja strony
st.set_page_config(page_title="Budżet Rodzinny", layout="wide")

class StreamlitBudget:
    def __init__(self):
        self.data_file = "budzet_data.json"
        self.rodzina = {"Laura": 2018, "Zosia": 2022}
        self.load_data()
        
        if 'wybrana_data' not in st.session_state:
            st.session_state.wybrana_data = date.today()

    def load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.dane = json.load(f)
        else:
            self.dane = {"oszczednosci_suma": 0.0, "miesiace": {}, "sub_konta": {}, "cele_meta": {}, "harmonogram_rat": []}
        
        # Uzupełnienie brakujących kluczy
        for key in ["sub_konta", "cele_meta", "harmonogram_rat"]:
            if key not in self.dane: self.dane[key] = {} if key != "harmonogram_rat" else []

    def save_data(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.dane, f, indent=4, ensure_ascii=False)

    def inicjuj_okres(self, okres):
        if okres not in self.dane["miesiace"]:
            rok, mies = map(int, okres.split("-"))
            uprawnione = sum(1 for r in self.rodzina.values() if (rok - r) < 18)
            
            # Kopiowanie kosztów stałych
            poprzedni = date(rok, mies, 1).replace(day=1)
            poprzedni_okres = (poprzedni.replace(month=poprzedni.month-1 if poprzedni.month > 1 else 12, 
                                                 year=poprzedni.year if poprzedni.month > 1 else poprzedni.year-1)).strftime("%Y-%m")
            
            skopiowane = {}
            if poprzedni_okres in self.dane["miesiace"]:
                stare = self.dane["miesiace"][poprzedni_okres].get("oplaty_stale", {})
                skopiowane = {k: v for k, v in stare.items() if not k.startswith("[RATA]")}

            # Dodawanie rat
            curr_date = date(rok, mies, 1)
            for rata in self.dane["harmonogram_rat"]:
                start = datetime.strptime(rata['od'], "%Y-%m").date()
                koniec = datetime.strptime(rata['do'], "%Y-%m").date()
                if start <= curr_date <= koniec:
                    skopiowane[f"[RATA] {rata['nazwa']}"] = rata['kwota']

            self.dane["miesiace"][okres] = {
                "dochody": {"800+": uprawnione * 800},
                "oplaty_stale": skopiowane,
                "okazje": {}, "wydatki_zmienne": {}, "czy_zamkniety": False
            }
            self.save_data()

    def run(self):
        st.title("🏠 Budżet: Piotr & Natalia")
        
        # --- SIDEBAR: SEJF ---
        with st.sidebar:
            st.header("💰 Sejf")
            st.metric("Suma oszczędności", f"{self.dane['oszczednosci_suma']:.2f} zł")
            for k, v in self.dane["sub_konta"].items():
                st.write(f"• {k}: **{v:.2f} zł**")
            
            if st.button("➕ Zarządzaj Sejfem"):
                st.info("Funkcja zarządzania sub-kontami dostępna w panelu edycji.")

        # --- NAWIGACJA DATA ---
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            wybrany_okres = st.date_input("Wybierz miesiąc", st.session_state.wybrana_data)
            okres_str = wybrany_okres.strftime("%Y-%m")
            self.inicjuj_okres(okres_str)
            m_data = self.dane["miesiace"][okres_str]

        # --- STATYSTYKI ---
        tin = sum(m_data["dochody"].values())
        tout = sum(m_data["oplaty_stale"].values()) + sum(m_data["okazje"].values()) + sum(m_data["wydatki_zmienne"].values())
        saldo = tin - tout
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Przychody", f"{tin} zł")
        c2.metric("Wydatki", f"{tout} zł", delta=f"-{tout} zł", delta_color="inverse")
        c3.metric("Zostało", f"{saldo:.2f} zł")

        # --- SEKCJE WYDATKÓW ---
        tab1, tab2, tab3 = st.tabs(["📊 Przegląd", "➕ Dodaj Wydatek", "⚙️ Ustawienia"])
        
        with tab1:
            if m_data["czy_zamkniety"]:
                st.error("Miesiąc jest ZAMKNIĘTY. Aby edytować, użyj przycisku Odblokuj w Ustawieniach.")
            
            col_a, col_b = st.columns(2)
            with col_a:
                st.subheader("Stałe Opłaty")
                st.table(pd.DataFrame(m_data["oplaty_stale"].items(), columns=["Nazwa", "Kwota"]))
            with col_b:
                st.subheader("Wydatki Zmienne")
                st.table(pd.DataFrame(m_data["wydatki_zmienne"].items(), columns=["Nazwa", "Kwota"]))

        with tab2:
            if not m_data["czy_zamkniety"]:
                with st.form("Szybki Dodaj"):
                    kat = st.selectbox("Kategoria", ["wydatki_zmienne", "oplaty_stale", "dochody", "okazje"])
                    nazwa = st.text_input("Nazwa")
                    kwota = st.number_input("Kwota", min_value=0.0)
                    if st.form_submit_button("Zapisz"):
                        m_data[kat][nazwa] = kwota
                        self.save_data()
                        st.rerun()
            else:
                st.write("Odblokuj miesiąc, aby dodać wpis.")

        with tab3:
            if not m_data["czy_zamkniety"]:
                if st.button("🔴 ZAMKNIJ MIESIĄC I PRZELEJ"):
                    self.dane["oszczednosci_suma"] += saldo
                    m_data["czy_zamkniety"] = True
                    self.save_data()
                    st.rerun()
            else:
                if st.button("🔓 ODBLOKUJ MIESIĄC"):
                    self.dane["oszczednosci_suma"] -= saldo
                    m_data["czy_zamkniety"] = False
                    self.save_data()
                    st.rerun()

if __name__ == "__main__":
    app = StreamlitBudget()
    app.run()