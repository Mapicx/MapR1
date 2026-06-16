import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { EmergentPattern } from '../../types';
import { getAgentPositions } from './AgentNodes';
import { useProjectStore } from '../../stores/projectStore';

interface PatternOverlayProps {
  patterns: EmergentPattern[];
  showOverlay: boolean;
}

export default function PatternOverlay({ patterns, showOverlay }: PatternOverlayProps) {
  const { agents } = useProjectStore();
  const groupRef = useRef<THREE.Group>(null);

  const agentPositions = useMemo(() => getAgentPositions(agents), [agents]);

  // Get pattern color based on type
  const getPatternColor = (type: string): string => {
    const t = type.toLowerCase();
    if (t.includes('alliance') || t.includes('cooperation')) return '#10b981';
    if (t.includes('conflict') || t.includes('war')) return '#ef4444';
    if (t.includes('economic') || t.includes('trade')) return '#f59e0b';
    if (t.includes('social') || t.includes('movement')) return '#8b5cf6';
    if (t.includes('power') || t.includes('shift')) return '#3b82f6';
    return '#6bfb9a';
  };

  // Animate overlay
  useFrame((state) => {
    if (groupRef.current) {
      const t = state.clock.getElapsedTime();
      groupRef.current.children.forEach((child, idx) => {
        if (child instanceof THREE.Mesh) {
          const mat = child.material as THREE.MeshBasicMaterial;
          mat.opacity = showOverlay ? (0.15 + Math.sin(t * 2 + idx) * 0.05) : 0;
        }
      });
    }
  });

  if (!showOverlay || patterns.length === 0) return null;

  return (
    <group ref={groupRef}>
      {patterns.map((pattern, idx) => {
        // Get positions of involved agents
        const involvedPositions = pattern.involved_agent_ids
          .map(id => agentPositions.get(id))
          .filter(Boolean) as THREE.Vector3[];

        if (involvedPositions.length === 0) return null;

        // Calculate center point
        const center = new THREE.Vector3();
        involvedPositions.forEach(pos => center.add(pos));
        center.divideScalar(involvedPositions.length);

        // Calculate radius to encompass all agents
        let maxDist = 0;
        involvedPositions.forEach(pos => {
          const dist = center.distanceTo(pos);
          if (dist > maxDist) maxDist = dist;
        });
        const radius = maxDist + 5;

        const color = getPatternColor(pattern.pattern_type);

        return (
          <group key={pattern.id}>
            {/* Sphere overlay highlighting the pattern area */}
            <mesh position={[center.x, center.y, center.z]}>
              <sphereGeometry args={[radius, 32, 32]} />
              <meshBasicMaterial
                color={color}
                transparent
                opacity={0.15}
                blending={THREE.AdditiveBlending}
                side={THREE.BackSide}
                depthWrite={false}
              />
            </mesh>

            {/* Wireframe sphere */}
            <mesh position={[center.x, center.y, center.z]}>
              <sphereGeometry args={[radius, 16, 16]} />
              <meshBasicMaterial
                color={color}
                wireframe
                transparent
                opacity={0.3}
                blending={THREE.AdditiveBlending}
                depthWrite={false}
              />
            </mesh>

            {/* Pulsing ring at equator */}
            <mesh
              position={[center.x, center.y, center.z]}
              rotation={[Math.PI / 2, 0, 0]}
            >
              <ringGeometry args={[radius * 0.95, radius * 1.05, 48]} />
              <meshBasicMaterial
                color={color}
                transparent
                opacity={0.4}
                side={THREE.DoubleSide}
                blending={THREE.AdditiveBlending}
                depthWrite={false}
              />
            </mesh>

            {/* Connecting lines between involved agents */}
            {involvedPositions.map((pos, i) => {
              if (i === 0) return null;
              const prevPos = involvedPositions[i - 1];
              const points = [prevPos, pos];
              const geometry = new THREE.BufferGeometry().setFromPoints(points);

              return (
                <primitive
                  key={`line-${i}`}
                  object={new THREE.Line(
                    geometry,
                    new THREE.LineBasicMaterial({
                      color,
                      transparent: true,
                      opacity: 0.3,
                      blending: THREE.AdditiveBlending,
                      depthWrite: false,
                    })
                  )}
                />
              );
            })}
          </group>
        );
      })}
    </group>
  );
}
