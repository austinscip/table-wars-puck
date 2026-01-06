"""
TRIVIA WARS - REAL YDKJ Style Questions
Educational but asked in absurd, indirect, scenario-based ways
"""

from trivia_database import execute_query, get_placeholder, get_category_by_name

# REAL YDKJ-style questions - scenarios first, knowledge second
YDKJ_STYLE_QUESTIONS = [
    # ========================================
    # MEDICAL / SCIENCE SCENARIOS
    # ========================================
    {
        'category': 'Medical Malpractice',
        'setup': "Your dad stepped on a rusty nail 3 days ago. Now his leg is turning black and smells like death.",
        'question': "The doctor says it's gangrene. What's your move?",
        'answers': {
            'A': "Cut off his foot before it spreads",
            'B': "Let nature take its course",
            'C': "Rub essential oils on it",
            'D': "Google 'gangrene home remedies'"
        },
        'correct': 'A',
        'explanation': "Gangrene is dead tissue that spreads. Amputation stops it from killing you. Dark, but true.",
        'commentary_correct': "Correct! Gangrene spreads fast. Cut off the foot, save the leg. Brutal but necessary.",
        'commentary_wrong': "Wrong! Gangrene SPREADS. You gotta cut off the infected part or he dies. Biology is metal.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Medical Malpractice',
        'setup': "You're hiking in the woods and get bitten by a snake. Your friend screams 'SUCK OUT THE VENOM!'",
        'question': "Should you listen to your idiot friend?",
        'answers': {
            'A': "Yes, suck it out immediately",
            'B': "No, that makes it worse",
            'C': "Only if you have mouthwash",
            'D': "Cut an X over the bite first, THEN suck"
        },
        'correct': 'B',
        'explanation': "Sucking venom spreads it faster and poisons your mouth. Just stay calm and get to a hospital.",
        'commentary_correct': "Right! Hollywood lied to you. Sucking venom just spreads it and ruins your mouth. Stay still, call 911.",
        'commentary_wrong': "Wrong! Sucking venom is movie bullshit. It spreads the poison faster. Immobilize and get help.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Rejected Inventions',
        'setup': "You're trapped in a sealed room. The oxygen generator breaks. You check the air readout.",
        'question': "Which gas is STILL there at 78%, keeping you alive?",
        'answers': {
            'A': "Oxygen",
            'B': "Nitrogen",
            'C': "Carbon Dioxide",
            'D': "Helium"
        },
        'correct': 'B',
        'explanation': "Air is 78% nitrogen, 21% oxygen. Nitrogen doesn't help you breathe, but oxygen is the minority gas.",
        'commentary_correct': "Nitrogen! Air is mostly nitrogen (78%). Oxygen gets the credit but it's only 21%.",
        'commentary_wrong': "Nope! It's nitrogen at 78%. Oxygen is only 21%. The air you breathe is mostly useless nitrogen.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Rejected Inventions',
        'setup': "You're standing on Mount Everest's summit, gasping for air.",
        'question': "How high up are you right now?",
        'answers': {
            'A': "15,000 feet",
            'B': "20,000 feet",
            'C': "29,000 feet",
            'D': "35,000 feet"
        },
        'correct': 'C',
        'explanation': "29,032 feet. That's why you can't breathe - you're 5.5 miles above sea level.",
        'commentary_correct': "29,000 feet! That's why you're dying. 5.5 miles up, barely any oxygen. Congrats on the summit tho.",
        'commentary_wrong': "Wrong! 29,032 feet. That's 5.5 miles straight up. Your lungs hate it here.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Rejected Inventions',
        'setup': "You're in chemistry class. Your teacher hands you a gold ring and asks what symbol is on the periodic table.",
        'question': "What do you write?",
        'answers': {
            'A': "Go",
            'B': "Gd",
            'C': "Au",
            'D': "Ag"
        },
        'correct': 'C',
        'explanation': "Au comes from Latin 'aurum' (gold). Ag is silver. Chemistry keeps Latin alive.",
        'commentary_correct': "Au! From 'aurum' - Latin for gold. Dead languages living in chemistry class.",
        'commentary_wrong': "It's Au! From aurum (Latin for gold). Ag is silver, by the way. Science loves dead languages.",
        'difficulty': 'medium',
        'time_limit': 12
    },

    # ========================================
    # HISTORY / GEOGRAPHY SCENARIOS
    # ========================================
    {
        'category': 'Historical Dumbassery',
        'setup': "It's 1945. You're a German soldier and you just heard Hitler shot himself in his bunker.",
        'question': "What month is it?",
        'answers': {
            'A': "January 1945",
            'B': "May 1945",
            'C': "September 1945",
            'D': "December 1945"
        },
        'correct': 'B',
        'explanation': "Hitler died April 30, 1945. Germany surrendered May 7-8. WWII in Europe ended in May.",
        'commentary_correct': "May 1945! Hitler's bunker suicide happened April 30. Germany surrendered a week later.",
        'commentary_wrong': "Wrong! May 1945. Hitler died April 30, Germany surrendered May 7-8. VE Day, baby.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Historical Dumbassery',
        'setup': "You land in Sydney, Australia for vacation. You ask a local where the capital is so you can visit.",
        'question': "Where do they tell you to go?",
        'answers': {
            'A': "You're already here, mate",
            'B': "Melbourne",
            'C': "Canberra",
            'D': "Perth"
        },
        'correct': 'C',
        'explanation': "Sydney and Melbourne fought over being capital, so they built Canberra between them as a compromise.",
        'commentary_correct': "Canberra! Sydney and Melbourne couldn't decide, so they built a compromise city no one visits.",
        'commentary_wrong': "It's Canberra! Everyone thinks Sydney, but Sydney and Melbourne compromised on boring Canberra.",
        'difficulty': 'hard',
        'time_limit': 15
    },

    {
        'category': 'Historical Dumbassery',
        'setup': "You're filling out a form. It asks 'Number of U.S. States'.",
        'question': "What number do you write?",
        'answers': {
            'A': "48",
            'B': "50",
            'C': "52",
            'D': "51"
        },
        'correct': 'B',
        'explanation': "50 states. Alaska and Hawaii joined in 1959, making it 50 total.",
        'commentary_correct': "50! If you got this wrong, we need to talk about your education.",
        'commentary_wrong': "It's 50! Alaska and Hawaii are the last two. This is embarrassing if you missed it.",
        'difficulty': 'easy',
        'time_limit': 10
    },

    {
        'category': 'Historical Dumbassery',
        'setup': "You're a Chinese emperor in 200 BC. Mongol raiders keep attacking from the north.",
        'question': "What megaproject do you force millions of people to build?",
        'answers': {
            'A': "The Great Wall",
            'B': "The Forbidden City",
            'C': "The Terracotta Army",
            'D': "A really big moat"
        },
        'correct': 'A',
        'explanation': "The Great Wall of China was built to keep out Mongol invaders from the north.",
        'commentary_correct': "The Great Wall! Built to keep Mongols out. Turns out big walls help with that.",
        'commentary_wrong': "Wrong! The Great Wall was built specifically to stop northern invaders like the Mongols.",
        'difficulty': 'easy',
        'time_limit': 12
    },

    {
        'category': 'Historical Dumbassery',
        'setup': "You're voting in the first U.S. presidential election ever. Who's on the ballot?",
        'question': "Who wins?",
        'answers': {
            'A': "Thomas Jefferson",
            'B': "Benjamin Franklin",
            'C': "George Washington",
            'D': "John Adams"
        },
        'correct': 'C',
        'explanation': "George Washington - first president, 1789-1797. The OG.",
        'commentary_correct': "Washington! The guy on the $1 bill. First president, unanimous vote.",
        'commentary_wrong': "It's George Washington! First president. He's literally on the dollar bill.",
        'difficulty': 'easy',
        'time_limit': 10
    },

    # ========================================
    # POP CULTURE SCENARIOS
    # ========================================
    {
        'category': 'Florida Man Headlines',
        'setup': "You're Neo in The Matrix. Morpheus offers you two pills: one shows you reality, one keeps you asleep.",
        'question': "Which pill does Neo actually take in the movie?",
        'answers': {
            'A': "Red pill (reality)",
            'B': "Blue pill (stay asleep)",
            'C': "Both pills",
            'D': "He shoots Morpheus instead"
        },
        'correct': 'A',
        'explanation': "Red pill = wake up to reality. Blue pill = stay in the Matrix. Neo chose truth.",
        'commentary_correct': "Red pill! Welcome to the real world. Should've taken the blue one and stayed in bed.",
        'commentary_wrong': "Wrong! Red pill = reality, blue pill = blissful ignorance. Neo picked the hard truth.",
        'difficulty': 'easy',
        'time_limit': 12
    },

    {
        'category': 'Florida Man Headlines',
        'setup': "You're in a movie theater in 1993. Dinosaurs are eating people on screen and it looks REAL.",
        'question': "Who directed this masterpiece?",
        'answers': {
            'A': "George Lucas",
            'B': "Steven Spielberg",
            'C': "James Cameron",
            'D': "Christopher Nolan"
        },
        'correct': 'B',
        'explanation': "Steven Spielberg directed Jurassic Park (1993). Changed movies forever.",
        'commentary_correct': "Spielberg! The man made dinosaurs look real in 1993. Still holds up.",
        'commentary_wrong': "Wrong! Spielberg directed Jurassic Park. The dinosaur guy.",
        'difficulty': 'easy',
        'time_limit': 12
    },

    {
        'category': 'Florida Man Headlines',
        'setup': "Steve Jobs is on stage holding a rectangular device with a touchscreen. No keyboard. Just a screen.",
        'question': "What year is this happening?",
        'answers': {
            'A': "2005",
            'B': "2007",
            'C': "2009",
            'D': "2010"
        },
        'correct': 'B',
        'explanation': "2007 - the first iPhone launch. Changed everything.",
        'commentary_correct': "2007! The year we all became phone zombies. Thanks Steve.",
        'commentary_wrong': "It's 2007! The iPhone launch that made flip phones extinct overnight.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Florida Man Headlines',
        'setup': "You're in a bookstore. A kid asks you how many Harry Potter books there are.",
        'question': "What do you tell them?",
        'answers': {
            'A': "5 books",
            'B': "6 books",
            'C': "7 books",
            'D': "8 books"
        },
        'correct': 'C',
        'explanation': "7 main books. Cursed Child doesn't count. Fight me.",
        'commentary_correct': "Seven! The perfect magical number. We don't talk about Cursed Child.",
        'commentary_wrong': "It's 7! From Sorcerer's Stone to Deathly Hallows. Cursed Child is fan fiction.",
        'difficulty': 'easy',
        'time_limit': 12
    },

    {
        'category': 'Florida Man Headlines',
        'setup': "You're arguing with your friend about which movie made the most money ever.",
        'question': "Which film actually won the box office war?",
        'answers': {
            'A': "Titanic",
            'B': "Avatar",
            'C': "Avengers: Endgame",
            'D': "Star Wars"
        },
        'correct': 'B',
        'explanation': "Avatar with $2.9 billion. Blue people on a blue planet made ALL the money.",
        'commentary_correct': "Avatar! James Cameron's blue people won at $2.9 billion.",
        'commentary_wrong': "Wrong! Avatar at $2.9B. Those blue aliens printed money.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    # ========================================
    # QUICK THINKING / LOGIC
    # ========================================
    {
        'category': 'Terrible Life Advice',
        'setup': "You're filling out a calendar for next year. It's a leap year.",
        'question': "How many total days do you need to mark?",
        'answers': {
            'A': "364",
            'B': "365",
            'C': "366",
            'D': "367"
        },
        'correct': 'C',
        'explanation': "366 days - one extra day added to February every 4 years.",
        'commentary_correct': "366! That bonus February 29th. Happy birthday to the unlucky leap day babies.",
        'commentary_wrong': "It's 366! Leap years add a day to February every 4 years.",
        'difficulty': 'easy',
        'time_limit': 10
    },

    {
        'category': 'Terrible Life Advice',
        'setup': "Your browser won't load a website. The error says 'HTTP connection failed.'",
        'question': "What does HTTP actually stand for?",
        'answers': {
            'A': "HyperText Transfer Protocol",
            'B': "High Technology Text Program",
            'C': "Home Tool Transfer Platform",
            'D': "Hyper Transfer Text Process"
        },
        'correct': 'A',
        'explanation': "HyperText Transfer Protocol - how browsers talk to websites.",
        'commentary_correct': "Correct! The protocol that makes the internet work. You're welcome.",
        'commentary_wrong': "Wrong! HyperText Transfer Protocol. How your browser talks to the internet.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Terrible Life Advice',
        'setup': "You're making ice cubes. The thermometer reads 0°C.",
        'question': "What's happening to the water right now?",
        'answers': {
            'A': "It's boiling",
            'B': "It's freezing solid",
            'C': "Nothing yet",
            'D': "It's evaporating"
        },
        'correct': 'B',
        'explanation': "0°C (32°F) is the freezing point. Water becomes ice.",
        'commentary_correct': "Freezing! 0°C is where water says 'fuck it, I'm a solid now.'",
        'commentary_wrong': "It's freezing! 0°C = ice time. The metric system is beautifully simple.",
        'difficulty': 'easy',
        'time_limit': 10
    },

    {
        'category': 'Terrible Life Advice',
        'setup': "You break your arm. The doctor shows you an X-ray of your entire skeleton.",
        'question': "How many bones does she count in your adult body?",
        'answers': {
            'A': "186",
            'B': "206",
            'C': "226",
            'D': "246"
        },
        'correct': 'B',
        'explanation': "206 bones in adults. Babies have ~270 but they fuse as you grow up.",
        'commentary_correct': "206! Babies start with more (~270) but they fuse. Growing up = fewer bones.",
        'commentary_wrong': "Wrong! 206 bones. Babies have more but they fuse together as you age.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Terrible Life Advice',
        'setup': "You're in biology class. The teacher asks what part of the cell makes energy.",
        'question': "What's the only thing you remember from high school?",
        'answers': {
            'A': "Nucleus",
            'B': "Mitochondria",
            'C': "Ribosome",
            'D': "Cell membrane"
        },
        'correct': 'B',
        'explanation': "Mitochondria - the powerhouse of the cell. The one thing everyone remembers.",
        'commentary_correct': "MITOCHONDRIA! The powerhouse! You remembered! Your biology teacher is proud.",
        'commentary_wrong': "It's mitochondria! THE most famous fact from biology. The powerhouse of the cell.",
        'difficulty': 'easy',
        'time_limit': 10
    },

    # ========================================
    # MATH / PROBABILITY
    # ========================================
    {
        'category': 'Things That Got Banned',
        'setup': "You're calculating a tip at a restaurant. The bill is $200. You want to leave 15%.",
        'question': "How much money do you leave?",
        'answers': {
            'A': "$20",
            'B': "$25",
            'C': "$30",
            'D': "$35"
        },
        'correct': 'C',
        'explanation': "200 × 0.15 = $30. Or think: 10% is $20, plus half of that ($10) = $30.",
        'commentary_correct': "$30! Quick math: 10% is $20, plus 5% ($10) = $30 tip.",
        'commentary_wrong': "It's $30! Move the decimal: 200 × 0.15 = 30. Your server thanks you.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Things That Got Banned',
        'setup': "You flip a coin twice. You want heads both times.",
        'question': "What are your odds?",
        'answers': {
            'A': "1/2 (50%)",
            'B': "1/3 (33%)",
            'C': "1/4 (25%)",
            'D': "1/8 (12.5%)"
        },
        'correct': 'C',
        'explanation': "Each flip is 1/2. Both heads = 1/2 × 1/2 = 1/4 or 25%.",
        'commentary_correct': "1/4! Each flip is 50%, together it's 1/2 × 1/2 = 25%.",
        'commentary_wrong': "Wrong! 1/4. Independent events: 1/2 × 1/2 = 1/4 or 25% chance.",
        'difficulty': 'medium',
        'time_limit': 12
    },

    {
        'category': 'Things That Got Banned',
        'setup': "Your teacher asks you what number, when multiplied by itself, equals 144.",
        'question': "What do you answer?",
        'answers': {
            'A': "10",
            'B': "11",
            'C': "12",
            'D': "14"
        },
        'correct': 'C',
        'explanation': "12 × 12 = 144. Square root of 144 = 12.",
        'commentary_correct': "12! Because 12 × 12 = 144. Math that actually makes sense.",
        'commentary_wrong': "It's 12! Square root of 144. Just multiply it: 12 × 12 = 144.",
        'difficulty': 'easy',
        'time_limit': 10
    },

    {
        'category': 'Things That Got Banned',
        'setup': "You're playing poker. You want to count the cards in the deck.",
        'question': "How many cards are in a standard deck?",
        'answers': {
            'A': "48",
            'B': "50",
            'C': "52",
            'D': "54"
        },
        'correct': 'C',
        'explanation': "52 cards - 13 per suit × 4 suits. Jokers don't count.",
        'commentary_correct': "52! Four suits of 13 cards. Jokers are just extra.",
        'commentary_wrong': "It's 52! 13 cards per suit × 4 suits. Jokers don't count.",
        'difficulty': 'easy',
        'time_limit': 10
    },
]


def seed_ydkj_questions():
    """Load REAL YDKJ-style questions"""
    ph = get_placeholder()
    questions_added = 0

    # Clear old questions
    execute_query('DELETE FROM trivia_questions')
    print("🗑️ Cleared old questions")

    for q in YDKJ_STYLE_QUESTIONS:
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

    print(f"✅ Added {questions_added} YDKJ-style questions")


if __name__ == '__main__':
    print("Loading REAL YDKJ-style questions...")
    seed_ydkj_questions()
    print("🎉 YDKJ questions loaded!")
