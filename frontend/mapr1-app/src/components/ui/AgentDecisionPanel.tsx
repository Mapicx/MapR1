import { useEffect, useState } from 'react';
import type { AgentAction } from '../../types';

interface AgentDecisionPanelProps {
  action: AgentAction;
  onClose: () => void;
}

export default function AgentDecisionPanel({ action, onClose }: AgentDecisionPanelProps) {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    // Animate progress bar
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) {
          clearInterval(interval);
          setTimeout(onClose, 1000); // Auto-close after completion
          return 100;
        }
        return prev + 2;
      });
    }, 50);

    return () => clearInterval(interval);
  }, [onClose]);

  const getConfidenceColor = (confidence: number) => {
    if (confidence > 0.7) return 'text-scenario-optimistic';
    if (confidence < 0.4) return 'text-scenario-pessimistic';
    return 'text-primary';
  };

  return (
    <div className="fixed bottom-24 right-4 w-96 z-50 animate-slide-in">
      <div className="glass-panel rounded-xl p-5 border-t-2 border-t-primary shadow-[0_0_30px_rgba(107,251,154,0.3)] relative overflow-hidden">
        <div className="scan-line" />
        
        <div className="relative z-[1]">
          {/* Header */}
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-primary animate-pulse shadow-[0_0_8px_rgba(107,251,154,1)]" />
              <h3 className="font-mono text-sm text-primary font-semibold">Agent Decision</h3>
            </div>
            <button
              onClick={onClose}
              className="text-primary/60 hover:text-primary transition-colors"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>

          {/* Agent Info */}
          <div className="mb-3 pb-3 border-b border-primary/20">
            <p className="font-semibold text-primary">{action.agent_name}</p>
            <p className="text-xs text-primary/70 font-mono mt-0.5">
              {action.action_type.replace(/_/g, ' ').toUpperCase()}
            </p>
          </div>

          {/* Reasoning */}
          <div className="mb-3">
            <p className="text-xs font-mono text-primary/50 uppercase mb-1">Reasoning</p>
            <p className="text-sm text-primary/80 leading-relaxed">{action.reasoning}</p>
          </div>

          {/* Confidence Meter */}
          <div className="mb-3">
            <div className="flex items-center justify-between mb-1">
              <p className="text-xs font-mono text-primary/50 uppercase">Confidence</p>
              <span className={`text-sm font-mono font-bold ${getConfidenceColor(action.confidence)}`}>
                {(action.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <div className="h-2 bg-obsidian-darker rounded-full overflow-hidden">
              <div
                className={`h-full ${getConfidenceColor(action.confidence)} bg-current transition-all`}
                style={{ width: `${action.confidence * 100}%` }}
              />
            </div>
          </div>

          {/* Expected Outcome */}
          {action.outcome && (
            <div className="mb-3 p-3 bg-primary/5 rounded border-l-2 border-primary/40">
              <p className="text-xs font-mono text-primary/50 uppercase mb-1">Expected Outcome</p>
              <p className="text-xs text-primary/70">{action.outcome}</p>
            </div>
          )}

          {/* Execution Progress */}
          <div>
            <div className="flex items-center justify-between mb-1">
              <p className="text-xs font-mono text-primary/50 uppercase">Execution</p>
              <span className="text-xs font-mono text-primary">{progress}%</span>
            </div>
            <div className="h-1.5 bg-obsidian-darker rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all shadow-[0_0_8px_rgba(107,251,154,0.8)]"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Success/Failure Indicator */}
          {progress === 100 && action.executed && (
            <div className={`mt-3 p-2 rounded flex items-center gap-2 ${
              action.success
                ? 'bg-scenario-optimistic/10 border border-scenario-optimistic/30'
                : 'bg-scenario-pessimistic/10 border border-scenario-pessimistic/30'
            }`}>
              {action.success ? (
                <svg className="w-5 h-5 text-scenario-optimistic" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              ) : (
                <svg className="w-5 h-5 text-scenario-pessimistic" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              )}
              <span className={`text-xs font-mono font-semibold ${
                action.success ? 'text-scenario-optimistic' : 'text-scenario-pessimistic'
              }`}>
                {action.success ? 'Action Successful' : 'Action Failed'}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
