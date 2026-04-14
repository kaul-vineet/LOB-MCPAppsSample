import React from 'react';
import { createRoot } from 'react-dom/client';
import { McpBridgeProvider } from '../shared/McpBridge';
import { FluentWrapper } from '../shared/FluentWrapper';
import { ToastContainer } from '../shared/Toast';
import { ServiceNowApp } from './App';

createRoot(document.getElementById('root')!).render(
  <McpBridgeProvider appName="gtc-snow-widget">
    <FluentWrapper>
      <ServiceNowApp />
      <ToastContainer />
    </FluentWrapper>
  </McpBridgeProvider>
);
