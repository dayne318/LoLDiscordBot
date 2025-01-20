# In test_evaluate_performance.py
import sys
import os

# Add the directory containing your modules to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'LoLDiscordBot'))

from match_tracking import MatchTracking

def test_evaluate_performance():
    tracker = MatchTracking(bot=None, test_mode=True)

    # Example high-performance test
    stats = {
        'kills': 8,
        'deaths': 2,
        'assists': 10,
        'kill_participation': 70,
        'damage_delt': 60000,
        'gpm': 350,
        'cs_per_min': 7,
        'ward_score_per_min': 1.5,
    }
    role = 'Laner'
    score = tracker.evaluate_performance(stats, role)
    print(f"High Performance Score: {score}")  # Should output a high score

    # Example low-performance test
    stats = {
        'kills': 2,
        'deaths': 9,
        'assists': 3,
        'kill_participation': 20,
        'damage_delt': 10000,
        'gpm': 150,
        'cs_per_min': 2,
        'ward_score_per_min': 0.2,
    }
    role = 'Laner'
    score = tracker.evaluate_performance(stats, role)
    print(f"Low Performance Score: {score}")  # Should output a low score

if __name__ == "__main__":
    test_evaluate_performance()
