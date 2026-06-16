import axios from 'axios';
import type {
  Project,
  Scenario,
  Entity,
  Agent,
  AgentAction,
  EmergentPattern,
  SimulationStatus,
  AgentRelationship,
  Goal,
  Memory,
  WorldState,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Projects
export const projectAPI = {
  list: () => api.get<Project[]>('/projects'),
  create: (data: { name: string; description?: string }) => 
    api.post<Project>('/projects', data),
  get: (id: string) => api.get<Project>(`/projects/${id}`),
  update: (id: string, data: { name?: string; description?: string }) => 
    api.put<Project>(`/projects/${id}`, data),
  delete: (id: string) => api.delete(`/projects/${id}`),
};

// Scenarios
export const scenarioAPI = {
  generate: (projectId: string, prompt: string, numScenarios: number = 3) =>
    api.post<{ scenarios: Scenario[] }>(
      `/scenarios/generate?project_id=${projectId}&save=true`,
      { prompt, num_scenarios: numScenarios }
    ),
  list: (projectId?: string) => {
    const url = projectId ? `/scenarios?project_id=${projectId}` : '/scenarios';
    return api.get<Scenario[]>(url);
  },
  get: (id: string) => api.get<Scenario>(`/scenarios/${id}`),
  save: (id: string) => api.post(`/scenarios/${id}/save`),
  delete: (id: string) => api.delete(`/scenarios/${id}`),
};

// Entities
export const entityAPI = {
  list: (projectId: string) => 
    api.get<Entity[]>(`/projects/${projectId}/entities`),
  create: (projectId: string, data: Partial<Entity>) =>
    api.post<Entity>(`/projects/${projectId}/entities`, data),
  get: (id: string) => api.get<Entity>(`/entities/${id}`),
  update: (id: string, data: Partial<Entity>) =>
    api.put<Entity>(`/entities/${id}`, data),
  delete: (id: string) => api.delete(`/entities/${id}`),
};

// Agents
export const agentAPI = {
  list: (projectId: string) =>
    api.get<Agent[]>(`/projects/${projectId}/agents`),
  create: (projectId: string, data: Partial<Agent>) =>
    api.post<Agent>(`/projects/${projectId}/agents`, data),
  get: (id: string) => api.get<Agent>(`/agents/${id}`),
  update: (id: string, data: Partial<Agent>) =>
    api.put<Agent>(`/agents/${id}`, data),
  delete: (id: string) => api.delete(`/agents/${id}`),
  getGoals: (id: string) => api.get<Goal[]>(`/agents/${id}/goals`),
  getMemories: (id: string) => api.get<Memory[]>(`/agents/${id}/memories`),
  getRelationships: (id: string) =>
    api.get<AgentRelationship[]>(`/agents/${id}/relationships`),
};

// Simulation
export const simulationAPI = {
  step: (projectId: string) =>
    api.post<{
      step_number: number;
      actions: AgentAction[];
      events_generated: number;
      patterns_detected: number;
    }>(`/projects/${projectId}/simulate/step`),
  start: (projectId: string, maxSteps: number = 10, stepDelay: number = 1.0) =>
    api.post(`/projects/${projectId}/simulate/start`, {
      max_steps: maxSteps,
      step_delay: stepDelay,
    }),
  stop: (projectId: string) =>
    api.post(`/projects/${projectId}/simulate/stop`),
  status: (projectId: string) =>
    api.get<SimulationStatus>(`/projects/${projectId}/simulate/status`),
  history: (projectId: string, limit: number = 50) =>
    api.get<AgentAction[]>(`/projects/${projectId}/simulation/history?limit=${limit}`),
};

// Patterns
export const patternAPI = {
  detect: (projectId: string, timeWindow: number = 10, minSignificance: number = 0.5) =>
    api.post<EmergentPattern[]>(`/projects/${projectId}/patterns/detect`, {
      time_window: timeWindow,
      min_significance: minSignificance,
    }),
  list: (projectId: string) =>
    api.get<EmergentPattern[]>(`/projects/${projectId}/patterns`),
  get: (id: string) => api.get<EmergentPattern>(`/patterns/${id}`),
};

// World State
export const worldStateAPI = {
  get: (projectId: string) =>
    api.get<WorldState>(`/projects/${projectId}/world-state`),
};

// Relationships
export const relationshipAPI = {
  list: (projectId: string) =>
    api.get<AgentRelationship[]>(`/projects/${projectId}/relationships`),
};

export default api;
