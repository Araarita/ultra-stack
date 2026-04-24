import { create } from "zustand";

export interface Service {
  name: string;
  type: string;
  active: boolean;
  uptime_sec?: number;
  status_text?: string;
}

export interface SystemStatus {
  timestamp: string;
  services: Service[];
  total_active: number;
  total_services: number;
  resources: {
    ram_used_mb: number;
    ram_total_mb: number;
    ram_pct: number;
    disk_pct: number;
    load_avg: number;
  };
}

export interface LLMMode {
  mode: string;
  emoji: string;
  rank: number;
  description: string;
  avg_cost: string;
  cost_level: string;
  intelligence: string;
  speed: string;
  password_required: boolean;
}

interface UltraState {
  status: SystemStatus | null;
  llmMode: LLMMode | null;
  isLoading: boolean;
  setStatus: (s: SystemStatus) => void;
  setLLMMode: (m: LLMMode) => void;
  setLoading: (l: boolean) => void;
}

export const useUltraStore = create<UltraState>((set) => ({
  status: null,
  llmMode: null,
  isLoading: true,
  setStatus: (s) => set({ status: s }),
  setLLMMode: (m) => set({ llmMode: m }),
  setLoading: (l) => set({ isLoading: l }),
}));
