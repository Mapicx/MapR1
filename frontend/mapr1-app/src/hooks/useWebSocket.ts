import { useEffect, useState } from 'react';
import { wsService } from '../services/websocket';
import { useSimulationStore } from '../stores/simulationStore';
import type { WorldState, AgentAction, EmergentPattern } from '../types';

export function useWebSocket(projectId: string | null, enabled: boolean = true) {
  const [connected, setConnected] = useState(false);
  const [worldState, setWorldState] = useState<WorldState | null>(null);
  const simulationStore = useSimulationStore();

  useEffect(() => {
    if (!projectId || !enabled) return;

    // Connect to WebSocket
    wsService.connect(projectId);

    // Set up event handlers
    const handleConnected = () => setConnected(true);
    const handleDisconnected = () => setConnected(false);
    
    const handleWorldState = (state: WorldState) => {
      setWorldState(state);
    };

    const handleAction = (action: AgentAction) => {
      // Add action to store
      simulationStore.actions.push(action);
      simulationStore.recentActions.unshift(action);
      if (simulationStore.recentActions.length > 20) {
        simulationStore.recentActions.pop();
      }
    };

    const handlePattern = (pattern: EmergentPattern) => {
      // Add pattern to store
      const exists = simulationStore.patterns.find(p => p.id === pattern.id);
      if (!exists) {
        simulationStore.patterns.push(pattern);
      }
    };

    const handleSimulationStep = (data: any) => {
      if (simulationStore.status) {
        simulationStore.status.current_step = data.step;
      }
    };

    const handleSimulationComplete = () => {
      if (simulationStore.status) {
        simulationStore.status.is_running = false;
      }
    };

    // Register handlers
    wsService.on('connected', handleConnected);
    wsService.on('disconnected', handleDisconnected);
    wsService.on('worldState', handleWorldState);
    wsService.on('action', handleAction);
    wsService.on('pattern', handlePattern);
    wsService.on('simulationStep', handleSimulationStep);
    wsService.on('simulationComplete', handleSimulationComplete);

    // Cleanup
    return () => {
      wsService.off('connected', handleConnected);
      wsService.off('disconnected', handleDisconnected);
      wsService.off('worldState', handleWorldState);
      wsService.off('action', handleAction);
      wsService.off('pattern', handlePattern);
      wsService.off('simulationStep', handleSimulationStep);
      wsService.off('simulationComplete', handleSimulationComplete);
      wsService.disconnect();
    };
  }, [projectId, enabled]);

  return {
    connected,
    worldState,
    send: wsService.send.bind(wsService),
  };
}
