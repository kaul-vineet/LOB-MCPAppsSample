import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';

interface McpBridgeContextType {
  toolData: any;
  theme: 'light' | 'dark';
  callTool: (name: string, args?: Record<string, any>) => Promise<any>;
  notifyHeight: () => void;
}

const McpBridgeContext = createContext<McpBridgeContextType | null>(null);

export function McpBridgeProvider({ appName, children }: { appName: string; children: React.ReactNode }) {
  const [toolData, setToolData] = useState<any>(null);
  const [theme, setTheme] = useState<'light' | 'dark'>('light');
  const pendingCalls = useRef<Record<number, { resolve: (v: any) => void; reject: (e: Error) => void }>>({});
  const callIdRef = useRef(0);
  const initDone = useRef(false);

  // Send ui/initialize handshake
  const sendInit = useCallback(() => {
    window.parent.postMessage({
      jsonrpc: '2.0',
      id: 'mcp-ui-init',
      method: 'ui/initialize',
      params: { appInfo: { name: appName, version: '1.0' }, appCapabilities: {} }
    }, '*');
  }, [appName]);

  // Send ui/notifications/initialized
  const sendInitialized = useCallback(() => {
    if (initDone.current) return;
    initDone.current = true;
    window.parent.postMessage({
      jsonrpc: '2.0',
      method: 'ui/notifications/initialized'
    }, '*');
  }, []);

  // Notify height
  const notifyHeight = useCallback(() => {
    const h = document.body.scrollHeight;
    window.parent.postMessage({
      jsonrpc: '2.0',
      method: 'ui/notifyIntrinsicHeight',
      params: { height: h }
    }, '*');
  }, []);

  // callTool
  const callTool = useCallback((name: string, args?: Record<string, any>) => {
    return new Promise<any>((resolve, reject) => {
      const id = ++callIdRef.current;
      pendingCalls.current[id] = { resolve, reject };
      window.parent.postMessage({
        jsonrpc: '2.0', id,
        method: 'tools/call',
        params: { name, arguments: args || {} }
      }, '*');
      setTimeout(() => {
        if (pendingCalls.current[id]) {
          delete pendingCalls.current[id];
          reject(new Error('Tool call timed out'));
        }
      }, 20000);
    });
  }, []);

  useEffect(() => {
    const handler = (event: MessageEvent) => {
      const msg = event.data;
      if (!msg || typeof msg !== 'object') return;

      // SANDBOX_PROXY_READY
      if (msg.type === 'SANDBOX_PROXY_READY' || msg.type === 'SANDBOX_RESOURCE_READY') {
        sendInit();
        return;
      }

      // Init response
      if (msg.id === 'mcp-ui-init') {
        if (msg.result?.theme) setTheme(msg.result.theme === 'dark' ? 'dark' : 'light');
        sendInitialized();
        return;
      }

      // Theme change
      if (msg.jsonrpc === '2.0' && msg.method === 'ui/notifications/theme-change') {
        setTheme(msg.params?.theme === 'dark' ? 'dark' : 'light');
        return;
      }

      // Tool result
      if (msg.jsonrpc === '2.0' && msg.method === 'ui/notifications/tool-result') {
        const sc = msg.params?.structuredContent;
        if (sc !== undefined) setToolData(sc);
        return;
      }

      // callTool response
      if (msg.jsonrpc === '2.0' && msg.id && pendingCalls.current[msg.id]) {
        const cb = pendingCalls.current[msg.id];
        delete pendingCalls.current[msg.id];
        if (msg.result) {
          cb.resolve(msg.result.structuredContent || msg.result);
        } else {
          cb.reject(new Error(msg.error?.message || 'Tool call failed'));
        }
        return;
      }
    };

    window.addEventListener('message', handler);
    // Send init on load
    sendInit();

    // Legacy fallback: window.openai
    if ((window as any).openai?.toolOutput) {
      const out = (window as any).openai.toolOutput;
      setToolData(out.structuredContent ?? out);
    }

    return () => window.removeEventListener('message', handler);
  }, [sendInit, sendInitialized]);

  // Notify height whenever toolData changes
  useEffect(() => {
    if (toolData) {
      setTimeout(notifyHeight, 50);
    }
  }, [toolData, notifyHeight]);

  return (
    <McpBridgeContext.Provider value={{ toolData, theme, callTool, notifyHeight }}>
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
