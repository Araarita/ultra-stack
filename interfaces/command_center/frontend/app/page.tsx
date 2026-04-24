"use client";

import { useState } from "react";
import { useLiveStatus } from "@/hooks/useLiveStatus";
import { useUltraStore } from "@/store/useUltra";
import { StatusBar } from "@/components/StatusBar";
import { GraphPanel } from "@/components/GraphPanel";
import { ChatPanel } from "@/components/ChatPanel";
import { SidePanel } from "@/components/SidePanel";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export default function Home() {
  useLiveStatus(5000);
  const { status, llmMode, isLoading } = useUltraStore();
  const [activeTab, setActiveTab] = useState("graph");

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-slate-400">Conectando a Ultra Stack...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 text-white">
      {/* Header Status Bar */}
      <StatusBar status={status} llmMode={llmMode} />

      {/* Main Layout */}
      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 h-[calc(100vh-120px)]">
          {/* Panel Principal */}
          <div className="lg:col-span-2">
            <Tabs value={activeTab} onValueChange={setActiveTab} className="h-full flex flex-col">
              <TabsList className="bg-slate-900/50 border border-slate-800">
                <TabsTrigger value="graph">🌐 Grafo</TabsTrigger>
                <TabsTrigger value="services">🔧 Servicios</TabsTrigger>
                <TabsTrigger value="reports">📄 Reportes</TabsTrigger>
                <TabsTrigger value="logs">📜 Logs</TabsTrigger>
              </TabsList>

              <TabsContent value="graph" className="flex-1 mt-4">
                <GraphPanel />
              </TabsContent>

              <TabsContent value="services" className="flex-1 mt-4 overflow-auto">
                <SidePanel type="services" status={status} />
              </TabsContent>

              <TabsContent value="reports" className="flex-1 mt-4 overflow-auto">
                <SidePanel type="reports" />
              </TabsContent>

              <TabsContent value="logs" className="flex-1 mt-4 overflow-auto">
                <SidePanel type="logs" />
              </TabsContent>
            </Tabs>
          </div>

          {/* Chat Panel */}
          <div className="lg:col-span-1">
            <ChatPanel />
          </div>
        </div>
      </div>
    </div>
  );
}
