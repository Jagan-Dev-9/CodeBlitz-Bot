import time
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta

# ✅ Google Sheets setup
SHEET_NAME = "CodeBlitzTestRound"
JSON_KEY_FILE = "google_sheets_key.json"

# ✅ ENTER TEAMS IN BATTLES HERE (Each battle is a 1v1 match)
BATTLES = {
    # "Battle 1": ["sujeethhh_03", "nishanth_babbula"],
    # "Battle 2": ["kartikbala05", "ymvraghu1784"],
    # "Battle 3": ["achyut07", "gowthammagapu"],
    # "Battle 4": ["vshashank2005", "vinodalaparthi"],
    # "Battle 5": ["manideep25", "06aslan30"],
    # "Battle 6": ["saiteja8298", "rahulvarma32"],
    # "Battle 7": ["shivaram_25", "saisirish"],
    # "Battle 8": ["gaya_pran", "saisridhar3"],
    # "Battle 9": ["2320030247", "k_subramanyam03"],
    # "Battle 10": ["ajaycharan_07", "saiabhiramreddyg"],
    # "Battle 11": ["v.charita_sree", "jayakrishna9"],
    # "Battle 12": ["deepikavarma", "__navya_"],
    # "Battle 13": ["amrutha_777", "manikanta_9"],
    # "Battle 14": ["chandumogili2201", "tlillysanjana"],
    # "Battle 15": ["aarathi32", "MMAHENDERREDDY"],
}

# ✅ Problem IDs and their points
PROBLEM_IDS = {
    "1703/B": {"points": 200},
    "1370/A": {"points": 200},
    "1896/A": {"points": 200},
    "1883/B": {"points": 300},
    "96/A": {"points": 300},
}

# ✅ Tracking which team solved each problem first in each battle
BATTLE_TRACKER = {
    battle: {problem: {"winner": None, "first_submission_time": None} for problem in PROBLEM_IDS}
    for battle in BATTLES
}

# ✅ Authenticate Google Sheets
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1  # Access first sheet

# ✅ Fetch latest submissions from Codeforces
def fetch_latest_submissions(handle):
    url = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=5"
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

                    # ✅ Only update if the submission is correct ("OK")
                    if verdict == "OK":
                        current_winner = BATTLE_TRACKER[battle][problem_id]["winner"]
                        previous_time = BATTLE_TRACKER[battle][problem_id]["first_submission_time"]

                        # ✅ If no one has solved it yet, assign this team as the winner
                        if current_winner is None:
                            print(f"{team} solved {problem_id} first in {battle}!")
                            BATTLE_TRACKER[battle][problem_id]["winner"] = team
                            BATTLE_TRACKER[battle][problem_id]["first_submission_time"] = submission_time
                            update_leaderboard(battle, team, problem_id, readable_time)

                        # ✅ If another team already solved it, check who was faster
                        elif submission_time < previous_time:
                            print(f"{team} submitted {problem_id} faster than {current_winner} in {battle}! Updating points.")

                            # ✅ Remove points from the previous winner
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

            # ✅ Get all headers from Google Sheets
            headers = sheet.row_values(1)

            # ✅ Find correct column indexes based on problem_id
            col_index = headers.index(f"{problem_id} ✅") + 1
            time_col_index = headers.index(f"{problem_id} Time") + 1

            if remove_points:
                score -= PROBLEM_IDS[problem_id]["points"]  # Deduct points
                sheet.update_cell(i + 2, 2, score)  # Update score
                time.sleep(1)  # Small delay to avoid rate limit

                sheet.update_cell(i + 2, col_index, "❌")  # Mark problem as unsolved
                time.sleep(1)  # Small delay

                sheet.update_cell(i + 2, time_col_index, "")  # Clear submission time
                time.sleep(1)  # Small delay

                print(f"Removed points from {team} for {problem_id}. New score: {score}")

            else:
                score += PROBLEM_IDS[problem_id]["points"]  # Add points
                sheet.update_cell(i + 2, 2, score)  # Update score
                time.sleep(1)  # Small delay

                sheet.update_cell(i + 2, col_index, "✅")  # Mark problem as solved
                time.sleep(1)  # Small delay

                sheet.update_cell(i + 2, time_col_index, readable_time)  # Update submission time
                time.sleep(1)  # Small delay

                print(f"Updated leaderboard: {team} now has {score} points! Solved at {readable_time}")

# ✅ Main loop (checks submissions every 5 minutes)
while True:
    check_submissions()
    print("Waiting for the next check...")
    time.sleep(300)  # Wait for 5 minutes
