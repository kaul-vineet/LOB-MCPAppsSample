import React from 'react';
import { useMcpBridge } from './McpBridge';

export function ExpandButton() {
  const { canExpand, isFullscreen, requestFullscreen, exitFullscreen } = useMcpBridge();

  if (!canExpand) return null;

  return (
    <button
      onClick={isFullscreen ? exitFullscreen : requestFullscreen}
      title={isFullscreen ? 'Exit expanded view' : 'Expand'}
      style={{
        background: 'rgba(255,255,255,0.92)',
        border: '1px solid rgba(255,255,255,0.95)',
        color: '#111',
        borderRadius: '4px',
        padding: '4px 10px',
        cursor: 'pointer',
        fontSize: '12px',
        fontWeight: 600,
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        boxShadow: '0 1px 4px rgba(0,0,0,0.18)',
      }}
    >
      {isFullscreen ? '✕ Exit' : '⤢ Expand'}
    </button>
  );
}
