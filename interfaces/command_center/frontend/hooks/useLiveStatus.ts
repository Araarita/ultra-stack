"use client";
import { useEffect } from "react";
import { ultraAPI } from "@/lib/api";
import { useUltraStore } from "@/store/useUltra";

export function useLiveStatus(interval = 5000) {
  const { setStatus, setLLMMode, setLoading } = useUltraStore();

  useEffect(() => {
    let mounted = true;

    const fetchData = async () => {
      try {
        const [status, mode] = await Promise.all([
          ultraAPI.getStatus(),
          ultraAPI.getLLMStatus(),
        ]);
        if (mounted) {
          setStatus(status);
          setLLMMode(mode);
          setLoading(false);
        }
      } catch (e) {
        console.error("Status fetch error:", e);
      }
    };

    fetchData();
    const id = setInterval(fetchData, interval);

    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, [interval, setStatus, setLLMMode, setLoading]);
}
