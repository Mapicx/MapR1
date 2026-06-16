import { create } from 'zustand';
import type { Scenario } from '../types';
import { scenarioAPI } from '../services/api';

interface ScenarioStore {
  scenarios: Scenario[];
  selectedScenario: Scenario | null;
  isLoading: boolean;
  error: string | null;
  
  setSelectedScenario: (scenario: Scenario | null) => void;
  fetchScenarios: (projectId: string) => Promise<void>;
  generateScenarios: (projectId: string, prompt: string) => Promise<void>;
  deleteScenario: (id: string) => Promise<void>;
}

export const useScenarioStore = create<ScenarioStore>((set) => ({
  scenarios: [],
  selectedScenario: null,
  isLoading: false,
  error: null,

  setSelectedScenario: (scenario) => set({ selectedScenario: scenario }),

  fetchScenarios: async (projectId) => {
    set({ isLoading: true, error: null });
    try {
      const response = await scenarioAPI.list(projectId);
      set({ scenarios: response.data, isLoading: false });
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
    }
  },

  generateScenarios: async (projectId, prompt) => {
    set({ isLoading: true, error: null });
    try {
      const response = await scenarioAPI.generate(projectId, prompt);
      set((state) => ({
        scenarios: [...state.scenarios, ...response.data.scenarios],
        isLoading: false,
      }));
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
      throw error;
    }
  },

  deleteScenario: async (id) => {
    set({ isLoading: true, error: null });
    try {
      await scenarioAPI.delete(id);
      set((state) => ({
        scenarios: state.scenarios.filter((s) => s.id !== id),
        selectedScenario: state.selectedScenario?.id === id ? null : state.selectedScenario,
        isLoading: false,
      }));
    } catch (error: any) {
      set({ error: error.message, isLoading: false });
      throw error;
    }
  },
}));
