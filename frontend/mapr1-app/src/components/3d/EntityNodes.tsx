import { useRef, useState, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Text } from '@react-three/drei';
import * as THREE from 'three';
import type { Entity } from '../../types';

interface EntityNodesProps {
  entities: Entity[];
  selectedId?: string;
  onSelect: (entity: Entity) => void;
}

const TYPE_COLORS: Record<string, { core: string; emissive: string; shell: string }> = {
  nation:       { core: '#001a26', emissive: '#0ea5e9', shell: '#38bdf8' },
  organization: { core: '#001a26', emissive: '#3b82f6', shell: '#60a5fa' },
  person:       { core: '#1a0a3d', emissive: '#8b5cf6', shell: '#a78bfa' },
  company:      { core: '#3d1a00', emissive: '#f59e0b', shell: '#fbbf24' },
  faction:      { core: '#001a0d', emissive: '#10b981', shell: '#34d399' },
  location:     { core: '#1a0a3d', emissive: '#a855f7', shell: '#c084fc' },
  resource:     { core: '#3d1a00', emissive: '#f59e0b', shell: '#fcd34d' },
};

function EntityNode({
  entity,
  position,
  isSelected,
  onClick,
}: {
  entity: Entity;
  position: THREE.Vector3;
  isSelected: boolean;
  onClick: () => void;
}) {
  const coreRef = useRef<THREE.Mesh>(null);
  const shellRef = useRef<THREE.Mesh>(null);
  const glowRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  const radius = 3.0;
  const colors =
    TYPE_COLORS[entity.type] ||
    TYPE_COLORS[(entity.metadata?.type as string) ?? ''] ||
    { core: '#001a26', emissive: '#6bfb9a', shell: '#4ade80' };

  const baseY = position.y;

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    const floatY = baseY + Math.sin(t * 0.55 + position.x) * 0.4;

    if (coreRef.current) {
      coreRef.current.position.y = floatY;
      const mat = coreRef.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = 1.1 + Math.sin(t * 2.8 + position.x) ** 2 * 1.2;
    }
    if (shellRef.current) {
      shellRef.current.position.y = floatY;
      shellRef.current.rotation.y += 0.003;
      shellRef.current.rotation.z += 0.0015;
    }
    if (glowRef.current) {
      glowRef.current.position.y = floatY;
    }
  });

  const scale = isSelected ? 1.2 : hovered ? 1.08 : 1.0;

  return (
    <group
      position={[position.x, position.y, position.z]}
      scale={scale}
      onClick={(e) => { e.stopPropagation(); onClick(); }}
      onPointerOver={(e) => { e.stopPropagation(); setHovered(true); document.body.style.cursor = 'pointer'; }}
      onPointerOut={() => { setHovered(false); document.body.style.cursor = 'auto'; }}
    >
      {/* Solid glowing core */}
      <mesh ref={coreRef}>
        <sphereGeometry args={[radius * 0.78, 32, 32]} />
        <meshStandardMaterial
          color={colors.core}
          emissive={colors.emissive}
          emissiveIntensity={1.3}
          transparent
          opacity={0.92}
          toneMapped={false}
        />
      </mesh>

      {/* Geodesic wireframe shell */}
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

      {/* Outer glow */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[radius * 1.18, 16, 16]} />
        <meshBasicMaterial
          color={colors.emissive}
          transparent
          opacity={isSelected ? 0.13 : 0.06}
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

      {(hovered || isSelected) && (
        <Text
          position={[0, radius + 0.9, 0]}
          fontSize={0.45}
          color="#6bfb9a"
          anchorX="center"
          anchorY="middle"
          outlineWidth={0.04}
          outlineColor="#000000"
        >
          {entity.name}
        </Text>
      )}
    </group>
  );
}

export default function EntityNodes({ entities, selectedId, onSelect }: EntityNodesProps) {
  const positions = useMemo(() => {
    const count = entities.length;
    return entities.map((_, index) => {
      const cols = Math.ceil(Math.sqrt(count));
      const row = Math.floor(index / cols);
      const col = index % cols;
      const spacing = 22;
      const offsetX = ((cols - 1) * spacing) / 2;
      const offsetZ = (Math.ceil(count / cols) - 1) * spacing / 2;
      const y = Math.sin(index * 1.7) * 4;
      return new THREE.Vector3(col * spacing - offsetX, y, row * spacing - offsetZ);
    });
  }, [entities.length]);

  return (
    <group>
      {entities.map((entity, index) => (
        <EntityNode
          key={entity.id}
          entity={entity}
          position={positions[index] ?? new THREE.Vector3(0, 0, 0)}
          isSelected={entity.id === selectedId}
          onClick={() => onSelect(entity)}
        />
      ))}
    </group>
  );
}
