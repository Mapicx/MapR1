// MapR1 TypeScript Types

export interface Project {
  id: string;
  name: string;
  description?: string;
  created_at: string;
  updated_at: string;
  stats?: {
    scenarios: number;
    entities: number;
    agents: number;
  };
}

export interface Scenario {
  id: string;
  project_id?: string;
  title: string;
  description: string;
  category: 'optimistic' | 'pessimistic' | 'mixed' | 'neutral';
  probability: number;
  timeline: TimelineEvent[];
  created_at: string;
  saved: boolean;
}

export interface TimelineEvent {
  year: number;
  description: string;
  impact: 'low' | 'medium' | 'high';
}

export interface Entity {
  id: string;
  project_id: string;
  type: 'nation' | 'person' | 'company' | 'faction';
  name: string;
  description?: string;
  attributes: Record<string, any>;
  created_at: string;
}

export interface Agent {
  id: string;
  project_id: string;
  entity_id?: string;
  name: string;
  agent_type: string;
  agent_category?: string;
  role: string;
  personality: Personality;
  current_state: Record<string, any>;
  resources: Record<string, any>;
  created_at: string;
  last_active: string;
}

export interface Personality {
  openness: number;
  conscientiousness: number;
  extraversion: number;
  agreeableness: number;
  neuroticism: number;
  risk_tolerance: number;
  ambition: number;
  empathy: number;
  rationality: number;
  creativity: number;
  morality: number;
}

export interface AgentAction {
  id: string;
  agent_id: string;
  agent_name: string;
  action_type: string;
  description: string;
  reasoning: string;
  confidence: number;
  executed: boolean;
  success?: boolean;
  outcome?: string;
  impact: Record<string, any>;
  simulation_step: number;
  created_at: string;
}

export interface EmergentPattern {
  id: string;
  project_id: string;
  pattern_type: string;
  title: string;
  description: string;
  significance: number;
  involved_agent_ids: string[];
  involved_entity_ids: string[];
  evidence: any[];
  first_detected_step: number;
  detected_at: string;
}

export interface SimulationStatus {
  project_id: string;
  is_running: boolean;
  current_step: number;
  total_actions: number;
  started_at?: string;
  last_step_at?: string;
}

export interface AgentRelationship {
  id: string;
  project_id: string;
  source_agent_id: string;
  target_agent_id: string;
  relationship_type: string;
  strength: number; // -1 to 1
  trust: number; // 0 to 1
  influence: number; // -1 to 1
  interaction_count: number;
  last_interaction?: string;
  created_at: string;
  updated_at: string;
}

export interface Goal {
  id: string;
  agent_id: string;
  description: string;
  goal_type: string;
  priority: number;
  progress: number;
  status: 'active' | 'completed' | 'abandoned' | 'blocked';
  created_at: string;
  deadline?: string;
  completed_at?: string;
}

export interface Memory {
  id: string;
  agent_id: string;
  content: string;
  memory_type: string;
  importance: number;
  emotional_valence: number;
  related_agent_ids: string[];
  related_entity_ids: string[];
  created_at: string;
}

export interface WorldState {
  project_id: string;
  current_step: number;
  stability: number;
  economy: number;
  technology_level: number;
  active_conflicts: number;
  total_agents: number;
  total_entities: number;
  entity_types?: Record<string, number>;
  recent_events: string[];
  updated_at: string;
}

// 3D Visualization Types
export interface ScenarioNodeData {
  scenario: Scenario;
  position: [number, number, number];
  isSelected: boolean;
}

export interface EntityNodeData {
  entity: Entity;
  position: [number, number, number];
  orbitRadius: number;
  orbitSpeed: number;
  isSelected: boolean;
}

export interface AgentNodeData {
  agent: Agent;
  entityPosition: [number, number, number];
  orbitRadius: number;
  orbitSpeed: number;
  isActive: boolean;
  isSelected: boolean;
}

export interface RelationshipLineData {
  relationship: AgentRelationship;
  startPos: [number, number, number];
  endPos: [number, number, number];
}
