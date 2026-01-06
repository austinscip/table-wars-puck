"""
REWRITE ALL DIRECT QUESTIONS TO GANGRENE-STYLE INDIRECT
Converting factual questions into scenario-based immersive questions
"""

from trivia_database import execute_query, get_placeholder

# Map of old question text to new indirect version
REWRITES = [
    # ===== FROM BATCH 1 =====

    {
        'old_question': "Which planet is known as the Red Planet?",
        'new_setup': "You're on a first date at a planetarium. Your date points to a rusty-looking sphere and asks which planet that is.",
        'new_question': "What do you tell them to sound smart?",
        'new_answers': {
            'A': "Mars",
            'B': "Venus",
            'C': "Jupiter",
            'D': "Mercury"
        },
        'correct': 'A',
        'new_commentary_correct': "Correct! Mars = red planet. Your date is impressed. Maybe a second date?",
        'new_commentary_wrong': "Wrong! It's Mars. Your date thinks you're an idiot. No second date."
    },

    {
        'old_question': "Which company famously rejected the Beatles in 1962, saying 'guitar groups are on the way out'?",
        'new_setup': "You're arguing with a boomer music exec who claims record labels never make mistakes.",
        'new_question': "Which company do you bring up to destroy their argument?",
        'new_answers': {
            'A': "Columbia Records",
            'B': "Decca Records",
            'C': "RCA Victor",
            'D': "Atlantic Records"
        },
        'correct': 'B',
        'new_commentary_correct': "Correct! Decca rejected the Beatles. Boomer exec has no comeback. You win.",
        'new_commentary_wrong': "Wrong! Decca Records. Your argument collapses. Boomer wins."
    },

    {
        'old_question': "How many strings does a standard guitar have?",
        'new_setup': "You're at Guitar Center pretending you know how to play. The salesperson asks how many strings you need.",
        'new_question': "What's the standard number so you don't look like an idiot?",
        'new_answers': {
            'A': "4",
            'B': "5",
            'C': "6",
            'D': "7"
        },
        'correct': 'C',
        'new_commentary_correct': "Correct! 6 strings. Salesperson believes you. Crisis averted.",
        'new_commentary_wrong': "Wrong! It's 6. Salesperson knows you're a poser. Get out of the store."
    },

    {
        'old_question': "What percentage of your body weight is water?",
        'new_setup': "You're dehydrated at a music festival. Your friend says 'dude, you're like mostly water, drink something.'",
        'new_question': "What percentage of you is actually water?",
        'new_answers': {
            'A': "30%",
            'B': "50%",
            'C': "60%",
            'D': "80%"
        },
        'correct': 'C',
        'new_commentary_correct': "Correct! 60% water. You're basically a sentient puddle. Drink up.",
        'new_commentary_wrong': "Wrong! 60%. Your body is mostly water. Hydrate or die."
    },

    # ===== FROM BATCH 2 =====

    {
        'old_question': "What caused it?",  # Dancing Plague
        'new_setup': "You're a medieval doctor in 1518 Strasbourg. Hundreds of people are dancing uncontrollably for days, some to death.",
        'new_question': "What's your diagnosis?",
        'new_answers': {
            'A': "Mass psychogenic illness (dancing plague)",
            'B': "Contaminated bread with ergot fungus",
            'C': "A cult ritual gone wrong",
            'D': "Party drugs in the medieval wine"
        },
        'correct': 'A',
        'new_commentary_correct': "Correct! Mass hysteria. They literally danced themselves to death. Medieval times were weird.",
        'new_commentary_wrong': "Wrong! It was mass psychogenic illness. The dancing plague of 1518 was real."
    },

    {
        'old_question': "What was the main killer?",  # Napoleon Russia
        'new_setup': "You're Napoleon's military advisor in 1812. 600,000 soldiers invaded Russia, but only 10,000 made it back.",
        'new_question': "What killed 590,000 of your men?",
        'new_answers': {
            'A': "Winter, starvation, and disease (not combat)",
            'B': "Russian military superiority",
            'C': "Ambushes and guerrilla warfare",
            'D': "Friendly fire and poor leadership"
        },
        'correct': 'A',
        'new_commentary_correct': "Correct! Winter killed your army. Never invade Russia in winter, dummy.",
        'new_commentary_wrong': "Wrong! Winter, starvation, disease. Russia wins by freezing you to death."
    },

    {
        'old_question': "Why?",  # Kinder Eggs
        'new_setup': "You're at the Canadian border with a suitcase full of Kinder Surprise eggs. US Customs stops you.",
        'new_question': "Why are they confiscating your chocolate?",
        'new_answers': {
            'A': "Non-edible objects inside food violate FDA law",
            'B': "Choking hazard killed 12 kids",
            'C': "Chocolate quality too low",
            'D': "Trade war with Europe"
        },
        'correct': 'A',
        'new_commentary_correct': "Correct! FDA bans non-food inside food. Your Kinder eggs are contraband.",
        'new_commentary_wrong': "Wrong! FDA law bans toys inside food. You're going to chocolate jail."
    },

    {
        'old_question': "What was the reason?",  # Singapore Gum
        'new_setup': "You're in Singapore chewing gum. A cop stops you and says it's been banned since 1992.",
        'new_question': "What incident got gum banned nationwide?",
        'new_answers': {
            'A': "People stuck gum on subway sensors, breaking the system",
            'B': "Health concerns about artificial sweeteners",
            'C': "Too much litter on sidewalks",
            'D': "Religious opposition to mint flavoring"
        },
        'correct': 'A',
        'new_commentary_correct': "Correct! Gum vandalism broke the subway. Singapore said 'no more gum ever.'",
        'new_commentary_wrong': "Wrong! Gum on subway sensors = total ban. Singapore doesn't play."
    },

    {
        'old_question': "What does HTTP stand for?",
        'new_setup': "You're in a tech job interview. The interviewer asks what protocol your web browser uses to fetch cat videos.",
        'new_question': "What do you say?",
        'new_answers': {
            'A': "HyperText Transfer Protocol",
            'B': "High Tech Transmission Process",
            'C': "HyperText Transport Program",
            'D': "Host Transfer Text Protocol"
        },
        'correct': 'A',
        'new_commentary_correct': "Correct! HyperText Transfer Protocol. You got the job. Congrats.",
        'new_commentary_wrong': "Wrong! It's HyperText Transfer Protocol. Interview over. Try Wendy's."
    },

    {
        'old_question': "How many bones does an adult human have?",
        'new_setup': "You're in med school. First day of anatomy class. Professor points to a skeleton and asks how many bones you'll need to memorize.",
        'new_question': "What's the number?",
        'new_answers': {
            'A': "206",
            'B': "187",
            'C': "215",
            'D': "192"
        },
        'correct': 'A',
        'new_commentary_correct': "Correct! 206 bones. You might survive med school after all.",
        'new_commentary_wrong': "Wrong! 206 bones. The professor shakes their head. You're doomed."
    },

    {
        'old_question': "What was it marketed as?",  # Radithor
        'new_setup': "It's 1920. A salesman offers you 'Radithor' - bottled water with radium in it.",
        'new_question': "What's his sales pitch?",
        'new_answers': {
            'A': "A miracle cure-all tonic for energy and virility",
            'B': "Cleaning solution for tough stains",
            'C': "Pain relief for arthritis",
            'D': "Scientific experiment gone wrong"
        },
        'correct': 'A',
        'new_commentary_correct': "Correct! Radioactive health tonic. People's jaws fell off. The 1920s were wild.",
        'new_commentary_wrong': "Wrong! It was a 'cure-all' tonic. Radioactive water for virility. Everyone died."
    },

    {
        'old_question': "What's the penalty?",  # Alaska Bear
        'new_setup': "You're hiking in Alaska and see a sleeping bear. Your friend wants to wake it up for a selfie.",
        'new_question': "What's the legal penalty if you let them do it?",
        'new_answers': {
            'A': "Up to $10,000 fine and jail time",
            'B': "Just a warning",
            'C': "The bear gets to keep your camera",
            'D': "Community service cleaning parks"
        },
        'correct': 'A',
        'new_commentary_correct': "Correct! $10K fine and jail. Plus the bear might eat you. Double penalty.",
        'new_commentary_wrong': "Wrong! Up to $10,000 and jail time. Plus death by bear. Don't wake bears."
    }
]


def update_questions_to_indirect():
    """Update all direct questions to gangrene-style indirect"""
    updated = 0
    ph = get_placeholder()

    for rewrite in REWRITES:
        try:
            # Find the question by old question text
            old_q = rewrite['old_question']

            # Update to new indirect version
            execute_query(f'''
                UPDATE trivia_questions
                SET setup_text = {ph},
                    question_text = {ph},
                    host_commentary_correct = {ph},
                    host_commentary_wrong = {ph}
                WHERE question_text = {ph}
                   OR question_text LIKE {ph}
            ''', (
                rewrite['new_setup'],
                rewrite['new_question'],
                rewrite['new_commentary_correct'],
                rewrite['new_commentary_wrong'],
                old_q,
                f'%{old_q[:20]}%'  # Partial match in case of variations
            ))

            updated += 1
            print(f"✅ Updated: {old_q[:50]}...")

        except Exception as e:
            print(f"⚠️  Error updating '{rewrite['old_question'][:30]}...': {str(e)}")

    print(f"\n✅ Successfully converted {updated} questions to indirect gangrene-style")
    return updated


if __name__ == '__main__':
    from trivia_database import init_trivia_database
    init_trivia_database()
    update_questions_to_indirect()

    print("\n" + "="*60)
    print("ALL QUESTIONS NOW GANGRENE-STYLE INDIRECT!")
    print("="*60)
    print("\nExamples of transformations:")
    print("\n❌ OLD: 'Which planet is known as the Red Planet?'")
    print("✅ NEW: 'You're on a first date at a planetarium...'")
    print("         'What do you tell them to sound smart?'")
    print("\n❌ OLD: 'What does HTTP stand for?'")
    print("✅ NEW: 'You're in a tech job interview...'")
    print("         'What protocol does your browser use?'")
