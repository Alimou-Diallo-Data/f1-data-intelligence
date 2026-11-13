"""Analyse détaillée d'un Grand Prix."""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from api_jolpica import (
    obtenir_courses,
    obtenir_pitstops,
    obtenir_qualifications,
    obtenir_resultats,
)
from f1_theme import apply_f1_theme, styliser_figure


st.set_page_config(page_title="Analyse d'une course", page_icon="🏁", layout="wide")
apply_f1_theme()
st.title("🏁 Analyse d’un Grand Prix")


@st.cache_data(ttl=3600, show_spinner=False)
def charger_courses(saison: int):
    return obtenir_courses(saison)


@st.cache_data(ttl=3600, show_spinner=False)
def charger_course(saison: int, manche: int):
    return (
        obtenir_resultats(saison, manche),
        obtenir_qualifications(saison, manche),
        obtenir_pitstops(saison, manche),
    )


saison = st.sidebar.number_input(
    "Saison",
    min_value=1950,
    max_value=datetime.now().year,
    value=datetime.now().year,
    step=1,
)

try:
    courses = charger_courses(int(saison))
except Exception as erreur:
    st.error(f"Impossible de charger le calendrier : {erreur}")
    st.stop()

if courses.empty:
    st.warning("Aucune course disponible.")
    st.stop()

noms = dict(zip(courses["manche"].astype(int), courses["grand_prix"]))
manche = st.selectbox(
    "Grand Prix",
    options=list(noms),
    format_func=lambda valeur: f"Manche {valeur} — {noms[valeur]}",
)

try:
    with st.spinner("Chargement des résultats..."):
        resultats, qualifications, pitstops = charger_course(int(saison), int(manche))
except Exception as erreur:
    st.error(f"Impossible de charger la course : {erreur}")
    st.stop()

if resultats.empty:
    st.info("Les résultats de cette course ne sont pas encore disponibles.")
    st.stop()

vainqueur = resultats.sort_values("position").iloc[0]
pole = "Non disponible"
if not qualifications.empty:
    pole = qualifications.sort_values("position_qualification").iloc[0]["pilote"]

meilleur_tour = resultats.dropna(subset=["rang_meilleur_tour"])
nom_meilleur_tour = "Non disponible"
if not meilleur_tour.empty:
    nom_meilleur_tour = meilleur_tour.sort_values("rang_meilleur_tour").iloc[0]["pilote"]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Vainqueur", vainqueur["pilote"])
col2.metric("Pole position", pole)
col3.metric("Meilleur tour", nom_meilleur_tour)
col4.metric("Abandons", int(resultats["abandon"].sum()))

resultats_tab, progression_tab, qualification_tab, pitstop_tab = st.tabs(
    ["Résultats", "Progression", "Qualifications", "Arrêts aux stands"]
)

with resultats_tab:
    affichage = resultats[
        [
            "position",
            "pilote",
            "ecurie",
            "grille",
            "positions_gagnees",
            "points",
            "tours",
            "statut",
            "temps",
            "meilleur_tour",
        ]
    ].copy()
    st.dataframe(affichage, width="stretch", hide_index=True)

    figure = px.bar(
        resultats.sort_values("position", ascending=False),
        x="points",
        y="pilote",
        color="ecurie",
        orientation="h",
        title="Points inscrits",
    )
    st.plotly_chart(styliser_figure(figure), width="stretch")

with progression_tab:
    progression = resultats.dropna(subset=["positions_gagnees"]).copy()
    figure = px.bar(
        progression.sort_values("positions_gagnees"),
        x="positions_gagnees",
        y="pilote",
        color="positions_gagnees",
        color_continuous_scale=["#4a4a50", "#ffffff", "#E10600"],
        orientation="h",
        title="Positions gagnées ou perdues",
        labels={"positions_gagnees": "Positions gagnées", "pilote": "Pilote"},
    )
    st.plotly_chart(styliser_figure(figure), width="stretch")

    figure_grille = px.scatter(
        resultats,
        x="grille",
        y="position",
        color="ecurie",
        hover_name="pilote",
        title="Grille de départ contre classement final",
        labels={"grille": "Position de départ", "position": "Position finale"},
    )
    figure_grille.update_yaxes(autorange="reversed")
    figure_grille.update_xaxes(autorange="reversed")
    st.plotly_chart(styliser_figure(figure_grille), width="stretch")

with qualification_tab:
    if qualifications.empty:
        st.info("Qualifications indisponibles.")
    else:
        st.dataframe(
            qualifications[
                [
                    "position_qualification",
                    "pilote",
                    "ecurie",
                    "q1",
                    "q2",
                    "q3",
                ]
            ],
            width="stretch",
            hide_index=True,
        )

with pitstop_tab:
    if pitstops.empty:
        st.info("Arrêts aux stands indisponibles.")
    else:
        noms_pilotes = resultats.set_index("driver_id")["pilote"].to_dict()
        pitstops = pitstops.copy()
        pitstops["pilote"] = pitstops["driver_id"].map(noms_pilotes)
        st.dataframe(
            pitstops[
                ["pilote", "tour", "numero_arret", "heure", "duree"]
            ].sort_values(["tour", "pilote"]),
            width="stretch",
            hide_index=True,
        )

        durees = pitstops.dropna(subset=["duree"])
        if not durees.empty:
            figure = px.scatter(
                durees,
                x="tour",
                y="duree",
                color="pilote",
                title="Durée des arrêts par tour",
                labels={"tour": "Tour", "duree": "Durée (s)"},
            )
            st.plotly_chart(styliser_figure(figure), width="stretch")

