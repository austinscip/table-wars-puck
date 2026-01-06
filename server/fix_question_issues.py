"""
FIX QUESTION DATABASE ISSUES
1. Remove duplicate (dancing plague)
2. Fix miscategorized questions
3. Replace with proper YDKJ-style content
"""

from trivia_database import execute_query, get_placeholder, init_trivia_database

def fix_all_issues():
    """Fix duplicates, categories, and add replacements"""
    ph = get_placeholder()

    print("=" * 60)
    print("FIXING QUESTION DATABASE ISSUES")
    print("=" * 60)

    # 1. Remove duplicate dancing plague question (keep ID 80, remove 92)
    print("\n1. Removing duplicate dancing plague question (ID 92)...")
    execute_query(f'UPDATE trivia_questions SET is_active = 0 WHERE id = 92')
    print("   ✅ Duplicate removed")

    # 2. Get correct category IDs
    pop_culture = execute_query(
        f"SELECT id FROM trivia_categories WHERE name = 'Pop Culture Smackdown'",
        fetch_one=True
    )

    math_facts = execute_query(
        f"SELECT id FROM trivia_categories WHERE name = 'Math & Science Facts'",
        fetch_one=True
    )

    if not pop_culture:
        # Create Pop Culture category
        execute_query(
            f"INSERT INTO trivia_categories (name, emoji, description) VALUES ({ph}, {ph}, {ph})",
            ('Pop Culture Smackdown', '🎬', 'Movies, TV, music, and entertainment')
        )
        pop_culture = execute_query(
            f"SELECT id FROM trivia_categories WHERE name = 'Pop Culture Smackdown'",
            fetch_one=True
        )

    if not math_facts:
        # Create Math & Science category
        execute_query(
            f"INSERT INTO trivia_categories (name, emoji, description) VALUES ({ph}, {ph}, {ph})",
            ('Math & Science Facts', '🔬', 'Basic math and science knowledge')
        )
        math_facts = execute_query(
            f"SELECT id FROM trivia_categories WHERE name = 'Math & Science Facts'",
            fetch_one=True
        )

    # 3. Move Florida Man movie questions to Pop Culture
    print("\n2. Moving movie questions to Pop Culture...")
    movie_ids = [61, 62, 63, 64, 65]
    for qid in movie_ids:
        execute_query(
            f'UPDATE trivia_questions SET category_id = {ph} WHERE id = {ph}',
            (pop_culture['id'], qid)
        )
    print(f"   ✅ Moved {len(movie_ids)} questions to Pop Culture")

    # 4. Move Things That Got Banned math questions to Math & Science
    print("\n3. Moving math questions to Math & Science...")
    math_ids = [71, 72, 73, 74]
    for qid in math_ids:
        execute_query(
            f'UPDATE trivia_questions SET category_id = {ph} WHERE id = {ph}',
            (math_facts['id'], qid)
        )
    print(f"   ✅ Moved {len(math_ids)} questions to Math & Science")

    # 5. Move Rejected Inventions science facts to Math & Science
    print("\n4. Moving science facts to Math & Science...")
    science_ids = [53, 54, 55]
    for qid in science_ids:
        execute_query(
            f'UPDATE trivia_questions SET category_id = {ph} WHERE id = {ph}',
            (math_facts['id'], qid)
        )
    print(f"   ✅ Moved {len(science_ids)} questions to Math & Science")

    # 6. Add NEW Florida Man questions
    print("\n5. Adding NEW Florida Man questions...")
    florida_cat = execute_query(
        f"SELECT id FROM trivia_categories WHERE name = 'Florida Man Headlines'",
        fetch_one=True
    )

    new_florida_questions = [
        {
            'setup': "Florida Man arrested for calling 911 to complain about the quality of his cocaine.",
            'question': "What did the cops find when they showed up?",
            'answers': {
                'A': "The cocaine was real, just low quality",
                'B': "It was baking soda",
                'C': "It was sugar",
                'D': "There was no cocaine at all"
            },
            'correct': 'A',
            'explanation': "The cocaine was real. He just wanted better drugs. The police arrested him for possession.",
            'commentary_correct': "Correct! Real cocaine, just bad quality. He called the cops on himself. Florida.",
            'commentary_wrong': "Wrong! The cocaine was real, just low quality. He literally called 911 to complain about his drugs.",
            'difficulty': 'easy'
        },
        {
            'setup': "Florida Man breaks into restaurant, doesn't steal money. Instead, makes himself a burger and leaves.",
            'question': "What did he forget to do?",
            'answers': {
                'A': "Turn off the grill",
                'B': "Clean up his mess",
                'C': "He left his wallet at the crime scene",
                'D': "Lock the door behind him"
            },
            'correct': 'C',
            'explanation': "He dropped his wallet while cooking. Police showed up at his house the next morning.",
            'commentary_correct': "Correct! Left his wallet at the scene. Cops delivered it to his house along with handcuffs.",
            'commentary_wrong': "Wrong! He left his wallet. Police found him the next day. Criminal mastermind.",
            'difficulty': 'easy'
        },
        {
            'setup': "Florida Man arrested for attacking girlfriend with a Subway sandwich.",
            'question': "What type of sandwich was it?",
            'answers': {
                'A': "Italian BMT",
                'B': "Meatball Marinara",
                'C': "Tuna",
                'D': "Police report didn't specify"
            },
            'correct': 'D',
            'explanation': "The police report only said 'footlong sandwich' - they didn't care enough to specify.",
            'commentary_correct': "Correct! Even the cops didn't care what kind. Just 'footlong sandwich assault.'",
            'commentary_wrong': "Wrong! The report just said 'footlong sandwich.' The sandwich type remains a mystery.",
            'difficulty': 'medium'
        },
        {
            'setup': "Florida Man tries to pay for McDonald's with bag of weed.",
            'question': "What happened next?",
            'answers': {
                'A': "Drive-thru worker called the cops",
                'B': "Manager accepted it as payment",
                'C': "He drove off without food",
                'D': "Worker took the weed and gave him free food"
            },
            'correct': 'A',
            'explanation': "The drive-thru worker called police. Florida Man arrested for possession.",
            'commentary_correct': "Correct! Worker called the cops. Surprise: McDonald's doesn't accept weed as payment.",
            'commentary_wrong': "Wrong! The worker called police. No weed-for-burgers exchange program exists. Yet.",
            'difficulty': 'easy'
        },
        {
            'setup': "Florida Man arrested for threatening his neighbor with a samurai sword... while naked.",
            'question': "What was the argument about?",
            'answers': {
                'A': "Loud music",
                'B': "Property line dispute",
                'C': "Garbage cans",
                'D': "His neighbor's dog wouldn't stop barking"
            },
            'correct': 'C',
            'explanation': "They were fighting about where to put the garbage cans. Classic Florida escalation.",
            'commentary_correct': "Correct! Garbage can dispute = naked samurai sword fight. Florida logic.",
            'commentary_wrong': "Wrong! It was about garbage cans. Because Florida solves trash disputes with samurai swords.",
            'difficulty': 'medium'
        }
    ]

    for q in new_florida_questions:
        execute_query(f'''
            INSERT INTO trivia_questions (
                category_id, setup_text, question_text,
                answer_a, answer_b, answer_c, answer_d,
                correct_answer, explanation,
                host_commentary_correct, host_commentary_wrong,
                difficulty, time_limit, is_active
            ) VALUES (
                {ph}, {ph}, {ph},
                {ph}, {ph}, {ph}, {ph},
                {ph}, {ph},
                {ph}, {ph},
                {ph}, 15, 1
            )
        ''', (
            florida_cat['id'], q['setup'], q['question'],
            q['answers']['A'], q['answers']['B'], q['answers']['C'], q['answers']['D'],
            q['correct'], q['explanation'],
            q['commentary_correct'], q['commentary_wrong'],
            q['difficulty']
        ))

    print(f"   ✅ Added {len(new_florida_questions)} NEW Florida Man questions")

    # 7. Add NEW "Things That Got Banned" questions
    print("\n6. Adding NEW Things That Got Banned questions...")
    banned_cat = execute_query(
        f"SELECT id FROM trivia_categories WHERE name = 'Things That Got Banned'",
        fetch_one=True
    )

    new_banned_questions = [
        {
            'setup': "You're in Germany in 1941. Hitler just banned all typewriters.",
            'question': "Why did he ban them?",
            'answers': {
                'A': "People were typing anti-Nazi messages",
                'B': "He was paranoid people would forge documents",
                'C': "Paper shortage for the war effort",
                'D': "He preferred handwritten correspondence"
            },
            'correct': 'B',
            'explanation': "Hitler banned private typewriters because he was paranoid about document forgery.",
            'commentary_correct': "Correct! Hitler was paranoid about fake documents. Banned all typewriters. Classic dictator move.",
            'commentary_wrong': "Wrong! He was afraid of document forgery. Typewriter ban = peak paranoia.",
            'difficulty': 'hard'
        },
        {
            'setup': "You're in the UK trying to buy an energy drink called 'Cocaine.'",
            'question': "Why was it banned?",
            'answers': {
                'A': "Actually contained cocaine",
                'B': "Name was too controversial",
                'C': "Caused heart attacks",
                'D': "Marketing made kids want real cocaine"
            },
            'correct': 'B',
            'explanation': "The drink didn't contain cocaine, but the name was banned for being too controversial.",
            'commentary_correct': "Correct! No actual cocaine, just a terrible name. UK said 'nope.'",
            'commentary_wrong': "Wrong! Just the name was the problem. UK doesn't like energy drinks named after drugs.",
            'difficulty': 'medium'
        },
        {
            'setup': "You're in Saudi Arabia with a deck of playing cards.",
            'question': "Why are they banned?",
            'answers': {
                'A': "Gambling is forbidden in Islam",
                'B': "Kings/Queens = monarchy symbols",
                'C': "Cards are used for fortune telling",
                'D': "Western cultural influence"
            },
            'correct': 'A',
            'explanation': "Playing cards are banned because they're associated with gambling, which is forbidden.",
            'commentary_correct': "Correct! Gambling = forbidden. Cards = gambling tools. Cards = banned. Math checks out.",
            'commentary_wrong': "Wrong! It's about gambling. Islam forbids it. No cards allowed.",
            'difficulty': 'easy'
        },
        {
            'setup': "You're in North Korea trying to watch a movie. But blue jeans are banned in all films.",
            'question': "What's the official reason?",
            'answers': {
                'A': "Symbol of American imperialism",
                'B': "Distraction from the plot",
                'C': "Promotes capitalism",
                'D': "North Korea doesn't make denim"
            },
            'correct': 'A',
            'explanation': "Blue jeans are seen as a symbol of American culture and imperialism.",
            'commentary_correct': "Correct! Jeans = America = banned. North Korea logic.",
            'commentary_wrong': "Wrong! Jeans symbolize America. Can't have that in the Hermit Kingdom.",
            'difficulty': 'easy'
        }
    ]

    for q in new_banned_questions:
        execute_query(f'''
            INSERT INTO trivia_questions (
                category_id, setup_text, question_text,
                answer_a, answer_b, answer_c, answer_d,
                correct_answer, explanation,
                host_commentary_correct, host_commentary_wrong,
                difficulty, time_limit, is_active
            ) VALUES (
                {ph}, {ph}, {ph},
                {ph}, {ph}, {ph}, {ph},
                {ph}, {ph},
                {ph}, {ph},
                {ph}, 15, 1
            )
        ''', (
            banned_cat['id'], q['setup'], q['question'],
            q['answers']['A'], q['answers']['B'], q['answers']['C'], q['answers']['D'],
            q['correct'], q['explanation'],
            q['commentary_correct'], q['commentary_wrong'],
            q['difficulty']
        ))

    print(f"   ✅ Added {len(new_banned_questions)} NEW Things That Got Banned questions")

    # 8. Add NEW Rejected Inventions questions
    print("\n7. Adding NEW Rejected Inventions questions...")
    inventions_cat = execute_query(
        f"SELECT id FROM trivia_categories WHERE name = 'Rejected Inventions'",
        fetch_one=True
    )

    new_invention_questions = [
        {
            'setup': "In 1963, someone invented the 'Isolator' - a soundproof helmet with an oxygen tank.",
            'question': "What was it for?",
            'answers': {
                'A': "Help people focus by blocking all distractions",
                'B': "Deep-sea diving",
                'C': "Astronaut training",
                'D': "Sleep aid for insomniacs"
            },
            'correct': 'A',
            'explanation': "It was supposed to help people concentrate by blocking out all sights and sounds.",
            'commentary_correct': "Correct! Soundproof helmet for focus. Looks like a serial killer cosplay. Never caught on.",
            'commentary_wrong': "Wrong! It was for concentration. Like noise-canceling headphones but terrifying.",
            'difficulty': 'medium'
        },
        {
            'setup': "Someone invented a gun that shoots bullets designed to make people stop and laugh.",
            'question': "What was the bullet filled with?",
            'answers': {
                'A': "Laughing gas (nitrous oxide)",
                'B': "Tickle powder",
                'C': "Pepper spray",
                'D': "Helium"
            },
            'correct': 'A',
            'explanation': "Bullets filled with nitrous oxide gas to incapacitate targets with laughter.",
            'commentary_correct': "Correct! Nitrous oxide bullets. Shoot someone, they laugh uncontrollably. Dystopian as hell.",
            'commentary_wrong': "Wrong! Laughing gas bullets. Because regular bullets weren't weird enough.",
            'difficulty': 'hard'
        },
        {
            'setup': "In the 1950s, someone invented glasses with tiny windshield wipers.",
            'question': "What problem were they trying to solve?",
            'answers': {
                'A': "Rain on glasses",
                'B': "Sweaty lenses",
                'C': "Dust and dirt",
                'D': "Foggy lenses in cold weather"
            },
            'correct': 'A',
            'explanation': "Mini windshield wipers to clear rain off glasses. Absurd but technically functional.",
            'commentary_correct': "Correct! Tiny windshield wipers for your face. Ridiculous but kinda genius.",
            'commentary_wrong': "Wrong! It was for rain. Because apparently wiping your glasses with your hand is too hard.",
            'difficulty': 'easy'
        }
    ]

    for q in new_invention_questions:
        execute_query(f'''
            INSERT INTO trivia_questions (
                category_id, setup_text, question_text,
                answer_a, answer_b, answer_c, answer_d,
                correct_answer, explanation,
                host_commentary_correct, host_commentary_wrong,
                difficulty, time_limit, is_active
            ) VALUES (
                {ph}, {ph}, {ph},
                {ph}, {ph}, {ph}, {ph},
                {ph}, {ph},
                {ph}, {ph},
                {ph}, 15, 1
            )
        ''', (
            inventions_cat['id'], q['setup'], q['question'],
            q['answers']['A'], q['answers']['B'], q['answers']['C'], q['answers']['D'],
            q['correct'], q['explanation'],
            q['commentary_correct'], q['commentary_wrong'],
            q['difficulty']
        ))

    print(f"   ✅ Added {len(new_invention_questions)} NEW Rejected Inventions questions")

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY OF CHANGES")
    print("=" * 60)

    # Count active questions by category
    categories = execute_query('''
        SELECT
            c.name,
            COUNT(*) as count
        FROM trivia_questions q
        JOIN trivia_categories c ON q.category_id = c.id
        WHERE q.is_active = 1
        GROUP BY c.name
        ORDER BY count DESC
    ''', fetch_all=True)

    total = 0
    for cat in categories:
        print(f"{cat['name']}: {cat['count']} questions")
        total += cat['count']

    print("-" * 60)
    print(f"TOTAL ACTIVE QUESTIONS: {total}")
    print("=" * 60)


if __name__ == '__main__':
    init_trivia_database()
    fix_all_issues()
    print("\n✅ ALL ISSUES FIXED!")
