"""
YDKJ-STYLE QUESTIONS - BATCH 2
More absurd, funny, educational questions with indirect questioning
All with clear correct answers
"""

from trivia_database import execute_query, get_placeholder, get_category_by_name

NEW_QUESTIONS = [
    # ===== WAYS TO DIE STUPIDLY =====
    {
        'category': 'Ways to Die Stupidly',
        'setup': "You're at a party and someone dares you to chug a gallon of water in 10 minutes.",
        'question': "What actually kills you?",
        'answers': {
            'A': "Water intoxication (your brain swells)",
            'B': "Your stomach explodes",
            'C': "You drown from the inside",
            'D': "Nothing, water is safe"
        },
        'correct': 'A',
        'explanation': "Drinking too much water too fast dilutes your blood sodium levels. Your brain swells and you die. It's called water intoxication.",
        'commentary_correct': "Correct! Too much water kills your sodium balance. Your brain swells and you're dead. Ironic.",
        'commentary_wrong': "Wrong! Water intoxication is real. Your brain swells from low sodium. Death by H2O.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Ways to Die Stupidly',
        'setup': "You find a wild mushroom in your backyard. It's red with white spots, like Mario.",
        'question': "What happens if you eat it?",
        'answers': {
            'A': "You trip balls then vomit for hours",
            'B': "You grow 10 feet tall",
            'C': "Your liver fails and you die",
            'D': "Nothing, it's just a mushroom"
        },
        'correct': 'A',
        'explanation': "Amanita muscaria (fly agaric) is the Mario mushroom. It causes hallucinations, vomiting, and seizures. Won't kill you but you'll wish it did.",
        'commentary_correct': "Correct! The Mario mushroom makes you hallucinate then vomit for 6 hours. Fun times.",
        'commentary_wrong': "Wrong! Amanita muscaria = hallucinogenic nightmare. You won't die but you'll regret it.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Ways to Die Stupidly',
        'setup': "You're hiking in the desert. You haven't peed in 8 hours despite drinking water.",
        'question': "What's happening to you?",
        'answers': {
            'A': "Dehydration - your kidneys are shutting down",
            'B': "You have a bladder infection",
            'C': "Your water bottle was empty",
            'D': "You're sweating it all out (normal)"
        },
        'correct': 'A',
        'explanation': "If you're drinking water but not peeing in extreme heat, your kidneys are failing. You're severely dehydrated despite drinking. Seek medical help immediately.",
        'commentary_correct': "Correct! No pee + drinking water = kidney failure. Desert heat doesn't play.",
        'commentary_wrong': "Wrong! If you drink but don't pee, your kidneys are failing. That's bad.",
        'difficulty': 'hard',
        'time_limit': 15
    },

    # ===== FLORIDA MAN HEADLINES =====
    {
        'category': 'Florida Man Headlines',
        'setup': "Florida Man arrested for throwing alligator through Wendy's drive-thru window.",
        'question': "What charge did he actually face?",
        'answers': {
            'A': "Assault with a deadly weapon",
            'B': "Unlawful possession of wildlife",
            'C': "Disorderly conduct",
            'D': "Attempted murder"
        },
        'correct': 'A',
        'explanation': "Real 2016 headline. He was charged with assault with a deadly weapon. The alligator was the weapon. Only in Florida.",
        'commentary_correct': "Correct! Alligator = deadly weapon in Florida law. Gotta love it.",
        'commentary_wrong': "Wrong! Assault with a deadly weapon. The gator IS the weapon. Florida logic.",
        'difficulty': 'easy',
        'time_limit': 15
    },

    {
        'category': 'Florida Man Headlines',
        'setup': "Florida Man calls 911 because Taco Bell forgot his Crunchwrap.",
        'question': "What happened?",
        'answers': {
            'A': "He was arrested for misuse of 911",
            'B': "Taco Bell gave him a refund",
            'C': "Nothing, it's not illegal",
            'D': "Police escorted him to Taco Bell"
        },
        'correct': 'A',
        'explanation': "Real story. He called 911 multiple times over missing food. Arrested for misusing emergency services.",
        'commentary_correct': "Correct! Calling 911 for a Crunchwrap = arrest. Priorities, man.",
        'commentary_wrong': "Wrong! Misuse of 911. Don't call emergency services for fast food.",
        'difficulty': 'easy',
        'time_limit': 15
    },

    # ===== MEDICAL MALPRACTICE =====
    {
        'category': 'Medical Malpractice',
        'setup': "Your friend gets bit by a rattlesnake. He wants to suck the venom out like in movies.",
        'question': "What do you tell him?",
        'answers': {
            'A': "Don't - it spreads venom and causes infections",
            'B': "Do it - you have 30 seconds to save him",
            'C': "Cut an X over the bite first",
            'D': "Apply a tourniquet to stop blood flow"
        },
        'correct': 'A',
        'explanation': "NEVER suck snake venom. It doesn't work, spreads venom to your mouth, and causes infections. Keep still, call 911, wait for antivenom.",
        'commentary_correct': "Correct! Sucking venom is Hollywood BS. Keep still, call 911, don't die.",
        'commentary_wrong': "Wrong! Never suck venom. Doesn't work, makes it worse. Call 911 instead.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Medical Malpractice',
        'setup': "You cut yourself cooking. The bleeding won't stop after 15 minutes of pressure.",
        'question': "What's the next step?",
        'answers': {
            'A': "Go to ER - you might need stitches or have a clotting disorder",
            'B': "Superglue it shut",
            'C': "Pour alcohol on it to sterilize",
            'D': "Wait it out, all cuts stop eventually"
        },
        'correct': 'A',
        'explanation': "If bleeding doesn't stop after 15 minutes of direct pressure, you need medical attention. Could be a deep cut needing stitches or a clotting disorder.",
        'commentary_correct': "Correct! 15+ minutes bleeding = ER time. Don't bleed out over pride.",
        'commentary_wrong': "Wrong! Non-stop bleeding after 15 min = hospital. Could be serious.",
        'difficulty': 'easy',
        'time_limit': 15
    },

    # ===== HISTORICAL DUMBASSERY =====
    {
        'category': 'Historical Dumbassery',
        'setup': "In 1518, hundreds of people in Strasbourg danced for days without stopping until many died.",
        'question': "What caused it?",
        'answers': {
            'A': "Mass psychogenic illness (dancing plague)",
            'B': "Contaminated bread with ergot fungus",
            'C': "A cult ritual gone wrong",
            'D': "Party drugs in the medieval wine"
        },
        'correct': 'A',
        'explanation': "The Dancing Plague of 1518. People danced uncontrollably for days, some to death. Likely mass hysteria/psychogenic illness. History is wild.",
        'commentary_correct': "Correct! Mass psychogenic illness made people dance to death. Medieval times were weird.",
        'commentary_wrong': "Wrong! It was mass hysteria - the dancing plague of 1518. Google it.",
        'difficulty': 'hard',
        'time_limit': 15
    },

    {
        'category': 'Historical Dumbassery',
        'setup': "Napoleon tried to invade Russia with 600,000 men. How many made it back?",
        'question': "What was the main killer?",
        'answers': {
            'A': "Winter, starvation, and disease (not combat)",
            'B': "Russian military superiority",
            'C': "Ambushes and guerrilla warfare",
            'D': "Friendly fire and poor leadership"
        },
        'correct': 'A',
        'explanation': "Of 600,000 soldiers, only ~10,000 returned. Winter, starvation, and disease killed most. Combat was secondary. Never invade Russia in winter.",
        'commentary_correct': "Correct! Winter killed Napoleon's army, not Russians. Classic blunder.",
        'commentary_wrong': "Wrong! Winter, starvation, disease = 590,000 dead. Russia wins by freezing.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    # ===== THINGS THAT GOT BANNED =====
    {
        'category': 'Things That Got Banned',
        'setup': "Kinder Surprise eggs are illegal in the US.",
        'question': "Why?",
        'answers': {
            'A': "Non-edible objects inside food violate FDA law",
            'B': "Choking hazard killed 12 kids",
            'C': "Chocolate quality too low",
            'D': "Trade war with Europe"
        },
        'correct': 'A',
        'explanation': "FDA prohibits non-nutritive objects fully enclosed in food. The toy inside violates this 1938 law. You can buy them in Canada though.",
        'commentary_correct': "Correct! Non-edible stuff inside food = illegal. FDA doesn't mess around.",
        'commentary_wrong': "Wrong! FDA law bans non-food objects inside food. Kinder eggs = contraband.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Things That Got Banned',
        'setup': "In Singapore, chewing gum has been banned since 1992.",
        'question': "What was the reason?",
        'answers': {
            'A': "People stuck gum on subway sensors, breaking the system",
            'B': "Health concerns about artificial sweeteners",
            'C': "Too much litter on sidewalks",
            'D': "Religious opposition to mint flavoring"
        },
        'correct': 'A',
        'explanation': "Vandals stuck gum on train door sensors, disrupting the entire subway system. Singapore banned all chewing gum. Don't mess with public transit.",
        'commentary_correct': "Correct! Gum vandalism broke the subway. Singapore said 'no more gum ever.'",
        'commentary_wrong': "Wrong! Gum on subway sensors = entire ban. Singapore doesn't play.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    # ===== GENERAL KNOWLEDGE (EASY) =====
    {
        'category': 'General Knowledge',
        'setup': None,
        'question': "What does HTTP stand for?",
        'answers': {
            'A': "HyperText Transfer Protocol",
            'B': "High Tech Transmission Process",
            'C': "HyperText Transport Program",
            'D': "Host Transfer Text Protocol"
        },
        'correct': 'A',
        'explanation': "HyperText Transfer Protocol. It's how web browsers communicate with servers. Basic internet knowledge.",
        'commentary_correct': "Correct! HTTP = how the internet talks to itself. You passed Computer 101.",
        'commentary_wrong': "Wrong! HyperText Transfer Protocol. You use it every day, friend.",
        'difficulty': 'easy',
        'time_limit': 15
    },

    {
        'category': 'General Knowledge',
        'setup': None,
        'question': "How many bones does an adult human have?",
        'answers': {
            'A': "206",
            'B': "187",
            'C': "215",
            'D': "192"
        },
        'correct': 'A',
        'explanation': "206 bones in an adult skeleton. Babies have ~270 but many fuse together as they grow.",
        'commentary_correct': "Correct! 206 bones keeping you upright. Congrats on basic anatomy.",
        'commentary_wrong': "Wrong! 206 bones. You literally have a skeleton inside you right now.",
        'difficulty': 'easy',
        'time_limit': 15
    },

    # ===== REJECTED INVENTIONS =====
    {
        'category': 'Rejected Inventions',
        'setup': "In the 1920s, someone invented 'Radithor' - bottled water with radium in it.",
        'question': "What was it marketed as?",
        'answers': {
            'A': "A miracle cure-all tonic for energy and virility",
            'B': "Cleaning solution for tough stains",
            'C': "Pain relief for arthritis",
            'D': "Scientific experiment gone wrong"
        },
        'correct': 'A',
        'explanation': "Radithor was radium-laced water sold as a health tonic. People drank radioactive water for 'energy.' Spoiler: it killed them. Their jaws fell off.",
        'commentary_correct': "Correct! Radioactive water as medicine. Their jaws literally fell off. The 1920s were insane.",
        'commentary_wrong': "Wrong! It was a 'health tonic.' Radioactive water for virility. People died horribly.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'Rejected Inventions',
        'setup': "Someone invented edible deodorant pills in the 1960s.",
        'question': "What was supposed to happen?",
        'answers': {
            'A': "Your sweat would smell like roses",
            'B': "You'd stop sweating entirely",
            'C': "Your armpits would taste minty",
            'D': "Body odor would be neutralized internally"
        },
        'correct': 'A',
        'explanation': "The pills were supposed to make your sweat smell like perfume from the inside out. They didn't work and tasted terrible.",
        'commentary_correct': "Correct! Pills to make your BO smell like flowers. It failed spectacularly.",
        'commentary_wrong': "Wrong! Sweat perfume pills. Ridiculous concept, worse execution.",
        'difficulty': 'easy',
        'time_limit': 15
    },

    # ===== TERRIBLE LIFE ADVICE =====
    {
        'category': 'Terrible Life Advice',
        'setup': "Your car is sinking in a lake. You're trapped inside underwater.",
        'question': "What's the actual way to escape?",
        'answers': {
            'A': "Wait for the car to fill with water, pressure equalizes, then open the door",
            'B': "Smash the window immediately before it sinks",
            'C': "Call 911 and wait for rescue",
            'D': "Swim out through the sunroof"
        },
        'correct': 'A',
        'explanation': "Can't open door while sinking due to water pressure. Wait for car to fill completely (terrifying but necessary), pressure equalizes, THEN you can open the door and swim out.",
        'commentary_correct': "Correct! Wait for it to fill, pressure equalizes, escape. Scary but it works.",
        'commentary_wrong': "Wrong! You have to wait for the car to flood. Pressure makes doors impossible to open otherwise.",
        'difficulty': 'hard',
        'time_limit': 15
    },

    {
        'category': 'Terrible Life Advice',
        'setup': "You're lost in the woods with no water. You find a stream.",
        'question': "What's the safest move?",
        'answers': {
            'A': "Boil the water first, or use a filter if you have one",
            'B': "Drink it - dehydration is worse than parasites",
            'C': "Only drink from fast-moving water",
            'D': "Add iodine tablets from your emergency kit"
        },
        'correct': 'A',
        'explanation': "Stream water can have giardia, bacteria, and parasites. Boil it for 1 min or use a filter. Dehydration vs diarrhea is a bad trade-off in the wilderness.",
        'commentary_correct': "Correct! Boil or filter. Giardia will make you wish you were just thirsty.",
        'commentary_wrong': "Wrong! Boil it or filter it. Stream water has parasites that'll destroy you.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    # ===== WHEN ANIMALS ATTACK =====
    {
        'category': 'When Animals Attack',
        'setup': "You're swimming in the ocean and see a dorsal fin. It's a shark.",
        'question': "What do you do?",
        'answers': {
            'A': "Stay calm, swim smoothly to shore, don't splash or panic",
            'B': "Play dead and float face-down",
            'C': "Swim toward the shark to intimidate it",
            'D': "Scream for help and thrash wildly"
        },
        'correct': 'A',
        'explanation': "Sharks are attracted to erratic movement and panic. Stay calm, swim smoothly and steadily to shore. If attacked, punch the nose or gills.",
        'commentary_correct': "Correct! Calm smooth swimming. Panic = shark bait. Don't be bait.",
        'commentary_wrong': "Wrong! Stay calm, swim smoothly. Thrashing makes you look like injured prey.",
        'difficulty': 'medium',
        'time_limit': 15
    },

    {
        'category': 'When Animals Attack',
        'setup': "A wild bear charges you in the woods.",
        'question': "What's the right response?",
        'answers': {
            'A': "Stand your ground, make yourself big, yell loudly",
            'B': "Run as fast as you can",
            'C': "Climb the nearest tree",
            'D': "Play dead immediately"
        },
        'correct': 'A',
        'explanation': "If a bear charges, stand your ground, raise arms to look big, yell. Most charges are bluffs. If it's a grizzly THEN play dead. Black bears, fight back.",
        'commentary_correct': "Correct! Stand tall, yell loud. Most bear charges are fake. Don't run.",
        'commentary_wrong': "Wrong! Stand your ground and look big. Running triggers chase instinct.",
        'difficulty': 'hard',
        'time_limit': 15
    },

    # ===== CRIMINAL MASTERMINDS =====
    {
        'category': 'Criminal Masterminds',
        'setup': "A bank robber wrote his holdup note on the back of his own deposit slip.",
        'question': "What happened?",
        'answers': {
            'A': "Police used his account info to track him down",
            'B': "He successfully got away with $10,000",
            'C': "Bank teller didn't notice",
            'D': "He claimed it was a prank"
        },
        'correct': 'A',
        'explanation': "Real story. His name and account number were on the deposit slip. Police arrested him within hours. Criminal genius level: zero.",
        'commentary_correct': "Correct! Used his own deposit slip with his name on it. Arrested in 2 hours.",
        'commentary_wrong': "Wrong! His account info was on the note. Easiest arrest ever.",
        'difficulty': 'easy',
        'time_limit': 15
    },

    {
        'category': 'Criminal Masterminds',
        'setup': "Guy tries to rob a gun store. At 3pm. On a Saturday.",
        'question': "What went wrong?",
        'answers': {
            'A': "The store was full of armed customers who drew on him",
            'B': "Security guard shot him",
            'C': "His gun jammed",
            'D': "He forgot his mask"
        },
        'correct': 'A',
        'explanation': "Real 1990 story. Multiple armed customers drew their guns on him. He dropped his weapon and begged not to be shot. Arrested immediately.",
        'commentary_correct': "Correct! Robbing a gun store = room full of armed people. Not smart.",
        'commentary_wrong': "Wrong! Gun store = everyone has guns. He was surrounded instantly.",
        'difficulty': 'easy',
        'time_limit': 15
    },

    # ===== WEIRD LAWS =====
    {
        'category': 'Weird Laws',
        'setup': "In Alaska, it's illegal to wake a sleeping bear to take its photo.",
        'question': "What's the penalty?",
        'answers': {
            'A': "Up to $10,000 fine and jail time",
            'B': "Just a warning",
            'C': "The bear gets to keep your camera",
            'D': "Community service cleaning parks"
        },
        'correct': 'A',
        'explanation': "Real law. Waking a bear is considered wildlife harassment. Up to $10,000 fine and jail time. Also, the bear will probably kill you.",
        'commentary_correct': "Correct! $10K fine and jail. Plus the bear might eat you. Don't wake bears.",
        'commentary_wrong': "Wrong! $10,000 fine and jail time. Plus death by bear. Double penalty.",
        'difficulty': 'medium',
        'time_limit': 15
    }
]


def seed_batch_2_questions():
    """Add batch 2 questions to database"""
    added = 0
    ph = get_placeholder()

    for q in NEW_QUESTIONS:
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
            print(f"✅ Added: {q['question'][:50]}...")
        except Exception as e:
            print(f"⚠️  Error adding question: {str(e)}")

    print(f"\n✅ Successfully added {added} questions from Batch 2")
    return added


if __name__ == '__main__':
    from trivia_database import init_trivia_database
    init_trivia_database()
    seed_batch_2_questions()
