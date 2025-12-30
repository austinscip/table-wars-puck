"""
TV-Integrated Game Engines for Table Wars
Games 52-56: Real-time puck control with TV display

Each game engine:
- Receives WebSocket input from ESP32 (tilt, shake, button)
- Updates game state in real-time
- Sends state to TV for rendering
- Returns final score when game ends
"""

import time
import random
import math
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional

# ============================================================================
# GAME 52: PUCK RACER
# ============================================================================

@dataclass
class Obstacle:
    lane: float  # 1-4
    distance: float  # pixels from player
    type: str  # "cone", "skull", "warning"

@dataclass
class Collectible:
    lane: float
    distance: float
    type: str  # "coin", "nitro"
    collected: bool = False

class PuckRacer:
    """
    Endless runner racing game. Tilt to steer, avoid obstacles, collect coins.
    """

    def __init__(self):
        self.car_lane = 2.5  # Current lane (1-4, decimals for smooth movement)
        self.speed = 60  # Base speed (mph)
        self.score = 0
        self.distance = 0
        self.crashes = 0
        self.nitro_count = 3
        self.nitro_active = False
        self.nitro_timer = 0
        self.obstacles: List[Obstacle] = []
        self.collectibles: List[Collectible] = []
        self.combo = 0
        self.game_over = False
        self.start_time = time.time()
        self.last_update = time.time()

    def update(self, tilt_x: float, button_held: bool, shake_detected: bool) -> Dict:
        """
        Update game state based on puck input

        Args:
            tilt_x: Tilt angle -45 to 45 degrees
            button_held: Is button being held (accelerate)
            shake_detected: Did player shake (nitro boost)

        Returns:
            Game state dict for TV rendering
        """
        if self.game_over:
            return self.get_state()

        # Calculate delta time
        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # Update car position based on tilt (-45 to 45 degrees)
        # Map to lane movement: -45° = move left, +45° = move right
        lane_speed = (tilt_x / 45.0) * 3.0  # Max 3 lanes/sec movement
        self.car_lane += lane_speed * dt
        self.car_lane = max(1.0, min(4.0, self.car_lane))  # Clamp to lanes 1-4

        # Update speed based on button
        if button_held:
            self.speed = 100
        else:
            self.speed = 60

        # Nitro boost
        if shake_detected and self.nitro_count > 0 and not self.nitro_active:
            self.nitro_active = True
            self.nitro_count -= 1
            self.nitro_timer = 3.0  # 3 second boost

        if self.nitro_active:
            self.speed = 150
            self.nitro_timer -= dt
            if self.nitro_timer <= 0:
                self.nitro_active = False

        # Update distance traveled
        distance_delta = self.speed * dt * 1.5  # Scale for visual effect
        self.distance += distance_delta
        self.score += int(distance_delta / 10)  # +10 points per 100 units

        # Move obstacles toward player
        for obstacle in self.obstacles:
            obstacle.distance -= distance_delta

        # Move collectibles toward player
        for collectible in self.collectibles:
            if not collectible.collected:
                collectible.distance -= distance_delta

        # Remove off-screen obstacles
        self.obstacles = [obs for obs in self.obstacles if obs.distance > -50]

        # Spawn new obstacles (random)
        if random.random() < 0.02:  # 2% chance per frame
            self.spawn_obstacle()

        # Spawn new collectibles
        if random.random() < 0.015:  # 1.5% chance per frame
            self.spawn_collectible()

        # Collision detection
        self.check_collisions()

        # Check game over
        if self.crashes >= 3:
            self.game_over = True

        # Time limit: 90 seconds
        if time.time() - self.start_time > 90:
            self.game_over = True

        return self.get_state()

    def spawn_obstacle(self):
        """Spawn random obstacle in random lane"""
        lane = random.randint(1, 4)
        obstacle_type = random.choice(["cone", "cone", "skull", "warning"])  # Cones more common
        self.obstacles.append(Obstacle(lane=lane, distance=600, type=obstacle_type))

    def spawn_collectible(self):
        """Spawn coin or nitro refill"""
        lane = random.randint(1, 4)
        collectible_type = random.choice(["coin", "coin", "coin", "nitro"])  # Coins more common
        self.collectibles.append(Collectible(lane=lane, distance=600, type=collectible_type))

    def check_collisions(self):
        """Check for hits and collections"""
        # Check obstacle collisions
        for obstacle in self.obstacles:
            if obstacle.distance < 30 and obstacle.distance > -10:  # Within collision range
                if abs(self.car_lane - obstacle.lane) < 0.6:  # Hit!
                    self.crashes += 1
                    self.combo = 0  # Reset combo
                    obstacle.distance = -100  # Remove obstacle
                    self.score -= 200  # Penalty
                    return  # One collision per frame

            # Near-miss bonus
            if obstacle.distance < 30 and obstacle.distance > 20:
                if abs(self.car_lane - obstacle.lane) < 1.5 and abs(self.car_lane - obstacle.lane) > 0.6:
                    self.score += 50

        # Check collectible pickups
        for collectible in self.collectibles:
            if collectible.collected:
                continue
            if collectible.distance < 30 and collectible.distance > -10:
                if abs(self.car_lane - collectible.lane) < 0.8:  # Collected!
                    collectible.collected = True
                    if collectible.type == "coin":
                        self.combo += 1
                        coin_value = 100 * (2 if self.combo >= 3 else 1)  # Combo multiplier
                        self.score += coin_value
                    elif collectible.type == "nitro":
                        self.nitro_count = min(3, self.nitro_count + 1)
                        self.score += 200

    def get_state(self) -> Dict:
        """Return current game state for TV rendering"""
        return {
            "game_id": 52,
            "game_type": "puck_racer",
            "car_lane": round(self.car_lane, 2),
            "speed": self.speed,
            "score": self.score,
            "distance": int(self.distance),
            "crashes": self.crashes,
            "nitro_count": self.nitro_count,
            "nitro_active": self.nitro_active,
            "combo": self.combo,
            "obstacles": [
                {"lane": obs.lane, "distance": int(obs.distance), "type": obs.type}
                for obs in self.obstacles if obs.distance > 0 and obs.distance < 700
            ],
            "collectibles": [
                {"lane": col.lane, "distance": int(col.distance), "type": col.type}
                for col in self.collectibles if not col.collected and col.distance > 0 and col.distance < 700
            ],
            "game_over": self.game_over,
            "time_remaining": max(0, int(90 - (time.time() - self.start_time)))
        }


# ============================================================================
# GAME 53: OBSTACLE DODGER
# ============================================================================

@dataclass
class FallingObject:
    x: float  # 0-100 (percentage across screen)
    y: float  # 0-600 (pixels from top)
    speed: float
    type: str  # "meteor", "bomb", "star"

class ObstacleDodger:
    """
    2D movement - dodge falling objects from the sky
    """

    def __init__(self):
        self.player_x = 50  # Center (0-100%)
        self.player_y = 80  # Bottom area (0-100%)
        self.score = 0
        self.hits = 0
        self.objects: List[FallingObject] = []
        self.game_over = False
        self.start_time = time.time()
        self.last_update = time.time()

    def update(self, tilt_x: float, tilt_y: float, shake: bool) -> Dict:
        """Update game based on 2D tilt"""
        if self.game_over:
            return self.get_state()

        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # Move player based on tilt (X and Y)
        self.player_x += (tilt_x / 45.0) * 40 * dt  # Left/right
        self.player_y += (tilt_y / 45.0) * 30 * dt  # Forward/back

        self.player_x = max(10, min(90, self.player_x))
        self.player_y = max(10, min(90, self.player_y))

        # Spawn falling objects
        if random.random() < 0.03:
            self.spawn_object()

        # Update falling objects
        for obj in self.objects:
            obj.y += obj.speed * dt

        # Remove off-screen objects
        self.objects = [obj for obj in self.objects if obj.y < 105]

        # Collision detection
        for obj in self.objects:
            if abs(obj.x - self.player_x) < 8 and abs(obj.y - self.player_y) < 8:
                if obj.type == "star":
                    self.score += 200
                else:
                    self.hits += 1
                    self.score -= 100
                obj.y = 200  # Remove

        # Score for survival
        self.score += 1

        # Game over conditions
        if self.hits >= 5 or time.time() - self.start_time > 60:
            self.game_over = True

        return self.get_state()

    def spawn_object(self):
        x = random.uniform(10, 90)
        speed = random.uniform(20, 50)
        obj_type = random.choice(["meteor", "meteor", "bomb", "star"])
        self.objects.append(FallingObject(x=x, y=0, speed=speed, type=obj_type))

    def get_state(self) -> Dict:
        return {
            "game_id": 53,
            "game_type": "obstacle_dodger",
            "player_x": round(self.player_x, 1),
            "player_y": round(self.player_y, 1),
            "score": self.score,
            "hits": self.hits,
            "objects": [
                {"x": round(obj.x, 1), "y": round(obj.y, 1), "type": obj.type}
                for obj in self.objects if obj.y >= 0 and obj.y < 100
            ],
            "game_over": self.game_over,
            "time_remaining": max(0, int(60 - (time.time() - self.start_time)))
        }


# ============================================================================
# GAME 54: PUCK GOLF
# ============================================================================

class PuckGolf:
    """
    Shake to swing, tilt to aim. Get ball in hole in fewest strokes.
    """

    def __init__(self):
        self.ball_x = 50
        self.ball_y = 90
        self.hole_x = 50
        self.hole_y = 10
        self.aim_angle = 0  # degrees
        self.power = 0
        self.charging = False
        self.ball_vx = 0
        self.ball_vy = 0
        self.strokes = 0
        self.score = 1000
        self.hole_number = 1
        self.game_over = False
        self.start_time = time.time()
        self.last_update = time.time()

    def update(self, tilt_x: float, shake_intensity: float, button_held: bool) -> Dict:
        if self.game_over:
            return self.get_state()

        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # Tilt to aim
        self.aim_angle = tilt_x * 2  # -90 to +90 degrees

        # Hold button to charge power, shake to release
        if button_held and not self.charging:
            self.charging = True
            self.power = 0

        if self.charging:
            self.power = min(100, self.power + 50 * dt)

        # Shake to swing
        if shake_intensity > 10 and self.charging:
            self.swing()
            self.charging = False

        # Update ball physics
        self.ball_x += self.ball_vx * dt
        self.ball_y += self.ball_vy * dt

        # Friction
        self.ball_vx *= 0.98
        self.ball_vy *= 0.98

        # Bounds
        self.ball_x = max(5, min(95, self.ball_x))
        self.ball_y = max(5, min(95, self.ball_y))

        # Check if in hole
        dist = math.sqrt((self.ball_x - self.hole_x)**2 + (self.ball_y - self.hole_y)**2)
        if dist < 5 and abs(self.ball_vx) < 2 and abs(self.ball_vy) < 2:
            self.next_hole()

        # Game over after 9 holes
        if self.hole_number > 9:
            self.game_over = True

        return self.get_state()

    def swing(self):
        """Hit the ball based on power and aim"""
        self.strokes += 1
        self.score -= 50  # Penalty per stroke

        angle_rad = math.radians(self.aim_angle - 90)  # Convert to radians, adjust for screen coords
        force = self.power / 2

        self.ball_vx = math.cos(angle_rad) * force
        self.ball_vy = math.sin(angle_rad) * force

        self.power = 0

    def next_hole(self):
        """Move to next hole"""
        par = 3
        strokes_over = self.strokes - par

        if strokes_over <= 0:
            self.score += 300  # Bonus for under par
        else:
            self.score -= strokes_over * 100

        self.hole_number += 1
        self.ball_x = 50
        self.ball_y = 90
        self.hole_x = random.uniform(30, 70)
        self.hole_y = random.uniform(10, 30)
        self.strokes = 0
        self.ball_vx = 0
        self.ball_vy = 0

    def get_state(self) -> Dict:
        return {
            "game_id": 54,
            "game_type": "puck_golf",
            "ball_x": round(self.ball_x, 1),
            "ball_y": round(self.ball_y, 1),
            "hole_x": round(self.hole_x, 1),
            "hole_y": round(self.hole_y, 1),
            "aim_angle": round(self.aim_angle, 1),
            "power": round(self.power, 1),
            "charging": self.charging,
            "strokes": self.strokes,
            "hole_number": self.hole_number,
            "score": self.score,
            "game_over": self.game_over
        }


# ============================================================================
# GAME 55: SPACE INVADERS PUCK
# ============================================================================

@dataclass
class Alien:
    x: float
    y: float
    alive: bool = True

@dataclass
class Bullet:
    x: float
    y: float
    player_bullet: bool

class SpaceInvadersPuck:
    """
    Tilt to move ship, shake to shoot aliens
    """

    def __init__(self):
        self.ship_x = 50
        self.aliens: List[Alien] = []
        self.bullets: List[Bullet] = []
        self.score = 0
        self.lives = 3
        self.wave = 1
        self.game_over = False
        self.last_shot_time = 0
        self.last_update = time.time()
        self.spawn_aliens()

    def spawn_aliens(self):
        """Spawn grid of aliens"""
        self.aliens = []
        for row in range(4):
            for col in range(8):
                self.aliens.append(Alien(
                    x=15 + col * 10,
                    y=10 + row * 8
                ))

    def update(self, tilt_x: float, shake_intensity: float) -> Dict:
        if self.game_over:
            return self.get_state()

        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # Move ship
        self.ship_x += (tilt_x / 45.0) * 40 * dt
        self.ship_x = max(10, min(90, self.ship_x))

        # Shoot on shake (0.3s cooldown)
        if shake_intensity > 10 and now - self.last_shot_time > 0.3:
            self.bullets.append(Bullet(x=self.ship_x, y=90, player_bullet=True))
            self.last_shot_time = now

        # Update bullets
        for bullet in self.bullets:
            if bullet.player_bullet:
                bullet.y -= 80 * dt
            else:
                bullet.y += 40 * dt

        # Remove off-screen bullets
        self.bullets = [b for b in self.bullets if 0 < b.y < 100]

        # Alien shooting
        if random.random() < 0.01:
            alive_aliens = [a for a in self.aliens if a.alive]
            if alive_aliens:
                shooter = random.choice(alive_aliens)
                self.bullets.append(Bullet(x=shooter.x, y=shooter.y, player_bullet=False))

        # Check bullet-alien collisions
        for bullet in self.bullets[:]:
            if not bullet.player_bullet:
                continue
            for alien in self.aliens:
                if not alien.alive:
                    continue
                if abs(bullet.x - alien.x) < 5 and abs(bullet.y - alien.y) < 5:
                    alien.alive = False
                    self.score += 100
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    break

        # Check bullet-player collisions
        for bullet in self.bullets[:]:
            if bullet.player_bullet:
                continue
            if abs(bullet.x - self.ship_x) < 5 and abs(bullet.y - 90) < 5:
                self.lives -= 1
                if bullet in self.bullets:
                    self.bullets.remove(bullet)

        # Check if wave cleared
        if all(not a.alive for a in self.aliens):
            self.wave += 1
            self.score += 500
            self.spawn_aliens()

        # Game over
        if self.lives <= 0:
            self.game_over = True

        return self.get_state()

    def get_state(self) -> Dict:
        return {
            "game_id": 55,
            "game_type": "space_invaders",
            "ship_x": round(self.ship_x, 1),
            "aliens": [
                {"x": round(a.x, 1), "y": round(a.y, 1)}
                for a in self.aliens if a.alive
            ],
            "bullets": [
                {"x": round(b.x, 1), "y": round(b.y, 1), "player": b.player_bullet}
                for b in self.bullets
            ],
            "score": self.score,
            "lives": self.lives,
            "wave": self.wave,
            "game_over": self.game_over
        }


# ============================================================================
# GAME 56: PONG PUCK
# ============================================================================

class PongPuck:
    """
    Tilt to move paddle, play against AI
    """

    def __init__(self):
        self.paddle_y = 50
        self.ai_paddle_y = 50
        self.ball_x = 50
        self.ball_y = 50
        self.ball_vx = 30
        self.ball_vy = 20
        self.player_score = 0
        self.ai_score = 0
        self.game_over = False
        self.last_update = time.time()

    def update(self, tilt_y: float) -> Dict:
        if self.game_over:
            return self.get_state()

        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # Move player paddle
        self.paddle_y += (tilt_y / 45.0) * 50 * dt
        self.paddle_y = max(15, min(85, self.paddle_y))

        # AI paddle (simple tracking)
        if self.ball_y > self.ai_paddle_y + 2:
            self.ai_paddle_y += 30 * dt
        elif self.ball_y < self.ai_paddle_y - 2:
            self.ai_paddle_y -= 30 * dt
        self.ai_paddle_y = max(15, min(85, self.ai_paddle_y))

        # Move ball
        self.ball_x += self.ball_vx * dt
        self.ball_y += self.ball_vy * dt

        # Ball-paddle collision (player)
        if self.ball_x < 15 and abs(self.ball_y - self.paddle_y) < 10:
            self.ball_vx = abs(self.ball_vx)
            self.ball_vy += (self.ball_y - self.paddle_y) * 2  # Angle based on hit position

        # Ball-paddle collision (AI)
        if self.ball_x > 85 and abs(self.ball_y - self.ai_paddle_y) < 10:
            self.ball_vx = -abs(self.ball_vx)
            self.ball_vy += (self.ball_y - self.ai_paddle_y) * 2

        # Ball-wall collision (top/bottom)
        if self.ball_y < 5 or self.ball_y > 95:
            self.ball_vy *= -1

        # Scoring
        if self.ball_x < 0:
            self.ai_score += 1
            self.reset_ball()
        elif self.ball_x > 100:
            self.player_score += 1
            self.reset_ball()

        # Game over (first to 7)
        if self.player_score >= 7 or self.ai_score >= 7:
            self.game_over = True

        return self.get_state()

    def reset_ball(self):
        self.ball_x = 50
        self.ball_y = 50
        self.ball_vx = random.choice([-30, 30])
        self.ball_vy = random.uniform(-20, 20)

    def get_state(self) -> Dict:
        return {
            "game_id": 56,
            "game_type": "pong_puck",
            "paddle_y": round(self.paddle_y, 1),
            "ai_paddle_y": round(self.ai_paddle_y, 1),
            "ball_x": round(self.ball_x, 1),
            "ball_y": round(self.ball_y, 1),
            "player_score": self.player_score,
            "ai_score": self.ai_score,
            "game_over": self.game_over
        }


# ============================================================================
# GAME 57: CLAW MACHINE PRIZE GAME
# ============================================================================

@dataclass
class Prize:
    x: float  # 0-100 (percentage)
    y: float  # 0-100 (percentage)
    z: float  # depth 0-100
    type: str  # "teddy", "console", "cash", "gold_ring"
    value: int
    grabbed: bool = False

class ClawMachine:
    """
    Tilt to move claw in 2D, button to drop and grab prizes
    3D perspective view of claw machine interior
    """

    def __init__(self):
        self.claw_x = 50
        self.claw_y = 50
        self.claw_z = 0  # Height: 0 = top, 100 = bottom
        self.claw_open = True
        self.claw_descending = False
        self.claw_ascending = False
        self.grabbed_prize = None
        self.score = 0
        self.attempts_remaining = 5
        self.prizes: List[Prize] = []
        self.game_over = False
        self.start_time = time.time()
        self.last_update = time.time()

        # Spawn prizes at start
        self._spawn_prizes()

    def _spawn_prizes(self):
        """Spawn random prizes in the machine"""
        prize_types = [
            ("teddy", 100),
            ("teddy", 100),
            ("console", 500),
            ("cash", 300),
            ("gold_ring", 1000)
        ]

        for ptype, value in prize_types:
            for _ in range(2 if ptype == "teddy" else 1):
                self.prizes.append(Prize(
                    x=random.uniform(20, 80),
                    y=random.uniform(30, 80),
                    z=random.uniform(85, 95),
                    type=ptype,
                    value=value
                ))

    def update(self, tilt_x: float, tilt_y: float, button_held: bool) -> Dict:
        if self.game_over:
            return self.get_state()

        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # POSITIONING PHASE: Move claw with tilt
        if not self.claw_descending and not self.claw_ascending and self.claw_z == 0:
            # Move X and Y based on tilt
            self.claw_x += (tilt_x / 45.0) * 30 * dt
            self.claw_y += (tilt_y / 45.0) * 30 * dt
            self.claw_x = max(10, min(90, self.claw_x))
            self.claw_y = max(10, min(90, self.claw_y))

            # Button press = start descending
            if button_held and not self.claw_descending:
                self.claw_descending = True
                self.claw_open = True
                self.attempts_remaining -= 1

        # DESCENDING PHASE
        if self.claw_descending:
            self.claw_z += 60 * dt  # Descend at 60 units/sec

            if self.claw_z >= 90:  # Reached bottom
                self.claw_z = 90
                self.claw_open = False  # GRAB!
                self.claw_descending = False
                self.claw_ascending = True

                # Check if we grabbed anything
                self._attempt_grab()

        # ASCENDING PHASE
        if self.claw_ascending:
            self.claw_z -= 50 * dt  # Ascend slower

            if self.claw_z <= 0:  # Reached top
                self.claw_z = 0
                self.claw_ascending = False

                # Deliver prize if we have one
                if self.grabbed_prize:
                    self.score += self.grabbed_prize.value
                    self.prizes = [p for p in self.prizes if p != self.grabbed_prize]
                    self.grabbed_prize = None

                self.claw_open = True

        # Game over conditions
        if self.attempts_remaining <= 0 or time.time() - self.start_time > 120:
            self.game_over = True

        return self.get_state()

    def _attempt_grab(self):
        """Try to grab a prize at current claw position"""
        for prize in self.prizes:
            if prize.grabbed:
                continue

            # Check if claw is over prize
            distance = math.sqrt((self.claw_x - prize.x)**2 + (self.claw_y - prize.y)**2)

            if distance < 8:  # Within grab radius
                # Success chance depends on prize value
                success_chance = 0.8 if prize.type == "teddy" else 0.4

                if random.random() < success_chance:
                    prize.grabbed = True
                    self.grabbed_prize = prize
                    return

    def get_state(self) -> Dict:
        return {
            "game_id": 57,
            "game_type": "claw_machine",
            "claw_x": round(self.claw_x, 1),
            "claw_y": round(self.claw_y, 1),
            "claw_z": round(self.claw_z, 1),
            "claw_open": self.claw_open,
            "claw_descending": self.claw_descending,
            "score": self.score,
            "attempts_remaining": self.attempts_remaining,
            "prizes": [
                {
                    "x": round(p.x, 1),
                    "y": round(p.y, 1),
                    "z": round(p.z, 1),
                    "type": p.type,
                    "value": p.value,
                    "grabbed": p.grabbed
                }
                for p in self.prizes
            ],
            "grabbed_prize": {
                "type": self.grabbed_prize.type,
                "value": self.grabbed_prize.value
            } if self.grabbed_prize else None,
            "game_over": self.game_over
        }


# ============================================================================
# GAME 58: STACK THE BOXES
# ============================================================================

@dataclass
class Box:
    x: float  # Horizontal position (swinging)
    y: float  # Vertical stack position
    width: float
    velocity: float  # Swing speed
    placed: bool = False

class StackTheBoxes:
    """
    Timing-based stacking game. Boxes swing back and forth, tap to drop.
    3D boxes with physics, get smaller as you stack higher.
    """

    def __init__(self):
        self.boxes: List[Box] = []
        self.current_box = None
        self.stack_height = 0
        self.score = 0
        self.game_over = False
        self.base_width = 80
        self.start_time = time.time()
        self.last_update = time.time()

        # Spawn first box
        self._spawn_box()

    def _spawn_box(self):
        """Spawn new swinging box"""
        width = max(20, self.base_width - self.stack_height * 5)
        self.current_box = Box(
            x=50,
            y=10,  # Starts at top
            width=width,
            velocity=30 + self.stack_height * 5,  # Gets faster
            placed=False
        )
        self.boxes.append(self.current_box)

    def update(self, button_held: bool, shake_detected: bool) -> Dict:
        if self.game_over:
            return self.get_state()

        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        if self.current_box and not self.current_box.placed:
            # Swing box back and forth
            self.current_box.x += self.current_box.velocity * dt

            # Bounce at edges
            if self.current_box.x < 10 or self.current_box.x > 90:
                self.current_box.velocity *= -1

            # Button press = drop box
            if button_held or shake_detected:
                self._place_box()

        return self.get_state()

    def _place_box(self):
        """Place the current box and check alignment"""
        if not self.current_box:
            return

        self.current_box.placed = True
        self.current_box.y = 90 - self.stack_height * 8  # Stack position

        # Check alignment with box below
        if self.stack_height == 0:
            # First box - always perfect
            alignment = 1.0
        else:
            prev_box = self.boxes[-2]
            overlap = min(
                self.current_box.x + self.current_box.width/2,
                prev_box.x + prev_box.width/2
            ) - max(
                self.current_box.x - self.current_box.width/2,
                prev_box.x - prev_box.width/2
            )

            alignment = max(0, overlap / self.current_box.width)

        # Score based on alignment
        if alignment > 0.9:
            points = 500  # Perfect!
        elif alignment > 0.7:
            points = 300  # Great
        elif alignment > 0.5:
            points = 100  # Good
        else:
            points = 0  # Missed
            self.game_over = True  # Stack collapsed!
            return

        self.score += points
        self.stack_height += 1

        # Spawn next box if game continues
        if self.stack_height < 15:  # Max 15 boxes
            self._spawn_box()
        else:
            self.game_over = True  # WIN!

    def get_state(self) -> Dict:
        return {
            "game_id": 58,
            "game_type": "stack_boxes",
            "stack_height": self.stack_height,
            "score": self.score,
            "boxes": [
                {
                    "x": round(b.x, 1),
                    "y": round(b.y, 1),
                    "width": round(b.width, 1),
                    "placed": b.placed
                }
                for b in self.boxes
            ],
            "game_over": self.game_over,
            "game_won": self.game_over and self.stack_height >= 15
        }


# ============================================================================
# GAME 59: DUCK HUNT
# ============================================================================

@dataclass
class Duck:
    x: float
    y: float
    vx: float  # Velocity X
    vy: float  # Velocity Y
    type: str  # "duck", "bonus_duck"
    shot: bool = False

class DuckHunt:
    """
    Tilt to aim crosshair, shake to shoot flying ducks
    3D ducks flying across screen, bonus ducks worth more
    """

    def __init__(self):
        self.crosshair_x = 50
        self.crosshair_y = 50
        self.ducks: List[Duck] = []
        self.score = 0
        self.shots_fired = 0
        self.shots_hit = 0
        self.accuracy = 0
        self.round_number = 1
        self.ducks_per_round = 3
        self.ducks_spawned_this_round = 0
        self.game_over = False
        self.last_shot_time = 0
        self.start_time = time.time()
        self.last_update = time.time()

    def update(self, tilt_x: float, tilt_y: float, shake_intensity: float) -> Dict:
        if self.game_over:
            return self.get_state()

        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # Move crosshair with tilt
        self.crosshair_x += (tilt_x / 45.0) * 40 * dt
        self.crosshair_y += (tilt_y / 45.0) * 40 * dt
        self.crosshair_x = max(5, min(95, self.crosshair_x))
        self.crosshair_y = max(5, min(95, self.crosshair_y))

        # Shake to shoot (with cooldown)
        if shake_intensity > 12 and now - self.last_shot_time > 0.5:
            self._shoot()
            self.last_shot_time = now

        # Spawn ducks
        if self.ducks_spawned_this_round < self.ducks_per_round and random.random() < 0.01:
            self._spawn_duck()

        # Update duck positions
        for duck in self.ducks:
            if not duck.shot:
                duck.x += duck.vx * dt
                duck.y += duck.vy * dt

                # Bounce off edges
                if duck.x < 0 or duck.x > 100:
                    duck.vx *= -1
                if duck.y < 0 or duck.y > 100:
                    duck.vy *= -1

        # Remove off-screen ducks
        self.ducks = [d for d in self.ducks if not (d.shot or d.x < -10 or d.x > 110)]

        # Check if round is over
        if self.ducks_spawned_this_round >= self.ducks_per_round and len([d for d in self.ducks if not d.shot]) == 0:
            self._next_round()

        # Game over after 5 rounds
        if self.round_number > 5:
            self.game_over = True

        return self.get_state()

    def _spawn_duck(self):
        """Spawn a duck from random edge"""
        side = random.choice(["left", "right", "top", "bottom"])

        if side == "left":
            x, y = 0, random.uniform(20, 80)
            vx, vy = random.uniform(15, 25), random.uniform(-10, 10)
        elif side == "right":
            x, y = 100, random.uniform(20, 80)
            vx, vy = random.uniform(-25, -15), random.uniform(-10, 10)
        elif side == "top":
            x, y = random.uniform(20, 80), 0
            vx, vy = random.uniform(-10, 10), random.uniform(15, 25)
        else:  # bottom
            x, y = random.uniform(20, 80), 100
            vx, vy = random.uniform(-10, 10), random.uniform(-25, -15)

        duck_type = "bonus_duck" if random.random() < 0.2 else "duck"

        self.ducks.append(Duck(x=x, y=y, vx=vx, vy=vy, type=duck_type))
        self.ducks_spawned_this_round += 1

    def _shoot(self):
        """Fire shot at crosshair position"""
        self.shots_fired += 1

        # Check if we hit any duck
        for duck in self.ducks:
            if duck.shot:
                continue

            distance = math.sqrt((self.crosshair_x - duck.x)**2 + (self.crosshair_y - duck.y)**2)

            if distance < 8:  # Hit!
                duck.shot = True
                self.shots_hit += 1
                points = 200 if duck.type == "bonus_duck" else 100
                self.score += points
                break

        # Update accuracy
        self.accuracy = int((self.shots_hit / max(1, self.shots_fired)) * 100)

    def _next_round(self):
        """Advance to next round"""
        self.round_number += 1
        self.ducks_per_round = min(8, 3 + self.round_number)
        self.ducks_spawned_this_round = 0

    def get_state(self) -> Dict:
        return {
            "game_id": 59,
            "game_type": "duck_hunt",
            "crosshair_x": round(self.crosshair_x, 1),
            "crosshair_y": round(self.crosshair_y, 1),
            "score": self.score,
            "shots_fired": self.shots_fired,
            "shots_hit": self.shots_hit,
            "accuracy": self.accuracy,
            "round_number": self.round_number,
            "ducks": [
                {
                    "x": round(d.x, 1),
                    "y": round(d.y, 1),
                    "type": d.type,
                    "shot": d.shot
                }
                for d in self.ducks if not d.shot
            ],
            "game_over": self.game_over
        }


# ============================================================================
# GAME 60: CORRELATION WORD GAME
# ============================================================================

@dataclass
class WordPair:
    stimulus: str
    target: str
    shown: bool = False

class CorrelationWordGame:
    """
    Words scroll on screen. Press button when correlated word appears.
    Tests reaction time and word association knowledge.
    """

    def __init__(self):
        self.current_stimulus = ""
        self.current_word = ""
        self.word_scroll_position = 100  # Start off-screen right
        self.score = 0
        self.correct_hits = 0
        self.wrong_hits = 0
        self.missed = 0
        self.combo = 0
        self.word_pairs = self._generate_word_pairs()
        self.decoy_words = self._generate_decoy_words()
        self.current_pair_index = 0
        self.is_target_word = False
        self.word_passed = False
        self.game_over = False
        self.start_time = time.time()
        self.last_update = time.time()
        self.last_word_spawn = time.time()

        # Start first stimulus
        self._new_stimulus()

    def _generate_word_pairs(self):
        """Generate correlated word pairs"""
        return [
            WordPair("VITAMIN", "B12"),
            WordPair("VITAMIN", "C"),
            WordPair("COFFEE", "CAFFEINE"),
            WordPair("OCEAN", "SALT"),
            WordPair("MUSCLE", "PROTEIN"),
            WordPair("BONE", "CALCIUM"),
            WordPair("BLOOD", "IRON"),
            WordPair("ENERGY", "GLUCOSE"),
            WordPair("NIGHT", "MELATONIN"),
            WordPair("BANANA", "POTASSIUM"),
        ]

    def _generate_decoy_words(self):
        """Non-correlated words"""
        return ["CHAIR", "PURPLE", "LAMP", "FORK", "WINDOW", "CLOUD", "TIGER", "PENCIL", "ROBOT", "BEACH"]

    def _new_stimulus(self):
        """Show new stimulus word"""
        if self.current_pair_index >= len(self.word_pairs):
            self.game_over = True
            return

        pair = self.word_pairs[self.current_pair_index]
        self.current_stimulus = pair.stimulus
        self.current_pair_index += 1

    def _spawn_word(self):
        """Spawn a new word to scroll across screen"""
        # Randomly show target or decoy
        if random.random() < 0.3:  # 30% chance of target
            pair = next((p for p in self.word_pairs if p.stimulus == self.current_stimulus), None)
            if pair:
                self.current_word = pair.target
                self.is_target_word = True
        else:
            self.current_word = random.choice(self.decoy_words)
            self.is_target_word = False

        self.word_scroll_position = 100
        self.word_passed = False
        self.last_word_spawn = time.time()

    def update(self, button_held: bool) -> Dict:
        if self.game_over:
            return self.get_state()

        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # Scroll current word across screen
        if self.current_word:
            self.word_scroll_position -= 30 * dt  # Scroll speed

            # Check if word passed the center without being caught
            if self.word_scroll_position < 40 and not self.word_passed:
                self.word_passed = True
                if self.is_target_word:
                    self.missed += 1
                    self.combo = 0
                    self.score -= 100

            # Remove word when off-screen
            if self.word_scroll_position < -20:
                self.current_word = ""

        # Spawn new word periodically
        if not self.current_word and now - self.last_word_spawn > 1.5:
            self._spawn_word()

        # Button press = attempt to catch word
        if button_held and self.current_word and 35 < self.word_scroll_position < 65:
            if self.is_target_word:
                # Correct!
                self.correct_hits += 1
                self.combo += 1
                combo_bonus = min(500, 100 * self.combo)
                self.score += 200 + combo_bonus
            else:
                # Wrong!
                self.wrong_hits += 1
                self.combo = 0
                self.score -= 150

            self.current_word = ""  # Clear word

        # Check game over
        if now - self.start_time > 90:  # 90 second game
            self.game_over = True

        return self.get_state()

    def get_state(self) -> Dict:
        return {
            "game_id": 60,
            "game_type": "correlation_word",
            "current_stimulus": self.current_stimulus,
            "current_word": self.current_word,
            "word_position": round(self.word_scroll_position, 1),
            "is_target": self.is_target_word,
            "score": self.score,
            "correct_hits": self.correct_hits,
            "wrong_hits": self.wrong_hits,
            "missed": self.missed,
            "combo": self.combo,
            "game_over": self.game_over,
            "time_remaining": max(0, int(90 - (time.time() - self.start_time)))
        }


# ============================================================================
# GAME 61: GREYHOUND RACING
# ============================================================================

@dataclass
class Greyhound:
    lane: int  # 1-6
    position: float  # 0-100 (race progress)
    speed: float
    name: str
    color: str
    odds: str  # "3:1", "5:1", etc.

class GreyhoundRacing:
    """
    Virtual greyhound race betting. Choose dog before race, shake to cheer your dog on.
    3D race track with animated greyhounds.
    """

    def __init__(self):
        self.greyhounds: List[Greyhound] = []
        self.player_bet = None  # Which lane player bet on
        self.bet_locked = False
        self.race_started = False
        self.race_over = False
        self.winner = None
        self.score = 0
        self.total_score = 0
        self.race_number = 1
        self.last_shake_time = 0
        self.start_time = time.time()
        self.race_start_time = None
        self.last_update = time.time()
        self.game_over = False

        # Generate greyhounds
        self._generate_greyhounds()

    def _generate_greyhounds(self):
        """Create 6 racing greyhounds with different odds"""
        names = ["Lightning", "Thunder", "Blaze", "Shadow", "Rocket", "Storm"]
        colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF"]
        odds = ["2:1", "3:1", "4:1", "5:1", "7:1", "10:1"]

        for i in range(6):
            self.greyhounds.append(Greyhound(
                lane=i+1,
                position=0,
                speed=random.uniform(8, 12),
                name=names[i],
                color=colors[i],
                odds=odds[i]
            ))

    def update(self, tilt_x: float, shake_intensity: float, button_held: bool) -> Dict:
        if self.game_over:
            return self.get_state()

        now = time.time()
        dt = now - self.last_update
        self.last_update = now

        # BETTING PHASE (first 10 seconds)
        if not self.bet_locked and not self.race_started:
            # Tilt left/right to select lane (1-6)
            selected_lane = int((tilt_x + 45) / 90 * 5) + 1
            selected_lane = max(1, min(6, selected_lane))

            # Button to confirm bet
            if button_held:
                self.player_bet = selected_lane
                self.bet_locked = True
                print(f"Player bet on lane {selected_lane}")

            # Auto-start race after 10 seconds
            if now - self.start_time > 10:
                if not self.player_bet:
                    self.player_bet = random.randint(1, 6)  # Random bet
                self.bet_locked = True
                self.race_started = True
                self.race_start_time = now

        # RACING PHASE
        if self.race_started and not self.race_over:
            # Update greyhound positions
            for dog in self.greyhounds:
                # Add randomness to speed
                speed_variation = random.uniform(0.9, 1.1)
                dog.position += dog.speed * speed_variation * dt

                # Boost if player shakes and this is their dog
                if dog.lane == self.player_bet and shake_intensity > 12 and now - self.last_shake_time > 0.5:
                    dog.position += 2  # Small boost
                    self.last_shake_time = now

            # Check for winner
            for dog in self.greyhounds:
                if dog.position >= 100:
                    self.race_over = True
                    self.winner = dog

                    # Calculate winnings
                    if dog.lane == self.player_bet:
                        multiplier = int(dog.odds.split(':')[0])
                        winnings = 100 * multiplier
                        self.score += winnings
                        self.total_score += winnings
                    else:
                        self.score = 0  # Lost bet

                    break

        # POST-RACE: Wait 5 seconds then new race
        if self.race_over and now - self.race_start_time > 8:
            self._next_race()

        # Game over after 5 races
        if self.race_number > 5:
            self.game_over = True

        return self.get_state()

    def _next_race(self):
        """Start next race"""
        self.race_number += 1
        self.race_started = False
        self.race_over = False
        self.bet_locked = False
        self.player_bet = None
        self.winner = None
        self.greyhounds = []
        self._generate_greyhounds()
        self.start_time = time.time()

    def get_state(self) -> Dict:
        return {
            "game_id": 61,
            "game_type": "greyhound_racing",
            "race_number": self.race_number,
            "betting_phase": not self.bet_locked and not self.race_started,
            "race_started": self.race_started,
            "race_over": self.race_over,
            "player_bet": self.player_bet,
            "last_race_winnings": self.score,
            "total_score": self.total_score,
            "greyhounds": [
                {
                    "lane": dog.lane,
                    "position": round(dog.position, 1),
                    "name": dog.name,
                    "color": dog.color,
                    "odds": dog.odds,
                    "is_winner": self.winner and dog.lane == self.winner.lane
                }
                for dog in self.greyhounds
            ],
            "winner": {
                "lane": self.winner.lane,
                "name": self.winner.name
            } if self.winner else None,
            "game_over": self.game_over
        }


# ============================================================================
# GAME MANAGER
# ============================================================================

# Active game sessions (puck_id -> game_instance)
active_games: Dict[int, any] = {}

def start_game(puck_id: int, game_id: int):
    """Start a new TV game for a puck"""
    if game_id == 52:
        active_games[puck_id] = PuckRacer()
    elif game_id == 53:
        active_games[puck_id] = ObstacleDodger()
    elif game_id == 54:
        active_games[puck_id] = PuckGolf()
    elif game_id == 55:
        active_games[puck_id] = SpaceInvadersPuck()
    elif game_id == 56:
        active_games[puck_id] = PongPuck()
    elif game_id == 57:
        active_games[puck_id] = ClawMachine()
    elif game_id == 58:
        active_games[puck_id] = StackTheBoxes()
    elif game_id == 59:
        active_games[puck_id] = DuckHunt()
    elif game_id == 60:
        active_games[puck_id] = CorrelationWordGame()
    elif game_id == 61:
        active_games[puck_id] = GreyhoundRacing()
    else:
        raise ValueError(f"Unknown TV game: {game_id}")

    return active_games[puck_id].get_state()

def update_game(puck_id: int, input_data: Dict) -> Optional[Dict]:
    """Update game state based on puck input"""
    if puck_id not in active_games:
        return None

    game = active_games[puck_id]

    # Route to correct update method based on game type
    if isinstance(game, PuckRacer):
        return game.update(
            tilt_x=input_data.get('tilt_x', 0),
            button_held=input_data.get('button_held', False),
            shake_detected=input_data.get('shake_detected', False)
        )
    elif isinstance(game, ObstacleDodger):
        return game.update(
            tilt_x=input_data.get('tilt_x', 0),
            tilt_y=input_data.get('tilt_y', 0),
            shake=input_data.get('shake_detected', False)
        )
    elif isinstance(game, PuckGolf):
        return game.update(
            tilt_x=input_data.get('tilt_x', 0),
            shake_intensity=input_data.get('shake_intensity', 0),
            button_held=input_data.get('button_held', False)
        )
    elif isinstance(game, SpaceInvadersPuck):
        return game.update(
            tilt_x=input_data.get('tilt_x', 0),
            shake_intensity=input_data.get('shake_intensity', 0)
        )
    elif isinstance(game, PongPuck):
        return game.update(
            tilt_y=input_data.get('tilt_y', 0)
        )
    elif isinstance(game, ClawMachine):
        return game.update(
            tilt_x=input_data.get('tilt_x', 0),
            tilt_y=input_data.get('tilt_y', 0),
            button_held=input_data.get('button_held', False)
        )
    elif isinstance(game, StackTheBoxes):
        return game.update(
            button_held=input_data.get('button_held', False),
            shake_detected=input_data.get('shake_detected', False)
        )
    elif isinstance(game, DuckHunt):
        return game.update(
            tilt_x=input_data.get('tilt_x', 0),
            tilt_y=input_data.get('tilt_y', 0),
            shake_intensity=input_data.get('shake_intensity', 0)
        )
    elif isinstance(game, CorrelationWordGame):
        return game.update(
            button_held=input_data.get('button_held', False)
        )
    elif isinstance(game, GreyhoundRacing):
        return game.update(
            tilt_x=input_data.get('tilt_x', 0),
            shake_intensity=input_data.get('shake_intensity', 0),
            button_held=input_data.get('button_held', False)
        )

    return None

def end_game(puck_id: int) -> Optional[int]:
    """End game and return final score"""
    if puck_id not in active_games:
        return None

    game = active_games[puck_id]
    final_score = game.score if hasattr(game, 'score') else 0

    del active_games[puck_id]
    return final_score

def get_game_state(puck_id: int) -> Optional[Dict]:
    """Get current game state"""
    if puck_id not in active_games:
        return None
    return active_games[puck_id].get_state()
