"use client";

import { Badge } from "@/components/ui/badge";
import { Activity, Cpu, HardDrive, MemoryStick, Zap } from "lucide-react";
import type { SystemStatus, LLMMode } from "@/store/useUltra";

interface Props {
  status: SystemStatus | null;
  llmMode: LLMMode | null;
}

export function StatusBar({ status, llmMode }: Props) {
  if (!status) return null;

  const healthColor =
    status.total_active === status.total_services
      ? "bg-green-500/10 text-green-400 border-green-500/30"
      : status.total_active > status.total_services * 0.7
      ? "bg-yellow-500/10 text-yellow-400 border-yellow-500/30"
      : "bg-red-500/10 text-red-400 border-red-500/30";

  const modeColors: Record<string, string> = {
    FREE: "bg-slate-500/10 text-slate-400 border-slate-500/30",
    NORMAL: "bg-green-500/10 text-green-400 border-green-500/30",
    KIMI: "bg-purple-500/10 text-purple-400 border-purple-500/30",
    BOOST: "bg-yellow-500/10 text-yellow-400 border-yellow-500/30",
    TURBO: "bg-red-500/10 text-red-400 border-red-500/30",
  };

  return (
    <header className="sticky top-0 z-50 glass border-b border-slate-800">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-xl">
              🚀
            </div>
            <div>
              <h1 className="text-lg font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                Ultra Command Center
              </h1>
              <p className="text-xs text-slate-500">Erik &middot; Production</p>
            </div>
          </div>

          {/* KPIs */}
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className={healthColor}>
              <Activity className="w-3 h-3 mr-1" />
              {status.total_active}/{status.total_services} Services
            </Badge>

            <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/30">
              <MemoryStick className="w-3 h-3 mr-1" />
              RAM {status.resources.ram_pct}%
            </Badge>

            <Badge className="bg-cyan-500/10 text-cyan-400 border-cyan-500/30">
              <HardDrive className="w-3 h-3 mr-1" />
              Disk {status.resources.disk_pct}%
            </Badge>

            <Badge className="bg-indigo-500/10 text-indigo-400 border-indigo-500/30">
              <Cpu className="w-3 h-3 mr-1" />
              Load {status.resources.load_avg.toFixed(2)}
            </Badge>

            {llmMode && (
              <Badge className={modeColors[llmMode.mode] || modeColors.NORMAL}>
                <Zap className="w-3 h-3 mr-1" />
                {llmMode.emoji} {llmMode.mode}
              </Badge>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
