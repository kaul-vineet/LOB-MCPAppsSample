import React, { useState, useEffect, useCallback } from 'react';
import { MessageBar, MessageBarBody } from '@fluentui/react-components';

type ToastType = 'success' | 'error' | 'info';

interface ToastMsg { message: string; type: ToastType; key: number }

let showToastGlobal: (msg: string, type?: ToastType) => void = () => {};

export function useToast() {
  return useCallback((msg: string, type: ToastType = 'success') => {
    showToastGlobal(msg, type);
  }, []);
}

export function ToastContainer() {
  const [queue, setQueue] = useState<ToastMsg[]>([]);
  const visible = queue[0] ?? null;

  useEffect(() => {
    showToastGlobal = (msg, type = 'success') => {
      setQueue(q => [...q, { message: msg, type, key: Date.now() }]);
    };
  }, []);

  useEffect(() => {
    if (!visible) return;
    const t = setTimeout(() => setQueue(q => q.slice(1)), 3000);
    return () => clearTimeout(t);
  }, [visible]);

  if (!visible) return null;

  const intent = visible.type === 'error' ? 'error' : visible.type === 'info' ? 'info' : 'success';

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      style={{ position: 'fixed', top: 12, left: '50%', transform: 'translateX(-50%)', zIndex: 999, minWidth: 280 }}
    >
      <MessageBar intent={intent}>
        <MessageBarBody>{visible.message}</MessageBarBody>
      </MessageBar>
    </div>
  );
}
