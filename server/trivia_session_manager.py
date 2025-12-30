"""
TRIVIA SESSION MANAGER
Handles curated 20-minute trivia sessions with skill game breaks

Session Structure:
- Round 1: 5 trivia questions
- Skill Break 1: Pick from 51 skill games
- Round 2: 5 trivia questions
- Skill Break 2: Pick from 51 skill games
- Round 3: 5 trivia questions
- Final Results & Leaderboard
"""

from database import execute_query, get_placeholder
from trivia_database import get_random_question
import random

class TriviaSessionManager:
    """Manages curated trivia sessions with skill game breaks"""

    def __init__(self, session_code):
        self.session_code = session_code
        self.session = self._load_session()

    def _load_session(self):
        """Load session from database"""
        ph = get_placeholder()
        return execute_query(
            f'SELECT * FROM trivia_sessions WHERE session_code = {ph}',
            (self.session_code,),
            fetch_one=True
        )

    def get_session_state(self):
        """
        Get current state of session

        Returns:
            {
                'phase': 'trivia_round' | 'skill_break' | 'final_results',
                'round': 1-3,
                'questions_completed': 0-5,
                'total_questions': 15,
                'skill_breaks_completed': 0-2,
                'time_remaining': seconds
            }
        """
        session = self._load_session()
        current_round = session['current_round']

        # Count questions answered in current round
        ph = get_placeholder()
        questions_in_round = execute_query(f'''
            SELECT COUNT(DISTINCT question_id) as count
            FROM trivia_answers
            WHERE session_id = {ph}
        ''', (session['id'],), fetch_one=True)['count']

        # Determine phase
        questions_per_round = 5
        questions_this_round = questions_in_round % questions_per_round

        if questions_this_round >= questions_per_round:
            if current_round < 3:
                phase = 'skill_break'
            else:
                phase = 'final_results'
        else:
            phase = 'trivia_round'

        skill_breaks = execute_query(f'''
            SELECT COUNT(*) as count
            FROM trivia_skill_breaks
            WHERE session_id = {ph}
        ''', (session['id'],), fetch_one=True)['count']

        # Calculate time remaining (30 seconds per question, 2 minutes per skill break)
        questions_left = 15 - questions_in_round
        skill_breaks_left = 2 - skill_breaks
        time_remaining = (questions_left * 30) + (skill_breaks_left * 120)

        return {
            'phase': phase,
            'round': current_round,
            'questions_completed': questions_in_round,
            'total_questions': 15,
            'skill_breaks_completed': skill_breaks,
            'time_remaining': time_remaining,
            'session_code': self.session_code
        }

    def get_next_question(self):
        """
        Get next question for current round
        Mix of difficulties and categories
        """
        session = self._load_session()

        # Get questions already asked in this session
        ph = get_placeholder()
        asked_ids = execute_query(f'''
            SELECT DISTINCT question_id
            FROM trivia_answers
            WHERE session_id = {ph}
        ''', (session['id'],))

        exclude_ids = [q['question_id'] for q in asked_ids] if asked_ids else []

        # Mix difficulties: 40% easy, 40% medium, 20% hard
        difficulty_pool = ['easy', 'easy', 'medium', 'medium', 'hard']
        questions_this_round = len(exclude_ids) % 5
        difficulty = difficulty_pool[questions_this_round]

        # Get random question with that difficulty
        question = get_random_question(
            difficulty=difficulty,
            exclude_ids=exclude_ids if exclude_ids else None
        )

        if not question:
            # Fallback: any question we haven't asked
            question = get_random_question(exclude_ids=exclude_ids if exclude_ids else None)

        return question

    def complete_question(self):
        """Mark question as completed, check if round is done"""
        state = self.get_session_state()

        if state['questions_completed'] % 5 == 0 and state['questions_completed'] > 0:
            # Round complete
            if state['round'] < 3:
                return {'status': 'skill_break_needed', 'round': state['round']}
            else:
                return {'status': 'session_complete'}

        return {'status': 'next_question'}

    def start_skill_break(self, skill_game_id, skill_game_name):
        """Record skill break started"""
        session = self._load_session()
        ph = get_placeholder()

        execute_query(f'''
            INSERT INTO trivia_skill_breaks
            (session_id, round_number, skill_game_id, skill_game_name)
            VALUES ({ph}, {ph}, {ph}, {ph})
        ''', (session['id'], session['current_round'], skill_game_id, skill_game_name))

    def complete_skill_break(self, winner_puck_id, bonus_points=500):
        """Record skill break results and advance to next round"""
        session = self._load_session()
        ph = get_placeholder()

        # Update skill break with winner
        execute_query(f'''
            UPDATE trivia_skill_breaks
            SET winner_puck_id = {ph}, bonus_points = {ph}
            WHERE session_id = {ph} AND round_number = {ph}
        ''', (winner_puck_id, bonus_points, session['id'], session['current_round']))

        # Award bonus points to winner
        execute_query(f'''
            UPDATE trivia_session_players
            SET total_score = total_score + {ph}
            WHERE session_id = {ph} AND puck_id = {ph}
        ''', (bonus_points, session['id'], winner_puck_id))

        # Advance to next round
        execute_query(f'''
            UPDATE trivia_sessions
            SET current_round = current_round + 1
            WHERE id = {ph}
        ''', (session['id'],))

    def get_final_results(self):
        """Get final leaderboard and session stats"""
        session = self._load_session()
        ph = get_placeholder()

        # Get player scores
        players = execute_query(f'''
            SELECT
                p.puck_id,
                p.player_name,
                p.total_score,
                COUNT(CASE WHEN a.is_correct = 1 THEN 1 END) as correct_answers,
                COUNT(a.id) as total_answers,
                AVG(CASE WHEN a.is_correct = 1 THEN a.response_time_ms END) as avg_response_time
            FROM trivia_session_players p
            LEFT JOIN trivia_answers a ON a.session_id = p.session_id AND a.puck_id = p.puck_id
            WHERE p.session_id = {ph}
            GROUP BY p.puck_id, p.player_name, p.total_score
            ORDER BY p.total_score DESC
        ''', (session['id'],))

        # Get skill break winners
        skill_breaks = execute_query(f'''
            SELECT skill_game_name, winner_puck_id, bonus_points
            FROM trivia_skill_breaks
            WHERE session_id = {ph}
            ORDER BY round_number
        ''', (session['id'],))

        return {
            'players': players,
            'skill_breaks': skill_breaks,
            'total_questions': 15,
            'total_rounds': 3
        }

def get_51_skill_games():
    """
    Return list of 51 skill games available for breaks
    These are from the ESP32 firmware
    """
    return [
        {'id': 1, 'name': 'Reaction Time', 'description': 'Tap as fast as you can!'},
        {'id': 2, 'name': 'Shake Master', 'description': 'Shake faster than your opponent'},
        {'id': 3, 'name': 'Spin Champion', 'description': 'Spin the puck as many times as you can'},
        {'id': 4, 'name': 'Memory Match', 'description': 'Remember the color sequence'},
        {'id': 5, 'name': 'Tap Rhythm', 'description': 'Match the beat pattern'},
        # NOTE: Full list of 51 games would be here
        # For demo purposes, showing structure
        # Real implementation would load from ESP32 firmware manifest
    ]


def pick_random_skill_game():
    """Pick a random skill game for the break"""
    games = get_51_skill_games()
    return random.choice(games)
