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
        background: 'transparent',
        border: '1px solid rgba(255,255,255,0.4)',
        color: 'inherit',
        borderRadius: '4px',
        padding: '4px 10px',
        cursor: 'pointer',
        fontSize: '12px',
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
      }}
    >
      {isFullscreen ? '✕ Exit' : '⤢ Expand'}
    </button>
  );
}
