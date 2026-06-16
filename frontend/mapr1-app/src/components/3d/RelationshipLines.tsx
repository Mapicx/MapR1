import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import type { AgentRelationship, Agent } from '../../types';
import { getAgentPositions } from './AgentNodes';
import { useScenarioStore } from '../../stores/scenarioStore';
import { getScenarioPositions } from './ScenarioNodes';

interface RelationshipLinesProps {
  relationships: AgentRelationship[];
  agents: Agent[];
  showRelationships: boolean;
}

const REL_COLORS: Record<string, string> = {
  alliance:      '#10b981',
  cooperation:   '#10b981',
  conflict:      '#ef4444',
  rivalry:       '#ef4444',
  trade:         '#f59e0b',
  economic:      '#f59e0b',
  influence:     '#8b5cf6',
  power:         '#8b5cf6',
  information:   '#3b82f6',
  knowledge:     '#3b82f6',
};

function getRelColor(type: string): string {
  const t = type.toLowerCase();
  for (const [k, v] of Object.entries(REL_COLORS)) {
    if (t.includes(k)) return v;
  }
  return '#6bfb9a';
}

// A single animated connection line between two 3D points
function ConnectionLine({
  start,
  end,
  color,
  opacity = 0.55,
  animOffset = 0,
}: {
  start: THREE.Vector3;
  end: THREE.Vector3;
  color: string;
  opacity?: number;
  animOffset?: number;
}) {
  const lineRef = useRef<THREE.Line>(null);
  const dotRef = useRef<THREE.Mesh>(null);

  // Midpoint slightly elevated for a gentle arc
  const mid = useMemo(() => {
    const m = new THREE.Vector3().addVectors(start, end).multiplyScalar(0.5);
    m.y += start.distanceTo(end) * 0.12;
    return m;
  }, [start, end]);

  // Quadratic bezier curve points
  const curve = useMemo(() => {
    const c = new THREE.QuadraticBezierCurve3(start, mid, end);
    return c.getPoints(48);
  }, [start, mid, end]);

  const geometry = useMemo(() => {
    return new THREE.BufferGeometry().setFromPoints(curve);
  }, [curve]);

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    // Pulse the line opacity
    if (lineRef.current) {
      const mat = lineRef.current.material as THREE.LineBasicMaterial;
      mat.opacity = opacity * (0.7 + Math.sin(t * 1.5 + animOffset) * 0.3);
    }
    // Animate a travelling dot along the curve
    if (dotRef.current) {
      const progress = ((t * 0.25 + animOffset * 0.1) % 1);
      const idx = Math.floor(progress * (curve.length - 1));
      const pt = curve[idx];
      if (pt) {
        dotRef.current.position.set(pt.x, pt.y, pt.z);
      }
    }
  });

  return (
    <group>
      {/* The arc line */}
      <primitive object={new THREE.Line(geometry, new THREE.LineBasicMaterial({
        color,
        transparent: true,
        opacity,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }))} ref={lineRef} />

      {/* Travelling dot */}
      <mesh ref={dotRef}>
        <sphereGeometry args={[0.12, 8, 8]} />
        <meshBasicMaterial
          color={color}
          transparent
          opacity={0.9}
          blending={THREE.AdditiveBlending}
        />
      </mesh>
    </group>
  );
}

export default function RelationshipLines({
  relationships,
  agents,
  showRelationships,
}: RelationshipLinesProps) {
  const { scenarios } = useScenarioStore();

  // Agent positions — same layout as AgentNodes
  const agentPositions = useMemo(() => getAgentPositions(agents), [agents]);

  // Scenario positions — same layout as ScenarioNodes
  const scenarioPositions = useMemo(
    () => getScenarioPositions(scenarios.length),
    [scenarios.length]
  );

  // Build scenario connections: connect each scenario to its nearest neighbours
  const scenarioConnections = useMemo(() => {
    if (scenarios.length < 2) return [];
    const conns: { start: THREE.Vector3; end: THREE.Vector3; color: string; key: string }[] = [];

    scenarios.forEach((s, i) => {
      // Connect to next 1-2 scenarios (ring + cross connections for visual interest)
      const targets = [
        (i + 1) % scenarios.length,
        scenarios.length > 3 ? (i + 2) % scenarios.length : -1,
      ].filter((t) => t !== -1 && t !== i);

      targets.forEach((j) => {
        const colorMap: Record<string, string> = {
          optimistic: '#10b981',
          pessimistic: '#ef4444',
          mixed: '#8b5cf6',
          neutral: '#6bfb9a',
        };
        const color = colorMap[scenarios[i].category] || '#6bfb9a';
        conns.push({
          start: scenarioPositions[i],
          end: scenarioPositions[j],
          color,
          key: `sc-${i}-${j}`,
        });
      });
    });

    return conns;
  }, [scenarios, scenarioPositions]);

  if (!showRelationships) return null;

  return (
    <group>
      {/* Agent relationship lines */}
      {relationships.map((rel, i) => {
        const src = agentPositions.get(rel.source_agent_id);
        const tgt = agentPositions.get(rel.target_agent_id);
        if (!src || !tgt) return null;
        return (
          <ConnectionLine
            key={rel.id}
            start={src}
            end={tgt}
            color={getRelColor(rel.relationship_type)}
            opacity={0.55 + (rel.strength ?? 0.5) * 0.3}
            animOffset={i * 0.7}
          />
        );
      })}

      {/* Scenario connection lines */}
      {scenarioConnections.map((conn, i) => (
        <ConnectionLine
          key={conn.key}
          start={conn.start}
          end={conn.end}
          color={conn.color}
          opacity={0.45}
          animOffset={i * 0.5}
        />
      ))}
    </group>
  );
}
