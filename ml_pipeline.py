"""Pipeline éducatif de prédiction de podium en Formule 1."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Any

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


VARIABLES_NUMERIQUES = [
    "grille",
    "points_avant_course",
    "victoires_avant_course",
    "podiums_avant_course",
    "courses_disputees",
    "position_moyenne_5",
    "grille_moyenne_5",
    "taux_abandon_5",
    "forme_ecurie_5",
]

VARIABLES_CATEGORIELLES = [
    "driver_id",
    "constructor_id",
    "circuit_id",
]

VARIABLE_CIBLE = "podium"


@dataclass
class ResultatEntrainement:
    """Conteneur des modèles, métriques et prédictions."""

    modeles: dict[str, Pipeline]
    meilleur_modele: str
    metriques: pd.DataFrame
    predictions_test: pd.DataFrame
    donnees_variables: pd.DataFrame
    saison_test: int


def construire_variables(resultats: pd.DataFrame) -> pd.DataFrame:
    """Construit uniquement des variables disponibles avant la course.

    Toutes les statistiques historiques utilisent ``shift(1)`` afin d'éviter
    d'inclure le résultat de la course à prédire.
    """

    if resultats.empty:
        return pd.DataFrame()

    df = resultats.copy()
    colonnes_requises = {
        "saison",
        "manche",
        "driver_id",
        "constructor_id",
        "circuit_id",
        "position",
        "grille",
        "points",
        "abandon",
        "podium",
        "victoire",
    }
    manquantes = colonnes_requises.difference(df.columns)
    if manquantes:
        raise ValueError(
            "Colonnes manquantes pour le modèle : "
            + ", ".join(sorted(manquantes))
        )

    df = df.sort_values(["saison", "manche", "driver_id"]).reset_index(drop=True)
    for colonne in ["saison", "manche", "position", "grille", "points"]:
        df[colonne] = pd.to_numeric(df[colonne], errors="coerce")

    df["abandon"] = df["abandon"].astype(float)
    df["podium"] = df["podium"].astype(int)
    df["victoire"] = df["victoire"].astype(int)

    groupe_saison = df.groupby(["saison", "driver_id"], sort=False)
    groupe_pilote = df.groupby("driver_id", sort=False)
    groupe_ecurie = df.groupby("constructor_id", sort=False)

    df["points_avant_course"] = groupe_saison["points"].transform(
        lambda serie: serie.cumsum().shift(1).fillna(0)
    )
    df["victoires_avant_course"] = groupe_saison["victoire"].transform(
        lambda serie: serie.cumsum().shift(1).fillna(0)
    )
    df["podiums_avant_course"] = groupe_saison["podium"].transform(
        lambda serie: serie.cumsum().shift(1).fillna(0)
    )
    df["courses_disputees"] = groupe_pilote.cumcount()

    df["position_moyenne_5"] = groupe_pilote["position"].transform(
        lambda serie: serie.shift(1).rolling(5, min_periods=1).mean()
    )
    df["grille_moyenne_5"] = groupe_pilote["grille"].transform(
        lambda serie: serie.shift(1).rolling(5, min_periods=1).mean()
    )
    df["taux_abandon_5"] = groupe_pilote["abandon"].transform(
        lambda serie: serie.shift(1).rolling(5, min_periods=1).mean()
    )
    df["forme_ecurie_5"] = groupe_ecurie["position"].transform(
        lambda serie: serie.shift(1).rolling(5, min_periods=1).mean()
    )

    # Une grille égale à zéro signifie généralement un départ depuis les stands.
    df.loc[df["grille"] <= 0, "grille"] = 20

    return df


def _preprocesseur() -> ColumnTransformer:
    numerique = Pipeline(
        steps=[
            ("imputation", SimpleImputer(strategy="median")),
            ("standardisation", StandardScaler()),
        ]
    )
    categoriel = Pipeline(
        steps=[
            ("imputation", SimpleImputer(strategy="most_frequent")),
            (
                "encodage",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("numerique", numerique, VARIABLES_NUMERIQUES),
            ("categoriel", categoriel, VARIABLES_CATEGORIELLES),
        ]
    )


def _creer_modeles() -> dict[str, Pipeline]:
    return {
        "Régression logistique": Pipeline(
            steps=[
                ("preparation", _preprocesseur()),
                (
                    "modele",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        random_state=42,
                    ),
                ),
            ]
        ),
        "Forêt aléatoire": Pipeline(
            steps=[
                ("preparation", _preprocesseur()),
                (
                    "modele",
                    RandomForestClassifier(
                        n_estimators=350,
                        min_samples_leaf=3,
                        class_weight="balanced_subsample",
                        random_state=42,
                        n_jobs=-1,
                    ),
                ),
            ]
        ),
    }


def _calculer_metriques(
    nom: str,
    y_vrai: pd.Series,
    probabilites: np.ndarray,
    predictions: np.ndarray,
) -> dict[str, Any]:
    metriques: dict[str, Any] = {
        "modèle": nom,
        "accuracy": accuracy_score(y_vrai, predictions),
        "precision": precision_score(y_vrai, predictions, zero_division=0),
        "rappel": recall_score(y_vrai, predictions, zero_division=0),
        "f1": f1_score(y_vrai, predictions, zero_division=0),
        "brier": brier_score_loss(y_vrai, probabilites),
    }
    if y_vrai.nunique() == 2:
        metriques["roc_auc"] = roc_auc_score(y_vrai, probabilites)
    else:
        metriques["roc_auc"] = np.nan
    return metriques


def entrainer_modeles(resultats: pd.DataFrame) -> ResultatEntrainement:
    """Entraîne deux modèles avec la dernière saison comme jeu de test."""

    donnees = construire_variables(resultats)
    saisons = sorted(donnees["saison"].dropna().astype(int).unique())
    if len(saisons) < 2:
        raise ValueError("Il faut au moins deux saisons pour entraîner et tester.")

    saison_test = saisons[-1]
    train = donnees[donnees["saison"] < saison_test].copy()
    test = donnees[donnees["saison"] == saison_test].copy()

    if train.empty or test.empty:
        raise ValueError("La séparation chronologique ne contient pas assez de données.")

    x_train = train[VARIABLES_NUMERIQUES + VARIABLES_CATEGORIELLES]
    y_train = train[VARIABLE_CIBLE]
    x_test = test[VARIABLES_NUMERIQUES + VARIABLES_CATEGORIELLES]
    y_test = test[VARIABLE_CIBLE]

    metriques: list[dict[str, Any]] = []
    modeles = _creer_modeles()

    # Modèle de référence : prédire un podium pour les trois premiers de la grille.
    prediction_reference = (test["grille"] <= 3).astype(int).to_numpy()
    probabilite_reference = np.where(prediction_reference == 1, 0.75, 0.10)
    metriques.append(
        _calculer_metriques(
            "Référence : top 3 grille",
            y_test,
            probabilite_reference,
            prediction_reference,
        )
    )

    predictions_test = test[
        [
            "saison",
            "manche",
            "grand_prix",
            "pilote",
            "driver_id",
            "ecurie",
            "position",
            "grille",
            "podium",
        ]
    ].copy()

    for nom, pipeline in modeles.items():
        pipeline.fit(x_train, y_train)
        probabilites = pipeline.predict_proba(x_test)[:, 1]
        predictions = (probabilites >= 0.5).astype(int)
        metriques.append(
            _calculer_metriques(nom, y_test, probabilites, predictions)
        )
        predictions_test[f"probabilité_{nom}"] = probabilites
        predictions_test[f"prédiction_{nom}"] = predictions

    metriques_df = pd.DataFrame(metriques).sort_values(
        ["f1", "roc_auc"],
        ascending=False,
    )
    meilleurs_ml = metriques_df[
        metriques_df["modèle"].isin(modeles.keys())
    ].iloc[0]["modèle"]

    return ResultatEntrainement(
        modeles=modeles,
        meilleur_modele=str(meilleurs_ml),
        metriques=metriques_df.reset_index(drop=True),
        predictions_test=predictions_test.reset_index(drop=True),
        donnees_variables=donnees,
        saison_test=saison_test,
    )


def importance_variables(
    resultat: ResultatEntrainement,
    repetitions: int = 8,
) -> pd.DataFrame:
    """Calcule l'importance par permutation sur la saison de test."""

    test = resultat.donnees_variables[
        resultat.donnees_variables["saison"] == resultat.saison_test
    ]
    x_test = test[VARIABLES_NUMERIQUES + VARIABLES_CATEGORIELLES]
    y_test = test[VARIABLE_CIBLE]
    modele = resultat.modeles[resultat.meilleur_modele]

    importance = permutation_importance(
        modele,
        x_test,
        y_test,
        scoring="f1",
        n_repeats=repetitions,
        random_state=42,
        n_jobs=-1,
    )
    return (
        pd.DataFrame(
            {
                "variable": x_test.columns,
                "importance": importance.importances_mean,
                "écart_type": importance.importances_std,
            }
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def scenario_depuis_pilote(
    resultat: ResultatEntrainement,
    driver_id: str,
    circuit_id: str,
    position_grille: int,
) -> pd.DataFrame:
    """Construit un scénario à partir des dernières statistiques du pilote."""

    historique = resultat.donnees_variables
    pilote = historique[historique["driver_id"] == driver_id].sort_values(
        ["saison", "manche"]
    )
    if pilote.empty:
        raise ValueError("Pilote absent des données d'entraînement.")

    scenario = pilote.iloc[[-1]][
        VARIABLES_NUMERIQUES + VARIABLES_CATEGORIELLES
    ].copy()
    scenario["grille"] = int(position_grille)
    scenario["circuit_id"] = circuit_id
    return scenario


def predire_scenario(
    resultat: ResultatEntrainement,
    scenario: pd.DataFrame,
) -> float:
    modele = resultat.modeles[resultat.meilleur_modele]
    return float(modele.predict_proba(scenario)[:, 1][0])


def serialiser_modele(resultat: ResultatEntrainement) -> bytes:
    """Sérialise le résultat complet pour un téléchargement Streamlit."""

    tampon = BytesIO()
    joblib.dump(resultat, tampon)
    return tampon.getvalue()
