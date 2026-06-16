import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars, Grid } from '@react-three/drei';
import { Suspense, useState, useEffect } from 'react';
import ScenarioNodes from './3d/ScenarioNodes';
import EntityNodes from './3d/EntityNodes';
import AgentNodes from './3d/AgentNodes';
import RelationshipLines from './3d/RelationshipLines';
import ActionBeams from './3d/ActionBeams';
import PatternOverlay from './3d/PatternOverlay';
import { useProjectStore } from '../stores/projectStore';
import { useSimulationStore } from '../stores/simulationStore';

interface Scene3DProps {
  activeView?: 'scenarios' | 'entities' | 'agents';
}

export default function Scene3D({ activeView }: Scene3DProps) {
  const { entities, agents, relationships, selectedEntity, selectedAgent, setSelectedEntity, setSelectedAgent } = useProjectStore();
  const { recentActions, patterns } = useSimulationStore();

  const [showRelationships, setShowRelationships] = useState(true);
  const [showActionBeams, setShowActionBeams] = useState(true);
  const [showPatterns, setShowPatterns] = useState(true);
  const [viewMode, setViewMode] = useState<'scenarios' | 'entities' | 'agents' | 'all'>('all');

  useEffect(() => {
    if (activeView) {
      setViewMode(activeView);
    }
  }, [activeView]);

  return (
    <div className="relative w-full h-full">
      <Canvas
        camera={{ position: [0, 10, 50], fov: 55 }}
        gl={{ antialias: true, alpha: false, toneMapping: 1 }}
        style={{ background: '#0a0a0a' }}
        onCreated={({ gl }) => {
          gl.toneMappingExposure = 1.5;
          gl.setClearColor(0x0a0a0a, 1);
        }}
      >
        <Suspense fallback={null}>
          {/* Enhanced lighting for colorful spheres */}
          <ambientLight intensity={0.4} color="#1a331a" />
          <directionalLight position={[15, 25, 15]} intensity={1.2} color="#6bfb9a" />
          <directionalLight position={[-10, 15, -10]} intensity={0.5} color="#4ade80" />
          <pointLight position={[0, 0, 0]} intensity={3} color="#6bfb9a" distance={120} />
          <pointLight position={[20, 10, -20]} intensity={1.5} color="#10b981" distance={80} />
          <pointLight position={[-20, -5, 20]} intensity={1} color="#34d399" distance={60} />

          <Stars radius={120} depth={60} count={6000} factor={5} saturation={0} fade speed={0.8} />

          <Grid
            args={[200, 200]}
            position={[0, -15, 0]}
            cellSize={2}
            cellThickness={0.5}
            cellColor="#6bfb9a"
            sectionSize={10}
            sectionThickness={1}
            sectionColor="#10b981"
            fadeDistance={100}
            fadeStrength={1}
            infiniteGrid
          />

          {(viewMode === 'scenarios' || viewMode === 'all') && (
            <ScenarioNodes />
          )}

          {(viewMode === 'entities' || viewMode === 'all') && entities.length > 0 && (
            <EntityNodes entities={entities} selectedId={selectedEntity?.id} onSelect={setSelectedEntity} />
          )}

          {(viewMode === 'agents' || viewMode === 'all') && agents.length > 0 && (
            <AgentNodes agents={agents} selectedId={selectedAgent?.id} onSelect={setSelectedAgent} />
          )}

          {/* Always show relationship lines when there's content */}
          {showRelationships && (
            <RelationshipLines relationships={relationships} agents={agents} showRelationships={showRelationships} />
          )}

          {showActionBeams && recentActions.length > 0 && (
            <ActionBeams recentActions={recentActions} maxBeams={10} />
          )}

          {/* Pattern overlay */}
          {showPatterns && patterns.length > 0 && (
            <PatternOverlay patterns={patterns} showOverlay={showPatterns} />
          )}

          <OrbitControls enableDamping dampingFactor={0.05} rotateSpeed={0.5} zoomSpeed={0.8} minDistance={10} maxDistance={120} />
        </Suspense>
      </Canvas>

      {/* Nebula Overlay */}
      <div className="nebula-overlay" />

      {/* View controls - positioned to avoid left sidebar (w-64 = 256px) */}
      <div className="absolute top-4 left-72 glass-panel p-3 z-10 rounded-lg">
        <div className="text-[10px] font-mono uppercase tracking-widest text-primary/50 mb-2 relative z-[1]">
          View Mode
        </div>
        <div className="flex flex-row gap-1 flex-wrap relative z-[1]">
          {(['all', 'scenarios', 'entities', 'agents'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider transition-all ${
                viewMode === mode
                  ? 'bg-primary/20 border border-primary text-primary shadow-[0_0_8px_rgba(107,251,154,0.3)]'
                  : 'border border-primary/20 text-primary/50 hover:border-primary/40 hover:text-primary/70'
              }`}
            >
              {mode}
            </button>
          ))}
        </div>

        <div className="border-t border-primary/20 pt-2 mt-2 space-y-1.5 relative z-[1]">
          <label className="flex items-center gap-2 text-[11px] text-primary/60 cursor-pointer hover:text-primary/80 transition-colors">
            <input type="checkbox" checked={showRelationships} onChange={(e) => setShowRelationships(e.target.checked)} className="accent-neon-green w-3 h-3" />
            <span className="font-mono uppercase tracking-wider">Relationships</span>
          </label>
          <label className="flex items-center gap-2 text-[11px] text-primary/60 cursor-pointer hover:text-primary/80 transition-colors">
            <input type="checkbox" checked={showActionBeams} onChange={(e) => setShowActionBeams(e.target.checked)} className="accent-neon-green w-3 h-3" />
            <span className="font-mono uppercase tracking-wider">Action Beams</span>
          </label>
          <label className="flex items-center gap-2 text-[11px] text-primary/60 cursor-pointer hover:text-primary/80 transition-colors">
            <input type="checkbox" checked={showPatterns} onChange={(e) => setShowPatterns(e.target.checked)} className="accent-neon-green w-3 h-3" />
            <span className="font-mono uppercase tracking-wider">Pattern Overlay</span>
          </label>
        </div>
      </div>
    </div>
  );
}
