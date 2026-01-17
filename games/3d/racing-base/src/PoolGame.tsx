import { Canvas } from '@react-three/fiber'
import { Physics, RigidBody, CuboidCollider } from '@react-three/rapier'
import { Environment, PerspectiveCamera, OrbitControls } from '@react-three/drei'
import { EffectComposer, Bloom, Vignette, ChromaticAberration, DepthOfField } from '@react-three/postprocessing'
import { BlendFunction } from 'postprocessing'
import { useState, useRef, useEffect } from 'react'
import * as THREE from 'three'

// WebSocket connection for puck data
let ws: WebSocket | null = null

function connectPuck() {
  if (ws) return ws

  ws = new WebSocket('ws://localhost:8080')

  ws.onopen = () => {
    console.log('🎮 Puck connected!')
    ws?.send(JSON.stringify({ type: 'DISPLAY_CONNECT' }))
  }

  ws.onerror = (error) => {
    console.log('⚠️ Puck WebSocket not available (using keyboard fallback)')
  }

  return ws
}

// Pool table component
function PoolTable() {
  return (
    <RigidBody type="fixed" colliders="cuboid">
      {/* Table surface */}
      <mesh receiveShadow position={[0, -0.5, 0]}>
        <boxGeometry args={[20, 1, 10]} />
        <meshStandardMaterial color="#0a5d29" roughness={0.8} />
      </mesh>

      {/* Rails */}
      <mesh position={[0, 0.5, 5.5]}>
        <boxGeometry args={[20, 1, 0.5]} />
        <meshStandardMaterial color="#8B4513" metalness={0.3} roughness={0.7} />
      </mesh>
      <mesh position={[0, 0.5, -5.5]}>
        <boxGeometry args={[20, 1, 0.5]} />
        <meshStandardMaterial color="#8B4513" metalness={0.3} roughness={0.7} />
      </mesh>
      <mesh position={[10.25, 0.5, 0]}>
        <boxGeometry args={[0.5, 1, 10]} />
        <meshStandardMaterial color="#8B4513" metalness={0.3} roughness={0.7} />
      </mesh>
      <mesh position={[-10.25, 0.5, 0]}>
        <boxGeometry args={[0.5, 1, 10]} />
        <meshStandardMaterial color="#8B4513" metalness={0.3} roughness={0.7} />
      </mesh>

      {/* Invisible collision walls */}
      <CuboidCollider args={[10, 0.5, 0.25]} position={[0, 0, 5.5]} />
      <CuboidCollider args={[10, 0.5, 0.25]} position={[0, 0, -5.5]} />
      <CuboidCollider args={[0.25, 0.5, 5]} position={[10, 0, 0]} />
      <CuboidCollider args={[0.25, 0.5, 5]} position={[-10, 0, 0]} />
    </RigidBody>
  )
}

// Cue ball controlled by puck tilt
function CueBall({ playerColor = '#ffffff', playerId = 1 }: { playerColor?: string; playerId?: number }) {
  const ballRef = useRef<any>()
  const [tiltX, setTiltX] = useState(0)
  const [tiltY, setTiltY] = useState(0)
  const [isPuckConnected, setIsPuckConnected] = useState(false)

  useEffect(() => {
    const socket = connectPuck()

    if (socket) {
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          // Puck gyro data → ball force
          if (data.type === 'SENSOR_UPDATE' && data.puckId === `puck-${playerId}`) {
            // Accelerometer X/Y → tilt direction
            const ax = data.data.ax || 0
            const ay = data.data.ay || 0

            setTiltX(ax / 10) // Scale for ball force
            setTiltY(ay / 10)
            setIsPuckConnected(true)
          }

          // Puck shake → power shot
          if (data.type === 'SHAKE_DETECTED' && data.puckId === `puck-${playerId}`) {
            if (ballRef.current) {
              // Apply impulse based on shake intensity
              const impulse = { x: tiltX * 50, y: 0, z: tiltY * 50 }
              ballRef.current.applyImpulse(impulse, true)
            }
          }
        } catch (err) {
          // Non-JSON message, ignore
        }
      }
    }

    // Keyboard fallback (Arrow keys)
    const handleKey = (e: KeyboardEvent) => {
      if (!isPuckConnected) {
        if (e.key === 'ArrowLeft') setTiltX(-1)
        if (e.key === 'ArrowRight') setTiltX(1)
        if (e.key === 'ArrowUp') setTiltY(-1)
        if (e.key === 'ArrowDown') setTiltY(1)
        if (e.key === ' ' && ballRef.current) {
          // Space = power shot
          ballRef.current.applyImpulse({ x: tiltX * 30, y: 0, z: tiltY * 30 }, true)
        }
      }
    }

    const handleKeyUp = (e: KeyboardEvent) => {
      if (!isPuckConnected) {
        if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') setTiltX(0)
        if (e.key === 'ArrowUp' || e.key === 'ArrowDown') setTiltY(0)
      }
    }

    window.addEventListener('keydown', handleKey)
    window.addEventListener('keyup', handleKeyUp)

    return () => {
      window.removeEventListener('keydown', handleKey)
      window.removeEventListener('keyup', handleKeyUp)
    }
  }, [tiltX, tiltY, isPuckConnected, playerId])

  // Apply continuous force based on tilt
  useEffect(() => {
    if (ballRef.current && (tiltX !== 0 || tiltY !== 0)) {
      const force = { x: tiltX * 5, y: 0, z: tiltY * 5 }
      ballRef.current.applyImpulse(force, true)
    }
  }, [tiltX, tiltY])

  return (
    <RigidBody
      ref={ballRef}
      position={[0, 1, 0]}
      colliders="ball"
      restitution={0.8}
      friction={0.1}
      linearDamping={0.5}
      angularDamping={0.5}
    >
      <mesh castShadow>
        <sphereGeometry args={[0.5, 32, 32]} />
        <meshStandardMaterial
          color={playerColor}
          metalness={0.9}
          roughness={0.1}
          emissive={playerColor}
          emissiveIntensity={0.2}
        />
      </mesh>
    </RigidBody>
  )
}

// Target balls (break on epic shots)
function TargetBall({ position, color = '#ff0040' }: { position: [number, number, number]; color?: string }) {
  const ballRef = useRef<any>()
  const [isBroken, setIsBroken] = useState(false)

  useEffect(() => {
    if (!ballRef.current) return

    // Check velocity for epic shot detection
    const interval = setInterval(() => {
      if (ballRef.current) {
        const vel = ballRef.current.linvel()
        const speed = Math.sqrt(vel.x ** 2 + vel.y ** 2 + vel.z ** 2)

        // Epic shot = fracture effect
        if (speed > 15 && !isBroken) {
          setIsBroken(true)
          console.log('💥 EPIC SHOT! Ball fractured!')
          // TODO: Replace with fracture mesh (pmndrs/pinata)
        }
      }
    }, 100)

    return () => clearInterval(interval)
  }, [isBroken])

  if (isBroken) {
    // Show shattered pieces (simplified)
    return (
      <group position={position}>
        {Array.from({ length: 8 }).map((_, i) => (
          <RigidBody
            key={i}
            position={[
              (Math.random() - 0.5) * 2,
              Math.random() * 2,
              (Math.random() - 0.5) * 2
            ]}
            colliders="cuboid"
          >
            <mesh castShadow>
              <boxGeometry args={[0.2, 0.2, 0.2]} />
              <meshStandardMaterial color={color} />
            </mesh>
          </RigidBody>
        ))}
      </group>
    )
  }

  return (
    <RigidBody
      ref={ballRef}
      position={position}
      colliders="ball"
      restitution={0.9}
      friction={0.1}
    >
      <mesh castShadow>
        <sphereGeometry args={[0.5, 32, 32]} />
        <meshStandardMaterial
          color={color}
          metalness={0.8}
          roughness={0.2}
        />
      </mesh>
    </RigidBody>
  )
}

// Main game scene
export function PoolGame() {
  return (
    <div style={{ width: '100vw', height: '100vh', background: '#000' }}>
      <Canvas shadows camera={{ position: [0, 15, 15], fov: 50 }}>
        {/* Cinematic lighting */}
        <ambientLight intensity={0.2} />
        <directionalLight
          position={[10, 20, 10]}
          intensity={1.5}
          castShadow
          shadow-mapSize={[2048, 2048]}
        />
        <pointLight position={[0, 5, 0]} intensity={2} color="#00ffff" />
        <pointLight position={[-5, 5, -5]} intensity={1.5} color="#ff0080" />

        {/* Poly Haven bar HDRI */}
        <Environment files="/textures/brown_photostudio_02_1k.hdr" background />

        {/* Fog */}
        <fog attach="fog" args={['#000428', 10, 50]} />

        {/* Physics world */}
        <Physics gravity={[0, -9.81, 0]}>
          <PoolTable />

          {/* Player balls (4 players) */}
          <CueBall playerColor="#00ffff" playerId={1} />
          <CueBall playerColor="#ff00ff" playerId={2} />
          <CueBall playerColor="#ffff00" playerId={3} />
          <CueBall playerColor="#00ff00" playerId={4} />

          {/* Target balls */}
          <TargetBall position={[0, 1, -3]} color="#ff0040" />
          <TargetBall position={[1, 1, -3]} color="#ff6b00" />
          <TargetBall position={[-1, 1, -3]} color="#ffd700" />
          <TargetBall position={[0.5, 1, -4]} color="#00ff80" />
          <TargetBall position={[-0.5, 1, -4]} color="#0080ff" />
        </Physics>

        {/* Cinematic post-processing */}
        <EffectComposer>
          {/* Heavy bloom for god rays */}
          <Bloom
            intensity={2}
            luminanceThreshold={0.2}
            luminanceSmoothing={0.9}
            height={300}
          />

          {/* Vignette */}
          <Vignette
            offset={0.3}
            darkness={0.7}
            blendFunction={BlendFunction.NORMAL}
          />

          {/* Chromatic aberration */}
          <ChromaticAberration
            offset={[0.002, 0.002]}
            blendFunction={BlendFunction.NORMAL}
          />

          {/* Depth of field (cinematic focus) */}
          <DepthOfField
            focusDistance={0.01}
            focalLength={0.05}
            bokehScale={3}
          />
        </EffectComposer>

        {/* Camera controls */}
        <OrbitControls
          enablePan={false}
          minDistance={10}
          maxDistance={30}
          maxPolarAngle={Math.PI / 2.5}
        />

        <PerspectiveCamera makeDefault position={[0, 15, 15]} fov={50} />
      </Canvas>

      {/* HUD */}
      <div style={{
        position: 'fixed',
        top: 20,
        left: 20,
        color: '#fff',
        fontFamily: 'monospace',
        fontSize: '1.2rem',
        textShadow: '0 2px 10px rgba(0,0,0,0.8)',
        pointerEvents: 'none'
      }}>
        <div>🎱 CINEMATIC POOL</div>
        <div style={{ fontSize: '0.9rem', opacity: 0.7, marginTop: 10 }}>
          {ws?.readyState === WebSocket.OPEN
            ? '🎮 Puck Connected'
            : '⌨️  Arrow Keys + Space (Puck Fallback)'}
        </div>
        <div style={{ fontSize: '0.8rem', opacity: 0.5, marginTop: 10 }}>
          Shake puck for power shot 💥
        </div>
      </div>

      {/* Controls */}
      <div style={{
        position: 'fixed',
        bottom: 20,
        left: '50%',
        transform: 'translateX(-50%)',
        color: '#fff',
        fontFamily: 'monospace',
        fontSize: '0.9rem',
        background: 'rgba(0,0,0,0.7)',
        padding: '15px 30px',
        borderRadius: 10,
        textAlign: 'center',
        backdropFilter: 'blur(10px)',
        pointerEvents: 'none'
      }}>
        <div>TILT PUCK → Aim | SHAKE → Power Shot</div>
        <div style={{ opacity: 0.5, marginTop: 5 }}>
          (Keyboard: Arrow Keys + Space)
        </div>
      </div>
    </div>
  )
}
