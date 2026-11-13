"""Exploration de la météo, des tours, arrêts et relais OpenF1."""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from api_openf1 import (
    obtenir_arrets,
    obtenir_meteo,
    obtenir_pilotes_session,
    obtenir_relais,
    obtenir_sessions,
    obtenir_tours,
)
from f1_theme import apply_f1_theme, styliser_figure


st.set_page_config(page_title="Télémétrie OpenF1", page_icon="📡", layout="wide")
apply_f1_theme()
st.title("📡 Télémétrie et stratégie OpenF1")
st.write(
    "Analyse exploratoire des tours, de la météo, des arrêts aux stands "
    "et des pneumatiques. Les données historiques OpenF1 commencent en 2023."
)


@st.cache_data(ttl=3600, show_spinner=False)
def charger_sessions(annee: int) -> pd.DataFrame:
    return obtenir_sessions(annee)


@st.cache_data(ttl=3600, show_spinner=False)
def charger_session(session_key: int):
    return {
        "pilotes": obtenir_pilotes_session(session_key),
        "meteo": obtenir_meteo(session_key),
        "tours": obtenir_tours(session_key),
        "arrets": obtenir_arrets(session_key),
        "relais": obtenir_relais(session_key),
    }


annee = st.sidebar.number_input(
    "Année",
    min_value=2023,
    max_value=datetime.now().year,
    value=max(2023, datetime.now().year - 1),
    step=1,
)

try:
    sessions = charger_sessions(int(annee))
except Exception as erreur:
    st.error(f"OpenF1 est momentanément indisponible : {erreur}")
    st.stop()

if sessions.empty:
    st.info("Aucune session de course OpenF1 pour cette année.")
    st.stop()

sessions = sessions.sort_values("date_start")
libelles = {
    int(ligne.session_key): (
        f"{ligne.country_name} — {ligne.circuit_short_name} "
        f"({str(ligne.date_start)[:10]})"
    )
    for ligne in sessions.itertuples()
}
session_key = st.selectbox(
    "Course",
    options=list(libelles),
    format_func=lambda cle: libelles[cle],
)

try:
    with st.spinner("Chargement de la télémétrie..."):
        donnees = charger_session(int(session_key))
except Exception as erreur:
    st.error(f"Chargement OpenF1 impossible : {erreur}")
    st.stop()

pilotes = donnees["pilotes"].copy()
meteo = donnees["meteo"].copy()
tours = donnees["tours"].copy()
arrets = donnees["arrets"].copy()
relais = donnees["relais"].copy()

if pilotes.empty:
    noms: dict[int, str] = {}
else:
    pilotes["driver_number"] = pd.to_numeric(
        pilotes["driver_number"], errors="coerce"
    )
    pilotes = pilotes.dropna(subset=["driver_number"]).drop_duplicates(
        "driver_number", keep="last"
    )
    noms = {
        int(ligne.driver_number): (
            getattr(ligne, "full_name", None)
            or getattr(ligne, "broadcast_name", None)
            or f"#{int(ligne.driver_number)}"
        )
        for ligne in pilotes.itertuples()
    }


def ajouter_nom_pilote(df: pd.DataFrame) -> pd.DataFrame:
    resultat = df.copy()
    if "driver_number" in resultat:
        resultat["driver_number"] = pd.to_numeric(
            resultat["driver_number"], errors="coerce"
        )
        resultat["pilote"] = resultat["driver_number"].map(
            lambda numero: noms.get(int(numero), f"#{int(numero)}")
            if pd.notna(numero)
            else "Inconnu"
        )
    return resultat


meteo_tab, tours_tab, arrets_tab, pneus_tab = st.tabs(
    ["Météo", "Meilleurs tours", "Arrêts", "Pneumatiques"]
)

with meteo_tab:
    if meteo.empty:
        st.info("Aucune donnée météo disponible.")
    else:
        for colonne in ["air_temperature", "track_temperature", "rainfall"]:
            if colonne in meteo:
                meteo[colonne] = pd.to_numeric(meteo[colonne], errors="coerce")

        col1, col2, col3 = st.columns(3)
        col1.metric(
            "Air moyen",
            f"{meteo['air_temperature'].mean():.1f} °C"
            if "air_temperature" in meteo
            else "—",
        )
        col2.metric(
            "Piste moyenne",
            f"{meteo['track_temperature'].mean():.1f} °C"
            if "track_temperature" in meteo
            else "—",
        )
        pluie = (
            pd.to_numeric(meteo.get("rainfall"), errors="coerce").max()
            if "rainfall" in meteo
            else 0
        )
        col3.metric("Pluie détectée", "Oui" if pluie > 0 else "Non")

        temperatures = [
            colonne
            for colonne in ["air_temperature", "track_temperature"]
            if colonne in meteo
        ]
        if temperatures:
            figure = px.line(
                meteo,
                x="date",
                y=temperatures,
                labels={"value": "Température (°C)", "date": "Temps"},
                title="Évolution des températures",
            )
            st.plotly_chart(styliser_figure(figure), width="stretch")

with tours_tab:
    if tours.empty or "lap_duration" not in tours:
        st.info("Aucun tour chronométré disponible.")
    else:
        tours = ajouter_nom_pilote(tours)
        tours["lap_duration"] = pd.to_numeric(
            tours["lap_duration"], errors="coerce"
        )
        meilleurs = (
            tours.dropna(subset=["lap_duration"])
            .sort_values("lap_duration")
            .drop_duplicates("driver_number")
            .head(20)
        )
        figure = px.bar(
            meilleurs.sort_values("lap_duration", ascending=False),
            x="lap_duration",
            y="pilote",
            orientation="h",
            color="lap_duration",
            color_continuous_scale=["#00D2BE", "#E10600"],
            labels={"lap_duration": "Temps (secondes)", "pilote": "Pilote"},
            title="Meilleur tour de chaque pilote",
        )
        st.plotly_chart(styliser_figure(figure), width="stretch")
        st.dataframe(
            meilleurs.reindex(
                columns=[
                    "pilote",
                    "lap_number",
                    "lap_duration",
                    "duration_sector_1",
                    "duration_sector_2",
                    "duration_sector_3",
                ]
            ),
            width="stretch",
            hide_index=True,
        )

with arrets_tab:
    if arrets.empty:
        st.info("Aucun arrêt aux stands disponible.")
    else:
        arrets = ajouter_nom_pilote(arrets)
        arrets["pit_duration"] = pd.to_numeric(
            arrets.get("pit_duration"), errors="coerce"
        )
        resume = (
            arrets.groupby("pilote", as_index=False)
            .agg(
                nombre_arrets=("driver_number", "size"),
                duree_moyenne=("pit_duration", "mean"),
            )
            .sort_values(["nombre_arrets", "duree_moyenne"])
        )
        figure = px.bar(
            resume,
            x="pilote",
            y="nombre_arrets",
            color="duree_moyenne",
            color_continuous_scale=["#00D2BE", "#E10600"],
            title="Nombre d'arrêts par pilote",
        )
        st.plotly_chart(styliser_figure(figure), width="stretch")
        st.dataframe(resume, width="stretch", hide_index=True)

with pneus_tab:
    if relais.empty:
        st.info("Aucune donnée de relais disponible.")
    else:
        relais = ajouter_nom_pilote(relais)
        relais["longueur_relais"] = (
            pd.to_numeric(relais.get("lap_end"), errors="coerce")
            - pd.to_numeric(relais.get("lap_start"), errors="coerce")
            + 1
        )
        figure = px.bar(
            relais.dropna(subset=["compound", "longueur_relais"]),
            x="pilote",
            y="longueur_relais",
            color="compound",
            title="Répartition des relais par type de pneu",
            labels={"longueur_relais": "Nombre de tours", "compound": "Pneu"},
        )
        st.plotly_chart(styliser_figure(figure), width="stretch")
        st.dataframe(
            relais.reindex(
                columns=[
                    "pilote",
                    "stint_number",
                    "compound",
                    "lap_start",
                    "lap_end",
                    "longueur_relais",
                    "tyre_age_at_start",
                ]
            ),
            width="stretch",
            hide_index=True,
        )
