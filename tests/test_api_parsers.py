"""Tests de transformation des réponses Jolpica, sans accès réseau."""

from __future__ import annotations

import importlib.util
import unittest
from unittest.mock import patch


REQUESTS_DISPONIBLE = importlib.util.find_spec("requests") is not None
if REQUESTS_DISPONIBLE:
    from api_jolpica import obtenir_resultats


REPONSE_RESULTATS = {
    "RaceTable": {
        "Races": [
            {
                "season": "2024",
                "round": "1",
                "raceName": "Grand Prix de test",
                "date": "2024-01-01",
                "Circuit": {
                    "circuitId": "test",
                    "circuitName": "Circuit test",
                    "Location": {"country": "Testland"},
                },
                "Results": [
                    {
                        "position": "1",
                        "grid": "3",
                        "points": "25",
                        "laps": "50",
                        "status": "Finished",
                        "Driver": {
                            "driverId": "pilote_test",
                            "code": "TST",
                            "givenName": "Pilote",
                            "familyName": "Test",
                        },
                        "Constructor": {
                            "constructorId": "team_test",
                            "name": "Écurie Test",
                        },
                        "FastestLap": {
                            "rank": "1",
                            "lap": "42",
                            "Time": {"time": "1:20.000"},
                        },
                    }
                ],
            }
        ]
    }
}


@unittest.skipUnless(
    REQUESTS_DISPONIBLE,
    "La dépendance requests n'est pas installée dans cet environnement.",
)
class TestJolpicaParsers(unittest.TestCase):
    @patch("api_jolpica.paginer_api", return_value=[REPONSE_RESULTATS])
    def test_resultats_aplatis_et_types(self, _mock_pages):
        df = obtenir_resultats(2024, 1)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.loc[0, "pilote"], "Pilote Test")
        self.assertEqual(df.loc[0, "positions_gagnees"], 2)
        self.assertEqual(df.loc[0, "podium"], 1)
        self.assertFalse(bool(df.loc[0, "abandon"]))


if __name__ == "__main__":
    unittest.main()
