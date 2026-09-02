"""Minimal realistic JSON response fixtures for Jolpica F1 API testing."""

SAMPLE_RACE_RESULTS_PAYLOAD = {
    "MRData": {
        "xmlns": "http://ergast.com/mrd/1.5",
        "series": "f1",
        "url": "https://api.jolpi.ca/ergast/f1/2024/1/results.json",
        "limit": "30",
        "offset": "0",
        "total": "2",
        "RaceTable": {
            "season": "2024",
            "round": "1",
            "Races": [
                {
                    "season": "2024",
                    "round": "1",
                    "url": "https://en.wikipedia.org/wiki/2024_Bahrain_Grand_Prix",
                    "raceName": "Bahrain Grand Prix",
                    "Circuit": {
                        "circuitId": "bahrain",
                        "url": "https://en.wikipedia.org/wiki/Bahrain_International_Circuit",
                        "circuitName": "Bahrain International Circuit",
                        "Location": {
                            "lat": "26.0325",
                            "long": "50.5106",
                            "locality": "Sakhir",
                            "country": "Bahrain",
                        },
                    },
                    "date": "2024-03-02",
                    "time": "15:00:00Z",
                    "Results": [
                        {
                            "number": "1",
                            "position": "1",
                            "positionText": "1",
                            "points": "26",
                            "Driver": {
                                "driverId": "max_verstappen",
                                "permanentNumber": "33",
                                "code": "VER",
                                "givenName": "Max",
                                "familyName": "Verstappen",
                                "dateOfBirth": "1997-09-30",
                                "nationality": "Dutch",
                            },
                            "Constructor": {
                                "constructorId": "red_bull",
                                "name": "Red Bull",
                                "nationality": "Austrian",
                            },
                            "grid": "1",
                            "laps": "57",
                            "status": "Finished",
                            "Time": {"millis": "5504742", "time": "1:31:44.742"},
                            "FastestLap": {
                                "rank": "1",
                                "lap": "39",
                                "Time": {"time": "1:32.608"},
                            },
                        },
                        {
                            "number": "11",
                            "position": "2",
                            "positionText": "2",
                            "points": "18",
                            "Driver": {
                                "driverId": "perez",
                                "permanentNumber": "11",
                                "code": "PER",
                                "givenName": "Sergio",
                                "familyName": "Pérez",
                                "dateOfBirth": "1990-01-26",
                                "nationality": "Mexican",
                            },
                            "Constructor": {
                                "constructorId": "red_bull",
                                "name": "Red Bull",
                                "nationality": "Austrian",
                            },
                            "grid": "5",
                            "laps": "57",
                            "status": "Finished",
                            "Time": {"millis": "5527199", "time": "+22.457"},
                        },
                    ],
                }
            ],
        },
    }
}

SAMPLE_QUALIFYING_PAYLOAD = {
    "MRData": {
        "limit": "30",
        "offset": "0",
        "total": "1",
        "RaceTable": {
            "season": "2024",
            "round": "1",
            "Races": [
                {
                    "season": "2024",
                    "round": "1",
                    "raceName": "Bahrain Grand Prix",
                    "Circuit": {"circuitId": "bahrain", "circuitName": "Bahrain International Circuit"},
                    "QualifyingResults": [
                        {
                            "number": "1",
                            "position": "1",
                            "Driver": {"driverId": "max_verstappen", "code": "VER"},
                            "Constructor": {"constructorId": "red_bull", "name": "Red Bull"},
                            "Q1": "1:30.031",
                            "Q2": "1:29.374",
                            "Q3": "1:29.179",
                        }
                    ],
                }
            ],
        },
    }
}

SAMPLE_SPRINT_PAYLOAD = {
    "MRData": {
        "limit": "30",
        "offset": "0",
        "total": "1",
        "RaceTable": {
            "season": "2024",
            "round": "5",
            "Races": [
                {
                    "season": "2024",
                    "round": "5",
                    "raceName": "Chinese Grand Prix",
                    "SprintResults": [
                        {
                            "number": "1",
                            "position": "1",
                            "positionText": "1",
                            "points": "8",
                            "Driver": {"driverId": "max_verstappen", "code": "VER"},
                            "Constructor": {"constructorId": "red_bull", "name": "Red Bull"},
                            "grid": "4",
                            "laps": "19",
                            "status": "Finished",
                        }
                    ],
                }
            ],
        },
    }
}

SAMPLE_PITSTOPS_PAGE_1 = {
    "MRData": {
        "limit": "2",
        "offset": "0",
        "total": "3",
        "RaceTable": {
            "season": "2024",
            "round": "1",
            "Races": [
                {
                    "season": "2024",
                    "round": "1",
                    "PitStops": [
                        {"driverId": "sainz", "stop": "1", "lap": "14", "time": "15:25:30", "duration": "24.123"},
                        {"driverId": "leclerc", "stop": "1", "lap": "15", "time": "15:27:00", "duration": "23.456"},
                    ],
                }
            ],
        },
    }
}

SAMPLE_PITSTOPS_PAGE_2 = {
    "MRData": {
        "limit": "2",
        "offset": "2",
        "total": "3",
        "RaceTable": {
            "season": "2024",
            "round": "1",
            "Races": [
                {
                    "season": "2024",
                    "round": "1",
                    "PitStops": [
                        {"driverId": "norris", "stop": "1", "lap": "16", "time": "15:28:45", "duration": "24.500"},
                    ],
                }
            ],
        },
    }
}

SAMPLE_LAPS_PAGE_1 = {
    "MRData": {
        "limit": "2",
        "offset": "0",
        "total": "3",
        "RaceTable": {
            "season": "2024",
            "round": "1",
            "Races": [
                {
                    "season": "2024",
                    "round": "1",
                    "Laps": [
                        {
                            "number": "1",
                            "Timings": [
                                {"driverId": "max_verstappen", "position": "1", "time": "1:36.415"},
                                {"driverId": "leclerc", "position": "2", "time": "1:37.520"},
                            ],
                        }
                    ],
                }
            ],
        },
    }
}

SAMPLE_LAPS_PAGE_2 = {
    "MRData": {
        "limit": "2",
        "offset": "2",
        "total": "3",
        "RaceTable": {
            "season": "2024",
            "round": "1",
            "Races": [
                {
                    "season": "2024",
                    "round": "1",
                    "Laps": [
                        {
                            "number": "2",
                            "Timings": [
                                {"driverId": "max_verstappen", "position": "1", "time": "1:35.120"},
                            ],
                        }
                    ],
                }
            ],
        },
    }
}

SAMPLE_DRIVER_STANDINGS_PAYLOAD = {
    "MRData": {
        "limit": "30",
        "offset": "0",
        "total": "1",
        "StandingsTable": {
            "season": "2024",
            "round": "1",
            "StandingsLists": [
                {
                    "season": "2024",
                    "round": "1",
                    "DriverStandings": [
                        {
                            "position": "1",
                            "positionText": "1",
                            "points": "26",
                            "wins": "1",
                            "Driver": {"driverId": "max_verstappen", "code": "VER"},
                            "Constructors": [{"constructorId": "red_bull", "name": "Red Bull"}],
                        }
                    ],
                }
            ],
        },
    }
}

SAMPLE_CONSTRUCTOR_STANDINGS_PAYLOAD = {
    "MRData": {
        "limit": "30",
        "offset": "0",
        "total": "1",
        "StandingsTable": {
            "season": "2024",
            "round": "1",
            "StandingsLists": [
                {
                    "season": "2024",
                    "round": "1",
                    "ConstructorStandings": [
                        {
                            "position": "1",
                            "positionText": "1",
                            "points": "44",
                            "wins": "1",
                            "Constructor": {"constructorId": "red_bull", "name": "Red Bull"},
                        }
                    ],
                }
            ],
        },
    }
}

SAMPLE_CIRCUITS_PAYLOAD = {
    "MRData": {
        "limit": "30",
        "offset": "0",
        "total": "1",
        "CircuitTable": {
            "Circuits": [
                {
                    "circuitId": "albert_park",
                    "circuitName": "Albert Park Grand Prix Circuit",
                    "Location": {"locality": "Melbourne", "country": "Australia"},
                }
            ]
        },
    }
}
