import streamlit as st
from streamlit_autorefresh import st_autorefresh
from utils import load_apikey, get_current_time, gauge
import requests

st.set_page_config(page_title='Temps d\'attente en agence OPT-NC', layout = 'wide', page_icon = 'assets/images/favicon.jpg', initial_sidebar_state = 'auto')

st_autorefresh(interval=2 * 60 * 1000, key="dataframerefresh")

apikey = load_apikey()
headers = {
    "x-apikey": apikey,
    "Content-Type": "application/json"
}

API_TEMPS_ATTENTE_BASE_URL = "https://api.opt.nc/temps-attente-agences/"

current_time = get_current_time()
st.markdown(
    f"""
    <h1 style='text-align: center;'>{current_time}</h1>
    """, 
    unsafe_allow_html=True
)

# requête pour récuperer les commune
response_communes = requests.get(API_TEMPS_ATTENTE_BASE_URL+"communes", headers=headers)

if response_communes.status_code == 200:
    # liste des communes
    communes = response_communes.json()
    #liste communes en MAJ
    communes_maj = [x.upper() for x in communes]
    # menu déroulant pour sélection de commune
    selected_commune = st.sidebar.selectbox("Sélectionnez une commune :", communes_maj)
    
    # Requête pour récuperer agences avec la commune sélectionner
    response_agences = requests.get(API_TEMPS_ATTENTE_BASE_URL+"agences", headers=headers, params={"commune": selected_commune})

    if response_agences.status_code == 200:
        # liste de tout les "bâtiments" OPT
        agences = response_agences.json()

        agences_OPT = []
        # récupération des agences OPT
        for agence in agences :
            if agence["type"]=="AGENCE" or agence["type"]=="ANNEXE" :
                agences_OPT.append(agence)
   
        # Extraire le nom de l'agence 
        designation_agences = [agence['designation'] for agence in agences_OPT]
        
        # menu déroulant pour sélection agence
        selected_agence = st.sidebar.selectbox("Sélectionnez une agence :", designation_agences)

        # affichage logos partenaires
        st.sidebar.image("assets/images/logo_opt.png", width=250)
        st.sidebar.image("assets/images/logo_unc.jpg", width=250)
        
        # ajout temps d'attente en texte
        for agence in agences_OPT :
            if agence["designation"]==selected_agence:
                temps_attente_agence=(agence["realAvgWaitingTimeMs"])/1000
        
        gauge(round(temps_attente_agence/60))

    else:
        st.write(f"Erreur lors de la récupération des agences : {response_agences.status_code}")
else:
    st.write(f"Erreur lors de la récupération des communes : {response_communes.status_code}")
