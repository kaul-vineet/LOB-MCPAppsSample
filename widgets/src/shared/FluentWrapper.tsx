import React from 'react';
import { FluentProvider, webLightTheme, webDarkTheme } from '@fluentui/react-components';
import { useTheme } from './McpBridge';

export function FluentWrapper({ children }: { children: React.ReactNode }) {
  const theme = useTheme();
  return (
    <FluentProvider theme={theme === 'dark' ? webDarkTheme : webLightTheme} style={{ background: 'transparent' }}>
      {children}
    </FluentProvider>
  );
}
