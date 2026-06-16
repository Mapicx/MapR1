import { create } from 'zustand';
import type { Project, Entity, Agent, AgentRelationship } from '../types';
import { projectAPI, entityAPI, agentAPI } from '../services/api';

interface ProjectStore {
  currentProject: Project | null;
  projects: Project[];
  entities: Entity[];
  agents: Agent[];
  relationships: AgentRelationship[];
  selectedEntity: Entity | null;
  selectedAgent: Agent | null;
  loading: boolean;
  error: string | null;
  
  setCurrentProject: (project: Project | null) => void;
  fetchProjects: () => Promise<void>;
  createProject: (name: string, description?: string) => Promise<Project | null>;
  deleteProject: (id: string) => Promise<void>;
  
  fetchEntities: (projectId: string) => Promise<void>;
  fetchAgents: (projectId: string) => Promise<void>;
  fetchRelationships: (agentId: string) => Promise<void>;
  setSelectedEntity: (entity: Entity | null) => void;
  setSelectedAgent: (agent: Agent | null) => void;
}

export const useProjectStore = create<ProjectStore>((set, get) => ({
  currentProject: null,
  projects: [],
  entities: [],
  agents: [],
  relationships: [],
  selectedEntity: null,
  selectedAgent: null,
  loading: false,
  error: null,

  setCurrentProject: (project) => {
    set({ currentProject: project });
    if (project) {
      get().fetchEntities(project.id);
      get().fetchAgents(project.id);
    }
  },

  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const response = await projectAPI.list();
      set({ projects: response.data, loading: false });
    } catch (error: any) {
      set({ error: error.message, loading: false });
    }
  },

  createProject: async (name, description) => {
    set({ loading: true, error: null });
    try {
      const response = await projectAPI.create({ name, description });
      const newProject = response.data;
      set((state) => ({
        projects: [...state.projects, newProject],
        currentProject: newProject,
        loading: false,
      }));
      return newProject;
    } catch (error: any) {
      set({ error: error.message, loading: false });
      return null;
    }
  },

  deleteProject: async (id) => {
    set({ loading: true, error: null });
    try {
      await projectAPI.delete(id);
      set((state) => ({
        projects: state.projects.filter((p) => p.id !== id),
        currentProject: state.currentProject?.id === id ? null : state.currentProject,
        loading: false,
      }));
    } catch (error: any) {
      set({ error: error.message, loading: false });
      throw error;
    }
  },

  fetchEntities: async (projectId) => {
    try {
      const response = await entityAPI.list(projectId);
      set({ entities: response.data });
    } catch (error: any) {
      console.error('Failed to fetch entities:', error);
    }
  },

  fetchAgents: async (projectId) => {
    try {
      const response = await agentAPI.list(projectId);
      set({ agents: response.data });
    } catch (error: any) {
      console.error('Failed to fetch agents:', error);
    }
  },

  fetchRelationships: async (agentId) => {
    try {
      const response = await agentAPI.getRelationships(agentId);
      set({ relationships: response.data });
    } catch (error: any) {
      console.error('Failed to fetch relationships:', error);
    }
  },

  setSelectedEntity: (entity) => set({ selectedEntity: entity }),
  setSelectedAgent: (agent) => set({ selectedAgent: agent }),
}));
