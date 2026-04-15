import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useApp, type App } from '@modelcontextprotocol/ext-apps/react';
import type { McpUiHostContext } from '@modelcontextprotocol/ext-apps';

interface McpBridgeContextType {
  toolData: any;
  theme: 'light' | 'dark';
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  notifyHeight: () => void;
  requestFullscreen: () => void;
  exitFullscreen: () => void;
  isFullscreen: boolean;
  canExpand: boolean;
  isConnected: boolean;
  isLoading: boolean;
}

const McpBridgeContext = createContext<McpBridgeContextType | null>(null);

export function McpBridgeProvider({ appName, children }: { appName: string; children: React.ReactNode }) {
  const [toolData, setToolData] = useState<any>(null);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const [isFullscreen, setIsFullscreen] = useState(false);
  const lastHeight = useRef(0);

  // Use the official ext-apps React hook for connection lifecycle
  const { app, isConnected, error } = useApp({
    appInfo: { name: appName, version: '1.0.0' },
    capabilities: {},
    onAppCreated: (app: App) => {
      app.ontoolresult = (result) => {
        if (result?.structuredContent) {
          setToolData(result.structuredContent);
        }
      };
      app.onhostcontextchanged = (ctx: McpUiHostContext) => {
        if (ctx?.theme) {
          setTheme(ctx.theme === 'dark' ? 'dark' : 'light');
        }
        if (ctx?.displayMode) {
          setIsFullscreen(ctx.displayMode === 'fullscreen');
        }
      };
    },
  });

  // Apply initial host context on connection
  useEffect(() => {
    if (!app || !isConnected) return;
    const ctx = app.getHostContext();
    if (ctx?.theme) setTheme(ctx.theme === 'dark' ? 'dark' : 'light');
    if (ctx?.displayMode) setIsFullscreen(ctx.displayMode === 'fullscreen');
  }, [app, isConnected]);

  // Legacy fallback: window.openai toolOutput (for older hosts)
  useEffect(() => {
    if ((window as any).openai?.toolOutput) {
      const out = (window as any).openai.toolOutput;
      setToolData(out.structuredContent ?? out);
    }
  }, []);

  // Notify height — deduplicated to avoid flicker
  // Kept as fallback alongside ext-apps autoResize (which handles standard hosts)
  const notifyHeight = useCallback(() => {
    const h = document.body.scrollHeight;
    if (h === lastHeight.current) return;
    lastHeight.current = h;
    if ((window as any).openai?.notifyIntrinsicHeight) {
      (window as any).openai.notifyIntrinsicHeight({ height: h });
    }
  }, []);

  // Fullscreen via official SDK
  const requestFullscreen = useCallback(async () => {
    if (app && isConnected) {
      try {
        const result = await app.requestDisplayMode({ mode: 'fullscreen' });
        setIsFullscreen(result.mode === 'fullscreen');
        return;
      } catch { /* fall through to legacy */ }
    }
    // Legacy fallback
    if ((window as any).openai?.requestDisplayMode) {
      (window as any).openai.requestDisplayMode({ mode: 'fullscreen' });
    }
    setIsFullscreen(true);
  }, [app, isConnected]);

  const exitFullscreen = useCallback(async () => {
    if (app && isConnected) {
      try {
        const result = await app.requestDisplayMode({ mode: 'inline' });
        setIsFullscreen(result.mode === 'fullscreen');
        return;
      } catch { /* fall through to legacy */ }
    }
    // Legacy fallback
    if ((window as any).openai?.requestDisplayMode) {
      (window as any).openai.requestDisplayMode({ mode: 'inline' });
    }
    setIsFullscreen(false);
  }, [app, isConnected]);

  // callTool with single retry on failure
  const callToolOnce = useCallback(async (name: string, args?: Record<string, any>): Promise<any> => {
    if (app && isConnected) {
      const result = await app.callServerTool({ name, arguments: args || {} });
      if (result.isError) {
        throw new Error(
          result.content?.map((c: any) => ('text' in c ? c.text : '')).join('') || 'Tool call failed'
        );
      }
      return result.structuredContent || result;
    }
    throw new Error('Not connected to MCP host');
  }, [app, isConnected]);

  const callTool = useCallback(async (name: string, args?: Record<string, any>) => {
    try {
      return await callToolOnce(name, args);
    } catch (e) {
      // Retry once after 1s for transient errors
      await new Promise(r => setTimeout(r, 1000));
      return callToolOnce(name, args);
    }
  }, [callToolOnce]);

  // Notify height whenever toolData changes (legacy host support)
  useEffect(() => {
    if (toolData) {
      setTimeout(notifyHeight, 100);
      setTimeout(notifyHeight, 300);
    }
  }, [toolData, notifyHeight]);

  // Debounced ResizeObserver for legacy height notifications
  // (ext-apps autoResize handles the standard protocol path)
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout>;
    const observer = new ResizeObserver(() => {
      clearTimeout(timer);
      timer = setTimeout(notifyHeight, 100);
    });
    observer.observe(document.body);
    return () => { observer.disconnect(); clearTimeout(timer); };
  }, [notifyHeight]);

  // Log connection errors for diagnostics
  useEffect(() => {
    if (error) {
      console.warn('[McpBridge] Connection error:', error.message);
    }
  }, [error]);

  const isLoading = !isConnected && !error;

  // Check if host supports display mode changes
  const canExpand = !!(app && typeof app.requestDisplayMode === 'function') ||
    !!(typeof (window as any).openai?.requestDisplayMode === 'function');

  return (
    <McpBridgeContext.Provider value={{
      toolData, theme, callTool, notifyHeight,
      requestFullscreen, exitFullscreen, isFullscreen, canExpand,
      isConnected, isLoading,
    }}>
      {children}
    </McpBridgeContext.Provider>
  );
}

export function useMcpBridge() {
  const ctx = useContext(McpBridgeContext);
  if (!ctx) throw new Error('useMcpBridge must be inside McpBridgeProvider');
  return ctx;
}

export function useToolData<T = any>(): T | null {
  return useMcpBridge().toolData as T | null;
}

export function useTheme(): 'light' | 'dark' {
  return useMcpBridge().theme;
}
