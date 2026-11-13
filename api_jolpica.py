"""Accès robuste à l'API Jolpica F1.

Les fonctions retournent des DataFrames prêts à être utilisés par Streamlit.
L'API est non officielle et destinée ici à un projet éducatif.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = "https://api.jolpi.ca/ergast/f1"
USER_AGENT = "F1DataIntelligence/2.0"
TAILLE_PAGE = 100

CIRCUITS_GEOJSON_URL = (
    "https://raw.githubusercontent.com/bacinger/f1-circuits/"
    "master/f1-circuits.geojson"
)


def _creer_session() -> requests.Session:
    """Crée une session HTTP avec reprises automatiques."""

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


def interroger_api(
    chemin: str,
    *,
    limit: int = TAILLE_PAGE,
    offset: int = 0,
) -> dict[str, Any]:
    """Interroge un endpoint Jolpica et retourne le contenu ``MRData``."""

    url = f"{BASE_URL}/{chemin.strip('/')}/"
    response = SESSION.get(
        url,
        params={"limit": min(limit, TAILLE_PAGE), "offset": offset},
        timeout=30,
    )
    response.raise_for_status()

    contenu = response.json()
    if "MRData" not in contenu:
        raise ValueError("La réponse Jolpica ne contient pas MRData.")

    return contenu["MRData"]


def paginer_api(chemin: str) -> list[dict[str, Any]]:
    """Télécharge toutes les pages d'un endpoint Jolpica."""

    pages: list[dict[str, Any]] = []
    offset = 0

    while True:
        page = interroger_api(chemin, offset=offset)
        pages.append(page)

        total = int(page.get("total", 0))
        limite = int(page.get("limit", TAILLE_PAGE))
        offset += limite

        if offset >= total or limite <= 0:
            break

    return pages


def obtenir_pilotes(saison: int = 2026) -> pd.DataFrame:
    """Retourne la liste des pilotes connus pour une saison."""

    data = interroger_api(f"{saison}/drivers")
    pilotes = data.get("DriverTable", {}).get("Drivers", [])

    colonnes = [
        "driverId",
        "permanentNumber",
        "code",
        "givenName",
        "familyName",
        "dateOfBirth",
        "nationality",
    ]

    return pd.json_normalize(pilotes).reindex(columns=colonnes)


def obtenir_classement_pilotes(saison: int = 2026) -> pd.DataFrame:
    """Retourne le dernier classement disponible des pilotes."""

    data = interroger_api(f"{saison}/driverstandings")
    listes = data.get("StandingsTable", {}).get("StandingsLists", [])

    colonnes = [
        "driverId",
        "ecurie",
        "ecurie_id",
        "points",
        "victoires",
        "position",
    ]
    if not listes:
        return pd.DataFrame(columns=colonnes)

    lignes: list[dict[str, Any]] = []
    for entree in listes[0].get("DriverStandings", []):
        constructeurs = entree.get("Constructors", [])
        ecurie = constructeurs[-1] if constructeurs else {}
        lignes.append(
            {
                "driverId": entree.get("Driver", {}).get("driverId"),
                "ecurie": ecurie.get("name"),
                "ecurie_id": ecurie.get("constructorId"),
                "points": entree.get("points"),
                "victoires": entree.get("wins"),
                "position": entree.get("position"),
            }
        )

    df = pd.DataFrame(lignes, columns=colonnes)
    for colonne in ["points", "victoires", "position"]:
        df[colonne] = pd.to_numeric(df[colonne], errors="coerce")
    return df


def obtenir_classement_constructeurs(saison: int = 2026) -> pd.DataFrame:
    """Retourne le dernier classement disponible des constructeurs."""

    data = interroger_api(f"{saison}/constructorstandings")
    listes = data.get("StandingsTable", {}).get("StandingsLists", [])

    colonnes = [
        "position",
        "constructeur_id",
        "constructeur",
        "nationalite",
        "points",
        "victoires",
    ]
    if not listes:
        return pd.DataFrame(columns=colonnes)

    lignes: list[dict[str, Any]] = []
    for entree in listes[0].get("ConstructorStandings", []):
        constructeur = entree.get("Constructor", {})
        lignes.append(
            {
                "position": entree.get("position"),
                "constructeur_id": constructeur.get("constructorId"),
                "constructeur": constructeur.get("name"),
                "nationalite": constructeur.get("nationality"),
                "points": entree.get("points"),
                "victoires": entree.get("wins"),
            }
        )

    df = pd.DataFrame(lignes, columns=colonnes)
    for colonne in ["position", "points", "victoires"]:
        df[colonne] = pd.to_numeric(df[colonne], errors="coerce")
    return df


def obtenir_pilotes_complet(saison: int = 2026) -> pd.DataFrame:
    """Combine les informations des pilotes avec le classement."""

    pilotes = obtenir_pilotes(saison)
    classement = obtenir_classement_pilotes(saison)
    return pilotes.merge(classement, on="driverId", how="left")


def obtenir_courses(saison: int = 2026) -> pd.DataFrame:
    """Retourne le calendrier complet d'une saison."""

    data = interroger_api(f"{saison}/races")
    courses = data.get("RaceTable", {}).get("Races", [])
    df = pd.json_normalize(courses, sep="_")

    renommage = {
        "season": "saison",
        "round": "manche",
        "raceName": "grand_prix",
        "date": "date",
        "time": "heure",
        "Circuit_circuitId": "circuit_id",
        "Circuit_circuitName": "circuit",
        "Circuit_Location_locality": "ville",
        "Circuit_Location_country": "pays",
        "Circuit_Location_lat": "latitude",
        "Circuit_Location_long": "longitude",
    }

    df = df.rename(columns=renommage)
    df = df.reindex(columns=renommage.values())
    df["saison"] = pd.to_numeric(df["saison"], errors="coerce")
    df["manche"] = pd.to_numeric(df["manche"], errors="coerce")
    return df


def _ligne_resultat(course: dict[str, Any], resultat: dict[str, Any]) -> dict[str, Any]:
    pilote = resultat.get("Driver", {})
    constructeur = resultat.get("Constructor", {})
    circuit = course.get("Circuit", {})
    lieu = circuit.get("Location", {})
    meilleur_tour = resultat.get("FastestLap", {})

    return {
        "saison": course.get("season"),
        "manche": course.get("round"),
        "grand_prix": course.get("raceName"),
        "date": course.get("date"),
        "circuit_id": circuit.get("circuitId"),
        "circuit": circuit.get("circuitName"),
        "pays": lieu.get("country"),
        "driver_id": pilote.get("driverId"),
        "code": pilote.get("code"),
        "pilote": " ".join(
            valeur
            for valeur in [pilote.get("givenName"), pilote.get("familyName")]
            if valeur
        ),
        "nationalite": pilote.get("nationality"),
        "constructor_id": constructeur.get("constructorId"),
        "ecurie": constructeur.get("name"),
        "position": resultat.get("position"),
        "grille": resultat.get("grid"),
        "points": resultat.get("points"),
        "tours": resultat.get("laps"),
        "statut": resultat.get("status"),
        "temps": resultat.get("Time", {}).get("time"),
        "temps_ms": resultat.get("Time", {}).get("millis"),
        "rang_meilleur_tour": meilleur_tour.get("rank"),
        "numero_meilleur_tour": meilleur_tour.get("lap"),
        "meilleur_tour": meilleur_tour.get("Time", {}).get("time"),
        "vitesse_moyenne": meilleur_tour.get("AverageSpeed", {}).get("speed"),
    }


def obtenir_resultats(
    saison: int,
    manche: int | str | None = None,
) -> pd.DataFrame:
    """Retourne les résultats d'une course ou de toute une saison."""

    chemin = f"{saison}/results" if manche is None else f"{saison}/{manche}/results"
    pages = paginer_api(chemin)

    lignes: list[dict[str, Any]] = []
    for page in pages:
        courses = page.get("RaceTable", {}).get("Races", [])
        for course in courses:
            for resultat in course.get("Results", []):
                lignes.append(_ligne_resultat(course, resultat))

    df = pd.DataFrame(lignes)
    if df.empty:
        return df

    df = df.drop_duplicates(["saison", "manche", "driver_id"])
    for colonne in [
        "saison",
        "manche",
        "position",
        "grille",
        "points",
        "tours",
        "temps_ms",
        "rang_meilleur_tour",
        "numero_meilleur_tour",
        "vitesse_moyenne",
    ]:
        df[colonne] = pd.to_numeric(df[colonne], errors="coerce")

    statut = df["statut"].fillna("")
    df["abandon"] = ~statut.str.match(r"^(Finished|\+\d+ Laps?)$", case=False)
    df["podium"] = (df["position"] <= 3).astype(int)
    df["victoire"] = (df["position"] == 1).astype(int)
    df["positions_gagnees"] = df["grille"] - df["position"]
    df.loc[df["grille"] <= 0, "positions_gagnees"] = pd.NA
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return df.sort_values(["saison", "manche", "position"]).reset_index(drop=True)


def _ligne_qualification(
    course: dict[str, Any],
    resultat: dict[str, Any],
) -> dict[str, Any]:
    pilote = resultat.get("Driver", {})
    constructeur = resultat.get("Constructor", {})
    circuit = course.get("Circuit", {})

    return {
        "saison": course.get("season"),
        "manche": course.get("round"),
        "grand_prix": course.get("raceName"),
        "date": course.get("date"),
        "circuit_id": circuit.get("circuitId"),
        "driver_id": pilote.get("driverId"),
        "code": pilote.get("code"),
        "pilote": " ".join(
            valeur
            for valeur in [pilote.get("givenName"), pilote.get("familyName")]
            if valeur
        ),
        "constructor_id": constructeur.get("constructorId"),
        "ecurie": constructeur.get("name"),
        "position_qualification": resultat.get("position"),
        "q1": resultat.get("Q1"),
        "q2": resultat.get("Q2"),
        "q3": resultat.get("Q3"),
    }


def obtenir_qualifications(
    saison: int,
    manche: int | str | None = None,
) -> pd.DataFrame:
    """Retourne les qualifications d'une course ou de toute une saison."""

    chemin = (
        f"{saison}/qualifying"
        if manche is None
        else f"{saison}/{manche}/qualifying"
    )
    pages = paginer_api(chemin)

    lignes: list[dict[str, Any]] = []
    for page in pages:
        courses = page.get("RaceTable", {}).get("Races", [])
        for course in courses:
            for resultat in course.get("QualifyingResults", []):
                lignes.append(_ligne_qualification(course, resultat))

    df = pd.DataFrame(lignes)
    if df.empty:
        return df

    df = df.drop_duplicates(["saison", "manche", "driver_id"])
    df["saison"] = pd.to_numeric(df["saison"], errors="coerce")
    df["manche"] = pd.to_numeric(df["manche"], errors="coerce")
    df["position_qualification"] = pd.to_numeric(
        df["position_qualification"],
        errors="coerce",
    )
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df.sort_values(["saison", "manche", "position_qualification"])


def obtenir_pitstops(saison: int, manche: int | str) -> pd.DataFrame:
    """Retourne les arrêts aux stands d'une course."""

    data = interroger_api(f"{saison}/{manche}/pitstops")
    courses = data.get("RaceTable", {}).get("Races", [])
    lignes: list[dict[str, Any]] = []

    for course in courses:
        for arret in course.get("PitStops", []):
            lignes.append(
                {
                    "saison": course.get("season"),
                    "manche": course.get("round"),
                    "grand_prix": course.get("raceName"),
                    "driver_id": arret.get("driverId"),
                    "tour": arret.get("lap"),
                    "numero_arret": arret.get("stop"),
                    "heure": arret.get("time"),
                    "duree": arret.get("duration"),
                }
            )

    df = pd.DataFrame(lignes)
    if not df.empty:
        for colonne in ["saison", "manche", "tour", "numero_arret", "duree"]:
            df[colonne] = pd.to_numeric(df[colonne], errors="coerce")
    return df


def obtenir_tours(saison: int, manche: int | str) -> pd.DataFrame:
    """Retourne les temps au tour d'une course Jolpica."""

    pages = paginer_api(f"{saison}/{manche}/laps")
    lignes: list[dict[str, Any]] = []

    for page in pages:
        for course in page.get("RaceTable", {}).get("Races", []):
            for tour in course.get("Laps", []):
                for timing in tour.get("Timings", []):
                    lignes.append(
                        {
                            "saison": course.get("season"),
                            "manche": course.get("round"),
                            "grand_prix": course.get("raceName"),
                            "tour": tour.get("number"),
                            "driver_id": timing.get("driverId"),
                            "position": timing.get("position"),
                            "temps": timing.get("time"),
                        }
                    )

    df = pd.DataFrame(lignes)
    if not df.empty:
        for colonne in ["saison", "manche", "tour", "position"]:
            df[colonne] = pd.to_numeric(df[colonne], errors="coerce")
    return df


def obtenir_resultats_historiques(
    saison_debut: int,
    saison_fin: int,
    progression: Callable[[int, int], None] | None = None,
) -> pd.DataFrame:
    """Télécharge et concatène les résultats de plusieurs saisons."""

    if saison_debut > saison_fin:
        raise ValueError("La saison de début doit précéder la saison de fin.")

    tableaux: list[pd.DataFrame] = []
    saisons = list(range(saison_debut, saison_fin + 1))

    for index, saison in enumerate(saisons, start=1):
        tableau = obtenir_resultats(saison)
        if not tableau.empty:
            tableaux.append(tableau)
        if progression:
            progression(index, len(saisons))

    if not tableaux:
        return pd.DataFrame()
    return pd.concat(tableaux, ignore_index=True)


ALIAS_CIRCUIT_VERS_LIEU = {
    "albert_park": "Melbourne",
    "shanghai": "Shanghai",
    "suzuka": "Suzuka",
    "miami": "Miami",
    "villeneuve": "Montreal",
    "monaco": "Monaco",
    "catalunya": "Barcelona",
    "red_bull_ring": "Spielberg",
    "silverstone": "Silverstone",
    "spa": "Spa Francorchamps",
    "hungaroring": "Budapest",
    "zandvoort": "Zandvoort",
    "monza": "Monza",
    "baku": "Baku",
    "marina_bay": "Singapore",
    "americas": "Austin",
    "rodriguez": "Mexico City",
    "interlagos": "Sao Paulo",
    "vegas": "Las Vegas",
    "losail": "Lusail",
    "yas_marina": "Yas Marina",
    "jeddah": "Jeddah",
    "bahrain": "Sakhir",
}


def obtenir_traces_circuits() -> dict[str, dict[str, Any]]:
    """Retourne les coordonnées GeoJSON des circuits disponibles."""

    response = SESSION.get(CIRCUITS_GEOJSON_URL, timeout=30)
    response.raise_for_status()
    data = response.json()

    par_lieu: dict[str, dict[str, Any]] = {}
    for feature in data.get("features", []):
        lieu = feature.get("properties", {}).get("Location")
        if lieu:
            par_lieu[lieu] = {
                "coordinates": feature.get("geometry", {}).get("coordinates", []),
                "bbox": feature.get("bbox"),
            }

    return {
        circuit_id: par_lieu[lieu]
        for circuit_id, lieu in ALIAS_CIRCUIT_VERS_LIEU.items()
        if lieu in par_lieu
    }


if __name__ == "__main__":
    print(obtenir_courses(2026).head())
    print(obtenir_pilotes_complet(2026).head())
