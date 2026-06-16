import { create } from 'zustand';
import type { AgentAction, EmergentPattern, SimulationStatus } from '../types';
import { simulationAPI, patternAPI } from '../services/api';

interface SimulationStore {
  status: SimulationStatus | null;
  actions: AgentAction[];
  recentActions: AgentAction[];
  patterns: EmergentPattern[];
  isLoading: boolean;
  error: string | null;
  
  fetchStatus: (projectId: string) => Promise<void>;
  runStep: (projectId: string) => Promise<void>;
  startSimulation: (projectId: string) => Promise<void>;
  stopSimulation: (projectId: string) => Promise<void>;
  fetchHistory: (projectId: string) => Promise<void>;
  fetchPatterns: (projectId: string) => Promise<void>;
  detectPatterns: (projectId: string) => Promise<void>;
}

export const useSimulationStore = create<SimulationStore>((set, get) => ({
  status: null,
  actions: [],
  recentActions: [],
  patterns: [],
  isLoading: false,
  error: null,

  fetchStatus: async (projectId) => {
    try {
      const response = await simulationAPI.status(projectId);
      set({ status: response.data });
    } catch (error: any) {
      set({ error: error.message });
    }
  },

  runStep: async (projectId) => {
    set({ isLoading: true, error: null });
    try {
      const response = await simulationAPI.step(projectId);
      const newActions = response.data.actions;
      
      set((state) => ({
        actions: [...state.actions, ...newActions],
        recentActions: [...newActions, ...state.recentActions].slice(0, 20), // Keep last 20
        isLoading: false,
      }));
      
      // Fetch updated status
      await get().fetchStatus(projectId);
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
      throw error;
    }
  },

  startSimulation: async (projectId) => {
    set({ isLoading: true, error: null });
    try {
      await simulationAPI.start(projectId);
      set({ isLoading: false });
      
      // Poll status
      const pollInterval = setInterval(async () => {
        const status = await simulationAPI.status(projectId);
        set({ status: status.data });
        
        if (!status.data.is_running) {
          clearInterval(pollInterval);
          await get().fetchHistory(projectId);
          await get().fetchPatterns(projectId);
        }
      }, 2000);
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
      throw error;
    }
  },

  stopSimulation: async (projectId) => {
    try {
      await simulationAPI.stop(projectId);
      await get().fetchStatus(projectId);
    } catch (error: any) {
      set({ error: error.message });
      throw error;
    }
  },

  fetchHistory: async (projectId) => {
    try {
      const response = await simulationAPI.history(projectId);
      set({ 
        actions: response.data,
        recentActions: response.data.slice(0, 20)
      });
    } catch (error: any) {
      set({ error: error.message });
    }
  },

  fetchPatterns: async (projectId) => {
    try {
      const response = await patternAPI.list(projectId);
      set({ patterns: response.data });
    } catch (error: any) {
      set({ error: error.message });
    }
  },

  detectPatterns: async (projectId) => {
    set({ isLoading: true, error: null });
    try {
      const response = await patternAPI.detect(projectId);
      set({ patterns: response.data, isLoading: false });
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
      throw error;
    }
  },
}));
