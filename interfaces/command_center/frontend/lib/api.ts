import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8200";

export const api = axios.create({
  baseURL: API_URL,
  timeout: 30000,
});

export const ultraAPI = {
  getStatus: () => api.get("/api/status").then((r) => r.data),
  getGraph: () => api.get("/api/graph").then((r) => r.data),
  getLLMStatus: () => api.get("/api/llm/status").then((r) => r.data),
  getLLMModes: () => api.get("/api/llm/modes").then((r) => r.data),
  setMode: (mode: string, password = "") =>
    api.post("/api/llm/set_mode", { mode, password }).then((r) => r.data),
  chat: (message: string) =>
    api.post("/api/chat", { message }).then((r) => r.data),
  serviceAction: (service: string, action: string) =>
    api.post("/api/service/action", { service, action }).then((r) => r.data),
  getLogs: (service: string, lines = 50) =>
    api.get(`/api/logs/${service}?lines=${lines}`).then((r) => r.data),
  listResearch: () => api.get("/api/reports/research").then((r) => r.data),
  getResearch: (name: string) =>
    api.get(`/api/reports/research/${name}`).then((r) => r.data),
  listCode: () => api.get("/api/reports/code").then((r) => r.data),
  getCode: (name: string) =>
    api.get(`/api/reports/code/${name}`).then((r) => r.data),
};
