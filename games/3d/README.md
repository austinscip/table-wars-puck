# Table Wars - 3D Games

Production-quality 3D game development using React Three Fiber + Cannon physics.

---

## Current Status

### ✅ Racing Game Base (Cloned)
**Running at:** http://localhost:3000/

**What we have:**
- Full R3F + Cannon physics setup
- Vehicle controller with realistic physics
- Beautiful shaders and post-processing
- Sky, environment HDR, fog
- Real-time shadows (4096x4096 shadow maps)
- Keyboard controls
- HUD (speed, minimap, clock, leaderboard)
- Checkpoints and goal detection
- Editor mode for level design
- Production-ready build pipeline (Vite)

**Tech Stack:**
- React 18
- React Three Fiber (R3F)
- Cannon-es physics (@react-three/cannon)
- Drei helpers (@react-three/drei)
- Zustand state management
- TypeScript
- Vite

**License:** MIT (can modify and sell)

---

## Next Steps: Racing → Combat

### 1. Replace Vehicle with Warrior Character

**Current:** `models/Vehicle.tsx` - car with wheel physics

**Replace with:**
- Third-person character controller
- Capsule physics body (not wheels)
- Mixamo character model (rigged + animated)
- Animations: idle, run, attack, dodge, hit, death

**Assets:**
- Download from Mixamo (CC0/free)
- Export as GLB with animations
- Place in `/public/models/`

---

### 2. Create Combat System

**Files to create:**
- `models/Warrior.tsx` - player character
- `models/Enemy.tsx` - AI opponents
- `models/Weapon.tsx` - axe/sword hitbox
- `effects/CombatSystem.tsx` - hit detection, damage

**Combat Mechanics:**
- **Tap** → Attack (swing weapon)
- **Shake** → Special attack (AOE)
- **Tilt** → Movement (accelerometer X/Y)
- **Hold Tap** → Dodge roll

---

### 3. Convert Track to Arena

**Current:** Racing track with checkpoints

**Convert to:**
- Circular arena (like our 2D version)
- Enemy spawn points
- Destructible objects
- Boss arena variations

**Keep:**
- Heightmap system (terrain)
- Collision boundaries
- Goal triggers (for wave completion)

---

### 4. Enhance Post-Processing

**Already has:**
- Environment HDR
- Real-time shadows
- Fog

**Add:**
- Bloom (god rays, weapon glow)
- Depth of field (cinematic focus)
- Film grain
- Vignette
- Color grading (moody nordic palette)

**Use:** `@react-three/postprocessing`

---

### 5. Puck Integration

**Replace keyboard controls with WebSocket:**

```tsx
// Current: Keyboard.tsx listens to keys
useEffect(() => {
  const onKeyDown = (e) => { /* ... */ }
  window.addEventListener('keydown', onKeyDown)
}, [])

// New: WebSocket listener
useEffect(() => {
  const ws = new WebSocket('ws://localhost:8080')

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)

    if (data.type === 'SENSOR_UPDATE') {
      // Tilt → movement
      actions.setMovement(data.ax, data.ay)
    }

    if (data.type === 'BUTTON_PRESS') {
      // Tap → attack
      actions.attack()
    }

    if (data.type === 'SHAKE_DETECTED') {
      // Shake → special
      actions.special()
    }
  }
}, [])
```

---

## File Structure

```
games/3d/racing-base/
├── src/
│   ├── App.tsx              # Main game scene
│   ├── store.ts             # Zustand state (vehicle → warrior)
│   ├── controls/
│   │   ├── Keyboard.tsx     # Replace with WebSocket
│   │   └── ...
│   ├── models/
│   │   ├── Vehicle.tsx      # REPLACE → Warrior.tsx
│   │   ├── Track.tsx        # CONVERT → Arena.tsx
│   │   └── ...              # ADD → Enemy.tsx, Weapon.tsx
│   ├── effects/
│   │   ├── Cameras.tsx      # Third-person follow cam
│   │   └── ...              # ADD → CombatSystem.tsx
│   └── ui/
│       ├── Speed.tsx        # REPLACE → Health.tsx
│       ├── Clock.tsx        # Keep (combat timer)
│       └── ...              # ADD → KillCount.tsx
```

---

## How to Run

```bash
cd games/3d/racing-base
npm install
npm run dev
```

Open http://localhost:3000/

---

## How to Modify

### Quick Start: Change Car Color
1. Open `src/App.tsx`
2. Find `<Vehicle>` component
3. Modify material color

### Add New Model:
1. Place GLB in `/public/models/`
2. Create component in `src/models/YourModel.tsx`
3. Import in `App.tsx`
4. Add to scene: `<YourModel />`

### Add Physics Body:
```tsx
import { useBox } from '@react-three/cannon'

function MyObject() {
  const [ref] = useBox(() => ({
    mass: 1,
    position: [0, 5, 0],
  }))

  return (
    <mesh ref={ref}>
      <boxGeometry />
      <meshStandardMaterial color="red" />
    </mesh>
  )
}
```

---

## Resources

**Mixamo Characters:**
https://www.mixamo.com/
- Free rigged characters
- Animations: idle, run, attack, etc.
- Export as GLB

**HDR Environments:**
https://polyhaven.com/hdris
- Free CC0 HDRIs
- Realistic lighting

**React Three Fiber Docs:**
https://docs.pmnd.rs/react-three-fiber

**Cannon Physics Docs:**
https://pmndrs.github.io/cannon-es/

---

## Timeline Estimate

**Already Built (Racing Base):** ✅
- R3F setup
- Physics engine
- Post-processing
- Build pipeline

**Week 1:** Character controller + basic combat
**Week 2:** Enemy AI + arena system
**Week 3:** Polish + puck integration
**Week 4:** Multiplayer combat

---

## Why This Base Is Perfect

1. **Production Quality** - Not a tutorial project
2. **MIT License** - Can modify and sell
3. **Modern Stack** - React 18, R3F 8, TypeScript
4. **Physics Ready** - Cannon-es integrated
5. **Great Performance** - 60 FPS on laptops
6. **Beautiful Graphics** - HDR, shadows, shaders
7. **AI-Friendly Code** - Clean structure for Cursor

---

**Status:** Racing game running locally ✅
**Next:** Replace car with warrior character 🗡️
