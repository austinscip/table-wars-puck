"""
TRIVIA WARS - Improved Questions Database
Educational blend with variety for different game types
"""

from trivia_database import execute_query, get_placeholder, get_category_by_name

# Improved questions with educational value + entertainment
IMPROVED_QUESTIONS = [
    # ========================================
    # SCIENCE & NATURE (Educational)
    # ========================================
    {
        'category': 'Rejected Inventions',  # Repurpose as Science
        'setup': "",
        'question': "What is the most abundant gas in Earth's atmosphere?",
        'answers': {
            'A': "Oxygen",
            'B': "Carbon Dioxide",
            'C': "Nitrogen",
            'D': "Hydrogen"
        },
        'correct': 'C',
        'explanation': "Nitrogen makes up 78% of Earth's atmosphere. Oxygen is only 21%.",
        'commentary_correct': "Correct! Nitrogen is 78%. Oxygen gets all the credit but nitrogen does the heavy lifting.",
        'commentary_wrong': "Nope! It's nitrogen at 78%. Oxygen is only 21% - nitrogen is the majority shareholder here.",
        'difficulty': 'easy',
        'time_limit': 12
    },

    {
        'category': 'Rejected Inventions',
        'setup': "You're standing at the base of Mount Everest.",
        'question': "Approximately how tall is Mount Everest?",
        'answers': {
            'A': "15,000 feet",
            'B': "20,000 feet",
            'C': "29,000 feet",
            'D': "35,000 feet"
        },
        'correct': 'C',
        'explanation': "Mount Everest is 29,032 feet (8,849 meters) tall - the highest point on Earth.",
        'commentary_correct': "Right! 29,032 feet. That's 5.5 miles straight up. Bring a jacket.",
        'commentary_wrong': "Wrong! It's 29,032 feet - about 5.5 miles tall. Your lungs would hate you up there.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Rejected Inventions',
        'setup': "",
        'question': "How long does it take light from the Sun to reach Earth?",
        'answers': {
            'A': "Instantly",
            'B': "8 minutes",
            'C': "1 hour",
            'D': "24 hours"
        },
        'correct': 'B',
        'explanation': "Light travels at 186,000 miles/second and takes about 8 minutes to travel 93 million miles to Earth.",
        'commentary_correct': "Correct! 8 minutes. Which means when you see the sun, you're looking 8 minutes into the past.",
        'commentary_wrong': "Nope! It's 8 minutes. Light is fast, but space is big. Really big.",
        'difficulty': 'easy',
        'time_limit': 12
    },

    {
        'category': 'Rejected Inventions',
        'setup': "",
        'question': "What is the chemical symbol for gold?",
        'answers': {
            'A': "Go",
            'B': "Gd",
            'C': "Au",
            'D': "Ag"
        },
        'correct': 'C',
        'explanation': "Au comes from the Latin word 'aurum' meaning gold. Ag is silver, by the way.",
        'commentary_correct': "Yes! Au from aurum. Latin is dead but still useful for chemistry.",
        'commentary_wrong': "Wrong! It's Au (from aurum). Ag is silver if you were wondering.",
        'difficulty': 'medium',
        'time_limit': 12
    },

    {
        'category': 'Rejected Inventions',
        'setup': "A blue whale's heart is about the size of:",
        'question': "How big is it really?",
        'answers': {
            'A': "A basketball",
            'B': "A small car",
            'C': "A refrigerator",
            'D': "A phone booth"
        },
        'correct': 'B',
        'explanation': "A blue whale's heart weighs about 400 pounds and is the size of a small car. It beats 5-6 times per minute.",
        'commentary_correct': "Right! Small car-sized heart. And it only beats 5-6 times per minute. Chill whale.",
        'commentary_wrong': "Nope! It's car-sized - about 400 pounds. Blue whales don't mess around.",
        'difficulty': 'hard',
        'time_limit': 15
    },

    # ========================================
    # HISTORY & GEOGRAPHY (Educational)
    # ========================================
    {
        'category': 'Historical Dumbassery',  # Repurpose as History
        'setup': "",
        'question': "In what year did World War II end?",
        'answers': {
            'A': "1943",
            'B': "1945",
            'C': "1947",
            'D': "1950"
        },
        'correct': 'B',
        'explanation': "World War II ended in 1945 with Germany's surrender in May and Japan's in September.",
        'commentary_correct': "Correct! 1945. VE Day in May, VJ Day in September. History class wasn't for nothing!",
        'commentary_wrong': "Wrong! It's 1945. Germany surrendered in May, Japan in September. The history books don't lie.",
        'difficulty': 'easy',
        'time_limit': 12
    },

    {
        'category': 'Historical Dumbassery',
        'setup': "",
        'question': "What is the capital of Australia?",
        'answers': {
            'A': "Sydney",
            'B': "Melbourne",
            'C': "Canberra",
            'D': "Perth"
        },
        'correct': 'C',
        'explanation': "Canberra is the capital. Sydney and Melbourne couldn't agree who should be capital, so they built Canberra between them.",
        'commentary_correct': "Yes! Canberra. Sydney and Melbourne fought over it, so they compromised with Canberra.",
        'commentary_wrong': "Nope! Everyone thinks Sydney, but it's Canberra. Melbourne and Sydney compromised on it.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Historical Dumbassery',
        'setup': "",
        'question': "How many states are in the United States?",
        'answers': {
            'A': "48",
            'B': "50",
            'C': "52",
            'D': "51"
        },
        'correct': 'B',
        'explanation': "50 states. Alaska and Hawaii joined in 1959, making it 50.",
        'commentary_correct': "Right! 50 states. If you missed this, we need to have a talk about your education.",
        'commentary_wrong': "It's 50! Come on, this is basic geography. Alaska and Hawaii are the last two.",
        'difficulty': 'easy',
        'time_limit': 10
    },

    {
        'category': 'Historical Dumbassery',
        'setup': "",
        'question': "The Great Wall of China was built primarily to defend against:",
        'answers': {
            'A': "Mongol invasions",
            'B': "Japanese invasions",
            'C': "Korean invasions",
            'D': "Russian invasions"
        },
        'correct': 'A',
        'explanation': "Built mainly to protect against Mongol and other nomadic invasions from the north.",
        'commentary_correct': "Correct! Mongols from the north. Turns out a big wall helps with that.",
        'commentary_wrong': "Wrong! It was the Mongols. The wall was built to keep northern nomads out.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Historical Dumbassery',
        'setup': "",
        'question': "Who was the first President of the United States?",
        'answers': {
            'A': "Thomas Jefferson",
            'B': "Benjamin Franklin",
            'C': "George Washington",
            'D': "John Adams"
        },
        'correct': 'C',
        'explanation': "George Washington, 1789-1797. The OG president.",
        'commentary_correct': "Yes! George Washington. You know, the guy on the dollar bill.",
        'commentary_wrong': "It's George Washington! Come on, he's literally on the $1 bill.",
        'difficulty': 'easy',
        'time_limit': 10
    },

    # ========================================
    # POP CULTURE & ENTERTAINMENT
    # ========================================
    {
        'category': 'Florida Man Headlines',  # Repurpose as Pop Culture
        'setup': "",
        'question': "In The Matrix, which color pill does Neo take?",
        'answers': {
            'A': "Red",
            'B': "Blue",
            'C': "Green",
            'D': "Purple"
        },
        'correct': 'A',
        'explanation': "Neo takes the red pill to see reality. The blue pill would have kept him in the Matrix.",
        'commentary_correct': "Red pill! Welcome to reality. Should've taken the blue pill and stayed in bed.",
        'commentary_wrong': "Wrong! It's the red pill. Blue pill = stay asleep, red pill = wake up to reality.",
        'difficulty': 'easy',
        'time_limit': 12
    },

    {
        'category': 'Florida Man Headlines',
        'setup': "",
        'question': "Who directed the movie 'Jurassic Park'?",
        'answers': {
            'A': "George Lucas",
            'B': "Steven Spielberg",
            'C': "James Cameron",
            'D': "Christopher Nolan"
        },
        'correct': 'B',
        'explanation': "Steven Spielberg directed Jurassic Park in 1993. Dinosaurs eating people never looked so good.",
        'commentary_correct': "Spielberg! The man, the myth, the dinosaur director.",
        'commentary_wrong': "Wrong! Steven Spielberg made the dinos come alive in 1993.",
        'difficulty': 'easy',
        'time_limit': 12
    },

    {
        'category': 'Florida Man Headlines',
        'setup': "",
        'question': "What year did the first iPhone come out?",
        'answers': {
            'A': "2005",
            'B': "2007",
            'C': "2009",
            'D': "2010"
        },
        'correct': 'B',
        'explanation': "2007. Steve Jobs changed everything with a phone that actually worked.",
        'commentary_correct': "2007! The year smartphones became actually smart. RIP flip phones.",
        'commentary_wrong': "Nope! 2007. The year everything changed and we all became phone zombies.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Florida Man Headlines',
        'setup': "",
        'question': "How many Harry Potter books are there?",
        'answers': {
            'A': "5",
            'B': "6",
            'C': "7",
            'D': "8"
        },
        'correct': 'C',
        'explanation': "7 main books. Cursed Child doesn't count because reasons.",
        'commentary_correct': "Seven! The perfect magical number. Cursed Child is fan fiction, fight me.",
        'commentary_wrong': "It's 7! From Sorcerer's Stone to Deathly Hallows. Cursed Child doesn't count.",
        'difficulty': 'easy',
        'time_limit': 12
    },

    {
        'category': 'Florida Man Headlines',
        'setup': "",
        'question': "What is the highest-grossing movie of all time?",
        'answers': {
            'A': "Titanic",
            'B': "Avatar",
            'C': "Avengers: Endgame",
            'D': "Star Wars"
        },
        'correct': 'B',
        'explanation': "Avatar with $2.9 billion. Blue people on a blue planet made ALL the money.",
        'commentary_correct': "Avatar! James Cameron and his blue people won the money race.",
        'commentary_wrong': "Wrong! Avatar at $2.9B. Those blue people made serious cash.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    # ========================================
    # GENERAL KNOWLEDGE & QUICK FACTS
    # ========================================
    {
        'category': 'Terrible Life Advice',  # Repurpose as General Knowledge
        'setup': "",
        'question': "How many days are in a leap year?",
        'answers': {
            'A': "364",
            'B': "365",
            'C': "366",
            'D': "367"
        },
        'correct': 'C',
        'explanation': "366 days in a leap year. Extra day in February every 4 years.",
        'commentary_correct': "366! That bonus February 29th every 4 years. Happy birthday leap day babies.",
        'commentary_wrong': "It's 366! We add a day to February every 4 years. Math is hard.",
        'difficulty': 'easy',
        'time_limit': 10
    },

    {
        'category': 'Terrible Life Advice',
        'setup': "",
        'question': "What does 'HTTP' stand for?",
        'answers': {
            'A': "HyperText Transfer Protocol",
            'B': "High Technology Text Program",
            'C': "Home Tool Transfer Platform",
            'D': "Hyper Transfer Text Process"
        },
        'correct': 'A',
        'explanation': "HyperText Transfer Protocol - the foundation of web communication.",
        'commentary_correct': "Correct! The protocol that makes the internet work. You're welcome.",
        'commentary_wrong': "Wrong! HyperText Transfer Protocol. It's how your browser talks to websites.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Terrible Life Advice',
        'setup': "",
        'question': "What is the freezing point of water in Celsius?",
        'answers': {
            'A': "-10°C",
            'B': "0°C",
            'C': "10°C",
            'D': "32°C"
        },
        'correct': 'B',
        'explanation': "0°C (32°F). Water freezes at zero. The metric system makes sense.",
        'commentary_correct': "Zero! Nice and simple. Unlike Fahrenheit which is 32° because... reasons.",
        'commentary_wrong': "It's 0°C! Water freezes at zero. Celsius is logical like that.",
        'difficulty': 'easy',
        'time_limit': 10
    },

    {
        'category': 'Terrible Life Advice',
        'setup': "",
        'question': "How many bones are in the adult human body?",
        'answers': {
            'A': "186",
            'B': "206",
            'C': "226",
            'D': "246"
        },
        'correct': 'B',
        'explanation': "206 bones in adults. Babies have more (~270) but they fuse as you grow.",
        'commentary_correct': "206! Babies have more but they fuse together. Growing up = fewer bones.",
        'commentary_wrong': "Wrong! 206 bones. Babies start with ~270 but they fuse as you age.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Terrible Life Advice',
        'setup': "",
        'question': "What is the powerhouse of the cell?",
        'answers': {
            'A': "Nucleus",
            'B': "Mitochondria",
            'C': "Ribosome",
            'D': "Cell membrane"
        },
        'correct': 'B',
        'explanation': "Mitochondria - the only thing you remember from biology class.",
        'commentary_correct': "Mitochondria! You remembered! Biology teachers everywhere are proud.",
        'commentary_wrong': "It's mitochondria! THE most famous thing from biology class.",
        'difficulty': 'easy',
        'time_limit': 10
    },

    # ========================================
    # MATH & LOGIC (Quick Thinking)
    # ========================================
    {
        'category': 'Things That Got Banned',  # Repurpose as Math/Logic
        'setup': "",
        'question': "What is 15% of 200?",
        'answers': {
            'A': "20",
            'B': "25",
            'C': "30",
            'D': "35"
        },
        'correct': 'C',
        'explanation': "200 × 0.15 = 30. Or think of it as 10% (20) + 5% (10) = 30.",
        'commentary_correct': "30! Quick math: 10% of 200 is 20, plus half of that (10) = 30.",
        'commentary_wrong': "It's 30! Move that decimal: 200 × 0.15 = 30. Math works.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Things That Got Banned',
        'setup': "",
        'question': "If you flip a coin twice, what's the probability of getting heads both times?",
        'answers': {
            'A': "1/2",
            'B': "1/3",
            'C': "1/4",
            'D': "1/8"
        },
        'correct': 'C',
        'explanation': "1/2 × 1/2 = 1/4. Each flip is independent at 50%, together it's 25%.",
        'commentary_correct': "1/4! Each flip is 50%, so 1/2 × 1/2 = 1/4. Probability 101.",
        'commentary_wrong': "Wrong! It's 1/4. Independent events: 1/2 × 1/2 = 1/4 or 25%.",
        'difficulty': 'medium',
        'time_limit': 12
    },

    {
        'category': 'Things That Got Banned',
        'setup': "You have a 3-gallon jug and a 5-gallon jug.",
        'question': "Can you measure exactly 4 gallons?",
        'answers': {
            'A': "Yes",
            'B': "No",
            'C': "Only with a third jug",
            'D': "Only if you have a scale"
        },
        'correct': 'A',
        'explanation': "Fill 5-gal, pour into 3-gal (leaving 2 in 5-gal). Empty 3-gal, pour 2-gal in. Fill 5-gal again, top off the 3-gal (taking 1). You have 4 left!",
        'commentary_correct': "Yes! Classic puzzle. Takes a few pours but it works. Die Hard fans know this one.",
        'commentary_wrong': "You can! Fill 5, pour to 3, empty 3, pour remainder, fill 5, top off 3 = 4 gallons left.",
        'difficulty': 'hard',
        'time_limit': 20
    },

    {
        'category': 'Things That Got Banned',
        'setup': "",
        'question': "What is the square root of 144?",
        'answers': {
            'A': "10",
            'B': "11",
            'C': "12",
            'D': "14"
        },
        'correct': 'C',
        'explanation': "12 × 12 = 144. Classic square root.",
        'commentary_correct': "12! Because 12 × 12 = 144. Math that actually makes sense.",
        'commentary_wrong': "It's 12! Just multiply it by itself: 12 × 12 = 144.",
        'difficulty': 'easy',
        'time_limit': 10
    },

    {
        'category': 'Things That Got Banned',
        'setup': "",
        'question': "In a standard deck of cards, how many cards are there?",
        'answers': {
            'A': "48",
            'B': "50",
            'C': "52",
            'D': "54"
        },
        'correct': 'C',
        'explanation': "52 cards (13 per suit × 4 suits). Jokers don't count.",
        'commentary_correct': "52! Four suits of 13 cards each. Jokers are bonus content.",
        'commentary_wrong': "It's 52! 13 cards per suit × 4 suits. Jokers don't count.",
        'difficulty': 'easy',
        'time_limit': 10
    },
]


def seed_improved_questions():
    """Load improved questions into database"""
    ph = get_placeholder()
    questions_added = 0

    # First, clear existing questions
    execute_query('DELETE FROM trivia_questions')
    print("🗑️ Cleared old questions")

    for q in IMPROVED_QUESTIONS:
        category = get_category_by_name(q['category'])
        if not category:
            print(f"⚠️ Category not found: {q['category']}")
            continue

        try:
            execute_query(f'''
                INSERT INTO trivia_questions
                (category_id, question_text, setup_text,
                 answer_a, answer_b, answer_c, answer_d,
                 correct_answer, explanation,
                 host_commentary_correct, host_commentary_wrong,
                 difficulty, time_limit)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            ''', (
                category['id'],
                q['question'],
                q.get('setup', ''),
                q['answers']['A'],
                q['answers']['B'],
                q['answers']['C'],
                q['answers']['D'],
                q['correct'],
                q.get('explanation', ''),
                q.get('commentary_correct', ''),
                q.get('commentary_wrong', ''),
                q.get('difficulty', 'medium'),
                q.get('time_limit', 15)
            ))
            questions_added += 1
        except Exception as e:
            print(f"Error adding question: {e}")

    print(f"✅ Added {questions_added} improved questions to database")


if __name__ == '__main__':
    print("Loading improved trivia questions...")
    seed_improved_questions()
    print("🎉 Improved questions loaded!")
