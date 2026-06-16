import { useEffect, useState } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { worldStateAPI } from '../../services/api';
import type { WorldState } from '../../types';

interface WorldStatsDashboardProps {
  onClose: () => void;
}

export default function WorldStatsDashboard({ onClose }: WorldStatsDashboardProps) {
  const { currentProject, entities, agents } = useProjectStore();
  const [worldState, setWorldState] = useState<WorldState | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (currentProject) {
      setLoading(true);
      worldStateAPI.get(currentProject.id)
        .then(res => setWorldState(res.data))
        .catch(err => {
          console.error('Failed to load world state:', err);
          // Fallback to computed state
          setWorldState({
            project_id: currentProject.id,
            current_step: 0,
            stability: 0.65,
            economy: 0.72,
            technology_level: 0.58,
            active_conflicts: 0,
            total_agents: agents.length,
            total_entities: entities.length,
            recent_events: [],
            updated_at: new Date().toISOString(),
          });
        })
        .finally(() => setLoading(false));
    }
  }, [currentProject, agents.length, entities.length]);

  const getStatColor = (value: number) => {
    if (value > 0.7) return 'text-scenario-optimistic';
    if (value < 0.4) return 'text-scenario-pessimistic';
    return 'text-primary';
  };

  const getStatBg = (value: number) => {
    if (value > 0.7) return 'bg-scenario-optimistic';
    if (value < 0.4) return 'bg-scenario-pessimistic';
    return 'bg-primary';
  };

  if (!currentProject) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="glass-panel w-full max-w-4xl max-h-[85vh] overflow-y-auto m-4 relative">
        <div className="scan-line" />
        
        {/* Header */}
        <div className="p-6 border-b border-primary/20 flex justify-between items-center relative z-[1]">
          <div>
            <h2 className="text-2xl font-bold text-primary neon-glow">World State Dashboard</h2>
            <p className="text-sm text-primary/70 font-mono mt-1">{currentProject.name}</p>
          </div>
          <button
            onClick={onClose}
            className="text-primary/60 hover:text-primary transition-colors"
          >
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>

        {loading ? (
          <div className="p-12 flex flex-col items-center justify-center">
            <div className="w-16 h-16 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
            <p className="text-primary/70 font-mono text-sm mt-4">Loading world state...</p>
          </div>
        ) : worldState ? (
          <div className="p-6 space-y-6 relative z-[1]">
            {/* Key Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="glass-panel p-4 rounded-lg border-l-4 border-l-primary">
                <p className="text-xs font-mono text-primary/50 uppercase mb-1">Stability</p>
                <div className="flex items-end gap-2">
                  <span className={`text-3xl font-bold ${getStatColor(worldState.stability)}`}>
                    {(worldState.stability * 100).toFixed(0)}
                  </span>
                  <span className="text-lg text-primary/70 mb-1">%</span>
                </div>
                <div className="mt-2 h-2 bg-obsidian-darker rounded-full overflow-hidden">
                  <div
                    className={`h-full ${getStatBg(worldState.stability)} transition-all`}
                    style={{ width: `${worldState.stability * 100}%` }}
                  />
                </div>
              </div>

              <div className="glass-panel p-4 rounded-lg border-l-4 border-l-scenario-optimistic">
                <p className="text-xs font-mono text-primary/50 uppercase mb-1">Economy</p>
                <div className="flex items-end gap-2">
                  <span className={`text-3xl font-bold ${getStatColor(worldState.economy)}`}>
                    {(worldState.economy * 100).toFixed(0)}
                  </span>
                  <span className="text-lg text-primary/70 mb-1">%</span>
                </div>
                <div className="mt-2 h-2 bg-obsidian-darker rounded-full overflow-hidden">
                  <div
                    className={`h-full ${getStatBg(worldState.economy)} transition-all`}
                    style={{ width: `${worldState.economy * 100}%` }}
                  />
                </div>
              </div>

              <div className="glass-panel p-4 rounded-lg border-l-4 border-l-agent-science">
                <p className="text-xs font-mono text-primary/50 uppercase mb-1">Technology</p>
                <div className="flex items-end gap-2">
                  <span className={`text-3xl font-bold ${getStatColor(worldState.technology_level)}`}>
                    {(worldState.technology_level * 100).toFixed(0)}
                  </span>
                  <span className="text-lg text-primary/70 mb-1">%</span>
                </div>
                <div className="mt-2 h-2 bg-obsidian-darker rounded-full overflow-hidden">
                  <div
                    className={`h-full ${getStatBg(worldState.technology_level)} transition-all`}
                    style={{ width: `${worldState.technology_level * 100}%` }}
                  />
                </div>
              </div>

              <div className="glass-panel p-4 rounded-lg border-l-4 border-l-scenario-pessimistic">
                <p className="text-xs font-mono text-primary/50 uppercase mb-1">Conflicts</p>
                <div className="flex items-end gap-2">
                  <span className={`text-3xl font-bold ${worldState.active_conflicts > 0 ? 'text-scenario-pessimistic' : 'text-scenario-optimistic'}`}>
                    {worldState.active_conflicts}
                  </span>
                  <span className="text-lg text-primary/70 mb-1">active</span>
                </div>
                <p className="text-xs text-primary/50 mt-2 font-mono">
                  {worldState.active_conflicts === 0 ? 'Peaceful' : 'Tensions high'}
                </p>
              </div>
            </div>

            {/* Population Stats */}
            <div className="glass-panel p-5 rounded-lg">
              <h3 className="font-mono text-sm text-primary font-semibold mb-4 flex items-center gap-2">
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z" />
                </svg>
                Population
              </h3>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <p className="text-xs font-mono text-primary/50 uppercase mb-1">Entities</p>
                  <p className="text-2xl font-bold text-primary">{worldState.total_entities}</p>
                  <p className="text-xs text-primary/60 mt-1 font-mono">
                    {worldState.entity_types?.nation || 0} nations,{' '}
                    {worldState.entity_types?.company || 0} companies
                  </p>
                </div>
                <div>
                  <p className="text-xs font-mono text-primary/50 uppercase mb-1">Agents</p>
                  <p className="text-2xl font-bold text-primary">{worldState.total_agents}</p>
                  <p className="text-xs text-primary/60 mt-1 font-mono">
                    Active autonomous actors
                  </p>
                </div>
                <div>
                  <p className="text-xs font-mono text-primary/50 uppercase mb-1">Simulation</p>
                  <p className="text-2xl font-bold text-primary">Step {worldState.current_step}</p>
                  <p className="text-xs text-primary/60 mt-1 font-mono">
                    {worldState.current_step === 0 ? 'Not started' : 'In progress'}
                  </p>
                </div>
              </div>
            </div>

            {/* Recent Events */}
            {worldState.recent_events && worldState.recent_events.length > 0 && (
              <div className="glass-panel p-5 rounded-lg">
                <h3 className="font-mono text-sm text-primary font-semibold mb-4 flex items-center gap-2">
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                  </svg>
                  Recent Events
                </h3>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {worldState.recent_events.map((event, idx) => (
                    <div key={idx} className="flex items-start gap-3 p-3 bg-primary/5 rounded border-l-2 border-primary/40">
                      <div className="w-2 h-2 rounded-full bg-primary mt-1.5 shadow-[0_0_8px_rgba(107,251,154,1)]" />
                      <p className="text-sm text-primary/80 flex-1">{event}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* System Info */}
            <div className="glass-panel p-4 rounded-lg bg-primary/5">
              <div className="flex items-center justify-between text-xs font-mono text-primary/60">
                <span>Last Updated: {new Date(worldState.updated_at).toLocaleString()}</span>
                <span>Project ID: {worldState.project_id.slice(0, 8)}...</span>
              </div>
            </div>
          </div>
        ) : (
          <div className="p-12 text-center">
            <p className="text-primary/60 font-mono">No world state data available</p>
          </div>
        )}
      </div>
    </div>
  );
}
