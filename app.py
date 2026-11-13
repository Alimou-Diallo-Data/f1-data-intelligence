"""Page d'accueil du dashboard F1 Data Intelligence."""

from __future__ import annotations

import math
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from api_jolpica import (
    obtenir_classement_constructeurs,
    obtenir_courses,
    obtenir_pilotes_complet,
    obtenir_traces_circuits,
)
from f1_theme import (
    apply_f1_theme,
    afficher_banniere_hero,
    couleur_equipe,
    styliser_figure,
)


st.set_page_config(
    page_title="F1 Data Intelligence",
    page_icon="🏎️",
    layout="wide",
)
apply_f1_theme()

afficher_banniere_hero(
    "assets/hero.jpg",
    "🏎️ F1 Data Intelligence",
    "Analyse, comparaison, télémétrie et prédiction de podium.",
    chemin_logo="assets/f1-logo.png",
)


DRAPEAUX_PAYS = {
    "Australia": "🇦🇺",
    "China": "🇨🇳",
    "Japan": "🇯🇵",
    "USA": "🇺🇸",
    "United States": "🇺🇸",
    "Canada": "🇨🇦",
    "Monaco": "🇲🇨",
    "Spain": "🇪🇸",
    "Austria": "🇦🇹",
    "UK": "🇬🇧",
    "United Kingdom": "🇬🇧",
    "Belgium": "🇧🇪",
    "Hungary": "🇭🇺",
    "Netherlands": "🇳🇱",
    "Italy": "🇮🇹",
    "Azerbaijan": "🇦🇿",
    "Singapore": "🇸🇬",
    "Mexico": "🇲🇽",
    "Brazil": "🇧🇷",
    "Qatar": "🇶🇦",
    "UAE": "🇦🇪",
    "United Arab Emirates": "🇦🇪",
    "Saudi Arabia": "🇸🇦",
    "Bahrain": "🇧🇭",
    "France": "🇫🇷",
    "Germany": "🇩🇪",
}


@st.cache_data(ttl=3600, show_spinner=False)
def charger_donnees(annee: int):
    return (
        obtenir_pilotes_complet(annee),
        obtenir_courses(annee),
        obtenir_classement_constructeurs(annee),
    )


@st.cache_data(ttl=86400, show_spinner=False)
def charger_traces_circuits():
    try:
        return obtenir_traces_circuits()
    except Exception:
        return {}


saison = st.sidebar.number_input(
    "Choisir une saison",
    min_value=1950,
    max_value=datetime.now().year,
    value=datetime.now().year,
    step=1,
)

st.sidebar.markdown(
    """
    <div class="source-note">
    Les données Jolpica sont non officielles et utilisées à des fins éducatives.
    </div>
    """,
    unsafe_allow_html=True,
)

try:
    with st.spinner("Chargement de la saison..."):
        df_pilotes, df_courses, df_constructeurs = charger_donnees(int(saison))
except Exception as erreur:
    st.error(f"Impossible de récupérer les données : {erreur}")
    st.stop()


def ajouter_drapeaux(df: pd.DataFrame) -> pd.DataFrame:
    copie = df.copy()
    copie["pays"] = copie["pays"].apply(
        lambda pays: f"{DRAPEAUX_PAYS.get(pays, '🏁')} {pays}"
    )
    return copie


leader = "Non disponible"
if "position" in df_pilotes and df_pilotes["position"].notna().any():
    ligne_leader = df_pilotes.loc[df_pilotes["position"].idxmin()]
    leader = f"{ligne_leader.get('givenName', '')} {ligne_leader.get('familyName', '')}".strip()

leader_constructeur = "Non disponible"
if not df_constructeurs.empty:
    leader_constructeur = str(
        df_constructeurs.sort_values("position").iloc[0]["constructeur"]
    )

col1, col2, col3, col4 = st.columns(4)
col1.metric("Pilotes référencés", len(df_pilotes))
col2.metric("Grands Prix", len(df_courses))
col3.metric("Leader pilotes", leader)
col4.metric("Leader constructeurs", leader_constructeur)

onglet_apercu, onglet_calendrier, onglet_pilotes, onglet_classements, onglet_carte = st.tabs(
    ["Aperçu", "Calendrier", "Pilotes", "Classements", "Carte des circuits"]
)

with onglet_apercu:
    st.subheader(f"Aperçu de la saison {saison}")

    courses = df_courses.copy()
    courses["date_course"] = pd.to_datetime(courses["date"], errors="coerce")
    aujourd_hui = pd.Timestamp.now().normalize()
    courses_futures = courses[courses["date_course"] >= aujourd_hui]

    gauche, droite = st.columns([1, 2])
    with gauche:
        if not courses_futures.empty:
            prochaine = courses_futures.sort_values("date_course").iloc[0]
            st.metric("Prochain Grand Prix", prochaine["grand_prix"])
            st.write(
                f"📍 {prochaine['ville']}, {prochaine['pays']}  \n"
                f"📅 {prochaine['date_course'].date():%d/%m/%Y}"
            )
        else:
            st.info("Aucune course future dans le calendrier sélectionné.")

    with droite:
        if df_pilotes["points"].notna().any():
            top = (
                df_pilotes.dropna(subset=["points"])
                .nsmallest(8, "position")
                .copy()
            )
            top["pilote"] = (
                top["givenName"].fillna("") + " " + top["familyName"].fillna("")
            ).str.strip()
            figure = px.bar(
                top.sort_values("points"),
                x="points",
                y="pilote",
                color="ecurie_id",
                orientation="h",
                title="Top 8 du championnat",
                color_discrete_map={
                    identifiant: couleur_equipe(identifiant)
                    for identifiant in top["ecurie_id"].dropna().unique()
                },
                labels={"points": "Points", "pilote": "Pilote", "ecurie_id": "Écurie"},
            )
            st.plotly_chart(styliser_figure(figure), width="stretch")
        else:
            st.info("Classement indisponible pour cette saison.")

with onglet_calendrier:
    st.subheader(f"Calendrier F1 {saison}")
    calendrier = ajouter_drapeaux(df_courses)
    st.dataframe(
        calendrier,
        width="stretch",
        hide_index=True,
        column_config={
            "latitude": None,
            "longitude": None,
            "circuit_id": None,
        },
    )

with onglet_pilotes:
    st.subheader(f"Pilotes de la saison {saison}")
    pilotes_affichage = df_pilotes.copy()
    pilotes_affichage["pilote"] = (
        pilotes_affichage["givenName"].fillna("")
        + " "
        + pilotes_affichage["familyName"].fillna("")
    ).str.strip()
    st.dataframe(
        pilotes_affichage[
            [
                "position",
                "pilote",
                "code",
                "permanentNumber",
                "nationality",
                "ecurie",
                "points",
                "victoires",
            ]
        ],
        width="stretch",
        hide_index=True,
    )

    gauche, droite = st.columns(2)
    with gauche:
        nationalites = (
            df_pilotes["nationality"]
            .fillna("Non renseignée")
            .value_counts()
            .reset_index()
        )
        nationalites.columns = ["nationalité", "nombre"]
        figure = px.bar(
            nationalites,
            x="nationalité",
            y="nombre",
            title="Pilotes par nationalité",
            color_discrete_sequence=["#E10600"],
        )
        st.plotly_chart(styliser_figure(figure), width="stretch")

    with droite:
        par_ecurie = (
            df_pilotes.dropna(subset=["ecurie"])
            .groupby(["ecurie", "ecurie_id"])
            .size()
            .reset_index(name="nombre")
        )
        figure = px.bar(
            par_ecurie,
            x="ecurie",
            y="nombre",
            color="ecurie_id",
            title="Pilotes par écurie",
            color_discrete_map={
                identifiant: couleur_equipe(identifiant)
                for identifiant in par_ecurie["ecurie_id"].unique()
            },
            labels={"ecurie": "Écurie", "nombre": "Pilotes", "ecurie_id": "Écurie"},
        )
        figure.update_layout(showlegend=False)
        st.plotly_chart(styliser_figure(figure), width="stretch")

with onglet_classements:
    pilotes_tab, constructeurs_tab = st.tabs(["Pilotes", "Constructeurs"])

    with pilotes_tab:
        classement_pilotes = df_pilotes.dropna(subset=["position"]).sort_values(
            "position"
        )
        st.dataframe(
            classement_pilotes[
                ["position", "givenName", "familyName", "ecurie", "points", "victoires"]
            ],
            width="stretch",
            hide_index=True,
        )

    with constructeurs_tab:
        if df_constructeurs.empty:
            st.info("Classement constructeurs indisponible.")
        else:
            st.dataframe(
                df_constructeurs,
                width="stretch",
                hide_index=True,
            )
            figure = px.bar(
                df_constructeurs.sort_values("points"),
                x="points",
                y="constructeur",
                color="constructeur_id",
                orientation="h",
                title="Points par constructeur",
                color_discrete_map={
                    identifiant: couleur_equipe(identifiant)
                    for identifiant in df_constructeurs["constructeur_id"].unique()
                },
            )
            figure.update_layout(showlegend=False)
            st.plotly_chart(styliser_figure(figure), width="stretch")

with onglet_carte:
    st.subheader("Emplacement des circuits")
    carte = df_courses.copy()
    carte["latitude"] = pd.to_numeric(carte["latitude"], errors="coerce")
    carte["longitude"] = pd.to_numeric(carte["longitude"], errors="coerce")
    carte["date_course"] = pd.to_datetime(carte["date"], errors="coerce")
    carte = carte.dropna(subset=["latitude", "longitude"])
    aujourd_hui = pd.Timestamp.now().normalize()
    carte["statut"] = carte["date_course"].apply(
        lambda date: "Disputé" if pd.notna(date) and date < aujourd_hui else "À venir"
    )

    figure_carte = px.scatter_map(
        carte,
        lat="latitude",
        lon="longitude",
        color="statut",
        color_discrete_map={"Disputé": "#5a5a5f", "À venir": "#E10600"},
        hover_name="grand_prix",
        hover_data={"date": True, "latitude": False, "longitude": False},
        zoom=1,
        height=540,
        map_style="carto-darkmatter",
    )
    figure_carte.update_traces(marker=dict(size=13))
    st.plotly_chart(styliser_figure(figure_carte), width="stretch")

    st.divider()
    st.subheader("Tracé du circuit")
    traces = charger_traces_circuits()
    disponibles = carte[carte["circuit_id"].isin(traces.keys())]

    if disponibles.empty:
        st.info("Aucun tracé disponible pour cette saison.")
    else:
        grand_prix = st.selectbox("Choisir un Grand Prix", disponibles["grand_prix"])
        ligne = disponibles[disponibles["grand_prix"] == grand_prix].iloc[0]
        coordonnees = traces[ligne["circuit_id"]]["coordinates"]
        lons = [point[0] for point in coordonnees]
        lats = [point[1] for point in coordonnees]

        envergure = max(
            max(lons) - min(lons),
            max(lats) - min(lats),
            1e-6,
        )
        zoom = max(11, min(17, math.log2(1125 / (envergure * 1.5))))

        figure_trace = go.Figure(
            go.Scattermap(
                lon=lons,
                lat=lats,
                mode="lines",
                line=dict(color="#E10600", width=4),
                hoverinfo="skip",
            )
        )
        figure_trace.update_layout(
            map_style="carto-darkmatter",
            map_center={
                "lon": (max(lons) + min(lons)) / 2,
                "lat": (max(lats) + min(lats)) / 2,
            },
            map_zoom=zoom,
            height=500,
            showlegend=False,
        )
        st.plotly_chart(styliser_figure(figure_trace), width="stretch")
