"""
TRIVIA WARS - Game Engines
Core game logic for 10 YDKJ-style trivia game types
"""

import random
import time
from typing import Dict, List, Optional
from trivia_database import get_random_question, record_answer

class TriviaGameEngine:
    """Base class for all trivia game types"""

    def __init__(self, session_id, players, game_type_name):
        self.session_id = session_id
        self.players = players  # List of {puck_id, player_name, score, multiplier}
        self.game_type = game_type_name
        self.current_question = None
        self.question_start_time = None
        self.answers_received = {}
        self.round_number = 0

    def start_game(self):
        """Initialize game"""
        self.round_number = 1
        return self.get_initial_state()

    def get_initial_state(self):
        """Get initial game state for TV display"""
        return {
            'game_type': self.game_type,
            'players': self.players,
            'round': self.round_number,
            'status': 'starting'
        }

    def load_question(self, category_id=None, difficulty=None):
        """Load a random question"""
        self.current_question = get_random_question(category_id, difficulty)
        self.question_start_time = time.time()
        self.answers_received = {}

        return {
            'question_id': self.current_question['id'],
            'setup': self.current_question['setup_text'],
            'question': self.current_question['question_text'],
            'answers': {
                'A': self.current_question['answer_a'],
                'B': self.current_question['answer_b'],
                'C': self.current_question['answer_c'],
                'D': self.current_question['answer_d']
            },
            'time_limit': self.current_question['time_limit'],
            'category': self.current_question.get('category_name', '')
        }

    def submit_answer(self, puck_id, answer, response_time_ms=None):
        """Process a player's answer"""
        if not self.current_question:
            return {'error': 'No active question'}

        if puck_id in self.answers_received:
            return {'error': 'Already answered'}

        is_correct = (answer == self.current_question['correct_answer'])

        if response_time_ms is None:
            response_time_ms = int((time.time() - self.question_start_time) * 1000)

        # Calculate points (can be overridden by specific game types)
        points = self.calculate_points(puck_id, is_correct, response_time_ms)

        # Record in database
        player = next((p for p in self.players if p['puck_id'] == puck_id), None)
        multiplier = player['multiplier'] if player else 1.0

        record_answer(
            self.session_id,
            self.current_question['id'],
            puck_id,
            answer,
            is_correct,
            response_time_ms,
            points,
            multiplier
        )

        # Update player score
        if player:
            player['score'] += points

        self.answers_received[puck_id] = {
            'answer': answer,
            'is_correct': is_correct,
            'points': points,
            'response_time_ms': response_time_ms
        }

        return {
            'puck_id': puck_id,
            'is_correct': is_correct,
            'points': points,
            'commentary': self.get_commentary(is_correct)
        }

    def calculate_points(self, puck_id, is_correct, response_time_ms):
        """Calculate points earned (base implementation)"""
        if not is_correct:
            return 0

        base_points = 500
        player = next((p for p in self.players if p['puck_id'] == puck_id), None)
        multiplier = player['multiplier'] if player else 1.0

        return int(base_points * multiplier)

    def get_commentary(self, is_correct):
        """Get host commentary for answer"""
        if not self.current_question:
            return ""

        if is_correct:
            return self.current_question.get('host_commentary_correct', 'Correct!')
        else:
            return self.current_question.get('host_commentary_wrong', 'Wrong!')

    def get_results(self):
        """Get round results"""
        return {
            'question': self.current_question,
            'answers': self.answers_received,
            'players': self.players,
            'correct_answer': self.current_question['correct_answer'],
            'explanation': self.current_question.get('explanation', '')
        }

    def next_round(self):
        """Move to next round"""
        self.round_number += 1
        self.current_question = None
        self.answers_received = {}


# ========================================
# GAME TYPE 1: Category Royale
# ========================================
class CategoryRoyaleGame(TriviaGameEngine):
    """Players shake to pick category"""

    def __init__(self, session_id, players):
        super().__init__(session_id, players, 'category_royale')
        self.available_categories = []
        self.category_picks = {}

    def show_categories(self, categories):
        """Display 4 categories for selection"""
        self.available_categories = categories
        return {
            'phase': 'category_selection',
            'categories': categories,
            'instruction': 'SHAKE to pick your category! Fastest shake wins!'
        }

    def select_category(self, puck_id, category_id, shake_intensity):
        """Player shakes to pick category"""
        self.category_picks[puck_id] = {
            'category_id': category_id,
            'shake_intensity': shake_intensity,
            'timestamp': time.time()
        }

        # Fastest/hardest shake wins
        if len(self.category_picks) == len(self.players):
            winner = max(self.category_picks.items(), key=lambda x: x[1]['shake_intensity'])
            selected_category = winner[1]['category_id']
            return {
                'winner_puck_id': winner[0],
                'selected_category': selected_category,
                'phase': 'questions'
            }

        return {'waiting': True}


# ========================================
# GAME TYPE 2: Multiplier Madness
# ========================================
class MultiplierMadnessGame(TriviaGameEngine):
    """Players spin puck to set multiplier before each question"""

    def request_multipliers(self):
        """Ask all players to spin for multiplier"""
        return {
            'phase': 'multiplier_selection',
            'instruction': 'SPIN your puck to set your multiplier!',
            'options': {
                'slow': '1x (safe)',
                'medium': '2x (risky)',
                'fast': '3x (yolo)'
            }
        }

    def set_multiplier(self, puck_id, spin_speed):
        """Set player multiplier based on spin speed"""
        player = next((p for p in self.players if p['puck_id'] == puck_id), None)
        if not player:
            return {'error': 'Player not found'}

        # Map spin speed to multiplier
        if spin_speed < 100:
            multiplier = 1.0
        elif spin_speed < 200:
            multiplier = 2.0
        else:
            multiplier = 3.0

        player['multiplier'] = multiplier

        return {
            'puck_id': puck_id,
            'multiplier': multiplier,
            'message': f"{multiplier}x multiplier set!"
        }

    def calculate_points(self, puck_id, is_correct, response_time_ms):
        """Override points calculation with multiplier"""
        player = next((p for p in self.players if p['puck_id'] == puck_id), None)
        if not player:
            return 0

        base_points = 500 if is_correct else -200
        return int(base_points * player['multiplier'])


# ========================================
# GAME TYPE 3: Screw Your Neighbor
# ========================================
class ScrewNeighborGame(TriviaGameEngine):
    """Players can force others to answer"""

    def __init__(self, session_id, players):
        super().__init__(session_id, players, 'screw_neighbor')
        self.screws_active = {}

    def activate_screw(self, screwer_puck_id, target_puck_id):
        """Player screws another player"""
        screwer = next((p for p in self.players if p['puck_id'] == screwer_puck_id), None)
        if not screwer:
            return {'error': 'Player not found'}

        # Cost to screw
        screw_cost = 300
        if screwer['score'] < screw_cost:
            return {'error': 'Not enough points'}

        screwer['score'] -= screw_cost

        self.screws_active[target_puck_id] = {
            'screwed_by': screwer_puck_id,
            'cost': screw_cost
        }

        return {
            'target_puck_id': target_puck_id,
            'screwer_puck_id': screwer_puck_id,
            'message': f"Player {screwer_puck_id} screwed Player {target_puck_id}!",
            'instruction': f"Player {target_puck_id} MUST answer alone!"
        }

    def submit_answer(self, puck_id, answer, response_time_ms=None):
        """Override to handle screw mechanics"""
        result = super().submit_answer(puck_id, answer, response_time_ms)

        # Check if this player was screwed
        if puck_id in self.screws_active:
            screw_info = self.screws_active[puck_id]
            screwer_id = screw_info['screwed_by']
            screwer = next((p for p in self.players if p['puck_id'] == screwer_id), None)

            if result['is_correct']:
                # Target answered correctly - screwer loses double
                if screwer:
                    screwer['score'] -= screw_info['cost']
                result['message'] = "Screw FAILED! Screwer loses points!"
            else:
                # Target answered wrong - screwer steals points
                if screwer:
                    screwer['score'] += abs(result['points'])
                result['message'] = "Screw SUCCESS! Points stolen!"

            del self.screws_active[puck_id]

        return result


# ========================================
# GAME TYPE 4: Speed Pyramid
# ========================================
class SpeedPyramidGame(TriviaGameEngine):
    """Points based on answer speed"""

    def calculate_points(self, puck_id, is_correct, response_time_ms):
        """Points determined by speed tiers"""
        if not is_correct:
            return 0

        player = next((p for p in self.players if p['puck_id'] == puck_id), None)
        multiplier = player['multiplier'] if player else 1.0

        # Speed tiers
        if response_time_ms < 3000:  # 0-3 seconds
            tier = 'LEGENDARY'
            points = 1000
        elif response_time_ms < 6000:  # 4-6 seconds
            tier = 'EXPERT'
            points = 500
        elif response_time_ms < 10000:  # 7-10 seconds
            tier = 'AVERAGE'
            points = 200
        elif response_time_ms < 15000:  # 11-15 seconds
            tier = 'ROOKIE'
            points = 50
        else:  # 15+ seconds
            tier = 'CLUELESS'
            points = -100

        return int(points * multiplier)


# ========================================
# GAME TYPE 5: Trivia Gauntlet
# ========================================
class TriviaGauntletGame(TriviaGameEngine):
    """Elimination game - 3 wrong answers = out"""

    def __init__(self, session_id, players):
        super().__init__(session_id, players, 'trivia_gauntlet')
        self.wrong_counts = {p['puck_id']: 0 for p in players}
        self.eliminated = set()

    def submit_answer(self, puck_id, answer, response_time_ms=None):
        """Track wrong answers for elimination"""
        result = super().submit_answer(puck_id, answer, response_time_ms)

        if not result['is_correct']:
            self.wrong_counts[puck_id] += 1

            if self.wrong_counts[puck_id] >= 3:
                self.eliminated.add(puck_id)
                result['eliminated'] = True
                result['message'] = f"Player {puck_id} ELIMINATED! Puck goes dark."

        # Check if only one player remains
        active_players = len([p for p in self.players if p['puck_id'] not in self.eliminated])
        if active_players == 1:
            winner = next(p for p in self.players if p['puck_id'] not in self.eliminated)
            result['winner'] = winner['puck_id']
            result['message'] = f"Player {winner['puck_id']} WINS!"

        return result

    def get_results(self):
        """Include elimination status in results"""
        results = super().get_results()
        results['eliminated_players'] = list(self.eliminated)
        results['wrong_counts'] = self.wrong_counts
        return results


# ========================================
# GAME TYPE 6: Fact or Crap
# ========================================
class FactOrCrapGame(TriviaGameEngine):
    """True/False statements - tilt left (fact) or right (crap)"""

    def load_question(self, category_id=None, difficulty=None):
        """Override to load true/false style questions"""
        # In practice, you'd have a special question type for this
        # For now, we'll use regular questions but only show A/B
        question_data = super().load_question(category_id, difficulty)

        # Simplify to Fact (A) or Crap (B)
        question_data['answers'] = {
            'LEFT': question_data['answers']['A'],  # Fact
            'RIGHT': question_data['answers']['B']  # Crap
        }
        question_data['instruction'] = 'TILT LEFT = Fact, TILT RIGHT = Crap. HOLD button to DOUBLE DOWN!'

        return question_data

    def submit_answer(self, puck_id, answer, response_time_ms=None, double_down=False):
        """Handle double down mechanic"""
        player = next((p for p in self.players if p['puck_id'] == puck_id), None)

        if double_down and player:
            player['multiplier'] = 2.0

        result = super().submit_answer(puck_id, answer, response_time_ms)

        if double_down:
            result['double_down'] = True
            result['message'] = f"DOUBLE DOWN! {result['points']} points!"

        return result


# ========================================
# GAME TYPE 7: Hostage Trivia
# ========================================
class HostageGame(TriviaGameEngine):
    """One player is hostage - everyone else answers"""

    def __init__(self, session_id, players):
        super().__init__(session_id, players, 'hostage_trivia')
        self.hostage_puck_id = None

    def select_hostage(self):
        """Randomly select hostage"""
        self.hostage_puck_id = random.choice([p['puck_id'] for p in self.players])

        return {
            'hostage_puck_id': self.hostage_puck_id,
            'message': f"Player {self.hostage_puck_id} is the HOSTAGE!",
            'instruction': 'Everyone else: answer correctly to hurt the hostage!'
        }

    def calculate_points(self, puck_id, is_correct, response_time_ms):
        """Reversed scoring for hostage"""
        base_points = 500 if is_correct else -200

        # Hostage gets OPPOSITE points
        if puck_id == self.hostage_puck_id:
            return -base_points

        return base_points

    def get_results(self):
        """Show hostage-specific results"""
        results = super().get_results()
        results['hostage_puck_id'] = self.hostage_puck_id

        # Calculate how many answered correctly
        correct_count = sum(1 for ans in self.answers_received.values() if ans['is_correct'])
        results['majority_correct'] = correct_count > len(self.answers_received) / 2

        return results


# ========================================
# GAME ENGINE FACTORY
# ========================================
def create_game_engine(game_type_name, session_id, players):
    """Factory function to create appropriate game engine"""
    engines = {
        'category_royale': CategoryRoyaleGame,
        'multiplier_madness': MultiplierMadnessGame,
        'screw_neighbor': ScrewNeighborGame,
        'speed_pyramid': SpeedPyramidGame,
        'trivia_gauntlet': TriviaGauntletGame,
        'fact_or_crap': FactOrCrapGame,
        'hostage_trivia': HostageGame,
    }

    engine_class = engines.get(game_type_name, TriviaGameEngine)

    # Base class needs game_type_name, but subclasses hardcode it
    if engine_class == TriviaGameEngine:
        return engine_class(session_id, players, game_type_name)
    else:
        return engine_class(session_id, players)
