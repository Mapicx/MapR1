import { useEffect, useRef, useCallback } from 'react';
import { useScenarioStore } from '../../stores/scenarioStore';
import { useProjectStore } from '../../stores/projectStore';

interface LeftSidebarProps {
  activeView: 'scenarios' | 'entities' | 'agents';
  onViewChange: (view: 'scenarios' | 'entities' | 'agents') => void;
  onCreateNode: () => void;
  onOpenSettings: () => void;
  onOpenLogs: () => void;
}

export default function LeftSidebar({
  activeView,
  onViewChange,
  onCreateNode,
  onOpenSettings,
  onOpenLogs,
}: LeftSidebarProps) {
  const { scenarios, selectedScenario, setSelectedScenario } = useScenarioStore();
  const { entities, agents, selectedEntity, selectedAgent, setSelectedEntity, setSelectedAgent } = useProjectStore();
  const sidebarRef = useRef<HTMLElement>(null);

  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      optimistic: 'border-l-scenario-optimistic text-scenario-optimistic',
      pessimistic: 'border-l-scenario-pessimistic text-scenario-pessimistic',
      mixed: 'border-l-scenario-mixed text-scenario-mixed',
      neutral: 'border-l-scenario-neutral text-scenario-neutral',
    };
    return colors[category] || colors.neutral;
  };

  // Interactive grid cursor tracking
  const handleMouseMove = useCallback((e: MouseEvent) => {
    const sidebar = sidebarRef.current;
    if (!sidebar) return;
    const rect = sidebar.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    sidebar.style.setProperty('--mouse-x', `${x}px`);
    sidebar.style.setProperty('--mouse-y', `${y}px`);
  }, []);

  const handleMouseLeave = useCallback(() => {
    const sidebar = sidebarRef.current;
    if (!sidebar) return;
    sidebar.style.setProperty('--mouse-x', '50%');
    sidebar.style.setProperty('--mouse-y', '50%');
  }, []);

  useEffect(() => {
    const sidebar = sidebarRef.current;
    if (!sidebar) return;
    sidebar.addEventListener('mousemove', handleMouseMove);
    sidebar.addEventListener('mouseleave', handleMouseLeave);
    return () => {
      sidebar.removeEventListener('mousemove', handleMouseMove);
      sidebar.removeEventListener('mouseleave', handleMouseLeave);
    };
  }, [handleMouseMove, handleMouseLeave]);

  return (
    <aside
      ref={sidebarRef}
      id="left-sidebar"
      className="fixed left-0 top-16 bottom-8 w-64 z-40 frost-sidebar pointer-events-auto flex flex-col relative sidebar-overlay-left"
    >
      {/* Neon Frost Green Grid - animated cursor-reactive overlay */}
      <div className="grid-interactive" />

      {/* Header */}
      <div className="p-6 border-b border-primary/30 relative z-10">
        <div className="flex items-center gap-3 mb-4 animate-fade-in">
          <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center border border-primary/50 text-primary shadow-[0_0_10px_rgba(107,251,154,0.3)]">
            <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
            </svg>
          </div>
          <div>
            <h2 className="font-semibold text-primary">Simulation Core</h2>
            <p className="font-mono text-xs text-primary/70">MapR1 Engine v4.2</p>
          </div>
        </div>
        <button
          onClick={onCreateNode}
          className="w-full py-2 bg-primary/10 text-primary border border-primary/50 rounded font-mono text-sm hover:bg-primary/20 transition-all hover:shadow-[0_0_10px_rgba(107,251,154,0.2)] flex items-center justify-center gap-2"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clipRule="evenodd" />
          </svg>
          New Node
        </button>
      </div>

      {/* Navigation Tabs */}
      <nav className="flex-1 overflow-y-auto py-4 relative z-10">
        <div className="px-3 space-y-1 mb-8">
          <p className="px-4 text-xs font-mono text-primary/50 uppercase mb-2">Navigation</p>

          <button
            onClick={() => onViewChange('scenarios')}
            className={`w-full flex items-center gap-3 px-4 py-3 font-mono text-sm text-left transition-all ${
              activeView === 'scenarios'
                ? 'bg-primary/20 text-primary border-r-2 border-primary shadow-[inset_0_0_10px_rgba(107,251,154,0.1)]'
                : 'text-primary/70 hover:bg-primary/10 hover:text-primary'
            }`}
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M2 6a2 2 0 012-2h5l2 2h5a2 2 0 012 2v6a2 2 0 01-2 2H4a2 2 0 01-2-2V6z" />
            </svg>
            Scenarios
          </button>

          <button
            onClick={() => onViewChange('entities')}
            className={`w-full flex items-center gap-3 px-4 py-3 font-mono text-sm text-left transition-all ${
              activeView === 'entities'
                ? 'bg-primary/20 text-primary border-r-2 border-primary shadow-[inset_0_0_10px_rgba(107,251,154,0.1)]'
                : 'text-primary/70 hover:bg-primary/10 hover:text-primary'
            }`}
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
            </svg>
            Entities
          </button>

          <button
            onClick={() => onViewChange('agents')}
            className={`w-full flex items-center gap-3 px-4 py-3 font-mono text-sm text-left transition-all ${
              activeView === 'agents'
                ? 'bg-primary/20 text-primary border-r-2 border-primary shadow-[inset_0_0_10px_rgba(107,251,154,0.1)]'
                : 'text-primary/70 hover:bg-primary/10 hover:text-primary'
            }`}
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
            </svg>
            Agents
          </button>
        </div>

        {/* Scenario List */}
        {activeView === 'scenarios' && (
          <div className="px-3 space-y-2">
            <p className="px-4 text-xs font-mono text-primary/50 uppercase mb-2">
              Active Nodes ({scenarios.length})
            </p>

            {scenarios.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <p className="text-sm text-primary/60 font-mono">No scenarios yet</p>
                <p className="text-xs text-primary/40 mt-2">Generate scenarios to begin</p>
              </div>
            ) : (
              scenarios.map((scenario, idx) => (
                <div
                  key={scenario.id}
                  onClick={() => setSelectedScenario(scenario)}
                  className={`list-item animate-slide-in glass-panel p-3 mx-2 rounded-lg cursor-pointer transition-all border-l-2 ${getCategoryColor(scenario.category)} ${
                    selectedScenario?.id === scenario.id
                      ? 'bg-primary/20 shadow-[0_0_15px_rgba(107,251,154,0.2)]'
                      : 'hover:bg-primary/10'
                  }`}
                  style={{ animationDelay: `${idx * 0.05}s` }}
                >
                  <div className="flex justify-between items-start mb-1">
                    <h3 className="font-semibold text-sm">{scenario.title}</h3>
                    <span className="font-mono text-xs animate-pulse">
                      {((scenario.probability || 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                  <p className="font-mono text-[10px] text-primary/60">
                    {scenario.category.toUpperCase()} • {scenario.timeline?.length || 0} events
                  </p>
                </div>
              ))
            )}
          </div>
        )}

        {/* Entities List */}
        {activeView === 'entities' && (
          <div className="px-3 space-y-2">
            <p className="px-4 text-xs font-mono text-primary/50 uppercase mb-2">
              Entities ({entities.length})
            </p>

            {entities.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <p className="text-sm text-primary/60 font-mono">No entities yet</p>
                <p className="text-xs text-primary/40 mt-2">Create entities to populate your world</p>
              </div>
            ) : (
              entities.map((entity) => (
                <div
                  key={entity.id}
                  onClick={() => setSelectedEntity(entity)}
                  className={`glass-panel p-3 mx-2 rounded-lg cursor-pointer transition-all border-l-2 ${
                    selectedEntity?.id === entity.id
                      ? 'border-l-primary bg-primary/20 shadow-[0_0_15px_rgba(107,251,154,0.2)]'
                      : 'border-l-primary/40 hover:bg-primary/10'
                  }`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <h3 className="font-semibold text-sm text-primary">{entity.name}</h3>
                    <span className="font-mono text-[10px] text-primary/60 uppercase">
                      {entity.type}
                    </span>
                  </div>
                  {entity.description && (
                    <p className="font-mono text-[10px] text-primary/50 line-clamp-2">
                      {entity.description}
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        )}

        {/* Agents List */}
        {activeView === 'agents' && (
          <div className="px-3 space-y-2">
            <p className="px-4 text-xs font-mono text-primary/50 uppercase mb-2">
              Agents ({agents.length})
            </p>

            {agents.length === 0 ? (
              <div className="px-4 py-8 text-center">
                <p className="text-sm text-primary/60 font-mono">No agents yet</p>
                <p className="text-xs text-primary/40 mt-2">Create agents to simulate behavior</p>
              </div>
            ) : (
              agents.map((agent) => (
                <div
                  key={agent.id}
                  onClick={() => setSelectedAgent(agent)}
                  className={`glass-panel p-3 mx-2 rounded-lg cursor-pointer transition-all border-l-2 ${
                    selectedAgent?.id === agent.id
                      ? 'border-l-primary bg-primary/20 shadow-[0_0_15px_rgba(107,251,154,0.2)]'
                      : 'border-l-primary/40 hover:bg-primary/10'
                  }`}
                >
                  <div className="flex justify-between items-start mb-1">
                    <h3 className="font-semibold text-sm text-primary">{agent.name}</h3>
                    <span className="font-mono text-[10px] text-primary/60 uppercase">
                      {agent.agent_type}
                    </span>
                  </div>
                  <p className="font-mono text-[10px] text-primary/50">
                    {agent.role}
                  </p>
                </div>
              ))
            )}
          </div>
        )}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-primary/30 space-y-1 relative z-10">
        <button
          onClick={onOpenSettings}
          className="w-full flex items-center gap-3 px-4 py-2 text-primary/70 hover:bg-primary/10 hover:text-primary font-mono text-sm text-left transition-all rounded"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
          </svg>
          Settings
        </button>
        <button
          onClick={onOpenLogs}
          className="w-full flex items-center gap-3 px-4 py-2 text-primary/70 hover:bg-primary/10 hover:text-primary font-mono text-sm text-left transition-all rounded"
        >
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M2 5a2 2 0 012-2h12a2 2 0 012 2v10a2 2 0 01-2 2H4a2 2 0 01-2-2V5zm3.293 1.293a1 1 0 011.414 0l3 3a1 1 0 010 1.414l-3 3a1 1 0 01-1.414-1.414L7.586 10 5.293 7.707a1 1 0 010-1.414zM11 12a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
          </svg>
          Logs
        </button>
      </div>
    </aside>
  );
}
