import time
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta  # Import timedelta for time conversion

# Google Sheets setup
SHEET_NAME = "CodeBlitzTestRound"
JSON_KEY_FILE = "google_sheets_key.json"

# ✅ ENTER TEAMS IN BATTLES HERE (Each battle is a 1v1 match)
BATTLES = {
    "Battle 1": ["sunkavallisathvik", "QuantumSolver07"],
    # "Battle 2": ["TeamC", "TeamD"],
    # "Battle 3": ["TeamE", "TeamF"],
    # Add more battles here...
}

# ✅ Same problem set for all battles
# ✅ Updated problem set
# PROBLEM_IDS = {
#     "1921/A": {"points": 200},  # One and Two
#     "1920/B": {"points": 200},  # Make it Beautiful
#     "1919/A": {"points": 200},  # Everybody Likes Good Arrays!
#     "1918/B": {"points": 200},  # Extremely Round
#     "1917/A": {"points": 200},  # Two Permutations
# }
PROBLEM_IDS = {
    "1881/A": {"points": 200},
    "1878/A": {"points": 200},
    "1877/A": {"points": 200},
    "1873/C": {"points": 200},
    "1866/A": {"points": 200},
}

# ✅ Tracking which team solved each problem first in each battle
BATTLE_TRACKER = {battle: {problem: {"winner": None, "first_submission_time": None} for problem in PROBLEM_IDS} for battle in BATTLES}

# ✅ Authenticate Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1  # Access first sheet

# ✅ Fetch latest submissions from Codeforces
def fetch_latest_submissions(handle):
    url = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=10"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["result"]
    else:
        print(f"Failed to fetch data for {handle}: {response.status_code}")
        return []

# ✅ Check submissions & update leaderboard
def check_submissions():
    global BATTLE_TRACKER

    for battle, teams in BATTLES.items():
        for team in teams:
            submissions = fetch_latest_submissions(team)

            for submission in submissions:
                problem_id = f"{submission['problem']['contestId']}/{submission['problem']['index']}"
                verdict = submission['verdict']
                submission_time = submission['creationTimeSeconds']

                # ✅ Convert Unix timestamp to IST properly
                utc_time = datetime.utcfromtimestamp(submission_time)  # Convert to UTC first
                ist_time = utc_time + timedelta(hours=5, minutes=30)   # Add IST offset
                readable_time = ist_time.strftime('%H:%M:%S')  # Format time

                # ✅ Check if the problem is in our contest
                if problem_id in PROBLEM_IDS:
                    # ✅ Get the opponent team
                    opponent = [t for t in teams if t != team][0]

                    # ✅ If no team has solved it yet, assign the first solver
                    if BATTLE_TRACKER[battle][problem_id]["winner"] is None:
                        if verdict == "OK":
                            print(f"{team} solved {problem_id} first in {battle}!")
                            BATTLE_TRACKER[battle][problem_id]["winner"] = team
                            BATTLE_TRACKER[battle][problem_id]["first_submission_time"] = submission_time
                            update_leaderboard(battle, team, problem_id, readable_time)

                    # ✅ If already solved, check if the new submission was faster
                    else:
                        current_winner = BATTLE_TRACKER[battle][problem_id]["winner"]
                        previous_time = BATTLE_TRACKER[battle][problem_id]["first_submission_time"]

                        if verdict == "OK" and submission_time < previous_time:
                            print(f"{team} submitted {problem_id} faster than {current_winner} in {battle}! Updating points.")

                            # ✅ Remove points from previous winner
                            update_leaderboard(battle, current_winner, problem_id, remove_points=True)

                            # ✅ Assign new winner
                            BATTLE_TRACKER[battle][problem_id]["winner"] = team
                            BATTLE_TRACKER[battle][problem_id]["first_submission_time"] = submission_time
                            update_leaderboard(battle, team, problem_id, readable_time)

# ✅ Update Google Sheets leaderboard
def update_leaderboard(battle, team, problem_id, readable_time=None, remove_points=False):
    data = sheet.get_all_records()

    for i, row in enumerate(data):
        if row["Team Name"] == team:
            # ✅ Convert score to an integer, ensuring it's not empty
            score = int(row["Score"]) if str(row["Score"]).strip().isdigit() else 0
            # score = int(row["Score"]) if row["Score"].strip() else 0
            # score = int(row["Score"]) if isinstance(row["Score"], str) and row["Score"].strip() else row["Score"]

            # ✅ Get all headers from Google Sheets
            headers = sheet.row_values(1)

            # ✅ Find correct column indexes based on problem_id
            col_index = headers.index(f"{problem_id} ✅") + 1
            time_col_index = headers.index(f"{problem_id} Time") + 1

            if remove_points:
                score -= PROBLEM_IDS[problem_id]["points"]  # Deduct points
                sheet.update_cell(i + 2, 2, score)  # Update score
                sheet.update_cell(i + 2, col_index, "❌")  # Reset problem status
                sheet.update_cell(i + 2, time_col_index, "")  # Clear time
                print(f"Removed points from {team} for {problem_id}. New score: {score}")

            else:
                score += PROBLEM_IDS[problem_id]["points"]  # Add points
                sheet.update_cell(i + 2, 2, score)  # Update score
                sheet.update_cell(i + 2, col_index, "✅")  # Mark problem as solved
                sheet.update_cell(i + 2, time_col_index, readable_time)  # Update submission time
                print(f"Updated leaderboard: {team} now has {score} points! Solved at {readable_time}")

# ✅ Main loop (checks submissions every 5 minutes)
while True:
    check_submissions()
    print("Waiting for the next check...")
    time.sleep(30)  # Wait for 5 minutes
