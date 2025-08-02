import React from 'react';
import { useChatMessages } from '../../src/icui';

const TestComponent: React.FC = () => {
  const { messages } = useChatMessages();
  return <div>Test: {messages.length}</div>;
};

export default TestComponent;
