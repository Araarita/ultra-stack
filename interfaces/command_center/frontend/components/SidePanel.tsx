"use client";

import { useEffect, useState } from "react";
import { ultraAPI } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Play, Square, RotateCw, FileText } from "lucide-react";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";
import type { SystemStatus } from "@/store/useUltra";

interface Props {
  type: "services" | "reports" | "logs";
  status?: SystemStatus | null;
}

export function SidePanel({ type, status }: Props) {
  if (type === "services") return <ServicesPanel status={status} />;
  if (type === "reports") return <ReportsPanel />;
  if (type === "logs") return <LogsPanel />;
  return null;
}

function ServicesPanel({ status }: { status: SystemStatus | null | undefined }) {
  if (!status) return null;

  const handleAction = async (service: string, action: string) => {
    try {
      await ultraAPI.serviceAction(service, action);
      toast.success(`${service} ${action} exitoso`);
    } catch (e) {
      toast.error(`Error en ${action}`);
    }
  };

  return (
    <div className="space-y-2">
      {status.services.map((s) => (
        <Card key={s.name} className="bg-slate-900/50 border-slate-800 p-3">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="flex items-center gap-3">
              <div className={`w-2 h-2 rounded-full ${s.active ? "bg-green-500 animate-pulse" : "bg-red-500"}`} />
              <div>
                <p className="text-sm font-medium">{s.name}</p>
                <p className="text-[10px] text-slate-500">{s.type}</p>
              </div>
            </div>
            <div className="flex gap-1">
              <Badge variant={s.active ? "default" : "destructive"}>
                {s.active ? "Active" : "Down"}
              </Badge>
              {s.type === "systemd" && (
                <>
                  <Button size="icon" variant="ghost" onClick={() => handleAction(s.name, "restart")}>
                    <RotateCw className="w-3 h-3" />
                  </Button>
                  {s.active ? (
                    <Button size="icon" variant="ghost" onClick={() => handleAction(s.name, "stop")}>
                      <Square className="w-3 h-3" />
                    </Button>
                  ) : (
                    <Button size="icon" variant="ghost" onClick={() => handleAction(s.name, "start")}>
                      <Play className="w-3 h-3" />
                    </Button>
                  )}
                </>
              )}
            </div>
          </div>
        </Card>
      ))}
    </div>
  );
}

function ReportsPanel() {
  const [research, setResearch] = useState<any[]>([]);
  const [code, setCode] = useState<any[]>([]);
  const [selected, setSelected] = useState<{ content: string; name: string } | null>(null);

  useEffect(() => {
    ultraAPI.listResearch().then(setResearch);
    ultraAPI.listCode().then(setCode);
  }, []);

  const open = async (kind: "research" | "code", name: string) => {
    const data =
      kind === "research"
        ? await ultraAPI.getResearch(name)
        : await ultraAPI.getCode(name);
    setSelected({ content: data.content, name });
  };

  if (selected) {
    return (
      <Card className="bg-slate-900/50 border-slate-800 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-sm">{selected.name}</h3>
          <Button size="sm" variant="ghost" onClick={() => setSelected(null)}>
            ← Volver
          </Button>
        </div>
        <ScrollArea className="h-[500px]">
          <div className="prose prose-invert prose-sm max-w-none">
            <ReactMarkdown>{selected.content}</ReactMarkdown>
          </div>
        </ScrollArea>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <Card className="bg-slate-900/50 border-slate-800 p-3">
        <h3 className="font-semibold text-sm mb-2">🔍 Research ({research.length})</h3>
        <div className="space-y-1">
          {research.slice(0, 5).map((r) => (
            <button
              key={r.name}
              onClick={() => open("research", r.name)}
              className="w-full text-left text-xs p-2 rounded hover:bg-slate-800/50 flex items-center gap-2"
            >
              <FileText className="w-3 h-3 text-purple-400" />
              <span className="truncate">{r.name}</span>
            </button>
          ))}
        </div>
      </Card>

      <Card className="bg-slate-900/50 border-slate-800 p-3">
        <h3 className="font-semibold text-sm mb-2">💻 Code ({code.length})</h3>
        <div className="space-y-1">
          {code.slice(0, 5).map((r) => (
            <button
              key={r.name}
              onClick={() => open("code", r.name)}
              className="w-full text-left text-xs p-2 rounded hover:bg-slate-800/50 flex items-center gap-2"
            >
              <FileText className="w-3 h-3 text-pink-400" />
              <span className="truncate">{r.name}</span>
            </button>
          ))}
        </div>
      </Card>
    </div>
  );
}

function LogsPanel() {
  const services = ["ultra-bot", "ultra-monitor", "ultra-healer", "ultra-metrics"];
  const [selected, setSelected] = useState(services[0]);
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    const fetch = async () => {
      const data = await ultraAPI.getLogs(selected, 30);
      setLogs(data.logs);
    };
    fetch();
    const id = setInterval(fetch, 5000);
    return () => clearInterval(id);
  }, [selected]);

  return (
    <Card className="bg-slate-900/50 border-slate-800 p-3 h-full flex flex-col">
      <div className="flex gap-1 mb-3 flex-wrap">
        {services.map((s) => (
          <Button
            key={s}
            size="sm"
            variant={selected === s ? "default" : "outline"}
            onClick={() => setSelected(s)}
            className="text-xs h-7"
          >
            {s}
          </Button>
        ))}
      </div>
      <ScrollArea className="flex-1">
        <pre className="text-[10px] text-slate-400 font-mono whitespace-pre-wrap">
          {logs.join("\n")}
        </pre>
      </ScrollArea>
    </Card>
  );
}
