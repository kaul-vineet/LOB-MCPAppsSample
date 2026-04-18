import React from 'react';
import { createRoot } from 'react-dom/client';
import { ErrorBoundary } from '../shared/ErrorBoundary';
import { McpBridgeProvider } from '../shared/McpBridge';
import { FluentWrapper } from '../shared/FluentWrapper';
import { ToastContainer } from '../shared/Toast';
import { DocuSignApp } from './App';

createRoot(document.getElementById('root')!).render(
  <ErrorBoundary>
    <McpBridgeProvider appName="gtc-docusign-widget">
      <FluentWrapper>
        <DocuSignApp />
        <ToastContainer />
      </FluentWrapper>
    </McpBridgeProvider>
  </ErrorBoundary>
);
