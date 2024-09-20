import praw
import re
import tkinter as tk
from tkinter import scrolledtext

# Fixed player data file (adjust the file path accordingly)
PLAYER_DATA_FILE = 'players.txt'

# Initialize Reddit API client
reddit = praw.Reddit(
        client_id='X',
        client_secret='X',
        user_agent='X'
    )

import re


def load_player_data(PLAYER_DATA_FILE):
    player_data = {}
    current_party = None
    party_pattern = re.compile(
        r"^(.*?)(\s*\(\d+\))?$")  # Regex to capture party name and ignore the number in parentheses

    with open(PLAYER_DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # If the line contains a party, it will end with a number in parentheses
            if line.endswith(')'):
                match = party_pattern.match(line)
                if match:
                    current_party = match.group(1).strip()  # Extract the party name without the number
                continue

            # Skip empty lines
            if not line:
                continue

            # Split player data
            fields = line.split('\t')
            if len(fields) < 4:
                print(f"Warning: skipping invalid line {line}")
                continue

            # Extract player information
            player_name = fields[0].strip()
            constituency = fields[1].strip()
            region = fields[2].strip()
            start_date = fields[3].strip()
            end_date = fields[4].strip() if len(fields) > 4 else None  # End date is optional

            # Add player data to dictionary
            player_data[player_name.lower()] = {
                'author': player_name,
                'party': current_party,
                'constituency': constituency,
                'region': region,
                'start_date': start_date,
                'end_date': end_date
            }

    return player_data


# Example usage:
data = load_player_data(PLAYER_DATA_FILE)
for player, info in data.items():
    print(f"{player}: {info}")


def analyze_votes(submission, player_data):
    votes = {}
    all_votes = {}
    invalid_votes = []  # List to track invalid votes

    # Regex patterns for aye, nay, abstain (in English and French)
    aye_pattern = re.compile(r'\b(aye|oui|yea)\b', re.IGNORECASE)
    nay_pattern = re.compile(r'\b(nay|non|contre|no)\b', re.IGNORECASE)
    abstain_pattern = re.compile(r'\b(abstain|abstention)\b', re.IGNORECASE)

    # Fetch all comments in the post
    submission.comments.replace_more(limit=None)
    for comment in submission.comments.list():
        author = comment.author.name.lower() if comment.author else None

        if not author:
            continue  # Skip if author is None or deleted

        # Check for 'aye', 'nay', or 'abstain' in comment, case-insensitive
        comment_text = comment.body.lower()
        if aye_pattern.search(comment_text) or nay_pattern.search(comment_text) or abstain_pattern.search(comment_text):
            if author in player_data:
                player_info = player_data[author]
                if player_info.get('end_date') is not None:  # Check if end_date exists
                    invalid_votes.append(author)  # Treat as an invalid vote
                    continue

                if aye_pattern.search(comment_text):
                    vote_type = 'aye'
                elif nay_pattern.search(comment_text):
                    vote_type = 'nay'
                else:
                    vote_type = 'abstain'

                party = player_info['party']
                constituency = player_info['constituency']
                votes[author] = (vote_type, party, constituency, comment.created_utc)
            else:
                invalid_votes.append(author)  # Track invalid vote if author is not in player_data

        # Store all votes for detailed breakdown
        all_votes[author] = (comment_text, player_data.get(author, "Unknown"))

    return votes, all_votes, invalid_votes



def display_vote_breakdown(final_votes, all_votes, player_data, invalid_votes):
    # Clear the text box
    breakdown_box.config(state=tk.NORMAL)
    breakdown_box.delete(1.0, tk.END)

    # Tally the votes
    tally = {'Aye': 0, 'Nay': 0, 'Abstain': 0}
    party_tally = {}

    # Detailed Breakdown with Line Highlighting
    for author, vote_info in all_votes.items():
        if author.lower() == 'automoderator':
            continue  # Skip comments by 'autoModerator'

        comment_text = vote_info[0]
        vote_type = final_votes.get(author, (None,))[0]  # Get vote type, default to None

        # Get player data
        if author in player_data:
            data = player_data[author]
            riding = data.get('constituency', "Unknown")
            party = data.get('party', "Unknown")
            end_date = data.get('end_date')

            # If player has an end_date, treat them as invalid
            if end_date is not None:
                invalid_votes.append(author)
                continue  # Skip to next iteration
        else:
            riding = "Unknown"
            party = "Unknown"

        # Build the line text
        line_text = f"({riding})\t{author.capitalize()} [{party}]: {comment_text}\n"

        # Highlight the line based on vote type
        if vote_type == 'aye':
            breakdown_box.insert(tk.END, line_text, 'green_bg')
        elif vote_type == 'nay':
            breakdown_box.insert(tk.END, line_text, 'red_bg')
        elif vote_type == 'abstain':
            breakdown_box.insert(tk.END, line_text, 'yellow_bg')

        # Tally Votes
        if vote_type and vote_type.capitalize() in tally:
            tally[vote_type.capitalize()] += 1

            # Update party tally
            if party not in party_tally:
                party_tally[party] = {'Aye': 0, 'Nay': 0, 'Abstain': 0, 'No Vote': 0}
            party_tally[party][vote_type.capitalize()] += 1

    # Calculate number of people who haven't voted
    voted_people = set(final_votes.keys())
    all_people = set(player_data.keys())
    not_voted = all_people - voted_people

    # Handle non-voters
    for name in not_voted:
        if name in player_data:
            data = player_data[name]
            riding = data.get('constituency', "Unknown")
            party = data.get('party', "Unknown")
            end_date = data.get('end_date')

            # Skip if the player has an end_date (no longer active)
            if end_date is not None:
                continue

            if party not in party_tally:
                party_tally[party] = {'Aye': 0, 'Nay': 0, 'Abstain': 0, 'No Vote': 1}
            else:
                party_tally[party]['No Vote'] += 1

    # Final Tally Output
    tally_box.delete(1.0, tk.END)
    tally_text = "\nTally of Votes:\n"
    tally_text += f"Aye: {tally['Aye']}\n"
    tally_text += f"Nay: {tally['Nay']}\n"
    tally_text += f"Abstain: {tally['Abstain']}\n"

    # Party breakdown
    tally_text += "\nParty Breakdown:\n"
    for party, counts in party_tally.items():
        tally_text += f"{party}: Aye: {counts['Aye']}, Nay: {counts['Nay']}, Abstain: {counts['Abstain']}, No Vote: {counts['No Vote']}\n"

    tally_text += f"\nNumber of people who haven't voted: {len(not_voted)}\n"

    tally_box.insert(tk.END, tally_text)

    # Display invalid votes
    if invalid_votes:
        for invalid_voter in invalid_votes:
            if invalid_voter.lower() == 'automoderator':  # Skip autoModerator here as well
                continue
            breakdown_box.insert(tk.END, f"{invalid_voter.capitalize()} voted invalidly.\n", 'no_vote_bg')

    # Make the breakdown read-only after updating it
    breakdown_box.config(state=tk.DISABLED)



def analyze_votes_gui():
    reddit_link = entry_link.get()  # Get the Reddit link from the input box

    # Load player data from the fixed player file
    player_data = load_player_data(PLAYER_DATA_FILE)

    # Get the Reddit submission from the link
    submission = reddit.submission(url=reddit_link)

    # Analyze votes
    final_votes, all_votes, invalid_votes = analyze_votes(submission, player_data)

    # Display the results and tally, including invalid votes
    display_vote_breakdown(final_votes, all_votes, player_data, invalid_votes)



# Create the GUI window
root = tk.Tk()
root.title("Reddit Vote Analyzer")

# Link entry
tk.Label(root, text="Enter Reddit Post Link:").pack(pady=5)
entry_link = tk.Entry(root, width=50)
entry_link.pack(pady=5)

# Analyze button
analyze_button = tk.Button(root, text="Analyze Votes", command=analyze_votes_gui)
analyze_button.pack(pady=10)

# Breakdown text box (scrollable)
tk.Label(root, text="Breakdown of All Votes:").pack(pady=5)
breakdown_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=80, height=15)
breakdown_box.pack(pady=5)

# Tally text box (scrollable)
tk.Label(root, text="Tally of Votes:").pack(pady=5)
tally_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=15)
tally_box.pack(pady=5)

# Text tag configuration for line highlighting
breakdown_box.tag_configure('green_bg', background='lightgreen', foreground='black')
breakdown_box.tag_configure('red_bg', background='lightcoral', foreground='black')
breakdown_box.tag_configure('yellow_bg', background='lightyellow', foreground='black')
breakdown_box.tag_configure('no_vote_bg', background='lightgray', foreground='black')  # New tag for no votes


# Start the GUI event loop
root.mainloop()
