import { useState } from 'react';
import { useProjectStore } from '../../stores/projectStore';
import { useSimulationStore } from '../../stores/simulationStore';

interface TopBarProps {
  activeView: 'scenarios' | 'entities' | 'agents';
  onViewChange: (view: 'scenarios' | 'entities' | 'agents') => void;
  onProjectClick?: () => void;
  onOpenDashboard?: () => void;
}

export default function TopBar({ activeView, onViewChange, onProjectClick, onOpenDashboard }: TopBarProps) {
  const { currentProject } = useProjectStore();
  const { status, runStep, startSimulation, stopSimulation } = useSimulationStore();
  const [speed, setSpeed] = useState(1.0);
  const [autoRun, setAutoRun] = useState(false);
  const [maxSteps, setMaxSteps] = useState(10);

  const handleStep = async () => {
    if (currentProject) {
      await runStep(currentProject.id);
    }
  };

  const handleStart = async () => {
    if (currentProject) {
      await startSimulation(currentProject.id, maxSteps, speed);
      setAutoRun(true);
    }
  };

  const handleStop = async () => {
    if (currentProject) {
      await stopSimulation(currentProject.id);
      setAutoRun(false);
    }
  };

  const speedOptions = [
    { label: '0.5x', value: 2.0 },
    { label: '1x', value: 1.0 },
    { label: '2x', value: 0.5 },
    { label: '5x', value: 0.2 },
    { label: '10x', value: 0.1 },
  ];

  const navItems: { key: 'scenarios' | 'entities' | 'agents'; label: string }[] = [
    { key: 'scenarios', label: 'Scenarios' },
    { key: 'entities', label: 'Entities' },
    { key: 'agents', label: 'Agents' },
  ];

  return (
    <header className="fixed top-0 left-0 w-full z-50 flex justify-between items-center px-4 h-16 frost-navbar border-b border-primary/30 pointer-events-auto shadow-[0_0_20px_rgba(107,251,154,0.15)] fade-slide-in">
      <div className="flex items-center gap-6">
        <span
          className="font-bold text-2xl text-primary logo-pulse tracking-tight cursor-pointer"
          onClick={onProjectClick}
        >
          MapR1
        </span>
        <nav className="flex gap-1 ml-4">
          {navItems.map((item) => (
            <button
              key={item.key}
              onClick={() => onViewChange(item.key)}
              className={`px-4 py-2 font-mono text-sm transition-all rounded ${
                activeView === item.key
                  ? 'text-primary font-bold border-b-2 border-primary'
                  : 'text-primary/70 font-medium hover:text-primary hover:bg-primary/10'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="flex items-center gap-4">
        {/* World State Dashboard Button */}
        <button
          onClick={onOpenDashboard}
          className="p-2 text-primary/70 hover:text-primary hover:bg-primary/20 rounded transition-all"
          title="World State Dashboard"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
            <path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z" />
          </svg>
        </button>

        {/* Simulation Controls */}
        <div className="flex bg-surface-bright/50 rounded-lg p-1 border border-primary/30 gap-1">
          <button
            onClick={handleStart}
            disabled={status?.is_running}
            className="p-2 text-primary/70 hover:text-primary hover:bg-primary/20 rounded transition-all disabled:opacity-50"
            title="Start Simulation"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
            </svg>
          </button>
          <button
            onClick={handleStop}
            disabled={!status?.is_running}
            className="p-2 text-primary/70 hover:text-primary hover:bg-primary/20 rounded transition-all disabled:opacity-50"
            title="Stop Simulation"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8 7a1 1 0 00-1 1v4a1 1 0 001 1h4a1 1 0 001-1V8a1 1 0 00-1-1H8z" clipRule="evenodd" />
            </svg>
          </button>
          <button
            onClick={handleStep}
            disabled={status?.is_running}
            className="p-2 text-primary/70 hover:text-primary hover:bg-primary/20 rounded transition-all disabled:opacity-50"
            title="Run One Step"
          >
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M4.555 5.168A1 1 0 003 6v8a1 1 0 001.555.832L10 11.202V14a1 1 0 001.555.832l6-4a1 1 0 000-1.664l-6-4A1 1 0 0010 6v2.798l-5.445-3.63z" />
            </svg>
          </button>
        </div>

        {/* Speed Control */}
        <div className="flex items-center gap-2 glass-panel px-3 py-1.5 rounded-lg">
          <svg className="w-4 h-4 text-primary/60" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415L11 9.586V6z" clipRule="evenodd" />
          </svg>
          <select
            value={speed}
            onChange={(e) => setSpeed(parseFloat(e.target.value))}
            className="bg-obsidian-darker text-primary font-mono text-xs outline-none cursor-pointer border border-primary/20 rounded px-2 py-1"
            style={{ backgroundColor: '#050505', color: '#6bfb9a' }}
            disabled={status?.is_running}
          >
            {speedOptions.map((opt) => (
              <option key={opt.value} value={opt.value} className="bg-obsidian-darker text-primary" style={{ backgroundColor: '#050505', color: '#6bfb9a' }}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Auto-run Toggle */}
        <div className="flex items-center gap-2 glass-panel px-3 py-1.5 rounded-lg">
          <span className="text-xs font-mono text-primary/60">Auto</span>
          <button
            onClick={() => setAutoRun(!autoRun)}
            className={`relative w-10 h-5 rounded-full transition-colors ${
              autoRun ? 'bg-primary/40' : 'bg-primary/10'
            }`}
          >
            <div
              className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-primary transition-transform ${
                autoRun ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>
        </div>

        {/* Max Steps Input */}
        <div className="flex items-center gap-2 glass-panel px-3 py-1.5 rounded-lg">
          <span className="text-xs font-mono text-primary/60">Steps</span>
          <input
            type="number"
            value={maxSteps}
            onChange={(e) => setMaxSteps(parseInt(e.target.value) || 10)}
            min="1"
            max="1000"
            className="w-12 bg-transparent text-primary font-mono text-xs outline-none text-right"
            disabled={status?.is_running}
          />
        </div>

        {/* Status */}
        {status && (
          <div className="flex items-center gap-2 px-3 py-1 glass-panel rounded-full border-primary/50">
            <div className={`w-2 h-2 rounded-full ${status.is_running ? 'bg-primary animate-pulse shadow-[0_0_8px_rgba(107,251,154,1)]' : 'bg-primary/50'}`} />
            <span className="font-mono text-xs text-primary">
              Step {status.current_step}
            </span>
          </div>
        )}

        {/* Execute Button */}
        <button
          onClick={handleStep}
          className="flex items-center gap-2 bg-primary/20 text-primary px-4 py-2 rounded font-mono text-sm hover:bg-primary/40 hover:shadow-[0_0_15px_rgba(107,251,154,0.4)] transition-all border border-primary/50"
        >
          Execute Sim
        </button>
      </div>
    </header>
  );
}
