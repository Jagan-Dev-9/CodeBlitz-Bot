import time
import gspread
import requests
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from datetime import timedelta  # Import timedelta for time conversion

# Google Sheets setup
SHEET_NAME = "CodeBlitzTestRound"
JSON_KEY_FILE = "google_sheets_key.json"

# Codeforces setup
TEAM_HANDLES = {
    "sunkavallisathvik": "sunkavallisathvik",
    "QuantumSolver07": "QuantumSolver07"
}

PROBLEM_IDS = {
    "1881/A": {"points": 200, "claimed_by": None, "first_submission_time": None},
    "1878/A": {"points": 200, "claimed_by": None, "first_submission_time": None},
    "1877/A": {"points": 200, "claimed_by": None, "first_submission_time": None},
    "1873/C": {"points": 200, "claimed_by": None, "first_submission_time": None},
    "1866/A": {"points": 200, "claimed_by": None, "first_submission_time": None}
}

# Authenticate Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/spreadsheets",
         "https://www.googleapis.com/auth/spreadsheets.readonly", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_KEY_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).sheet1  # Access first sheet

# Function to fetch latest Codeforces submissions
def fetch_latest_submissions(handle):
    url = f"https://codeforces.com/api/user.status?handle={handle}&from=1&count=10"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()["result"]
    else:
        print(f"Failed to fetch data for {handle}: {response.status_code}")
        return []

# Function to check and update leaderboard
# Function to check and update leaderboard
def check_submissions():
    global PROBLEM_IDS

    for team, handle in TEAM_HANDLES.items():
        submissions = fetch_latest_submissions(handle)
        for submission in submissions:
            problem_id = f"{submission['problem']['contestId']}/{submission['problem']['index']}"
            verdict = submission['verdict']
            submission_time = submission['creationTimeSeconds']  # Get submission timestamp

            # Convert UTC time to Indian Standard Time (IST)
            ist_time = datetime.utcfromtimestamp(submission_time) + timedelta(hours=5, minutes=30)
            readable_time = ist_time.strftime('%H:%M:%S')

            # Check if problem is in our contest
            if problem_id in PROBLEM_IDS:
                # If problem already has a winner, compare submission times
                if PROBLEM_IDS[problem_id]["claimed_by"] is not None:
                    current_winner = PROBLEM_IDS[problem_id]["claimed_by"]
                    previous_time = PROBLEM_IDS[problem_id]["first_submission_time"]

                    # If this team submitted faster, override previous winner
                    if verdict == "OK" and submission_time < previous_time:
                        print(f"Team {team} submitted {problem_id} faster than {current_winner}! Updating points.")

                        # Remove points from previous winner
                        update_leaderboard(current_winner, problem_id, remove_points=True)

                        # Assign new winner
                        PROBLEM_IDS[problem_id]["claimed_by"] = team
                        PROBLEM_IDS[problem_id]["first_submission_time"] = submission_time
                        update_leaderboard(team, problem_id, readable_time)
                    continue  # Skip if they were slower

                # If problem hasn't been claimed, award points to the first correct submission
                if verdict == "OK":
                    print(f"Team {team} solved {problem_id} first!")
                    PROBLEM_IDS[problem_id]["claimed_by"] = team
                    PROBLEM_IDS[problem_id]["first_submission_time"] = submission_time
                    update_leaderboard(team, problem_id, readable_time)

# Function to update Google Sheets leaderboard
def update_leaderboard(team, problem_id, readable_time=None, remove_points=False):
    data = sheet.get_all_records(expected_headers=["Team Name", "Score", 
    "Q1 Solved?", "Q1 Time", "Q2 Solved?", "Q2 Time", 
    "Q3 Solved?", "Q3 Time", "Q4 Solved?", "Q4 Time", 
    "Q5 Solved?", "Q5 Time"])

    for i, row in enumerate(data):
        if row["Team Name"] == team:
            score = int(row["Score"])

            if remove_points:
                score -= PROBLEM_IDS[problem_id]["points"]  # Deduct points
                col_index = list(PROBLEM_IDS.keys()).index(problem_id) * 2 + 3  # Find correct problem column
                time_col_index = col_index + 1  # Time column next to the problem

                sheet.update_cell(i + 2, 2, score)  # Update score
                sheet.update_cell(i + 2, col_index, "❌")  # Reset problem status
                sheet.update_cell(i + 2, time_col_index, "")  # Clear time
                print(f"Removed points from {team} for {problem_id}. New score: {score}")

            else:
                score += PROBLEM_IDS[problem_id]["points"]  # Add points
                col_index = list(PROBLEM_IDS.keys()).index(problem_id) * 2 + 3  # Find correct problem column
                time_col_index = col_index + 1  # Time column next to the problem

                sheet.update_cell(i + 2, 2, score)  # Update score
                sheet.update_cell(i + 2, col_index, "✅")  # Mark problem as solved
                sheet.update_cell(i + 2, time_col_index, readable_time)  # Update submission time

                print(f"Updated leaderboard: {team} now has {score} points! Solved at {readable_time}")

# Main loop (checks submissions every 5 minutes)
while True:
    check_submissions()
    print("Waiting for the next check...")
    time.sleep(30)  # Wait for 5 minutes