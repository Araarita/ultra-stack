"use client";

import { useCallback, useEffect, useMemo } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  MarkerType,
  BackgroundVariant,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import dagre from "dagre";
import { ultraAPI } from "@/lib/api";
import { Card } from "@/components/ui/card";

// =========== NODO CUSTOM PREMIUM ===========
function UltraNode({ data }: { data: any }) {
  const active = data.active;

  const gradients: Record<string, string> = {
    user: "from-blue-500 to-cyan-500",
    interface: "from-purple-500 to-pink-500",
    memory: "from-emerald-500 to-teal-500",
    router: "from-orange-500 to-red-500",
    crew: "from-indigo-500 to-purple-500",
    agent: "from-yellow-500 to-orange-500",
    provider: "from-slate-500 to-slate-700",
    metrics: "from-pink-500 to-rose-500",
  };

  const gradient = gradients[data.nodeType || "interface"] || gradients.interface;

  return (
    <div
      className={`relative group transition-all duration-300 ${
        active ? "opacity-100" : "opacity-50 grayscale"
      }`}
    >
      {/* Glow effect */}
      <div
        className={`absolute -inset-0.5 bg-gradient-to-br ${gradient} rounded-xl blur opacity-60 group-hover:opacity-100 transition`}
      />

      <div className="relative bg-slate-900 border border-slate-700 rounded-xl px-4 py-3 min-w-[160px] shadow-xl">
        <Handle
          type="target"
          position={Position.Left}
          className="!w-2 !h-2 !bg-slate-600 !border-0"
        />

        <div className="flex items-center gap-2 mb-1">
          <div
            className={`w-8 h-8 rounded-lg bg-gradient-to-br ${gradient} flex items-center justify-center text-base shrink-0`}
          >
            {data.emoji}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-bold text-white truncate">
              {data.label}
            </div>
            {(data.port || data.interval || data.mode || data.agents) && (
              <div className="text-[9px] text-slate-400 truncate">
                {data.port && `:${data.port}`}
                {data.interval && `every ${data.interval}`}
                {data.mode && data.mode}
                {data.agents && `${data.agents} agents`}
              </div>
            )}
          </div>
          <div
            className={`w-2 h-2 rounded-full shrink-0 ${
              active ? "bg-green-500 animate-pulse" : "bg-red-500"
            }`}
          />
        </div>

        <Handle
          type="source"
          position={Position.Right}
          className="!w-2 !h-2 !bg-slate-600 !border-0"
        />
      </div>
    </div>
  );
}

const nodeTypes = {
  ultra: UltraNode,
};

// =========== AUTO-LAYOUT CON DAGRE ===========
function getLayoutedElements(nodes: any[], edges: any[], direction = "LR") {
  const isMobile = typeof window !== "undefined" && window.innerWidth < 768;
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({
    rankdir: isMobile ? "TB" : direction,
    nodesep: isMobile ? 40 : 60,
    ranksep: isMobile ? 50 : 100,
    marginx: 20,
    marginy: 20,
  });

  const nodeWidth = 180;
  const nodeHeight = 70;

  nodes.forEach((n) => g.setNode(n.id, { width: nodeWidth, height: nodeHeight }));
  edges.forEach((e) => g.setEdge(e.source, e.target));

  dagre.layout(g);

  return {
    nodes: nodes.map((n) => {
      const pos = g.node(n.id);
      return {
        ...n,
        position: { x: pos.x - nodeWidth / 2, y: pos.y - nodeHeight / 2 },
        targetPosition: isMobile ? Position.Top : Position.Left,
        sourcePosition: isMobile ? Position.Bottom : Position.Right,
      };
    }),
    edges,
  };
}

// =========== PANEL ===========
export function GraphPanel() {
  const [nodes, setNodes, onNodesChange] = useNodesState<any>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<any>([]);

  const loadGraph = useCallback(async () => {
    try {
      const data = await ultraAPI.getGraph();

      const rawNodes = data.nodes.map((n: any) => ({
        id: n.id,
        type: "ultra",
        position: { x: 0, y: 0 },
        data: {
          ...n.data,
          active: n.active,
          nodeType: n.type || "interface",
        },
      }));

      const rawEdges = data.edges.map((e: any) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        animated: e.animated || false,
        type: "smoothstep",
        style: {
          stroke: e.animated ? "#a855f7" : "#475569",
          strokeWidth: e.animated ? 2 : 1.5,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: e.animated ? "#a855f7" : "#475569",
        },
      }));

      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        rawNodes,
        rawEdges
      );

      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
    } catch (e) {
      console.error("Graph error:", e);
    }
  }, [setNodes, setEdges]);

  useEffect(() => {
    loadGraph();
    const id = setInterval(loadGraph, 15000);
    const onResize = () => loadGraph();
    window.addEventListener("resize", onResize);
    return () => {
      clearInterval(id);
      window.removeEventListener("resize", onResize);
    };
  }, [loadGraph]);

  const defaultViewport = useMemo(
    () => ({ x: 0, y: 0, zoom: 0.8 }),
    []
  );

  return (
    <Card className="h-full bg-gradient-to-br from-slate-950 to-slate-900 border-slate-800 overflow-hidden p-0">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2, maxZoom: 1.2 }}
        defaultViewport={defaultViewport}
        minZoom={0.3}
        maxZoom={1.5}
        proOptions={{ hideAttribution: true }}
        className="bg-transparent"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1.5}
          color="#475569"
          className="opacity-30"
        />
        <Controls
          className="!bg-slate-800/80 !border-slate-700 !shadow-xl"
          showInteractive={false}
        />
      </ReactFlow>
    </Card>
  );
}
