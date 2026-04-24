"use client";

import { useState, useRef, useEffect } from "react";
import { ultraAPI } from "@/lib/api";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Bot, User, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import { toast } from "sonner";

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "Hola Erik 👋 Soy Ultra, tu asistente con memoria persistente. ¿En qué puedo ayudarte?",
      timestamp: new Date().toISOString(),
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async () => {
    if (!input.trim() || loading) return;

    const userMsg: Message = {
      role: "user",
      content: input,
      timestamp: new Date().toISOString(),
    };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const { reply } = await ultraAPI.chat(input);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: reply,
          timestamp: new Date().toISOString(),
        },
      ]);
    } catch (e) {
      toast.error("Error chateando con Ultra");
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="h-full bg-slate-900/50 border-slate-800 flex flex-col">
      <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-sm">
          🤖
        </div>
        <div>
          <h2 className="text-sm font-semibold">Ultra Assistant</h2>
          <p className="text-[10px] text-green-400">● Online &middot; Letta memory</p>
        </div>
      </div>

      <ScrollArea className="flex-1 px-4 py-3" ref={scrollRef}>
        <div className="space-y-4">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex gap-2 ${m.role === "user" ? "justify-end" : ""}`}
            >
              {m.role === "assistant" && (
                <div className="w-7 h-7 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-xs shrink-0">
                  <Bot className="w-4 h-4" />
                </div>
              )}
              <div
                className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                  m.role === "user"
                    ? "bg-gradient-to-br from-purple-500 to-pink-500 text-white"
                    : "bg-slate-800/50 text-slate-200 border border-slate-700"
                }`}
              >
                <div className="prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown>{m.content}</ReactMarkdown>
                </div>
                <div className="text-[9px] opacity-50 mt-1">
                  {new Date(m.timestamp).toLocaleTimeString()}
                </div>
              </div>
              {m.role === "user" && (
                <div className="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center text-xs shrink-0">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="flex gap-2">
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4" />
              </div>
              <div className="bg-slate-800/50 border border-slate-700 rounded-lg px-3 py-2">
                <Loader2 className="w-4 h-4 animate-spin" />
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="p-3 border-t border-slate-800">
        <div className="flex gap-2">
          <Input
            placeholder="Escribe a Ultra..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            disabled={loading}
            className="bg-slate-800/50 border-slate-700"
          />
          <Button
            onClick={send}
            disabled={loading || !input.trim()}
            size="icon"
            className="bg-gradient-to-br from-purple-500 to-pink-500 hover:opacity-90"
          >
            <Send className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </Card>
  );
}
