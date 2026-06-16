import { useRef, useState, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Text } from '@react-three/drei';
import * as THREE from 'three';
import type { Agent } from '../../types';

interface AgentNodesProps {
  agents: Agent[];
  selectedId?: string;
  onSelect: (agent: Agent) => void;
}

// Export positions so RelationshipLines can use the same layout
export function getAgentPositions(agents: Agent[]): Map<string, THREE.Vector3> {
  const positions = new Map<string, THREE.Vector3>();
  const count = agents.length;
  if (count === 0) return positions;

  // Spread agents across the scene in a loose cluster layout
  agents.forEach((agent, index) => {
    const cols = Math.ceil(Math.sqrt(count));
    const row = Math.floor(index / cols);
    const col = index % cols;
    const spacing = 18;
    const offsetX = ((cols - 1) * spacing) / 2;
    const offsetZ = (Math.ceil(count / cols) - 1) * spacing / 2;
    // Add slight vertical variation
    const y = Math.sin(index * 1.7) * 4;
    positions.set(agent.id, new THREE.Vector3(
      col * spacing - offsetX,
      y,
      row * spacing - offsetZ
    ));
  });

  return positions;
}

const AGENT_COLORS: Record<string, { core: string; emissive: string; shell: string }> = {
  business:      { core: '#3d1a00', emissive: '#f59e0b', shell: '#fbbf24' },
  military:      { core: '#3d0000', emissive: '#ef4444', shell: '#f87171' },
  political:     { core: '#1e0a3d', emissive: '#8b5cf6', shell: '#a78bfa' },
  scientific:    { core: '#001a3d', emissive: '#3b82f6', shell: '#60a5fa' },
  cultural:      { core: '#3d0020', emissive: '#ec4899', shell: '#f472b6' },
  environmental: { core: '#001a0d', emissive: '#10b981', shell: '#34d399' },
  technological: { core: '#001a26', emissive: '#06b6d4', shell: '#22d3ee' },
  analyst:       { core: '#001a26', emissive: '#06b6d4', shell: '#22d3ee' },
  strategist:    { core: '#1e0a3d', emissive: '#8b5cf6', shell: '#a78bfa' },
  diplomat:      { core: '#001a0d', emissive: '#10b981', shell: '#34d399' },
  operative:     { core: '#3d0000', emissive: '#ef4444', shell: '#f87171' },
  hacker:        { core: '#001a26', emissive: '#06b6d4', shell: '#22d3ee' },
};

function getAgentColors(agent: Agent) {
  const key = (agent.agent_category || agent.agent_type || '').toLowerCase();
  for (const [k, v] of Object.entries(AGENT_COLORS)) {
    if (key.includes(k)) return v;
  }
  return { core: '#001a26', emissive: '#6bfb9a', shell: '#4ade80' };
}

function AgentNode({
  agent,
  position,
  isSelected,
  onClick,
}: {
  agent: Agent;
  position: THREE.Vector3;
  isSelected: boolean;
  onClick: () => void;
}) {
  const coreRef = useRef<THREE.Mesh>(null);
  const shellRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const colors = getAgentColors(agent);
  // Size based on importance — base 2.5, selected/hovered slightly larger
  const radius = 2.5;
  const scale = isSelected ? 1.25 : hovered ? 1.1 : 1.0;

  // Gentle float animation only — no orbiting
  const baseY = position.y;
  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    if (coreRef.current) {
      coreRef.current.position.y = baseY + Math.sin(t * 0.7 + position.x) * 0.35;
      const mat = coreRef.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = 1.2 + Math.sin(t * 3 + position.x) ** 2 * 1.2;
    }
    if (shellRef.current) {
      shellRef.current.position.y = baseY + Math.sin(t * 0.7 + position.x) * 0.35;
      shellRef.current.rotation.y += 0.004;
      shellRef.current.rotation.z += 0.002;
    }
    if (glowRef.current) {
      glowRef.current.position.y = baseY + Math.sin(t * 0.7 + position.x) * 0.35;
    }
  });

  return (
    <group
      position={[position.x, position.y, position.z]}
      scale={scale}
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true); document.body.style.cursor = 'pointer'; }}
      onPointerOut={() => { setHovered(false); document.body.style.cursor = 'auto'; }}
    >
      {/* Glowing solid core */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[radius * 0.78, 32, 32]} />
        <meshStandardMaterial
          color={colors.core}
          emissive={colors.emissive}
          emissiveIntensity={1.4}
          transparent
          opacity={0.92}
          toneMapped={false}
        />
      </mesh>

      {/* Geodesic wireframe shell — the defining visual */}
      <mesh ref={shellRef}>
        <icosahedronGeometry args={[radius, 2]} />
        <meshBasicMaterial
          color={colors.shell}
          wireframe
          transparent
          opacity={isSelected ? 0.85 : hovered ? 0.65 : 0.45}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* Outer glow bloom */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[radius * 1.15, 16, 16]} />
        <meshBasicMaterial
          color={colors.emissive}
          transparent
          opacity={isSelected ? 0.12 : 0.06}
          blending={THREE.AdditiveBlending}
          side={THREE.BackSide}
        />
      </mesh>

      {/* Selection ring */}
      {isSelected && (
        <mesh rotation={[Math.PI / 2, 0, 0]}>
          <ringGeometry args={[radius * 1.35, radius * 1.44, 48]} />
          <meshBasicMaterial
            color={colors.shell}
            transparent
            opacity={0.75}
            side={THREE.DoubleSide}
            blending={THREE.AdditiveBlending}
          />
        </mesh>
      )}

      {/* Label */}
      {(hovered || isSelected) && (
        <Text
          position={[0, radius + 0.7, 0]}
          fontSize={0.38}
          color="#6bfb9a"
          anchorX="center"
          anchorY="middle"
          outlineWidth={0.04}
          outlineColor="#000000"
        >
          {agent.name}
        </Text>
      )}
    </group>
  );
}

export default function AgentNodes({ agents, selectedId, onSelect }: AgentNodesProps) {
  const positions = useMemo(() => getAgentPositions(agents), [agents]);

  return (
    <group>
      {agents.map((agent) => {
        const pos = positions.get(agent.id) ?? new THREE.Vector3(0, 0, 0);
        return (
          <AgentNode
            key={agent.id}
            agent={agent}
            position={pos}
            isSelected={agent.id === selectedId}
            onClick={() => onSelect(agent)}
          />
        );
      })}
    </group>
  );
}
