"""Fonctions d'accès à OpenF1 pour la télémétrie historique."""

from __future__ import annotations

from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = "https://api.openf1.org/v1"
USER_AGENT = "F1DataIntelligence/2.0"


def _creer_session() -> requests.Session:
    reprises = Retry(
        total=4,
        connect=4,
        read=4,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET"}),
        respect_retry_after_header=True,
    )
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    session.mount("https://", HTTPAdapter(max_retries=reprises))
    return session


SESSION = _creer_session()


def interroger_openf1(endpoint: str, **parametres: Any) -> pd.DataFrame:
    """Interroge OpenF1 et retourne un DataFrame."""

    url = f"{BASE_URL}/{endpoint.strip('/')}"
    response = SESSION.get(url, params=parametres, timeout=45)
    response.raise_for_status()
    donnees = response.json()

    if not isinstance(donnees, list):
        raise ValueError("La réponse OpenF1 n'est pas une liste.")
    return pd.DataFrame(donnees)


def obtenir_sessions(annee: int, nom_session: str = "Race") -> pd.DataFrame:
    """Retourne les sessions d'une année, avec filtre de type de session."""

    return interroger_openf1(
        "sessions",
        year=annee,
        session_name=nom_session,
    )


def obtenir_pilotes_session(session_key: int | str) -> pd.DataFrame:
    return interroger_openf1("drivers", session_key=session_key)


def obtenir_meteo(session_key: int | str) -> pd.DataFrame:
    return interroger_openf1("weather", session_key=session_key)


def obtenir_tours(session_key: int | str) -> pd.DataFrame:
    return interroger_openf1("laps", session_key=session_key)


def obtenir_arrets(session_key: int | str) -> pd.DataFrame:
    return interroger_openf1("pit", session_key=session_key)


def obtenir_relais(session_key: int | str) -> pd.DataFrame:
    return interroger_openf1("stints", session_key=session_key)
