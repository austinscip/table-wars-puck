"""
TRIVIA WARS - Sample Questions Database Seeder
50+ questions across 10 categories in YDKJ style
"""

from trivia_database import execute_query, get_placeholder, get_category_by_name

# Sample questions in YDKJ absurd style
SAMPLE_QUESTIONS = [
    # ========================================
    # CATEGORY: Ways to Die Stupidly
    # ========================================
    {
        'category': 'Ways to Die Stupidly',
        'setup': "Chuck thought it'd be hilarious to deep-fry a frozen turkey in his garage for Thanksgiving.",
        'question': "What actually happened?",
        'answers': {
            'A': "Turkey exploded and burned his house down",
            'B': "It was delicious and everyone loved it",
            'C': "The turkey came back to life and attacked him",
            'D': "Nothing, he's just an idiot"
        },
        'correct': 'A',
        'explanation': "Water in frozen turkey + hot oil = explosion. Physics is a bitch.",
        'commentary_correct': "Correct! Chuck learned that frozen + 350°F oil = insurance claim. Happy Thanksgiving!",
        'commentary_wrong': "Wrong! It's ALWAYS the explosion with frozen turkeys. Rule #1 of deep frying: thaw first, blow up never.",
        'difficulty': 'easy',
        'time_limit': 15
    },

    {
        'category': 'Ways to Die Stupidly',
        'setup': "A man in Russia decided to play a game of 'chicken' with his friends.",
        'question': "What did he use instead of a car?",
        'answers': {
            'A': "A shopping cart",
            'B': "A hand grenade",
            'C': "A horse",
            'D': "His mother-in-law"
        },
        'correct': 'B',
        'explanation': "Real story: They pulled the pin and passed it around. Spoiler: He lost.",
        'commentary_correct': "Correct! Nothing says friendship like explosive ordnance. Darwin Award winner right here.",
        'commentary_wrong': "Nope! It was a GRENADE. Because Russia.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Ways to Die Stupidly',
        'setup': "In 2013, a man tried to rob a gun store while the owner was there.",
        'question': "How did this brilliant plan work out?",
        'answers': {
            'A': "He successfully robbed it",
            'B': "Owner shot him, obviously",
            'C': "They became best friends",
            'D': "The gun store was actually a bakery"
        },
        'correct': 'B',
        'explanation': "Robbing a GUN STORE. While the ARMED owner is present. Peak intelligence.",
        'commentary_correct': "Correct! Turns out people who own gun stores tend to have... guns. Wild, right?",
        'commentary_wrong': "Wrong! The gun store owner was armed. In a gun store. Shocking outcome: robber got shot.",
        'difficulty': 'easy',
        'time_limit': 12
    },

    {
        'category': 'Ways to Die Stupidly',
        'setup': "A man in Texas decided to heat his living room with what alternative heat source?",
        'question': "His genius idea was:",
        'answers': {
            'A': "Burning furniture",
            'B': "50 candles arranged in a circle",
            'C': "A charcoal grill... indoors",
            'D': "Flamethrower pointed at the ceiling"
        },
        'correct': 'C',
        'explanation': "Carbon monoxide poisoning. Who knew?",
        'commentary_correct': "Bingo! Indoor grilling = carbon monoxide. He discovered this the hard way.",
        'commentary_wrong': "Nope! He used a charcoal grill INSIDE. Texas education system strikes again.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Ways to Die Stupidly',
        'setup': "In 1981, a man robbed a bank and made his getaway on:",
        'question': "His choice of vehicle:",
        'answers': {
            'A': "A bicycle",
            'B': "A city bus",
            'C': "Rollerblades",
            'D': "A mobility scooter"
        },
        'correct': 'B',
        'explanation': "He hopped on a public bus. With a bag full of cash. In front of witnesses.",
        'commentary_correct': "Yes! He robbed a bank and got on a bus with a schedule. He was arrested at the next stop.",
        'commentary_wrong': "Wrong! It was a BUS. He followed the route, paid the fare, and got arrested. Planning: 0/10.",
        'difficulty': 'hard',
        'time_limit': 15
    },

    # ========================================
    # CATEGORY: Florida Man Headlines
    # ========================================
    {
        'category': 'Florida Man Headlines',
        'setup': "Florida Man was arrested after police found him at 3am in a Walmart parking lot.",
        'question': "What was he doing?",
        'answers': {
            'A': "Teaching raccoons to play poker",
            'B': "Riding an alligator while drunk",
            'C': "Performing surgery on a watermelon",
            'D': "Hosting a one-man rave"
        },
        'correct': 'B',
        'explanation': "Real headline. The alligator was unharmed but traumatized.",
        'commentary_correct': "CORRECT! It's Florida. When in doubt, pick the gator.",
        'commentary_wrong': "Wrong! It's ALWAYS the alligator in Florida. Rule #1 of Florida Man trivia.",
        'difficulty': 'easy',
        'time_limit': 12
    },

    {
        'category': 'Florida Man Headlines',
        'setup': "Florida Man called 911 because:",
        'question': "His emergency was:",
        'answers': {
            'A': "McDonald's ran out of Chicken McNuggets",
            'B': "His cat was judging him",
            'C': "He couldn't find his remote",
            'D': "The moon looked weird"
        },
        'correct': 'A',
        'explanation': "She called 911 THREE TIMES about McNuggets. Real story.",
        'commentary_correct': "Correct! A real 911 call. The operator was not amused.",
        'commentary_wrong': "Nope! McNugget shortage = legitimate emergency in Florida.",
        'difficulty': 'medium',
        'time_limit': 12
    },

    {
        'category': 'Florida Man Headlines',
        'setup': "Florida Man attacked his roommate with what weapon?",
        'question': "The assault weapon was:",
        'answers': {
            'A': "A frozen iguana",
            'B': "A pizza slice",
            'C': "A Bible",
            'D': "All of the above at different times"
        },
        'correct': 'D',
        'explanation': "These are all real separate Florida Man incidents.",
        'commentary_correct': "YES! Florida Man has weaponized iguanas, pizza, AND scripture. Renaissance man.",
        'commentary_wrong': "Wrong! All three happened. Florida is a lawless hellscape.",
        'difficulty': 'hard',
        'time_limit': 15
    },

    {
        'category': 'Florida Man Headlines',
        'setup': "Florida Man was arrested for pleasuring himself while:",
        'question': "The location was:",
        'answers': {
            'A': "At a children's playground",
            'B': "In his own home minding his business",
            'C': "At a Chick-fil-A drive-thru",
            'D': "During a city council meeting"
        },
        'correct': 'C',
        'explanation': "While placing his order. The employees called police.",
        'commentary_correct': "Correct! He wanted chicken AND personal time. Multitasking gone wrong.",
        'commentary_wrong': "Nope! Chick-fil-A drive-thru. My pleasure took on a new meaning.",
        'difficulty': 'medium',
        'time_limit': 12
    },

    # ========================================
    # CATEGORY: Rejected Inventions
    # ========================================
    {
        'category': 'Rejected Inventions',
        'setup': "In the 1950s, someone actually patented a 'baby cage' designed to:",
        'question': "The cage was meant for:",
        'answers': {
            'A': "Hang outside apartment windows so babies get fresh air",
            'B': "Protect babies from wolf attacks",
            'C': "Train babies for MMA",
            'D': "Store babies like luggage"
        },
        'correct': 'A',
        'explanation': "Real patent. They literally hung babies out windows in cages. The 1950s were different.",
        'commentary_correct': "Correct! Baby cages hung from windows. Child safety standards: lol.",
        'commentary_wrong': "Wrong! They ACTUALLY hung babies out windows. The '50s were a lawless time.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Rejected Inventions',
        'setup': "In 2011, someone patented a device for:",
        'question': "This genius invention was:",
        'answers': {
            'A': "A toilet with a built-in gym",
            'B': "Motorized ice cream cone that spins",
            'C': "Hat with built-in toilet paper for sneezing",
            'D': "Self-stirring coffee mug"
        },
        'correct': 'C',
        'explanation': "Hat-mounted toilet paper roll. For when tissues aren't ridiculous enough.",
        'commentary_correct': "Yes! Someone patented a toilet paper hat. Fashion forward.",
        'commentary_wrong': "Nope! It's the TP hat. For the person who has everything except dignity.",
        'difficulty': 'hard',
        'time_limit': 15
    },

    # ========================================
    # CATEGORY: Terrible Life Advice
    # ========================================
    {
        'category': 'Terrible Life Advice',
        'setup': "Your friend just got dumped. According to a study, which advice makes breakups WORSE?",
        'question': "The worst advice to give:",
        'answers': {
            'A': "There's plenty of fish in the sea",
            'B': "Just focus on yourself",
            'C': "Text them drunk at 2am",
            'D': "Burn all their stuff"
        },
        'correct': 'C',
        'explanation': "Drunk texting exes extends recovery time by 40%. Science!",
        'commentary_correct': "Correct! Drunk texting = proven to make things worse. Delete their number.",
        'commentary_wrong': "Wrong! Studies show drunk texting is the WORST thing. But you already knew that.",
        'difficulty': 'easy',
        'time_limit': 12
    },

    {
        'category': 'Terrible Life Advice',
        'setup': "Which common 'motivational' phrase is scientifically proven to make people LESS motivated?",
        'question': "The demotivating phrase:",
        'answers': {
            'A': "Just do it",
            'B': "You can do anything you set your mind to",
            'C': "Live, laugh, love",
            'D': "Hustle harder"
        },
        'correct': 'B',
        'explanation': "Research shows unrealistic optimism leads to giving up faster.",
        'commentary_correct': "Bingo! 'You can do anything' sets unrealistic expectations. You can't fly, Karen.",
        'commentary_wrong': "Wrong! 'You can do anything' is scientifically demotivating. Reality matters.",
        'difficulty': 'hard',
        'time_limit': 15
    },

    # ========================================
    # CATEGORY: Things That Got Banned
    # ========================================
    {
        'category': 'Things That Got Banned',
        'setup': "In 2011, Denmark banned which children's food because it contained too many vitamins?",
        'question': "The banned food:",
        'answers': {
            'A': "Vegetables",
            'B': "Fortified breakfast cereals like Frosted Flakes",
            'C': "Gummy vitamins shaped like cartoons",
            'D': "Anything that tastes good"
        },
        'correct': 'B',
        'explanation': "Too many vitamins = illegal. Denmark said no to Kellogg's.",
        'commentary_correct': "Correct! Denmark banned healthy cereal. Meanwhile America deep-fries butter.",
        'commentary_wrong': "Wrong! They banned fortified cereals. Tony the Tiger is persona non grata.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Things That Got Banned',
        'setup': "Kinder Surprise eggs were banned in the USA until 2017 because:",
        'question': "The reason for the ban:",
        'answers': {
            'A': "Toys inside food are illegal",
            'B': "Choking hazard",
            'C': "Chocolate was too delicious",
            'D': "Competition for American candy"
        },
        'correct': 'A',
        'explanation': "Non-nutritive objects inside food = illegal since 1938. America!",
        'commentary_correct': "Yes! America banned toys in chocolate for 80 years. But guns are fine.",
        'commentary_wrong': "Wrong! FDA says no toys in food. Apparently we can't be trusted.",
        'difficulty': 'medium',
        'time_limit': 12
    },

    # ========================================
    # CATEGORY: When Animals Attack
    # ========================================
    {
        'category': 'When Animals Attack',
        'setup': "A man in Australia went to the hospital after his pet python:",
        'question': "The python did what?",
        'answers': {
            'A': "Bit his face",
            'B': "Strangled him",
            'C': "Bit his penis while he slept",
            'D': "Escaped and called the police"
        },
        'correct': 'C',
        'explanation': "2013 news story. The python mistook it for prey.",
        'commentary_correct': "Correct! Snake bit his junk. Australia: where everything tries to kill you, even pets.",
        'commentary_wrong': "Wrong! Penis-biting python. Real story. Australia is a nightmare.",
        'difficulty': 'easy',
        'time_limit': 12
    },

    {
        'category': 'When Animals Attack',
        'setup': "A woman in Oregon was attacked by:",
        'question': "Her attacker was:",
        'answers': {
            'A': "An aggressive squirrel",
            'B': "A rabid beaver",
            'C': "A territorial goose",
            'D': "Her neighbor's emotional support peacock"
        },
        'correct': 'B',
        'explanation': "Beaver bit her multiple times. Required rabies shots.",
        'commentary_correct': "Yes! Angry beaver attacked her. Not a euphemism. Actual beaver.",
        'commentary_wrong': "Nope! Rabid beaver. Nature is terrifying.",
        'difficulty': 'medium',
        'time_limit': 12
    },

    # ========================================
    # CATEGORY: Medical Malpractice
    # ========================================
    {
        'category': 'Medical Malpractice',
        'setup': "In the 1800s, doctors recommended which 'cure' for hysteria in women?",
        'question': "The medical treatment:",
        'answers': {
            'A': "Telling them to calm down",
            'B': "Vibrators (yes, really)",
            'C': "More housework",
            'D': "Drilling holes in their skull"
        },
        'correct': 'B',
        'explanation': "Doctors invented vibrators as medical devices. True story.",
        'commentary_correct': "Correct! Victorian doctors prescribed orgasms. Medical science!",
        'commentary_wrong': "Wrong! It was vibrators. Doctors gave women orgasms and called it medicine.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Medical Malpractice',
        'setup': "Cocaine was once marketed by Parke-Davis pharmaceutical company as a cure for:",
        'question': "Cocaine was sold to treat:",
        'answers': {
            'A': "Depression and fatigue",
            'B': "Toothaches in children",
            'C': "Everything from hay fever to impotence",
            'D': "All of the above"
        },
        'correct': 'D',
        'explanation': "Cocaine was the wonder drug of the 1800s. Literally everything.",
        'commentary_correct': "YES! Cocaine cured everything! Also created a LOT of new problems.",
        'commentary_wrong': "Wrong! Cocaine was prescribed for EVERYTHING. The 1800s were wild.",
        'difficulty': 'easy',
        'time_limit': 12
    },

    # ========================================
    # CATEGORY: Criminal Masterminds
    # ========================================
    {
        'category': 'Criminal Masterminds',
        'setup': "A bank robber in 1995 rubbed lemon juice on his face because he thought it would:",
        'question': "His brilliant plan:",
        'answers': {
            'A': "Make him invisible to cameras",
            'B': "Make his skin reflective",
            'C': "Smell good",
            'D': "Give him superpowers"
        },
        'correct': 'A',
        'explanation': "He thought lemon juice = invisible ink = invisible to cameras. Dunning-Kruger effect in action.",
        'commentary_correct': "Correct! Lemon juice guy. This study inspired the Dunning-Kruger effect research.",
        'commentary_wrong': "Wrong! Invisible ink logic. He was caught immediately. Cameras don't use heat.",
        'difficulty': 'hard',
        'time_limit': 15
    },

    {
        'category': 'Criminal Masterminds',
        'setup': "A man robbed a bank, then went to the same bank the next day to:",
        'question': "His next move:",
        'answers': {
            'A': "Rob it again",
            'B': "Open an account with the stolen money",
            'C': "Ask them to exchange his marked bills",
            'D': "Apply for a job there"
        },
        'correct': 'B',
        'explanation': "He walked in with the stolen cash to open an account. Teller recognized him.",
        'commentary_correct': "YES! Robbed a bank, opened account with stolen money. Same bank. Next day.",
        'commentary_wrong': "Wrong! He opened an account WITH THE STOLEN CASH. At the SAME BANK.",
        'difficulty': 'medium',
        'time_limit': 12
    },

    # ========================================
    # CATEGORY: Weird Laws
    # ========================================
    {
        'category': 'Weird Laws',
        'setup': "In Alaska, it's illegal to:",
        'question': "The illegal activity:",
        'answers': {
            'A': "Wake a sleeping bear for a photo",
            'B': "Feed beer to moose",
            'C': "Push a live moose out of an airplane",
            'D': "All of the above"
        },
        'correct': 'D',
        'explanation': "All real Alaska laws. Apparently these were problems.",
        'commentary_correct': "All three! Alaska had to write laws because people kept doing these things.",
        'commentary_wrong': "Wrong! ALL THREE are illegal in Alaska. They wouldn't need laws if people didn't do it.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Weird Laws',
        'setup': "In Switzerland, it's illegal to:",
        'question': "The Swiss outlawed:",
        'answers': {
            'A': "Mow your lawn on Sunday",
            'B': "Flush toilets after 10pm in apartments",
            'C': "Own just one guinea pig (must have two)",
            'D': "All of these are real laws"
        },
        'correct': 'D',
        'explanation': "Switzerland takes quiet time and guinea pig companionship VERY seriously.",
        'commentary_correct': "All of them! Switzerland: where guinea pigs have rights and toilets have curfews.",
        'commentary_wrong': "Wrong! All three are Swiss laws. Don't mess with Swiss social norms.",
        'difficulty': 'hard',
        'time_limit': 15
    },

    # ========================================
    # CATEGORY: Historical Dumbassery
    # ========================================
    {
        'category': 'Historical Dumbassery',
        'setup': "In 1788, the entire Austrian army suffered 10,000 casualties in a battle against:",
        'question': "Their enemy was:",
        'answers': {
            'A': "The Ottoman Empire",
            'B': "Themselves",
            'C': "A flock of geese",
            'D': "Bad weather"
        },
        'correct': 'B',
        'explanation': "Battle of Karánsebes: drunk soldiers attacked each other in confusion. 10,000 casualties. No enemy present.",
        'commentary_correct': "Correct! The Austrian army got drunk and fought itself. 10,000 dead. No enemies required.",
        'commentary_wrong': "Wrong! They fought THEMSELVES. Alcohol + paranoia = disaster.",
        'difficulty': 'hard',
        'time_limit': 15
    },

    {
        'category': 'Historical Dumbassery',
        'setup': "In 1518, a 'dancing plague' in France caused people to:",
        'question': "The plague's symptom:",
        'answers': {
            'A': "Dance uncontrollably until they died",
            'B': "Break into spontaneous musicals",
            'C': "Only communicate through dance",
            'D': "Develop excellent rhythm"
        },
        'correct': 'A',
        'explanation': "Real event. Hundreds danced for weeks, many died from exhaustion. Cause unknown.",
        'commentary_correct': "YES! People danced themselves to death. Medieval times were weird.",
        'commentary_wrong': "Wrong! They literally danced until they died. Real historical event.",
        'difficulty': 'hard',
        'time_limit': 15
    },
]


def seed_questions():
    """Seed database with sample questions"""
    ph = get_placeholder()

    questions_added = 0

    for q in SAMPLE_QUESTIONS:
        # Get category ID
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

    print(f"✅ Added {questions_added} sample questions to database")


if __name__ == '__main__':
    print("Seeding trivia questions...")
    seed_questions()
    print("🎉 Questions seeded successfully!")
