"""
MULTIPLAYER GAME ENGINES - Table Wars
Real multiplayer games designed for bars, teams, and social chaos
"""

import time
import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# ============================================================================
# GAME MANAGER
# ============================================================================

active_multiplayer_games: Dict[int, any] = {}

def start_multiplayer_game(game_id: int, player_ids: List[int], team_assignments: Dict[int, int] = None):
    """Start a multiplayer game session"""
    session_id = int(time.time() * 1000)  # Unique session ID

    if game_id == 70:
        active_multiplayer_games[session_id] = KeepAwayChaos(player_ids)
    elif game_id == 71:
        active_multiplayer_games[session_id] = TugOfWarTeams(team_assignments or {})
    elif game_id == 72:
        active_multiplayer_games[session_id] = BombLobber(player_ids)
    elif game_id == 73:
        active_multiplayer_games[session_id] = SimonSaysSurvival(player_ids)
    else:
        raise ValueError(f"Unknown multiplayer game: {game_id}")

    return session_id, active_multiplayer_games[session_id].get_state()

def update_multiplayer_game(session_id: int, puck_id: int, input_data: Dict) -> Optional[Dict]:
    """Update multiplayer game state"""
    if session_id not in active_multiplayer_games:
        return None

    game = active_multiplayer_games[session_id]

    if isinstance(game, KeepAwayChaos):
        return game.update(
            puck_id=puck_id,
            tilt_x=input_data.get('tilt_x', 0),
            tilt_y=input_data.get('tilt_y', 0),
            shake_intensity=input_data.get('shake_intensity', 0)
        )
    elif isinstance(game, TugOfWarTeams):
        return game.update(
            puck_id=puck_id,
            shake_intensity=input_data.get('shake_intensity', 0),
            button_held=input_data.get('button_held', False)
        )
    elif isinstance(game, BombLobber):
        return game.update(
            puck_id=puck_id,
            tilt_x=input_data.get('tilt_x', 0),
            tilt_y=input_data.get('tilt_y', 0),
            button_held=input_data.get('button_held', False)
        )
    elif isinstance(game, SimonSaysSurvival):
        return game.update(
            puck_id=puck_id,
            tilt_x=input_data.get('tilt_x', 0),
            shake_intensity=input_data.get('shake_intensity', 0),
            button_held=input_data.get('button_held', False)
        )

    return None

def end_multiplayer_game(session_id: int):
    """End multiplayer game session"""
    if session_id in active_multiplayer_games:
        del active_multiplayer_games[session_id]
        return True
    return False

def get_multiplayer_game_state(session_id: int) -> Optional[Dict]:
    """Get current multiplayer game state"""
    if session_id in active_multiplayer_games:
        return active_multiplayer_games[session_id].get_state()
    return None

# ============================================================================
# GAME 70: KEEP AWAY CHAOS (4-8 players FFA)
# ============================================================================

@dataclass
class Player:
    puck_id: int
    name: str
    x: float = 50.0
    y: float = 50.0
    is_it: bool = False
    times_tagged: int = 0
    is_active: bool = True
    color: str = "#FFFFFF"

class KeepAwayChaos:
    """
    One player is IT, everyone else runs away
    Tilt to move, shake to speed boost
    If IT tags you, you become IT
    """

    def __init__(self, player_ids: List[int]):
        self.players: List[Player] = []
        self.round_number = 1
        self.round_start_time = time.time()
        self.round_duration = 90  # 90 seconds per round
        self.game_over = False
        self.tag_radius = 8.0
        self.last_update = time.time()

        # Create players
        colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF", "#FFA500", "#FF69B4"]
        for i, pid in enumerate(player_ids):
            self.players.append(Player(
                puck_id=pid,
                name=f"Player {i+1}",
                x=random.uniform(20, 80),
                y=random.uniform(20, 80),
                color=colors[i % len(colors)]
            ))

        # Random player starts as IT
        self.players[random.randint(0, len(self.players)-1)].is_it = True

    def update(self, puck_id: int, tilt_x: float, tilt_y: float, shake_intensity: float) -> Dict:
        if self.game_over:
            return self.get_state()

        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # Find player
        player = next((p for p in self.players if p.puck_id == puck_id), None)
        if not player or not player.is_active:
            return self.get_state()

        # Movement speed
        base_speed = 30
        boost_multiplier = 2 if shake_intensity > 15 else 1
        speed = base_speed * boost_multiplier

        # Update position based on tilt
        player.x += (tilt_x / 45.0) * speed * dt
        player.y += (tilt_y / 45.0) * speed * dt

        # Boundary collision
        player.x = max(5, min(95, player.x))
        player.y = max(5, min(95, player.y))

        # Tag detection (only if player is IT)
        if player.is_it:
            for other in self.players:
                if other.puck_id == puck_id or other.is_it or not other.is_active:
                    continue

                distance = math.sqrt((player.x - other.x)**2 + (player.y - other.y)**2)
                if distance < self.tag_radius:
                    # TAG!
                    player.is_it = False
                    other.is_it = True
                    other.times_tagged += 1
                    break

        # Check round end
        if now - self.round_start_time > self.round_duration:
            # Round over - player who is IT loses
            it_player = next((p for p in self.players if p.is_it), None)
            if it_player:
                it_player.times_tagged += 5  # Penalty for being IT at end

            self.game_over = True

        return self.get_state()

    def get_state(self) -> Dict:
        return {
            "game_id": 70,
            "game_type": "keep_away_chaos",
            "round_number": self.round_number,
            "time_remaining": max(0, int(self.round_duration - (time.time() - self.round_start_time))),
            "players": [
                {
                    "puck_id": p.puck_id,
                    "name": p.name,
                    "x": round(p.x, 1),
                    "y": round(p.y, 1),
                    "is_it": p.is_it,
                    "times_tagged": p.times_tagged,
                    "color": p.color,
                    "is_active": p.is_active
                }
                for p in self.players
            ],
            "game_over": self.game_over,
            "winner": min(self.players, key=lambda p: p.times_tagged).name if self.game_over else None
        }


# ============================================================================
# GAME 71: TUG OF WAR TEAMS
# ============================================================================

class TugOfWarTeams:
    """
    Two teams shake their pucks to pull rope
    Button press = power pull
    First team to pull flag to their side wins
    """

    def __init__(self, team_assignments: Dict[int, int]):
        self.team_assignments = team_assignments  # {puck_id: team_number (1 or 2)}
        self.rope_position = 50.0  # 0 = team 1 wins, 100 = team 2 wins
        self.round_number = 1
        self.team1_score = 0
        self.team2_score = 0
        self.round_start_time = time.time()
        self.game_over = False
        self.last_update = time.time()
        self.power_pull_cooldowns: Dict[int, float] = {}

    def update(self, puck_id: int, shake_intensity: float, button_held: bool) -> Dict:
        if self.game_over:
            return self.get_state()

        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        team = self.team_assignments.get(puck_id)
        if not team:
            return self.get_state()

        # Calculate pull force
        pull_force = shake_intensity * 0.5  # Base pull from shaking

        # Power pull bonus
        if button_held:
            if puck_id not in self.power_pull_cooldowns or now - self.power_pull_cooldowns[puck_id] > 3.0:
                pull_force += 20  # Big boost
                self.power_pull_cooldowns[puck_id] = now

        # Apply force to rope
        if team == 1:
            self.rope_position -= pull_force * dt
        else:
            self.rope_position += pull_force * dt

        # Check win condition
        if self.rope_position <= 0:
            self.team1_score += 1
            if self.team1_score >= 2:  # Best of 3
                self.game_over = True
            else:
                self._start_new_round()
        elif self.rope_position >= 100:
            self.team2_score += 1
            if self.team2_score >= 2:
                self.game_over = True
            else:
                self._start_new_round()

        return self.get_state()

    def _start_new_round(self):
        self.rope_position = 50.0
        self.round_number += 1
        self.round_start_time = time.time()
        self.power_pull_cooldowns.clear()

    def get_state(self) -> Dict:
        return {
            "game_id": 71,
            "game_type": "tug_of_war",
            "rope_position": round(self.rope_position, 1),
            "round_number": self.round_number,
            "team1_score": self.team1_score,
            "team2_score": self.team2_score,
            "game_over": self.game_over,
            "winner": "Team 1" if self.team1_score > self.team2_score else "Team 2" if self.game_over else None
        }


# ============================================================================
# GAME 72: BOMB LOBBER
# ============================================================================

@dataclass
class BombPlayer:
    puck_id: int
    name: str
    x: float
    y: float
    lives: int = 3
    has_bomb: bool = False
    color: str = "#FFFFFF"

class BombLobber:
    """
    Hot potato with aiming
    Tilt to aim at other player, button to throw
    Bomb explodes after timer, holder loses life
    """

    def __init__(self, player_ids: List[int]):
        self.players: List[BombPlayer] = []
        self.bomb_timer = 15.0
        self.bomb_start_time = time.time()
        self.game_over = False
        self.last_update = time.time()

        # Position players in circle
        colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF", "#FFA500", "#FF69B4"]
        num_players = len(player_ids)
        for i, pid in enumerate(player_ids):
            angle = (i / num_players) * 2 * math.pi
            x = 50 + math.cos(angle) * 30
            y = 50 + math.sin(angle) * 30

            self.players.append(BombPlayer(
                puck_id=pid,
                name=f"Player {i+1}",
                x=x,
                y=y,
                color=colors[i % len(colors)]
            ))

        # Random player starts with bomb
        self.players[random.randint(0, len(self.players)-1)].has_bomb = True

    def update(self, puck_id: int, tilt_x: float, tilt_y: float, button_held: bool) -> Dict:
        if self.game_over:
            return self.get_state()

        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # Check bomb timer
        time_remaining = self.bomb_timer - (now - self.bomb_start_time)
        if time_remaining <= 0:
            # BOOM!
            bomb_holder = next((p for p in self.players if p.has_bomb), None)
            if bomb_holder:
                bomb_holder.lives -= 1
                bomb_holder.has_bomb = False

                # Check if player eliminated
                if bomb_holder.lives <= 0:
                    # Game over check
                    active_players = [p for p in self.players if p.lives > 0]
                    if len(active_players) <= 1:
                        self.game_over = True
                        return self.get_state()

                # New round - give bomb to random alive player
                alive_players = [p for p in self.players if p.lives > 0]
                if alive_players:
                    random.choice(alive_players).has_bomb = True
                    self.bomb_start_time = time.time()

        # Handle bomb throw
        player = next((p for p in self.players if p.puck_id == puck_id), None)
        if player and player.has_bomb and button_held:
            # Find closest player in direction of tilt
            target_angle = math.atan2(tilt_y, tilt_x)

            best_target = None
            best_alignment = -1

            for other in self.players:
                if other.puck_id == puck_id or other.lives <= 0:
                    continue

                # Angle to other player
                dx = other.x - player.x
                dy = other.y - player.y
                other_angle = math.atan2(dy, dx)

                # How aligned is tilt with this player?
                alignment = math.cos(target_angle - other_angle)
                if alignment > best_alignment:
                    best_alignment = alignment
                    best_target = other

            if best_target and best_alignment > 0.5:  # Must be roughly pointing at them
                player.has_bomb = False
                best_target.has_bomb = True

        return self.get_state()

    def get_state(self) -> Dict:
        now = time.time()
        time_left = max(0, self.bomb_timer - (now - self.bomb_start_time))

        return {
            "game_id": 72,
            "game_type": "bomb_lobber",
            "bomb_timer": round(time_left, 1),
            "players": [
                {
                    "puck_id": p.puck_id,
                    "name": p.name,
                    "x": round(p.x, 1),
                    "y": round(p.y, 1),
                    "lives": p.lives,
                    "has_bomb": p.has_bomb,
                    "color": p.color
                }
                for p in self.players
            ],
            "game_over": self.game_over,
            "winner": next((p.name for p in self.players if p.lives > 0), None) if self.game_over else None
        }


# ============================================================================
# GAME 73: SIMON SAYS SURVIVAL
# ============================================================================

class SimonSaysSurvival:
    """
    TV shows command, players must execute
    Speed increases each round
    Elimination game - last player wins
    """

    def __init__(self, player_ids: List[int]):
        self.players = {pid: {"name": f"Player {i+1}", "active": True, "last_response": None}
                       for i, pid in enumerate(player_ids)}
        self.current_command = None
        self.command_start_time = None
        self.response_window = 2.0  # seconds to respond
        self.round_number = 0
        self.game_over = False
        self.commands = ["SHAKE", "TILT_LEFT", "TILT_RIGHT", "BUTTON", "SPIN"]

    def start_new_round(self):
        self.round_number += 1
        self.current_command = random.choice(self.commands)
        self.command_start_time = time.time()
        self.response_window = max(1.0, 2.0 - (self.round_number * 0.1))  # Gets faster

        # Reset responses
        for pid in self.players:
            self.players[pid]["last_response"] = None

    def update(self, puck_id: int, tilt_x: float, shake_intensity: float, button_held: bool) -> Dict:
        if self.game_over:
            return self.get_state()

        # Start first round
        if self.current_command is None:
            self.start_new_round()
            return self.get_state()

        # Record player response
        if puck_id in self.players and self.players[puck_id]["active"]:
            if self.current_command == "SHAKE" and shake_intensity > 15:
                self.players[puck_id]["last_response"] = "SHAKE"
            elif self.current_command == "TILT_LEFT" and tilt_x < -20:
                self.players[puck_id]["last_response"] = "TILT_LEFT"
            elif self.current_command == "TILT_RIGHT" and tilt_x > 20:
                self.players[puck_id]["last_response"] = "TILT_RIGHT"
            elif self.current_command == "BUTTON" and button_held:
                self.players[puck_id]["last_response"] = "BUTTON"

        # Check if time is up
        if time.time() - self.command_start_time > self.response_window:
            # Eliminate players who didn't respond correctly
            for pid in self.players:
                if self.players[pid]["active"]:
                    if self.players[pid]["last_response"] != self.current_command:
                        self.players[pid]["active"] = False

            # Check game over
            active_count = sum(1 for p in self.players.values() if p["active"])
            if active_count <= 1:
                self.game_over = True
            else:
                self.start_new_round()

        return self.get_state()

    def get_state(self) -> Dict:
        time_left = max(0, self.response_window - (time.time() - self.command_start_time)) if self.command_start_time else 0

        return {
            "game_id": 73,
            "game_type": "simon_says",
            "current_command": self.current_command,
            "time_remaining": round(time_left, 2),
            "round_number": self.round_number,
            "players": [
                {
                    "puck_id": pid,
                    "name": data["name"],
                    "active": data["active"],
                    "responded": data["last_response"] == self.current_command
                }
                for pid, data in self.players.items()
            ],
            "game_over": self.game_over,
            "winner": next((data["name"] for pid, data in self.players.items() if data["active"]), None) if self.game_over else None
        }
