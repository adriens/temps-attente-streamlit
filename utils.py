import streamlit as st
from datetime import datetime
import os
from dotenv import load_dotenv
import pytz
import plotly.graph_objects as go
import requests
import pandas as pd

INTERVALLE_AUTOREFRESH = 3 * 60 # 3 minutes
API_TEMPS_ATTENTE_BASE_URL = "https://api.opt.nc/temps-attente-agences/"
API_TEMPS_ATTENTE_BASE_URL_RAPIDAPI = "https://temps-attente-en-agence.p.rapidapi.com/"

# Obtenir la datetime dans le fuseau horaire de NC
def get_current_time():
    ncl_tz = pytz.timezone('Pacific/Noumea')
    ncl_time = datetime.now(ncl_tz)
    return ncl_time

def check_valid_hours(start, end):
    current_weekday = get_current_time().weekday()
    # Vérifier si c'est un samedi ou un dimanche
    if current_weekday in (5, 6):  # 5 = samedi, 6 = dimanche
        return False
    start_time = datetime.strptime(start, "%H:%M").time()
    end_time = datetime.strptime(end, "%H:%M").time()
    
    current_time = get_current_time().time()
    if start_time <= current_time <= end_time:
        return True
    else:
        return False

def load_apikey():
    # Charger le fichier .env
    load_dotenv()
    return os.getenv("OPTNC_WAITINGTIME_APIKEY")

def load_apikey_rapidapi():
    load_dotenv()
    return os.getenv("OPTNC_WAITINGTIME_APIKEY_RAPIDAPI")

def gauge(temps_attente):
    plage_temps = [5, 10, 15]
    plage_couleurs = ["green", "orange", "red"]

    # Déterminer la couleur basée sur le temps d'attente
    if temps_attente <= plage_temps[0]:
        color = plage_couleurs[0]
    elif temps_attente <= plage_temps[1]:
        color = plage_couleurs[1]
    else:
        color = plage_couleurs[2]

    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = temps_attente,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Temps d'attente (minutes)"},
        gauge={
            'axis': {'range': [0, 15]},  # Plage de l'axe
            'bar': {'color': color},  # Couleur de la barre selon la plage
        }
    ))

    st.plotly_chart(fig)

APIKEY = load_apikey()
headers = {
    "x-apikey": APIKEY,
    "Content-Type": "application/json"
}
APIKEY_RAPIDAPI = load_apikey_rapidapi()
headers_rapidapi = {
    "x-rapidapi-host":"temps-attente-en-agence.p.rapidapi.com",
    "x-rapidapi-key": APIKEY_RAPIDAPI
}

# pas de ttl puisqu'on ne l'appel qu'une seule fois
@st.cache_data(show_spinner=False)
def fetch_communes():
    # requête pour récuperer les communes
    response_communes = requests.get(API_TEMPS_ATTENTE_BASE_URL+"communes", headers=headers)
    if response_communes.status_code == 200:
        # liste des communes
        communes = response_communes.json()
        #liste communes en MAJ
        communes_maj = [x.upper() for x in communes]
        return communes_maj
    else:
        st.error(f"Erreur lors de la récupération des communes : {response_communes.status_code}")
        return []

@st.cache_data(ttl=INTERVALLE_AUTOREFRESH, show_spinner=False)
def fetch_agences(commune):
    # requête pour récuperer agences avec la commune sélectionnée
    response_agences = requests.get(API_TEMPS_ATTENTE_BASE_URL+"agences", headers=headers, params={"commune": commune})
    if response_agences.status_code == 200:
        # liste de tout les "bâtiments" OPT
        agences = response_agences.json()
        # récupération des agences OPT
        agences_OPT = []
        for agence in agences:
            if agence["type"] in ["AGENCE", "ANNEXE"]:
                agences_OPT.append(agence)
        return agences_OPT
    else:
        st.error(f"Erreur lors de la récupération des agences : {response_agences.status_code}")
        return []

@st.cache_data(ttl=INTERVALLE_AUTOREFRESH, show_spinner=False)
def fetch_agence_by_id(id_agence):
    response = requests.get(API_TEMPS_ATTENTE_BASE_URL+f"agences/{id_agence}", headers=headers)
    if response.status_code == 200:
        agence = response.json()
        return agence
    else:
        st.error(f"Erreur lors de la récupération de l'agence {id_agence} : {response.status_code}")
        return []

@st.cache_data(ttl=INTERVALLE_AUTOREFRESH, show_spinner=False)
def fetch_agence_historique(id_agence,debut,fin):
    params = {
        "debut": debut,
        "fin": fin
    }
    response = requests.get(API_TEMPS_ATTENTE_BASE_URL_RAPIDAPI + f"agences/{id_agence}/historique", headers=headers_rapidapi, params=params)
    if response.status_code == 200:
        historique = response.json()
        # Récupération des timestamps et des temps d'attente max en minutes
        times = [entry['timestamp'] for entry in historique]
        waiting_times = [entry['realMaxWaitingTimeMs'] / 60000 for entry in historique]  # Convertir en minutes
        # Convertir les timestamps en objets datetime
        times = pd.to_datetime(times, errors='coerce')
        # Ajouter un décalage de +11 heures pour correspondre à UTC+11
        # times = times + pd.Timedelta(hours=11)
        # Créer un DataFrame avec les données
        df = pd.DataFrame({
            "Time": times,
            "Waiting Time (minutes)": waiting_times
        })
        return df
    else:
        st.error(f"Erreur lors de la récupération de l'historique pour l'agence {id_agence} : {response.status_code}")
        return [], []