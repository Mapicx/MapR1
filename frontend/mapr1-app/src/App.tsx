import { useEffect, useState } from 'react';
import Scene3D from './components/Scene3D';
import TopBar from './components/ui/TopBar';
import LeftSidebar from './components/ui/LeftSidebar';
import RightSidebarEnhanced from './components/ui/RightSidebarEnhanced';
import WorldStatsDashboard from './components/ui/WorldStateDashboard';
import AgentDecisionPanel from './components/ui/AgentDecisionPanel';
import { useProjectStore } from './stores/projectStore';
import { useScenarioStore } from './stores/scenarioStore';
import { useSimulationStore } from './stores/simulationStore';
import { useWebSocket } from './hooks/useWebSocket';
import type { AgentAction } from './types';

type ViewType = 'scenarios' | 'entities' | 'agents';

function App() {
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [activeView, setActiveView] = useState<ViewType>('scenarios');
  const [showCreateNode, setShowCreateNode] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showLogs, setShowLogs] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [currentDecision, setCurrentDecision] = useState<AgentAction | null>(null);

  const { currentProject, fetchProjects, setCurrentProject } = useProjectStore();
  const { fetchScenarios } = useScenarioStore();
  const { recentActions } = useSimulationStore();

  // WebSocket connection (enabled by default, will gracefully fail if backend doesn't support it)
  const [wsEnabled, setWsEnabled] = useState(true);
  const { connected: wsConnected } = useWebSocket(currentProject?.id || null, wsEnabled);

  // Show decision panel for new actions
  useEffect(() => {
    if (recentActions.length > 0 && !recentActions[0].executed) {
      setCurrentDecision(recentActions[0]);
    }
  }, [recentActions]);

  // Load projects on mount
  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  // Load scenarios when project changes
  useEffect(() => {
    if (currentProject) {
      fetchScenarios(currentProject.id);
    }
  }, [currentProject, fetchScenarios]);

  // Show project selector if no project is selected
  useEffect(() => {
    if (!currentProject) {
      setShowProjectModal(true);
    }
  }, [currentProject]);

  return (
    <div className="h-screen w-screen bg-obsidian-base overflow-hidden flex flex-col relative">
      {/* 3D Scene - Full screen background */}
      <div className="absolute inset-0 z-0">
        <Scene3D activeView={activeView} />
      </div>

      {/* Top Bar - Overlay */}
      <TopBar
        activeView={activeView}
        onViewChange={setActiveView}
        onProjectClick={() => setShowProjectModal(true)}
        onOpenDashboard={() => setShowDashboard(true)}
      />

      {/* Main Content Area with Sidebars as Overlays */}
      <div className="flex-1 flex overflow-hidden relative z-10">
        {/* Left Sidebar - Overlay */}
        <LeftSidebar
          activeView={activeView}
          onViewChange={setActiveView}
          onCreateNode={() => setShowCreateNode(true)}
          onOpenSettings={() => setShowSettings(true)}
          onOpenLogs={() => setShowLogs(true)}
        />

        {/* Right Sidebar - Overlay */}
        <RightSidebarEnhanced />
      </div>

      {/* Bottom Live Ticker Bar */}
      <div className="fixed bottom-0 left-0 w-full z-50 h-8 frost-navbar border-t border-primary/40 flex items-center px-4 gap-4 pointer-events-auto">
        <span className="text-primary animate-pulse font-bold font-mono text-xs drop-shadow-[0_0_5px_rgba(107,251,154,0.8)] z-10 shrink-0">
          ● LIVE
        </span>
        
        {/* WebSocket Status */}
        <div className="flex items-center gap-2">
          <button
            onClick={() => setWsEnabled(!wsEnabled)}
            className={`text-[10px] font-mono px-2 py-0.5 rounded transition-all ${
              wsEnabled
                ? wsConnected
                  ? 'bg-scenario-optimistic/20 text-scenario-optimistic border border-scenario-optimistic/50'
                  : 'bg-scenario-pessimistic/20 text-scenario-pessimistic border border-scenario-pessimistic/50'
                : 'bg-primary/10 text-primary/50 border border-primary/30'
            }`}
            title={wsEnabled ? (wsConnected ? 'WebSocket Connected' : 'WebSocket Disconnected') : 'WebSocket Disabled'}
          >
            WS: {wsEnabled ? (wsConnected ? 'ON' : 'OFF') : 'DISABLED'}
          </button>
        </div>

        <div className="flex-1 ticker-wrap">
          <div className="ticker font-mono text-xs text-primary/80">
            {recentActions.length > 0 ? (
              recentActions.slice(0, 10).map((action, i) => (
                <span key={action.id}>
                  <span className="text-primary/50 mr-2">
                    {new Date(action.timestamp || action.created_at).toLocaleTimeString()}
                  </span>
                  <span className="text-primary font-bold">[{action.action_type}]</span>{' '}
                  {action.description || `Agent action executed`}
                  {i < recentActions.length - 1 && <span className="text-primary/30 mx-4">|</span>}
                </span>
              ))
            ) : (
              <>
                <span className="text-primary/50 mr-2">--:--:--</span>
                <span className="text-primary font-bold">[SYSTEM]</span> Awaiting simulation start...
                <span className="text-primary/30 mx-4">|</span>
                <span className="text-primary/50 mr-2">--:--:--</span>
                <span className="text-primary font-bold">[INFO]</span> Generate scenarios to begin
              </>
            )}
          </div>
        </div>
      </div>

      {/* Project Selection Modal */}
      {showProjectModal && (
        <ProjectModal onClose={() => setShowProjectModal(false)} />
      )}

      {/* Create Node Modal */}
      {showCreateNode && (
        <CreateNodeModal
          activeView={activeView}
          onClose={() => setShowCreateNode(false)}
        />
      )}

      {/* Settings Panel */}
      {showSettings && (
        <SettingsPanel onClose={() => setShowSettings(false)} />
      )}

      {/* Logs Panel */}
      {showLogs && (
        <LogsPanel onClose={() => setShowLogs(false)} />
      )}

      {/* World State Dashboard */}
      {showDashboard && (
        <WorldStatsDashboard onClose={() => setShowDashboard(false)} />
      )}

      {/* Agent Decision Floating Panel */}
      {currentDecision && (
        <AgentDecisionPanel
          action={currentDecision}
          onClose={() => setCurrentDecision(null)}
        />
      )}
    </div>
  );
}

// ============================================
// Project Selection Modal Component
// ============================================
function ProjectModal({ onClose }: { onClose: () => void }) {
  const { projects, createProject, setCurrentProject, loading } = useProjectStore();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    description: '',
  });

  const handleCreate = async () => {
    if (!formData.name.trim()) return;

    const newProject = await createProject(formData.name, formData.description);
    if (newProject) {
      setCurrentProject(newProject);
      onClose();
    }
  };

  const handleSelectProject = (project: any) => {
    setCurrentProject(project);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="glass-panel w-full max-w-2xl max-h-[80vh] overflow-y-auto m-4">
        <div className="p-6 border-b border-neon-green/20">
          <h2 className="text-2xl font-bold text-neon-green neon-glow">
            {showCreateForm ? 'Create New Project' : 'Select Project'}
          </h2>
        </div>

        <div className="p-6">
          {showCreateForm ? (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-mono uppercase tracking-wider text-gray-400 mb-2">
                  Project Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full bg-obsidian-darker border border-gray-700 focus:border-neon-green px-4 py-2 text-white outline-none transition-colors"
                  placeholder="Enter project name..."
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-mono uppercase tracking-wider text-gray-400 mb-2">
                  Description (Optional)
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full bg-obsidian-darker border border-gray-700 focus:border-neon-green px-4 py-2 text-white outline-none transition-colors resize-none"
                  rows={3}
                  placeholder="Enter project description..."
                />
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  onClick={handleCreate}
                  disabled={!formData.name.trim() || loading}
                  className="flex-1 px-4 py-2 bg-neon-green/10 border border-neon-green text-neon-green font-mono uppercase tracking-wider hover:bg-neon-green/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  {loading ? 'Creating...' : 'Create Project'}
                </button>
                <button
                  onClick={() => setShowCreateForm(false)}
                  className="px-4 py-2 border border-gray-700 text-gray-400 font-mono uppercase tracking-wider hover:border-gray-500 hover:text-gray-300 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <>
              {projects.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-gray-400 mb-6">No projects found. Create your first project to get started.</p>
                  <button
                    onClick={() => setShowCreateForm(true)}
                    className="px-6 py-3 bg-neon-green/10 border border-neon-green text-neon-green font-mono uppercase tracking-wider hover:bg-neon-green/20 transition-colors"
                  >
                    Create Project
                  </button>
                </div>
              ) : (
                <>
                  <div className="grid gap-3 mb-6">
                    {projects.map((project) => (
                      <button
                        key={project.id}
                        onClick={() => handleSelectProject(project)}
                        className="text-left p-4 bg-obsidian-darker border border-gray-700 hover:border-neon-green/50 transition-colors group"
                      >
                        <h3 className="text-lg font-semibold text-white group-hover:text-neon-green transition-colors">
                          {project.name}
                        </h3>
                        {project.description && (
                          <p className="text-sm text-gray-400 mt-1">{project.description}</p>
                        )}
                        <div className="flex gap-4 mt-2 text-xs font-mono text-gray-500">
                          <span>Created: {new Date(project.created_at).toLocaleDateString()}</span>
                        </div>
                      </button>
                    ))}
                  </div>

                  <button
                    onClick={() => setShowCreateForm(true)}
                    className="w-full px-4 py-2 border border-neon-green/30 text-neon-green/70 font-mono uppercase tracking-wider hover:border-neon-green hover:text-neon-green transition-colors"
                  >
                    + New Project
                  </button>
                </>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ============================================
// Create Node Modal Component
// ============================================
function CreateNodeModal({
  activeView,
  onClose,
}: {
  activeView: ViewType;
  onClose: () => void;
}) {
  const { currentProject } = useProjectStore();
  const { generateScenarios } = useScenarioStore();
  const [prompt, setPrompt] = useState('');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [nodeType, setNodeType] = useState(activeView === 'entities' ? 'nation' : 'analyst');
  const [loading, setLoading] = useState(false);

  const handleCreateScenario = async () => {
    if (!currentProject || !prompt.trim()) return;
    setLoading(true);
    try {
      await generateScenarios(currentProject.id, prompt);
      onClose();
    } catch (e) {
      console.error('Failed to generate scenarios:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateEntity = async () => {
    if (!currentProject || !name.trim()) return;
    setLoading(true);
    try {
      const { entityAPI } = await import('./services/api');
      await entityAPI.create(currentProject.id, {
        name,
        description,
        type: nodeType as any,
        attributes: {},
      });
      // Refresh entities
      useProjectStore.getState().fetchEntities(currentProject.id);
      onClose();
    } catch (e) {
      console.error('Failed to create entity:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAgent = async () => {
    if (!currentProject || !name.trim()) return;
    setLoading(true);
    try {
      const { agentAPI } = await import('./services/api');
      await agentAPI.create(currentProject.id, {
        name,
        role: description || 'Default role',
        agent_type: nodeType,
      } as any);
      // Refresh agents
      useProjectStore.getState().fetchAgents(currentProject.id);
      onClose();
    } catch (e) {
      console.error('Failed to create agent:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = () => {
    if (activeView === 'scenarios') handleCreateScenario();
    else if (activeView === 'entities') handleCreateEntity();
    else handleCreateAgent();
  };

  const getTitle = () => {
    if (activeView === 'scenarios') return 'Generate Scenarios';
    if (activeView === 'entities') return 'Create Entity';
    return 'Create Agent';
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="glass-panel w-full max-w-lg m-4 relative overflow-hidden">
        <div className="scan-line" />
        <div className="p-6 border-b border-primary/20 relative z-[1]">
          <h2 className="text-xl font-bold text-primary neon-glow">{getTitle()}</h2>
        </div>
        <div className="p-6 space-y-4 relative z-[1]">
          {activeView === 'scenarios' ? (
            <div>
              <label className="block text-sm font-mono uppercase tracking-wider text-primary/60 mb-2">
                Scenario Prompt
              </label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                className="w-full bg-obsidian-darker border border-primary/30 focus:border-primary px-4 py-2 text-white outline-none transition-colors resize-none font-mono text-sm"
                rows={4}
                placeholder="Describe the scenario to generate..."
                autoFocus
              />
            </div>
          ) : (
            <>
              <div>
                <label className="block text-sm font-mono uppercase tracking-wider text-primary/60 mb-2">
                  Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full bg-obsidian-darker border border-primary/30 focus:border-primary px-4 py-2 text-white outline-none transition-colors font-mono text-sm"
                  placeholder={`Enter ${activeView === 'entities' ? 'entity' : 'agent'} name...`}
                  autoFocus
                />
              </div>
              <div>
                <label className="block text-sm font-mono uppercase tracking-wider text-primary/60 mb-2">
                  {activeView === 'entities' ? 'Description' : 'Role'}
                </label>
                <input
                  type="text"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full bg-obsidian-darker border border-primary/30 focus:border-primary px-4 py-2 text-white outline-none transition-colors font-mono text-sm"
                  placeholder={activeView === 'entities' ? 'Enter description...' : 'Enter role...'}
                />
              </div>
              <div>
                <label className="block text-sm font-mono uppercase tracking-wider text-primary/60 mb-2">
                  Type
                </label>
                <select
                  value={nodeType}
                  onChange={(e) => setNodeType(e.target.value)}
                  className="w-full bg-obsidian-darker border border-primary/30 focus:border-primary px-4 py-2 text-white outline-none transition-colors font-mono text-sm"
                  style={{ backgroundColor: '#050505', color: '#ffffff' }}
                >
                  {activeView === 'entities' ? (
                    <>
                      <option value="nation" style={{ backgroundColor: '#050505', color: '#ffffff' }}>Nation</option>
                      <option value="person" style={{ backgroundColor: '#050505', color: '#ffffff' }}>Person</option>
                      <option value="company" style={{ backgroundColor: '#050505', color: '#ffffff' }}>Company</option>
                      <option value="faction" style={{ backgroundColor: '#050505', color: '#ffffff' }}>Faction</option>
                    </>
                  ) : (
                    <>
                      <option value="analyst" style={{ backgroundColor: '#050505', color: '#ffffff' }}>Analyst</option>
                      <option value="strategist" style={{ backgroundColor: '#050505', color: '#ffffff' }}>Strategist</option>
                      <option value="diplomat" style={{ backgroundColor: '#050505', color: '#ffffff' }}>Diplomat</option>
                      <option value="operative" style={{ backgroundColor: '#050505', color: '#ffffff' }}>Operative</option>
                    </>
                  )}
                </select>
              </div>
            </>
          )}

          <div className="flex gap-3 pt-2">
            <button
              onClick={handleSubmit}
              disabled={loading || (activeView === 'scenarios' ? !prompt.trim() : !name.trim())}
              className="flex-1 px-4 py-2 bg-primary/10 border border-primary text-primary font-mono uppercase tracking-wider text-sm hover:bg-primary/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all hover:shadow-[0_0_10px_rgba(107,251,154,0.3)]"
            >
              {loading ? 'Processing...' : activeView === 'scenarios' ? 'Generate' : 'Create'}
            </button>
            <button
              onClick={onClose}
              className="px-4 py-2 border border-gray-700 text-gray-400 font-mono uppercase tracking-wider text-sm hover:border-gray-500 hover:text-gray-300 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ============================================
// Settings Panel Component
// ============================================
function SettingsPanel({ onClose }: { onClose: () => void }) {
  const [apiUrl, setApiUrl] = useState(
    import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'
  );

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="glass-panel w-full max-w-lg m-4 relative overflow-hidden">
        <div className="scan-line" />
        <div className="p-6 border-b border-primary/20 flex justify-between items-center relative z-[1]">
          <h2 className="text-xl font-bold text-primary neon-glow">Settings</h2>
          <button
            onClick={onClose}
            className="text-primary/60 hover:text-primary transition-colors"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
        <div className="p-6 space-y-6 relative z-[1]">
          {/* API Configuration */}
          <div>
            <h3 className="font-mono text-sm text-primary/80 uppercase tracking-wider mb-3">
              API Configuration
            </h3>
            <div>
              <label className="block text-xs font-mono text-primary/50 mb-1">
                Backend URL
              </label>
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                className="w-full bg-obsidian-darker border border-primary/30 focus:border-primary px-3 py-2 text-white outline-none transition-colors font-mono text-sm"
              />
            </div>
          </div>

          {/* Display Settings */}
          <div>
            <h3 className="font-mono text-sm text-primary/80 uppercase tracking-wider mb-3">
              Display
            </h3>
            <div className="space-y-2">
              <label className="flex items-center gap-3 text-sm text-primary/70 cursor-pointer hover:text-primary transition-colors">
                <input type="checkbox" defaultChecked className="accent-neon-green" />
                <span className="font-mono">Show grid overlay</span>
              </label>
              <label className="flex items-center gap-3 text-sm text-primary/70 cursor-pointer hover:text-primary transition-colors">
                <input type="checkbox" defaultChecked className="accent-neon-green" />
                <span className="font-mono">Enable scan-line effects</span>
              </label>
              <label className="flex items-center gap-3 text-sm text-primary/70 cursor-pointer hover:text-primary transition-colors">
                <input type="checkbox" defaultChecked className="accent-neon-green" />
                <span className="font-mono">Node label tooltips</span>
              </label>
            </div>
          </div>

          {/* Simulation Settings */}
          <div>
            <h3 className="font-mono text-sm text-primary/80 uppercase tracking-wider mb-3">
              Simulation
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-mono text-primary/50 mb-1">Max Steps</label>
                <input
                  type="number"
                  defaultValue={10}
                  className="w-full bg-obsidian-darker border border-primary/30 focus:border-primary px-3 py-2 text-white outline-none transition-colors font-mono text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-mono text-primary/50 mb-1">Step Delay (s)</label>
                <input
                  type="number"
                  defaultValue={1.0}
                  step={0.1}
                  className="w-full bg-obsidian-darker border border-primary/30 focus:border-primary px-3 py-2 text-white outline-none transition-colors font-mono text-sm"
                />
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="w-full px-4 py-2 bg-primary/10 border border-primary text-primary font-mono uppercase tracking-wider text-sm hover:bg-primary/20 transition-all"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================
// Logs Panel Component
// ============================================
function LogsPanel({ onClose }: { onClose: () => void }) {
  const { actions, recentActions } = useSimulationStore();
  const displayActions = recentActions.length > 0 ? recentActions : actions;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="glass-panel w-full max-w-3xl max-h-[80vh] m-4 flex flex-col relative overflow-hidden">
        <div className="scan-line" />
        <div className="p-4 border-b border-primary/20 flex justify-between items-center relative z-[1]">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-bold text-primary neon-glow">System Logs</h2>
            <div className="flex items-center gap-2 px-2 py-0.5 glass-panel rounded-full text-xs">
              <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse shadow-[0_0_5px_rgba(107,251,154,1)]" />
              <span className="font-mono text-primary/80">LIVE</span>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-primary/60 hover:text-primary transition-colors"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 font-mono text-sm relative z-[1]">
          {displayActions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="w-16 h-16 rounded-full border-2 border-dashed border-primary/40 animate-[spin_8s_linear_infinite] flex items-center justify-center mb-4">
                <div className="w-2 h-2 bg-primary rounded-full shadow-[0_0_8px_rgba(107,251,154,1)]" />
              </div>
              <p className="text-primary/60">No simulation actions recorded yet.</p>
              <p className="text-primary/40 text-xs mt-1">Run a simulation step to see logs here.</p>
            </div>
          ) : (
            <div className="space-y-1">
              {displayActions.map((action, idx) => (
                <div
                  key={action.id || idx}
                  className="flex items-start gap-3 py-1.5 px-2 hover:bg-primary/5 rounded transition-colors group"
                >
                  <span className="text-primary/40 text-[10px] shrink-0 pt-0.5">
                    {action.created_at
                      ? new Date(action.created_at).toLocaleTimeString()
                      : `STEP ${action.simulation_step}`}
                  </span>
                  <span
                    className={`shrink-0 text-[10px] font-bold px-1 py-0.5 rounded ${
                      action.success
                        ? 'text-scenario-optimistic bg-scenario-optimistic/10'
                        : action.success === false
                        ? 'text-scenario-pessimistic bg-scenario-pessimistic/10'
                        : 'text-primary bg-primary/10'
                    }`}
                  >
                    {action.success ? 'OK' : action.success === false ? 'FAIL' : 'LOG'}
                  </span>
                  <div className="flex-1 min-w-0">
                    <span className="text-primary font-semibold">[{action.agent_name}]</span>{' '}
                    <span className="text-primary/70">
                      {action.action_type.replace(/_/g, ' ')}
                    </span>
                    {action.description && (
                      <span className="text-primary/50 block text-xs mt-0.5 truncate group-hover:whitespace-normal">
                        {action.description}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
