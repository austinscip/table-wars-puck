"""
Balanced YDKJ-style questions
Mix of absurd/educational, easy/medium/hard
ALL with clear correct answers
"""

from trivia_database import execute_query, get_placeholder, get_category_by_name

BALANCED_QUESTIONS = [
    # ===== EASY - STRAIGHTFORWARD =====
    {
        'category': 'General Knowledge',  # Need to create this category
        'setup': None,
        'question': "Which planet is known as the Red Planet?",
        'answers': {
            'A': "Mars",
            'B': "Venus",
            'C': "Jupiter",
            'D': "Mercury"
        },
        'correct': 'A',
        'explanation': "Mars appears red because of iron oxide (rust) in its soil.",
        'commentary_correct': "Correct! Mars is literally rusting in space. Metal.",
        'commentary_wrong': "Wrong! It's Mars. The red one. Come on.",
        'difficulty': 'easy',
        'time_limit': 15
    },

    # ===== EASY - ABSURD SCENARIO =====
    {
        'category': 'Ways to Die Stupidly',
        'setup': "Todd wanted to win a bet by eating 20 raw eggs in one sitting.",
        'question': "What actually happened?",
        'answers': {
            'A': "He won the bet",
            'B': "He died from salmonella",
            'C': "Nothing, eggs are safe",
            'D': "His stomach exploded (not kidding)"
        },
        'correct': 'B',
        'explanation': "Raw eggs can contain salmonella bacteria. 20 eggs = Russian roulette with food poisoning.",
        'commentary_correct': "Correct! Salmonella doesn't care about your bet. Cook your eggs, Todd.",
        'commentary_wrong': "Wrong! Salmonella got him. Raw eggs aren't a game.",
        'difficulty': 'easy',
        'time_limit': 15
    },

    # ===== MEDIUM - EDUCATIONAL SCENARIO =====
    {
        'category': 'Medical Malpractice',
        'setup': "You're scuba diving and your buddy signals he's out of air. You both rush to the surface.",
        'question': "What's the biggest danger of ascending too fast?",
        'answers': {
            'A': "Shark attack",
            'B': "The bends (nitrogen bubbles in blood)",
            'C': "Drowning",
            'D': "Hypothermia"
        },
        'correct': 'B',
        'explanation': "Ascending too fast causes nitrogen to form bubbles in your blood. It's called decompression sickness or 'the bends' and can kill you.",
        'commentary_correct': "Correct! The bends will paralyze or kill you. Slow ascent or die.",
        'commentary_wrong': "Wrong! It's the bends. Nitrogen bubbles in your blood. Very bad.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    # ===== MEDIUM - POP CULTURE =====
    {
        'category': 'Historical Dumbassery',
        'setup': None,
        'question': "Which company famously rejected the Beatles in 1962, saying 'guitar groups are on the way out'?",
        'answers': {
            'A': "Columbia Records",
            'B': "Decca Records",
            'C': "RCA Victor",
            'D': "Atlantic Records"
        },
        'correct': 'B',
        'explanation': "Decca Records rejected the Beatles. Oops.",
        'commentary_correct': "Correct! Decca passed on the Beatles. They never lived it down.",
        'commentary_wrong': "Wrong! Decca Records. Biggest miss in music history.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    # ===== HARD - SCIENCE SCENARIO =====
    {
        'category': 'Ways to Die Stupidly',
        'setup': "You're trapped in a freezer at -20°F. You have matches. What's the biggest danger?",
        'question': "What kills you first in extreme cold?",
        'answers': {
            'A': "Your blood freezing",
            'B': "Your heart stopping from cold",
            'C': "Using too much oxygen breathing faster",
            'D': "Falling asleep (hypothermia)"
        },
        'correct': 'D',
        'explanation': "Hypothermia makes you sleepy. If you fall asleep in extreme cold, you don't wake up. Your body temperature drops and you die.",
        'commentary_correct': "Correct! Hypothermia makes you want to sleep. That sleep is permanent.",
        'commentary_wrong': "Wrong! You fall asleep from hypothermia and never wake up.",
        'difficulty': 'hard',
        'time_limit': 15
    },

    # ===== HARD - HISTORICAL FACT =====
    {
        'category': 'Historical Dumbassery',
        'setup': None,
        'question': "In 1788, the Austrian army accidentally attacked and killed 10,000 of their own soldiers. What caused it?",
        'answers': {
            'A': "Fog and confusion",
            'B': "They got drunk and started a brawl",
            'C': "Language barriers between units",
            'D': "Friendly fire from new weapons"
        },
        'correct': 'B',
        'explanation': "The Battle of Karánsebes: Austrian soldiers got drunk, started fighting over alcohol, and in the chaos thought they were being attacked by Turks. They attacked each other.",
        'commentary_correct': "Correct! They got drunk and killed 10,000 of their own men. Peak stupidity.",
        'commentary_wrong': "Wrong! They got wasted and killed each other. Look it up.",
        'difficulty': 'hard',
        'time_limit': 15
    },

    # ===== EASY - COMMON KNOWLEDGE =====
    {
        'category': 'General Knowledge',
        'setup': None,
        'question': "How many strings does a standard guitar have?",
        'answers': {
            'A': "4",
            'B': "5",
            'C': "6",
            'D': "7"
        },
        'correct': 'C',
        'explanation': "Standard guitars have 6 strings.",
        'commentary_correct': "Correct! 6 strings. Even if you've never played guitar.",
        'commentary_wrong': "Wrong! It's 6. Have you never seen a guitar?",
        'difficulty': 'easy',
        'time_limit': 15
    },

    # ===== MEDIUM - ABSURD BUT REAL =====
    {
        'category': 'Things That Got Banned',
        'setup': "In 2007, this toy was banned because kids kept swallowing the magnets.",
        'question': "What happens when you swallow two magnets?",
        'answers': {
            'A': "Nothing, they pass through",
            'B': "They attract through your intestine walls and tear them",
            'C': "You become magnetic",
            'D': "They dissolve in stomach acid"
        },
        'correct': 'B',
        'explanation': "Magnets attract each other THROUGH your intestine walls, pinching and tearing tissue. Requires surgery.",
        'commentary_correct': "Correct! Magnets pinch your intestines together. Surgery required.",
        'commentary_wrong': "Wrong! They attract through intestine walls and tear them apart.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    # ===== MEDIUM - SCIENTIFIC FACT =====
    {
        'category': 'Medical Malpractice',
        'setup': None,
        'question': "What percentage of your body weight is water?",
        'answers': {
            'A': "30%",
            'B': "50%",
            'C': "60%",
            'D': "80%"
        },
        'correct': 'C',
        'explanation': "The human body is about 60% water by weight.",
        'commentary_correct': "Correct! You're basically a sentient water balloon.",
        'commentary_wrong': "Wrong! It's 60%. You're mostly water, buddy.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    # ===== HARD - OBSCURE BUT REAL =====
    {
        'category': 'Rejected Inventions',
        'setup': "In the 1950s, someone invented a baby cage you hang OUTSIDE your apartment window.",
        'question': "Why did they think this was a good idea?",
        'answers': {
            'A': "Fire safety (escape route)",
            'B': "Fresh air for city babies",
            'C': "Sun exposure for vitamin D",
            'D': "Noise reduction inside"
        },
        'correct': 'B',
        'explanation': "Parents in cramped city apartments hung babies in cages outside windows for 'fresh air'. This was actually real in the 1930s-50s.",
        'commentary_correct': "Correct! City parents hung babies in window cages. Wild times.",
        'commentary_wrong': "Wrong! It was for 'fresh air'. Yes, really.",
        'difficulty': 'hard',
        'time_limit': 15
    }
]


def seed_balanced_questions():
    """Seed database with balanced question mix"""

    # First create General Knowledge category if it doesn't exist
    ph = get_placeholder()

    try:
        execute_query(f'''
            INSERT OR IGNORE INTO trivia_categories (name, emoji, description, difficulty)
            VALUES ({ph}, {ph}, {ph}, {ph})
        ''', ('General Knowledge', '🧠', 'Everyday knowledge everyone should know', 'easy'))
    except:
        pass

    # Seed questions
    added = 0
    for q in BALANCED_QUESTIONS:
        category = get_category_by_name(q['category'])

        if not category:
            print(f"⚠️  Category '{q['category']}' not found, skipping question")
            continue

        try:
            execute_query(f'''
                INSERT INTO trivia_questions
                (category_id, question_text, setup_text, answer_a, answer_b, answer_c, answer_d,
                 correct_answer, difficulty, time_limit, explanation,
                 host_commentary_correct, host_commentary_wrong)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            ''', (
                category['id'],
                q['question'],
                q['setup'] or '',
                q['answers']['A'],
                q['answers']['B'],
                q['answers']['C'],
                q['answers']['D'],
                q['correct'],
                q['difficulty'],
                q['time_limit'],
                q['explanation'],
                q['commentary_correct'],
                q['commentary_wrong']
            ))
            added += 1
        except Exception as e:
            print(f"⚠️  Error adding question: {str(e)}")

    print(f"✅ Added {added} balanced questions")


if __name__ == '__main__':
    from trivia_database import init_trivia_database, seed_trivia_data
    init_trivia_database()
    seed_trivia_data()
    seed_balanced_questions()
    print("Done!")
