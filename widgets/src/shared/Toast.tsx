import React, { useState, useEffect, useCallback } from 'react';
import { MessageBar, MessageBarBody } from '@fluentui/react-components';

type ToastType = 'success' | 'error' | 'info';

interface ToastState { message: string; type: ToastType; key: number }

let showToastGlobal: (msg: string, type?: ToastType) => void = () => {};

export function useToast() {
  return useCallback((msg: string, type: ToastType = 'success') => {
    showToastGlobal(msg, type);
  }, []);
}

export function ToastContainer() {
  const [toast, setToast] = useState<ToastState | null>(null);

  useEffect(() => {
    showToastGlobal = (msg, type = 'success') => {
      setToast({ message: msg, type, key: Date.now() });
    };
  }, []);

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 3000);
      return () => clearTimeout(t);
    }
  }, [toast]);

  if (!toast) return null;

  const intent = toast.type === 'error' ? 'error' : toast.type === 'info' ? 'info' : 'success';

  return (
    <div style={{ position: 'fixed', top: 12, left: '50%', transform: 'translateX(-50%)', zIndex: 999, minWidth: 280 }}>
      <MessageBar intent={intent}>
        <MessageBarBody>{toast.message}</MessageBarBody>
      </MessageBar>
    </div>
  );
}
