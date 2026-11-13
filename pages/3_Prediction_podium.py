"""Entraînement, évaluation et simulation d'un modèle de podium."""

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.metrics import confusion_matrix

from api_jolpica import obtenir_resultats_historiques
from f1_theme import apply_f1_theme, styliser_figure
from ml_pipeline import (
    entrainer_modeles,
    importance_variables,
    predire_scenario,
    scenario_depuis_pilote,
    serialiser_modele,
)


st.set_page_config(page_title="Prédiction podium", page_icon="🔮", layout="wide")
apply_f1_theme()
st.title("🔮 Prédiction de podium")
st.write(
    "Le modèle utilise uniquement des informations disponibles avant la course. "
    "La dernière saison de la période est conservée pour le test."
)


@st.cache_data(ttl=86400, show_spinner=False)
def charger_resultats(debut: int, fin: int):
    return obtenir_resultats_historiques(debut, fin)


annee_actuelle = datetime.now().year
fin_defaut = max(2019, annee_actuelle - 1)
debut_defaut = max(2010, fin_defaut - 7)

debut, fin = st.sidebar.slider(
    "Saisons pour le modèle",
    min_value=2000,
    max_value=annee_actuelle,
    value=(debut_defaut, fin_defaut),
)

st.sidebar.info(
    f"Entraînement : {debut}–{fin - 1}\n\n"
    f"Test chronologique : {fin}"
)

if st.button("Entraîner et évaluer", type="primary"):
    try:
        with st.spinner("Téléchargement des résultats et entraînement..."):
            donnees = charger_resultats(debut, fin)
            st.session_state["resultat_ml"] = entrainer_modeles(donnees)
    except Exception as erreur:
        st.error(f"Entraînement impossible : {erreur}")

resultat = st.session_state.get("resultat_ml")
if resultat is None:
    st.info("Clique sur « Entraîner et évaluer » pour commencer.")
    st.stop()

st.success(
    f"Modèle sélectionné : {resultat.meilleur_modele} — "
    f"saison testée : {resultat.saison_test}"
)

evaluation_tab, predictions_tab, importance_tab, simulateur_tab = st.tabs(
    ["Évaluation", "Prédictions test", "Variables", "Simulateur"]
)

with evaluation_tab:
    metriques = resultat.metriques.copy()
    metriques_affichage = metriques.copy()
    for colonne in ["accuracy", "precision", "rappel", "f1", "roc_auc"]:
        metriques_affichage[colonne] = metriques_affichage[colonne].map(
            lambda valeur: f"{valeur:.3f}" if pd.notna(valeur) else "—"
        )
    metriques_affichage["brier"] = metriques_affichage["brier"].map(
        lambda valeur: f"{valeur:.3f}"
    )
    st.dataframe(metriques_affichage, width="stretch", hide_index=True)

    figure = px.bar(
        metriques,
        x="modèle",
        y=["precision", "rappel", "f1", "roc_auc"],
        barmode="group",
        title="Comparaison des modèles",
        labels={"value": "Score", "variable": "Métrique"},
    )
    st.plotly_chart(styliser_figure(figure), width="stretch")

    colonne_prediction = f"prédiction_{resultat.meilleur_modele}"
    matrice = confusion_matrix(
        resultat.predictions_test["podium"],
        resultat.predictions_test[colonne_prediction],
    )
    figure_matrice = px.imshow(
        matrice,
        text_auto=True,
        color_continuous_scale=["#16161a", "#E10600"],
        labels={
            "x": "Prédiction",
            "y": "Réalité",
            "color": "Nombre",
        },
        x=["Pas de podium", "Podium"],
        y=["Pas de podium", "Podium"],
        title="Matrice de confusion",
    )
    st.plotly_chart(styliser_figure(figure_matrice), width="stretch")

with predictions_tab:
    colonne_proba = f"probabilité_{resultat.meilleur_modele}"
    tableau = resultat.predictions_test.copy()
    tableau["probabilité_podium"] = tableau[colonne_proba].map(
        lambda valeur: f"{valeur:.1%}"
    )
    st.dataframe(
        tableau[
            [
                "grand_prix",
                "pilote",
                "ecurie",
                "grille",
                "position",
                "podium",
                "probabilité_podium",
            ]
        ],
        width="stretch",
        hide_index=True,
    )
    st.download_button(
        "Télécharger les prédictions CSV",
        data=tableau.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"predictions_podium_{resultat.saison_test}.csv",
        mime="text/csv",
    )

with importance_tab:
    if st.button("Calculer l’importance des variables"):
        with st.spinner("Calcul de l'importance par permutation..."):
            importance = importance_variables(resultat)
        figure = px.bar(
            importance.sort_values("importance"),
            x="importance",
            y="variable",
            orientation="h",
            error_x="écart_type",
            title="Influence des variables sur le score F1",
        )
        st.plotly_chart(styliser_figure(figure), width="stretch")
        st.dataframe(importance, width="stretch", hide_index=True)
    else:
        st.info(
            "L’importance par permutation mesure la baisse du score lorsque "
            "chaque variable est mélangée."
        )

with simulateur_tab:
    donnees = resultat.donnees_variables
    derniers = (
        donnees.sort_values(["saison", "manche"])
        .drop_duplicates("driver_id", keep="last")
        .dropna(subset=["driver_id"])
    )
    noms = derniers.set_index("driver_id")["pilote"].to_dict()
    pilotes = sorted(noms, key=lambda identifiant: noms[identifiant])
    circuits_noms = (
        donnees[["circuit_id", "circuit"]]
        .dropna()
        .drop_duplicates("circuit_id")
        .set_index("circuit_id")["circuit"]
        .to_dict()
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        driver_id = st.selectbox(
            "Pilote",
            pilotes,
            format_func=lambda identifiant: noms[identifiant],
        )
    with col2:
        circuit_id = st.selectbox(
            "Circuit",
            sorted(circuits_noms),
            format_func=lambda identifiant: circuits_noms[identifiant],
        )
    with col3:
        grille = st.number_input(
            "Position sur la grille",
            min_value=1,
            max_value=20,
            value=5,
            step=1,
        )

    if st.button("Calculer la probabilité"):
        scenario = scenario_depuis_pilote(
            resultat,
            driver_id,
            circuit_id,
            int(grille),
        )
        probabilite = predire_scenario(resultat, scenario)
        st.metric(
            f"Probabilité de podium — {noms[driver_id]}",
            f"{probabilite:.1%}",
        )
        st.caption(
            "Cette probabilité est une estimation éducative, pas une certitude. "
            "Les incidents de course et la météo restent imprévisibles."
        )

    st.download_button(
        "Télécharger le modèle entraîné",
        data=serialiser_modele(resultat),
        file_name="modele_podium_f1.joblib",
        mime="application/octet-stream",
    )
