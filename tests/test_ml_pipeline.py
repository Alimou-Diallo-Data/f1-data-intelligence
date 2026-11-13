"""Tests locaux du pipeline de prédiction, sans appel à Internet."""

from __future__ import annotations

import unittest

import pandas as pd

from ml_pipeline import (
    construire_variables,
    entrainer_modeles,
    predire_scenario,
    scenario_depuis_pilote,
)


def fabriquer_resultats() -> pd.DataFrame:
    pilotes = [
        ("alpha", "Alpha", "team_a"),
        ("bravo", "Bravo", "team_a"),
        ("charlie", "Charlie", "team_b"),
        ("delta", "Delta", "team_b"),
        ("echo", "Echo", "team_c"),
        ("foxtrot", "Foxtrot", "team_c"),
    ]
    lignes = []
    for saison in [2022, 2023, 2024]:
        for manche in range(1, 7):
            rotation = (manche + saison) % len(pilotes)
            ordre = pilotes[rotation:] + pilotes[:rotation]
            for position, (driver_id, nom, constructor_id) in enumerate(
                ordre, start=1
            ):
                grille = (
                    (position + manche - 2) % len(pilotes)
                ) + 1
                lignes.append(
                    {
                        "saison": saison,
                        "manche": manche,
                        "grand_prix": f"GP {manche}",
                        "circuit_id": f"circuit_{manche}",
                        "circuit": f"Circuit {manche}",
                        "driver_id": driver_id,
                        "pilote": nom,
                        "constructor_id": constructor_id,
                        "ecurie": constructor_id,
                        "position": position,
                        "grille": grille,
                        "points": max(0, 8 - position),
                        "abandon": position == 6 and manche % 3 == 0,
                        "podium": int(position <= 3),
                        "victoire": int(position == 1),
                    }
                )
    return pd.DataFrame(lignes)


class TestPipelineML(unittest.TestCase):
    def setUp(self):
        self.resultats = fabriquer_resultats()

    def test_variables_avant_course_sans_fuite(self):
        variables = construire_variables(self.resultats)
        premiers = (
            variables.sort_values(["saison", "manche"])
            .groupby(["saison", "driver_id"])
            .head(1)
        )
        self.assertTrue((premiers["points_avant_course"] == 0).all())
        self.assertTrue((premiers["podiums_avant_course"] == 0).all())

    def test_separation_chronologique_et_predictions(self):
        resultat = entrainer_modeles(self.resultats)
        self.assertEqual(resultat.saison_test, 2024)
        self.assertFalse(resultat.metriques.empty)
        self.assertEqual(set(resultat.modeles), {
            "Régression logistique",
            "Forêt aléatoire",
        })
        colonne = f"probabilité_{resultat.meilleur_modele}"
        self.assertTrue(
            resultat.predictions_test[colonne].between(0, 1).all()
        )

    def test_simulateur(self):
        resultat = entrainer_modeles(self.resultats)
        scenario = scenario_depuis_pilote(
            resultat,
            driver_id="alpha",
            circuit_id="circuit_1",
            position_grille=2,
        )
        probabilite = predire_scenario(resultat, scenario)
        self.assertGreaterEqual(probabilite, 0)
        self.assertLessEqual(probabilite, 1)


if __name__ == "__main__":
    unittest.main()
