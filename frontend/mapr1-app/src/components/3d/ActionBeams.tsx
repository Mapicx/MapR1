import { useRef, useEffect } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { AgentAction } from '../../types';

interface ActionBeamsProps {
  recentActions: AgentAction[];
  maxBeams?: number;
}

interface BeamData {
  id: string;
  startPos: THREE.Vector3;
  endPos: THREE.Vector3;
  color: string;
  progress: number;
  lifetime: number;
  maxLifetime: number;
}

export default function ActionBeams({ recentActions, maxBeams = 10 }: ActionBeamsProps) {
  const beamsRef = useRef<BeamData[]>([]);
  const groupRef = useRef<THREE.Group>(null);

  // Add new beams when actions occur
  useEffect(() => {
    if (recentActions.length === 0) return;

    const latestAction = recentActions[0];
    
    // Generate random positions for demo (in real app, use agent positions)
    const startPos = new THREE.Vector3(
      (Math.random() - 0.5) * 15,
      (Math.random() - 0.5) * 5,
      (Math.random() - 0.5) * 15
    );
    
    const endPos = new THREE.Vector3(
      (Math.random() - 0.5) * 15,
      (Math.random() - 0.5) * 5,
      (Math.random() - 0.5) * 15
    );

    const color = getActionColor(latestAction.action_type);

    const newBeam: BeamData = {
      id: latestAction.id,
      startPos,
      endPos,
      color,
      progress: 0,
      lifetime: 0,
      maxLifetime: 2.0, // 2 seconds
    };

    beamsRef.current = [newBeam, ...beamsRef.current].slice(0, maxBeams);
  }, [recentActions, maxBeams]);

  // Animate beams
  useFrame((state, delta) => {
    beamsRef.current = beamsRef.current.filter((beam) => {
      beam.lifetime += delta;
      beam.progress = Math.min(beam.lifetime / beam.maxLifetime, 1);
      return beam.lifetime < beam.maxLifetime;
    });
  });

  // Get color based on action type
  const getActionColor = (actionType: string) => {
    const lowerType = actionType.toLowerCase();
    
    if (lowerType.includes('communicate')) return '#3b82f6'; // Blue
    if (lowerType.includes('move') || lowerType.includes('travel')) return '#06b6d4'; // Cyan
    if (lowerType.includes('attack') || lowerType.includes('conflict')) return '#ef4444'; // Red
    if (lowerType.includes('build') || lowerType.includes('create')) return '#10b981'; // Green
    if (lowerType.includes('trade') || lowerType.includes('exchange')) return '#f59e0b'; // Amber
    if (lowerType.includes('research') || lowerType.includes('study')) return '#8b5cf6'; // Purple
    
    return '#6bfb9a'; // Neon green default
  };

  return (
    <group ref={groupRef}>
      {beamsRef.current.map((beam) => {
        // Calculate current beam position based on progress
        const currentPos = new THREE.Vector3().lerpVectors(
          beam.startPos,
          beam.endPos,
          beam.progress
        );

        // Calculate opacity (fade out near end)
        const opacity = beam.progress < 0.8 
          ? 0.8 
          : (1 - beam.progress) * 4;

        return (
          <group key={beam.id}>
            {/* Beam particle */}
            <mesh position={currentPos}>
              <sphereGeometry args={[0.1, 8, 8]} />
              <meshBasicMaterial
                color={beam.color}
                transparent
                opacity={opacity}
              />
            </mesh>

            {/* Glow effect */}
            <mesh position={currentPos}>
              <sphereGeometry args={[0.2, 8, 8]} />
              <meshBasicMaterial
                color={beam.color}
                transparent
                opacity={opacity * 0.3}
              />
            </mesh>

            {/* Trail line */}
            {beam.progress > 0.1 && (
              <line>
                <bufferGeometry>
                  <bufferAttribute
                    attach="attributes-position"
                    count={2}
                    array={new Float32Array([
                      beam.startPos.x, beam.startPos.y, beam.startPos.z,
                      currentPos.x, currentPos.y, currentPos.z,
                    ])}
                    itemSize={3}
                  />
                </bufferGeometry>
                <lineBasicMaterial
                  color={beam.color}
                  transparent
                  opacity={opacity * 0.5}
                  linewidth={2}
                />
              </line>
            )}
          </group>
        );
      })}
    </group>
  );
}
