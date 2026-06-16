/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // MapR1 Cyber-Tactical Green Theme
        'obsidian-base': '#0a0a0a',
        'obsidian-darker': '#050505',
        'obsidian-lighter': '#131313',
        'surface': '#131313',
        'surface-dim': '#0a0a0a',
        'surface-bright': '#1a1a1a',
        'neon-green': '#6bfb9a',
        'primary': '#6bfb9a',
        'primary-dark': '#4ade80',
        'primary-darker': '#10b981',
        
        // Scenario colors
        'scenario-optimistic': '#10B981',
        'scenario-pessimistic': '#EF4444',
        'scenario-mixed': '#8B5CF6',
        'scenario-neutral': '#6B7280',
        
        // Agent category colors
        'agent-business': '#F59E0B',
        'agent-government': '#3B82F6',
        'agent-military': '#DC2626',
        'agent-social': '#10B981',
        'agent-criminal': '#7C3AED',
        'agent-science': '#06B6D4',
        'agent-media': '#EC4899',
        'agent-logistics': '#F97316',
        'agent-healthcare': '#FFFFFF',
        'agent-personal': '#A3A3A3',
        
        // Relationship colors
        'rel-ally': '#10B981',
        'rel-enemy': '#EF4444',
        'rel-neutral': '#6B7280',
        'rel-trade': '#F59E0B',
        'rel-mentor': '#3B82F6',
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
        'mono': ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'float': 'float 3s ease-in-out infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-10px)' },
        },
        glow: {
          'from': { boxShadow: '0 0 5px rgba(107, 251, 154, 0.4)' },
          'to': { boxShadow: '0 0 20px rgba(107, 251, 154, 0.8), 0 0 30px rgba(107, 251, 154, 0.6)' },
        },
      },
    },
  },
  plugins: [],
}
