import { useState, useEffect } from 'react';
import { useScenarioStore } from '../../stores/scenarioStore';
import { useSimulationStore } from '../../stores/simulationStore';
import { useProjectStore } from '../../stores/projectStore';
import { agentAPI } from '../../services/api';
import type { Memory, Goal } from '../../types';

export default function RightSidebarEnhanced() {
  const { selectedScenario } = useScenarioStore();
  const { selectedAgent, selectedEntity } = useProjectStore();
  const { patterns, actions } = useSimulationStore();
  
  const [activeTab, setActiveTab] = useState<'details' | 'memories' | 'goals' | 'patterns'>('details');
  const [memories, setMemories] = useState<Memory[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loadingMemories, setLoadingMemories] = useState(false);
  const [loadingGoals, setLoadingGoals] = useState(false);

  // Load memories and goals when agent is selected
  useEffect(() => {
    if (selectedAgent) {
      setLoadingMemories(true);
      setLoadingGoals(true);
      
      agentAPI.getMemories(selectedAgent.id)
        .then(res => setMemories(res.data))
        .catch(err => console.error('Failed to load memories:', err))
        .finally(() => setLoadingMemories(false));
      
      agentAPI.getGoals(selectedAgent.id)
        .then(res => setGoals(res.data))
        .catch(err => console.error('Failed to load goals:', err))
        .finally(() => setLoadingGoals(false));
    } else {
      setMemories([]);
      setGoals([]);
    }
  }, [selectedAgent]);

  const getPersonalityColor = (value: number) => {
    if (value > 0.7) return 'text-scenario-optimistic';
    if (value < 0.3) return 'text-scenario-pessimistic';
    return 'text-primary';
  };

  const getGoalStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-scenario-optimistic';
      case 'active': return 'text-primary';
      case 'blocked': return 'text-scenario-pessimistic';
      case 'abandoned': return 'text-scenario-neutral';
      default: return 'text-primary/60';
    }
  };

  return (
    <aside className="fixed top-16 right-0 bottom-8 w-80 z-40 frost-sidebar pointer-events-auto hidden lg:block overflow-y-auto sidebar-overlay-right">
      <div className="p-4 space-y-4 pt-6">
        {/* Tab Navigation */}
        {selectedAgent && (
          <div className="flex gap-1 mb-4 glass-panel p-1 rounded-lg">
            {(['details', 'memories', 'goals', 'patterns'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`flex-1 px-2 py-1.5 text-[10px] font-mono uppercase tracking-wider rounded transition-all ${
                  activeTab === tab
                    ? 'bg-primary/20 text-primary border border-primary/50'
                    : 'text-primary/60 hover:text-primary/80'
                }`}
              >
                {tab}
              </button>
            ))}
          </div>
        )}

        {/* Agent Details Panel */}
        {selectedAgent && activeTab === 'details' && (
          <div className="glass-panel rounded-xl p-5 border-t border-t-primary/50 relative overflow-hidden">
            <div className="scan-line" />
            <div className="relative z-[1]">
              <div className="flex items-center gap-2 mb-3 pb-2 border-b border-primary/30">
                <svg className="w-5 h-5 text-primary" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
                </svg>
                <h3 className="font-mono text-sm text-primary font-semibold">Agent Profile</h3>
              </div>

              <div className="space-y-3">
                <div>
                  <h4 className="font-semibold text-primary mb-1">{selectedAgent.name}</h4>
                  <p className="text-xs text-primary/70 font-mono">{selectedAgent.agent_type}</p>
                  <p className="text-xs text-primary/60 mt-1">{selectedAgent.role}</p>
                </div>

                {/* Personality Traits */}
                <div className="pt-2 border-t border-primary/20">
                  <p className="font-mono text-[10px] text-primary/50 uppercase mb-2">Personality</p>
                  <div className="space-y-1.5">
                    {Object.entries(selectedAgent.personality).map(([trait, value]) => (
                      <div key={trait} className="flex items-center justify-between">
                        <span className="text-[10px] text-primary/70 font-mono capitalize">
                          {trait.replace(/_/g, ' ')}
                        </span>
                        <div className="flex items-center gap-2">
                          <div className="w-16 h-1.5 bg-obsidian-darker rounded-full overflow-hidden">
                            <div
                              className={`h-full ${getPersonalityColor(value as number)} bg-current transition-all`}
                              style={{ width: `${(value as number) * 100}%` }}
                            />
                          </div>
                          <span className={`text-[10px] font-mono ${getPersonalityColor(value as number)}`}>
                            {((value as number) * 100).toFixed(0)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Resources */}
                {Object.keys(selectedAgent.resources || {}).length > 0 && (
                  <div className="pt-2 border-t border-primary/20">
                    <p className="font-mono text-[10px] text-primary/50 uppercase mb-2">Resources</p>
                    <div className="grid grid-cols-2 gap-2">
                      {Object.entries(selectedAgent.resources).map(([key, value]) => (
                        <div key={key} className="bg-primary/5 rounded p-2">
                          <p className="text-[9px] text-primary/50 font-mono uppercase">{key}</p>
                          <p className="text-xs text-primary font-mono">{String(value)}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Memories Tab */}
        {selectedAgent && activeTab === 'memories' && (
          <div className="glass-panel rounded-xl p-5 border-t border-t-primary/50 relative overflow-hidden">
            <div className="scan-line" />
            <div className="relative z-[1]">
              <div className="flex justify-between items-center mb-4 pb-2 border-b border-primary/30">
                <h3 className="font-mono text-sm text-primary font-semibold">Memories</h3>
                <span className="font-mono text-xs text-primary/70">{memories.length}</span>
              </div>

              {loadingMemories ? (
                <div className="py-6 text-center">
                  <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin mx-auto" />
                  <p className="text-xs text-primary/60 mt-2 font-mono">Loading memories...</p>
                </div>
              ) : memories.length === 0 ? (
                <div className="py-6 text-center">
                  <p className="text-xs text-primary/60 font-mono">No memories yet</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {memories.map((memory) => (
                    <div
                      key={memory.id}
                      className="p-3 bg-primary/5 border border-primary/20 rounded hover:bg-primary/10 transition-all"
                    >
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-mono text-[9px] text-primary/50 uppercase">{memory.memory_type}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-[9px] text-primary/70 font-mono">
                            Imp: {(memory.importance * 100).toFixed(0)}
                          </span>
                          <span className={`text-[9px] font-mono ${
                            memory.emotional_valence > 0 ? 'text-scenario-optimistic' : 
                            memory.emotional_valence < 0 ? 'text-scenario-pessimistic' : 
                            'text-scenario-neutral'
                          }`}>
                            {memory.emotional_valence > 0 ? '+' : ''}{memory.emotional_valence.toFixed(1)}
                          </span>
                        </div>
                      </div>
                      <p className="text-[10px] text-primary/80 leading-relaxed">{memory.content}</p>
                      <p className="text-[9px] text-primary/40 mt-1 font-mono">
                        {new Date(memory.created_at).toLocaleString()}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Goals Tab */}
        {selectedAgent && activeTab === 'goals' && (
          <div className="glass-panel rounded-xl p-5 border-t border-t-primary/50 relative overflow-hidden">
            <div className="scan-line" />
            <div className="relative z-[1]">
              <div className="flex justify-between items-center mb-4 pb-2 border-b border-primary/30">
                <h3 className="font-mono text-sm text-primary font-semibold">Goals</h3>
                <span className="font-mono text-xs text-primary/70">{goals.length}</span>
              </div>

              {loadingGoals ? (
                <div className="py-6 text-center">
                  <div className="w-8 h-8 border-2 border-primary/30 border-t-primary rounded-full animate-spin mx-auto" />
                  <p className="text-xs text-primary/60 mt-2 font-mono">Loading goals...</p>
                </div>
              ) : goals.length === 0 ? (
                <div className="py-6 text-center">
                  <p className="text-xs text-primary/60 font-mono">No goals set</p>
                </div>
              ) : (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {goals.map((goal) => (
                    <div
                      key={goal.id}
                      className="p-3 bg-primary/5 border border-primary/20 rounded hover:bg-primary/10 transition-all"
                    >
                      <div className="flex justify-between items-start mb-2">
                        <span className={`font-mono text-[9px] uppercase ${getGoalStatusColor(goal.status)}`}>
                          {goal.status}
                        </span>
                        <span className="text-[9px] text-primary/70 font-mono">
                          Priority: {goal.priority}
                        </span>
                      </div>
                      <p className="text-[10px] text-primary/80 leading-relaxed mb-2">{goal.description}</p>
                      <div className="flex items-center gap-2">
                        <div className="flex-1 h-1.5 bg-obsidian-darker rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary transition-all"
                            style={{ width: `${goal.progress * 100}%` }}
                          />
                        </div>
                        <span className="text-[9px] text-primary font-mono">
                          {(goal.progress * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-[9px] text-primary/50 mt-1 font-mono uppercase">{goal.goal_type}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Scenario Details Panel (when no agent selected) */}
        {!selectedAgent && selectedScenario && (
          <div className="glass-panel rounded-xl p-5 border-t border-t-primary/50 relative overflow-hidden">
            <div className="scan-line" />
            <div className="relative z-[1]">
              <div className="flex items-center gap-2 mb-3 pb-2 border-b border-primary/30">
                <svg className="w-5 h-5 text-primary" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                  <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                </svg>
                <h3 className="font-mono text-sm text-primary font-semibold">Scenario Details</h3>
              </div>

              <div className="space-y-3">
                <div>
                  <h4 className="font-semibold text-primary mb-1">{selectedScenario.title}</h4>
                  <p className="text-xs text-primary/70 leading-relaxed">{selectedScenario.description}</p>
                </div>

                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-primary/20">
                  <div>
                    <p className="font-mono text-[10px] text-primary/50 uppercase">Category</p>
                    <p className="font-mono text-xs text-primary">{selectedScenario.category}</p>
                  </div>
                  <div>
                    <p className="font-mono text-[10px] text-primary/50 uppercase">Probability</p>
                    <p className="font-mono text-xs text-primary">
                      {((selectedScenario.probability || 0) * 100).toFixed(0)}%
                    </p>
                  </div>
                </div>

                {selectedScenario.timeline && selectedScenario.timeline.length > 0 && (
                  <div className="pt-2 border-t border-primary/20">
                    <p className="font-mono text-[10px] text-primary/50 uppercase mb-2">Timeline Events</p>
                    <div className="space-y-2 max-h-60 overflow-y-auto">
                      {selectedScenario.timeline.map((event, idx) => (
                        <div key={idx} className="p-2 bg-primary/5 rounded border-l-2 border-primary/40">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-mono text-xs text-primary font-semibold">{event.year}</span>
                            <span className={`text-[9px] font-mono uppercase px-1.5 py-0.5 rounded ${
                              event.impact === 'high' ? 'bg-scenario-pessimistic/20 text-scenario-pessimistic' :
                              event.impact === 'medium' ? 'bg-primary/20 text-primary' :
                              'bg-scenario-neutral/20 text-scenario-neutral'
                            }`}>
                              {event.impact}
                            </span>
                          </div>
                          <p className="text-[10px] text-primary/70 leading-relaxed">{event.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Emergent Patterns Panel */}
        {(activeTab === 'patterns' || !selectedAgent) && (
          <div className="glass-panel rounded-xl p-5 border-t border-t-primary/50 relative overflow-hidden">
            <div className="scan-line" style={{ animationDelay: '2s' }} />
            <div className="relative z-[1]">
              <div className="flex justify-between items-center mb-4 pb-2 border-b border-primary/30">
                <h3 className="font-mono text-sm text-primary font-semibold flex items-center gap-2">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M6 2a1 1 0 00-1 1v1H4a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V6a2 2 0 00-2-2h-1V3a1 1 0 10-2 0v1H7V3a1 1 0 00-1-1zm0 5a1 1 0 000 2h8a1 1 0 100-2H6z" clipRule="evenodd" />
                  </svg>
                  Emergent Patterns
                </h3>
                <span className="font-mono text-xs text-primary/70">{patterns.length} detected</span>
              </div>

              {patterns.length === 0 ? (
                <div className="py-6 flex flex-col items-center">
                  <div className="w-12 h-12 rounded-full border-2 border-dashed border-primary/60 animate-[spin_10s_linear_infinite] flex items-center justify-center shadow-[0_0_15px_rgba(107,251,154,0.2)]">
                    <div className="w-2 h-2 bg-primary rounded-full shadow-[0_0_8px_rgba(107,251,154,1)]" />
                  </div>
                  <p className="text-center font-mono text-[10px] text-primary/60 mt-3">
                    Scanning simulation manifold...
                  </p>
                </div>
              ) : (
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {patterns.map((pattern) => (
                    <div
                      key={pattern.id}
                      className="p-3 bg-primary/5 border border-primary/20 rounded hover:bg-primary/10 transition-all cursor-pointer"
                    >
                      <div className="flex justify-between items-start mb-1">
                        <h4 className="font-semibold text-xs text-primary">{pattern.title}</h4>
                        <span className="font-mono text-[10px] text-primary/70">
                          {(pattern.significance * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-[10px] text-primary/60 leading-relaxed">
                        {pattern.description}
                      </p>
                      <p className="font-mono text-[9px] text-primary/40 mt-1">
                        {pattern.pattern_type.replace(/_/g, ' ').toUpperCase()}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Recent Actions Panel */}
        {actions.length > 0 && !selectedAgent && (
          <div className="glass-panel rounded-xl p-5 border-t border-t-primary/50 relative overflow-hidden">
            <div className="scan-line" style={{ animationDelay: '3s' }} />
            <div className="relative z-[1]">
              <div className="flex justify-between items-center mb-4 pb-2 border-b border-primary/30">
                <h3 className="font-mono text-sm text-primary font-semibold">Recent Actions</h3>
                <span className="font-mono text-xs text-primary/70">{actions.length}</span>
              </div>

              <div className="space-y-2 max-h-40 overflow-y-auto">
                {actions.slice(0, 5).map((action) => (
                  <div
                    key={action.id}
                    className={`p-2 rounded border ${
                      action.success
                        ? 'bg-scenario-optimistic/5 border-scenario-optimistic/20'
                        : 'bg-scenario-pessimistic/5 border-scenario-pessimistic/20'
                    }`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`w-1.5 h-1.5 rounded-full ${action.success ? 'bg-scenario-optimistic' : 'bg-scenario-pessimistic'}`} />
                      <span className="font-mono text-xs text-primary font-semibold">
                        {action.agent_name}
                      </span>
                    </div>
                    <p className="text-[10px] text-primary/70 ml-3.5">
                      {action.action_type.replace(/_/g, ' ')}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
