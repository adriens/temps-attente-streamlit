import streamlit as st
from streamlit_autorefresh import st_autorefresh
from utils import INTERVALLE_AUTOREFRESH, get_current_time, check_valid_hours, gauge, fetch_communes, fetch_agences, fetch_agence_by_id,fetch_agence_historique
from datetime import timedelta
import altair as alt
import pandas as pd


st.set_page_config(page_title='Temps d\'attente en agence OPT-NC', layout = 'wide', page_icon = 'assets/images/favicon.jpg', initial_sidebar_state = 'auto')

st_autorefresh(interval=INTERVALLE_AUTOREFRESH * 1000, key="dataframerefresh")

current_time = get_current_time().strftime("Nous sommes le %d/%m/%Y et il est %H:%M")
st.markdown(
    f"""
    <h1 style='text-align: center;'>{current_time}</h1>
    """, 
    unsafe_allow_html=True
)

if not check_valid_hours("07:45", "15:30"):
    st.markdown(
    "<h3 style='text-align: center;'>Les agences ne sont ouvertes que du lundi au vendredi de 07:45 à 15:30.</h1>", 
    unsafe_allow_html=True
    )
    st.stop()


# si aucun id n'est passé dans l'url, on ne met rien
selected_commune_param = None
selected_agence_param = None

# Permet de ne charger l'agence mit en query parameters seulement au chargement de la page
if 'page_loaded' not in st.session_state:
    st.session_state.page_loaded = True
    if "idAgence" in st.query_params:
        agence = fetch_agence_by_id(st.query_params["idAgence"])
        selected_commune_param = agence["commune"]
        selected_agence_param = agence["designation"]


# Récupérer les communes (mise en cache)
communes = sorted(fetch_communes())

if communes:
    # menu déroulant pour sélection de commune
    selected_commune = st.sidebar.selectbox(
        "Sélectionnez une commune :",
        communes,
        index=communes.index(selected_commune_param) if selected_commune_param in communes else 0
        )
    
    # Récupérer les agences pour la commune sélectionnée (mise en cache)
    agences = fetch_agences(selected_commune)

    if agences:
        # Extraire le nom de l'agence 
        designation_agences = [agence["designation"] for agence in agences]

        # menu déroulant pour sélection agence
        selected_agence = st.sidebar.selectbox(
            "Sélectionnez une agence :",
            designation_agences,
            index=designation_agences.index(selected_agence_param) if selected_agence_param in designation_agences else 0
            )

        # ajout temps d'attente en texte
        for agence in agences:
            if agence["designation"]==selected_agence:
                temps_attente_agence=(agence["realAvgWaitingTimeMs"])/1000
                st.query_params["idAgence"] = agence["idAgence"]
        
        gauge(round(temps_attente_agence/60))

        st.markdown(
            f"""
            <h1 style='text-align: center;'>{selected_agence}</h1>
            """, 
            unsafe_allow_html=True
        )

        #récuper l'id de l'agence
        id_agence = st.query_params["idAgence"]
        # Début de la journée à 7h45 avec UTC+11 YYYY-MM-DDTHH:MM:SS+HH:MM)
        debut = get_current_time().replace(hour=7, minute=45, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S+11:00")
        #heure de fin = heure actuelle moins un décalage de 11 heures
        fin = get_current_time().strftime("%Y-%m-%dT%H:%M:%S+11:00")
        # Récupérer l'historique de la journée actuelle
        df = fetch_agence_historique(id_agence, debut, fin)
        if not df.empty:
            # couleur selon le temps d'attente
            df['Color'] = pd.cut(
                df['Waiting Time (minutes)'],
                bins=[0, 5, 10, float('inf')],
                labels=['green', 'orange', 'red']
            )
            # création graphique avec couleur 
            chart = alt.Chart(df).mark_bar().encode(
                x=alt.X("Time:T", title="Heures"),
                y=alt.Y("Waiting Time (minutes):Q", title="Temps d'attente (minutes)"),
                color=alt.Color("Color:N", scale=None, legend=None)
            )
            # Afficher l'histogramme
            st.altair_chart(chart, use_container_width=True)
        else:
            st.write("Aucune donnée disponible pour l'historique de l'agence sélectionnée.")

# affichage logos partenaires
st.sidebar.image("assets/images/logo_opt.png", width=250)
st.sidebar.image("assets/images/logo_unc.jpg", width=250)

# Ajout du style et du script pour le tooltip
st.markdown("""
<style>
    [data-testid="stBaseButton-headerNoPadding"]:hover::after {
        content: "Ouvrir / Fermer";
        color: white;
    }
</style>
""", unsafe_allow_html=True)