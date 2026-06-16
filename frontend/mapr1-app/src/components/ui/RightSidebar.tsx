import { useScenarioStore } from '../../stores/scenarioStore';
import { useSimulationStore } from '../../stores/simulationStore';

export default function RightSidebar() {
  const { selectedScenario } = useScenarioStore();
  const { patterns, actions } = useSimulationStore();

  return (
    <aside className="fixed top-16 right-0 bottom-8 w-80 z-40 frost-sidebar pointer-events-auto hidden lg:block overflow-y-auto sidebar-overlay-right">
      <div className="p-4 space-y-4 pt-6">
        {/* Node Details Panel */}
        <div className="glass-panel rounded-xl p-5 border-t border-t-primary/50 relative overflow-hidden">
          <div className="scan-line" />
          {selectedScenario ? (
            <div className="relative z-[1]">
              <div className="flex items-center gap-2 mb-3 pb-2 border-b border-primary/30">
                <svg className="w-5 h-5 text-primary" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
                  <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
                </svg>
                <h3 className="font-mono text-sm text-primary font-semibold">Node Details</h3>
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
                    <div className="space-y-2 max-h-40 overflow-y-auto">
                      {selectedScenario.timeline.slice(0, 5).map((event, idx) => (
                        <div key={idx} className="text-xs">
                          <span className="font-mono text-primary font-semibold">{event.year}</span>
                          <span className="text-primary/70 ml-2">{event.description}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col justify-center items-center text-center py-8 relative z-[1]">
              <svg className="w-12 h-12 text-primary/70 mb-3 drop-shadow-[0_0_5px_rgba(107,251,154,0.5)]" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
              </svg>
              <p className="font-mono text-sm text-primary/90">Click any node to explore</p>
              <p className="font-mono text-[10px] text-primary/60 mt-2 animate-pulse">
                Awaiting target lock...
              </p>
            </div>
          )}
        </div>

        {/* Emergent Patterns Panel */}
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

        {/* Recent Actions Panel */}
        {actions.length > 0 && (
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
