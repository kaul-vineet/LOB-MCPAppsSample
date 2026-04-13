import React from 'react';
import { Text } from '@fluentui/react-components';

export function McpFooter({ label }: { label: string }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '8px 0', marginTop: '12px', borderTop: '1px solid var(--colorNeutralStroke2)',
      fontSize: '11px', opacity: 0.6
    }}>
      <Text size={100}>⚡ <strong>MCP Widget</strong> · {label}</Text>
      <Text size={100}>⚓ GTC</Text>
    </div>
  );
}
