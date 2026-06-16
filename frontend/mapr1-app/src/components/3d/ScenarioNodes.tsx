import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Html } from '@react-three/drei';
import * as THREE from 'three';
import { useScenarioStore } from '../../stores/scenarioStore';

const COLORS: Record<string, { core: string; emissive: string; shell: string }> = {
  optimistic: { core: '#002a14', emissive: '#10b981', shell: '#34d399' },
  pessimistic: { core: '#2a0000', emissive: '#ef4444', shell: '#f87171' },
  mixed:       { core: '#1a0a3d', emissive: '#8b5cf6', shell: '#a78bfa' },
  neutral:     { core: '#002a14', emissive: '#6bfb9a', shell: '#4ade80' },
};

// Export positions so connection lines can use the same layout
export function getScenarioPositions(count: number): THREE.Vector3[] {
  return Array.from({ length: count }, (_, index) => {
    const cols = Math.ceil(Math.sqrt(count));
    const row = Math.floor(index / cols);
    const col = index % cols;
    const spacing = 28;
    const offsetX = ((cols - 1) * spacing) / 2;
    const offsetZ = (Math.ceil(count / cols) - 1) * spacing / 2;
    const y = Math.sin(index * 1.5) * 5;
    return new THREE.Vector3(col * spacing - offsetX, y, row * spacing - offsetZ);
  });
}

function ScenarioNode({ scenario, position, index }: {
  scenario: any;
  position: THREE.Vector3;
  index: number;
}) {
  const coreRef = useRef<THREE.Mesh>(null);
  const shellRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const { selectedScenario, setSelectedScenario } = useScenarioStore();
  const isSelected = selectedScenario?.id === scenario.id;

  const colors = COLORS[scenario.category] || COLORS.neutral;
  // Radius driven by probability — range 3.5 to 7
  const radius = ((scenario.probability || 0.5) * 3.5) + 3.5;

  const baseY = position.y;

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    const floatY = baseY + Math.sin(t * 0.6 + index) * 0.5;

    if (coreRef.current) {
      coreRef.current.position.y = floatY;
      const mat = coreRef.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = 1.2 + Math.sin(t * 2.5 + index) ** 2 * 1.5;
    }
    if (shellRef.current) {
      shellRef.current.position.y = floatY;
      shellRef.current.rotation.y += 0.003;
      shellRef.current.rotation.z += 0.0015;
    }
    if (glowRef.current) {
      glowRef.current.position.y = floatY;
    }
    if (ringRef.current) {
      ringRef.current.position.y = floatY;
      ringRef.current.rotation.z -= 0.008;
    }
  });

  return (
    <group
      position={[position.x, position.y, position.z]}
      onClick={() => setSelectedScenario(scenario)}
      onPointerOver={(e) => { e.stopPropagation(); document.body.style.cursor = 'pointer'; }}
      onPointerOut={() => { document.body.style.cursor = 'default'; }}
    >
      {/* Solid glowing core */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[radius * 0.78, 32, 32]} />
        <meshStandardMaterial
          color={colors.core}
          emissive={colors.emissive}
          emissiveIntensity={1.5}
          transparent
          opacity={0.92}
          toneMapped={false}
        />
      </mesh>

      {/* Geodesic wireframe shell — key visual from reference */}
      <mesh ref={shellRef}>
        <icosahedronGeometry args={[radius, 2]} />
        <meshBasicMaterial
          color={colors.shell}
          wireframe
          transparent
          opacity={isSelected ? 0.85 : 0.5}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Outer glow */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[radius * 1.18, 16, 16]} />
        <meshBasicMaterial
          color={colors.emissive}
          transparent
          opacity={isSelected ? 0.14 : 0.07}
          blending={THREE.AdditiveBlending}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Selection ring */}
      {isSelected && (
        <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[radius * 1.35, radius * 1.44, 64]} />
          <meshBasicMaterial
            color={colors.shell}
            side={THREE.DoubleSide}
            transparent
            opacity={0.7}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      )}

      {/* Tooltip label */}
      <Html distanceFactor={22} style={{ pointerEvents: 'none' }}>
        <div style={{
          background: 'rgba(8, 18, 10, 0.88)',
          border: '1px solid rgba(107, 251, 154, 0.45)',
          backdropFilter: 'blur(8px)',
          padding: '5px 10px',
          borderRadius: '4px',
          whiteSpace: 'nowrap',
          boxShadow: '0 0 12px rgba(107, 251, 154, 0.15)',
        }}>
          <div style={{ color: '#6bfb9a', fontWeight: 600, fontSize: '12px', fontFamily: 'monospace' }}>
            {scenario.title}
          </div>
          <div style={{ color: 'rgba(107, 251, 154, 0.6)', fontSize: '10px', fontFamily: 'monospace' }}>
            {scenario.category} • {((scenario.probability || 0) * 100).toFixed(0)}%
          </div>
        </div>
      </Html>
    </group>
  );
}

export default function ScenarioNodes() {
  const { scenarios } = useScenarioStore();

  const positions = useMemo(
    () => getScenarioPositions(scenarios.length),
    [scenarios.length]
  );

  return (
    <group>
      {scenarios.map((scenario, index) => (
        <ScenarioNode
          key={scenario.id}
          scenario={scenario}
          position={positions[index] ?? new THREE.Vector3(0, 0, 0)}
          index={index}
        />
      ))}
    </group>
  );
}
