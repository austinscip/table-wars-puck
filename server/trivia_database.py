"""
TRIVIA WARS - Database Schema for YDKJ-Style Trivia Games
Extends existing TABLE WARS database with trivia-specific tables
"""

from database import get_db_connection, execute_query, get_placeholder, USE_POSTGRES

def init_trivia_database():
    """Initialize trivia-specific database tables"""

    ph = get_placeholder()

    # ========================================
    # TABLE: trivia_categories
    # ========================================
    execute_query('''
        CREATE TABLE IF NOT EXISTS trivia_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            emoji TEXT,
            description TEXT,
            difficulty TEXT CHECK(difficulty IN ('easy', 'medium', 'hard')),
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ========================================
    # TABLE: trivia_questions
    # ========================================
    execute_query('''
        CREATE TABLE IF NOT EXISTS trivia_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER NOT NULL,
            question_text TEXT NOT NULL,
            setup_text TEXT,
            answer_a TEXT NOT NULL,
            answer_b TEXT NOT NULL,
            answer_c TEXT NOT NULL,
            answer_d TEXT NOT NULL,
            correct_answer TEXT CHECK(correct_answer IN ('A', 'B', 'C', 'D')),
            explanation TEXT,
            host_commentary_correct TEXT,
            host_commentary_wrong TEXT,
            difficulty TEXT CHECK(difficulty IN ('easy', 'medium', 'hard')),
            time_limit INTEGER DEFAULT 15,
            is_active BOOLEAN DEFAULT 1,
            times_played INTEGER DEFAULT 0,
            times_correct INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (category_id) REFERENCES trivia_categories(id)
        )
    ''')

    # ========================================
    # TABLE: trivia_game_types
    # ========================================
    execute_query('''
        CREATE TABLE IF NOT EXISTS trivia_game_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            display_name TEXT NOT NULL,
            description TEXT,
            mechanics_description TEXT,
            min_players INTEGER DEFAULT 1,
            max_players INTEGER DEFAULT 4,
            duration_seconds INTEGER DEFAULT 300,
            is_active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # ========================================
    # TABLE: trivia_sessions
    # ========================================
    execute_query('''
        CREATE TABLE IF NOT EXISTS trivia_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bar_id INTEGER,
            table_number INTEGER,
            game_type_id INTEGER,
            session_code TEXT UNIQUE,
            status TEXT CHECK(status IN ('waiting', 'active', 'completed')) DEFAULT 'waiting',
            current_round INTEGER DEFAULT 1,
            total_rounds INTEGER DEFAULT 3,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (bar_id) REFERENCES bars(id),
            FOREIGN KEY (game_type_id) REFERENCES trivia_game_types(id)
        )
    ''')

    # ========================================
    # TABLE: trivia_session_players
    # ========================================
    execute_query('''
        CREATE TABLE IF NOT EXISTS trivia_session_players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            puck_id INTEGER NOT NULL,
            player_name TEXT,
            total_score INTEGER DEFAULT 0,
            multiplier REAL DEFAULT 1.0,
            powers_earned INTEGER DEFAULT 0,
            power_active TEXT,
            is_saboteur BOOLEAN DEFAULT 0,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES trivia_sessions(id),
            FOREIGN KEY (puck_id) REFERENCES pucks(id)
        )
    ''')

    # ========================================
    # TABLE: trivia_answers
    # ========================================
    execute_query('''
        CREATE TABLE IF NOT EXISTS trivia_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            puck_id INTEGER NOT NULL,
            answer_given TEXT CHECK(answer_given IN ('A', 'B', 'C', 'D')),
            is_correct BOOLEAN,
            response_time_ms INTEGER,
            points_earned INTEGER DEFAULT 0,
            multiplier_used REAL DEFAULT 1.0,
            was_screwed BOOLEAN DEFAULT 0,
            screwed_by_puck_id INTEGER,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES trivia_sessions(id),
            FOREIGN KEY (question_id) REFERENCES trivia_questions(id),
            FOREIGN KEY (puck_id) REFERENCES pucks(id)
        )
    ''')

    # ========================================
    # TABLE: trivia_skill_breaks
    # ========================================
    execute_query('''
        CREATE TABLE IF NOT EXISTS trivia_skill_breaks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            round_number INTEGER NOT NULL,
            skill_game_id INTEGER NOT NULL,
            skill_game_name TEXT NOT NULL,
            winner_puck_id INTEGER,
            bonus_points INTEGER DEFAULT 500,
            played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES trivia_sessions(id),
            FOREIGN KEY (winner_puck_id) REFERENCES pucks(id)
        )
    ''')

    print("✅ Trivia database tables created successfully")


def seed_trivia_data():
    """Seed database with initial trivia game types and sample data"""

    ph = get_placeholder()

    # ========================================
    # SEED: Game Types
    # ========================================
    game_types = [
        ('shake_attack', 'Shake Attack', 'Rapid-fire category matching', 'SHAKE when you see matches. Speed matters!', 2, 4, 300),
        ('category_royale', 'Category Royale', 'Pick your category', 'SHAKE to pick category. First shake wins!', 2, 4, 300),
        ('multiplier_madness', 'Multiplier Madness', 'Spin for risk', 'SPIN before each question. Fast = high risk, high reward!', 2, 4, 300),
        ('screw_neighbor', 'Screw Your Neighbor', 'Sabotage mechanics', 'SHAKE + HOLD to force opponent to answer. Costs points!', 2, 4, 300),
        ('fact_or_crap', 'Fact or Crap', 'True or false absurdity', 'TILT LEFT = Fact, RIGHT = Crap. HOLD button to double down!', 2, 4, 300),
        ('hostage_trivia', 'Hostage Trivia', 'One vs everyone', 'Random player is hostage. Everyone else answers. Reversed incentives!', 3, 4, 300),
        ('speed_pyramid', 'Speed Pyramid', 'Speed determines value', 'First 3 seconds = GOLD, 4-6 = SILVER, 7-10 = BRONZE', 2, 4, 300),
        ('trivia_gauntlet', 'Trivia Gauntlet', 'Elimination survival', '3 wrong answers = ELIMINATED. Last puck standing wins!', 2, 4, 300),
        ('chaos_round', 'Chaos Round', 'Random modifiers', 'Random rules: Opposite Day, Team Swap, Double Trouble, Mystery Multiplier', 2, 4, 300),
        ('all_or_nothing', 'All or Nothing', 'Final question showdown', 'Bet half your points on one final absurd question', 2, 4, 60),
    ]

    for game in game_types:
        try:
            execute_query(f'''
                INSERT OR IGNORE INTO trivia_game_types
                (name, display_name, description, mechanics_description, min_players, max_players, duration_seconds)
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
            ''', game)
        except:
            pass  # Already exists

    # ========================================
    # SEED: Categories
    # ========================================
    categories = [
        ('Ways to Die Stupidly', '💀', 'Darwin Award winners and natural selection fails', 'medium'),
        ('Florida Man Headlines', '🐊', 'Real news from America\'s weirdest state', 'easy'),
        ('Rejected Inventions', '💡', 'Patents that should never have been approved', 'medium'),
        ('Terrible Life Advice', '🤦', 'Things you should definitely NOT do', 'easy'),
        ('Things That Got Banned', '🚫', 'Outlawed foods, toys, and stupidity', 'medium'),
        ('When Animals Attack', '🦈', 'Nature fights back against dumb humans', 'easy'),
        ('Historical Dumbassery', '📜', 'Idiots from centuries past', 'hard'),
        ('Medical Malpractice', '💊', 'Old-timey doctor cures that were insane', 'medium'),
        ('Criminal Masterminds', '🚓', 'Who got caught immediately', 'easy'),
        ('Weird Laws', '⚖️', 'Real laws that make no sense', 'medium'),
    ]

    for cat in categories:
        try:
            execute_query(f'''
                INSERT OR IGNORE INTO trivia_categories
                (name, emoji, description, difficulty)
                VALUES ({ph}, {ph}, {ph}, {ph})
            ''', cat)
        except:
            pass  # Already exists

    print("✅ Trivia game types and categories seeded successfully")


# ========================================
# HELPER FUNCTIONS
# ========================================

def get_random_question(category_id=None, difficulty=None, exclude_ids=None):
    """Get a random question from database"""
    ph = get_placeholder()

    query = 'SELECT * FROM trivia_questions WHERE is_active = 1'
    params = []

    if category_id:
        query += f' AND category_id = {ph}'
        params.append(category_id)

    if difficulty:
        query += f' AND difficulty = {ph}'
        params.append(difficulty)

    if exclude_ids:
        placeholders = ','.join([ph] * len(exclude_ids))
        query += f' AND id NOT IN ({placeholders})'
        params.extend(exclude_ids)

    query += ' ORDER BY RANDOM() LIMIT 1'

    return execute_query(query, tuple(params), fetch_one=True)


def get_category_by_name(name):
    """Get category by name"""
    ph = get_placeholder()
    return execute_query(f'SELECT * FROM trivia_categories WHERE name = {ph}', (name,), fetch_one=True)


def create_trivia_session(bar_id, table_number, game_type_id):
    """Create new trivia session"""
    import random
    import string

    ph = get_placeholder()
    session_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

    execute_query(f'''
        INSERT INTO trivia_sessions (bar_id, table_number, game_type_id, session_code, status)
        VALUES ({ph}, {ph}, {ph}, {ph}, 'waiting')
    ''', (bar_id, table_number, game_type_id, session_code))

    return session_code


def add_player_to_session(session_id, puck_id, player_name=None):
    """Add player to trivia session"""
    ph = get_placeholder()

    execute_query(f'''
        INSERT INTO trivia_session_players (session_id, puck_id, player_name)
        VALUES ({ph}, {ph}, {ph})
    ''', (session_id, puck_id, player_name))


def record_answer(session_id, question_id, puck_id, answer_given, is_correct, response_time_ms, points_earned, multiplier=1.0):
    """Record player's answer"""
    ph = get_placeholder()

    execute_query(f'''
        INSERT INTO trivia_answers
        (session_id, question_id, puck_id, answer_given, is_correct, response_time_ms, points_earned, multiplier_used)
        VALUES ({ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph}, {ph})
    ''', (session_id, question_id, puck_id, answer_given, is_correct, response_time_ms, points_earned, multiplier))

    # Update player score
    execute_query(f'''
        UPDATE trivia_session_players
        SET total_score = total_score + {ph}
        WHERE session_id = {ph} AND puck_id = {ph}
    ''', (points_earned, session_id, puck_id))

    # Update question stats
    execute_query(f'''
        UPDATE trivia_questions
        SET times_played = times_played + 1,
            times_correct = times_correct + {ph}
        WHERE id = {ph}
    ''', (1 if is_correct else 0, question_id))


if __name__ == '__main__':
    print("Initializing TRIVIA WARS database...")
    init_trivia_database()
    seed_trivia_data()
    print("\n🎉 TRIVIA WARS database ready!")
