from match_tracking import MatchTracking

def test_evaluate_performance():
    # Initialize the MatchTracking instance
    tracker = MatchTracking(bot=None)

    # Define some mock stats for different scenarios
    test_cases = [
        {
            "description": "High performance Laner",
            "stats": {
                'kills': 9,
                'deaths': 2,
                'assists': 8,
                'kill_participation': 60,
                'damage_delt': 55000,
                'gpm': 340,
                'cs_per_min': 6,
                'ward_score_per_min': 0.7,
            },
            "role": "Laner",
            "expected_score_range": (0.5, 1.0)  # Expected score to be greater than threshold
        },
        {
            "description": "Low performance Jungle",
            "stats": {
                'kills': 2,
                'deaths': 8,
                'assists': 3,
                'kill_participation': 30,
                'damage_delt': 15000,
                'gpm': 250,
                'cs_per_min': 3,
                'ward_score_per_min': 0.3,
            },
            "role": "Jungle",
            "expected_score_range": (-1.0, 0.4)  # Expected score to be less than threshold
        },
        {
            "description": "Average Support",
            "stats": {
                'kills': 1,
                'deaths': 4,
                'assists': 12,
                'kill_participation': 50,
                'damage_delt': 20000,
                'gpm': 290,
                'cs_per_min': 0.5,
                'ward_score_per_min': 1.0,
            },
            "role": "Support",
            "expected_score_range": (0.3, 0.6)  # Expected score to be around the threshold
        }
    ]

    for case in test_cases:
        score = tracker.evaluate_performance(case["stats"], case["role"])
        print(f"{case['description']} - Performance Score: {score:.2f}")
        assert case["expected_score_range"][0] <= score <= case["expected_score_range"][1], \
            f"Test failed for {case['description']}: score {score} not in expected range {case['expected_score_range']}"

if __name__ == "__main__":
    test_evaluate_performance()
