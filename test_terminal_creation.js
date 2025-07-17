#!/usr/bin/env node
import fetch from 'node-fetch';

async function testTerminalCreation() {
  try {
    console.log('Testing terminal creation...');
    
    const response = await fetch('http://localhost:8000/api/terminals', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        name: 'Test Terminal'
      })
    });
    
    console.log('Response status:', response.status);
    console.log('Response headers:', Object.fromEntries(response.headers.entries()));
    
    const data = await response.json();
    console.log('Response data:', JSON.stringify(data, null, 2));
    
    if (data && data.id) {
      console.log('Terminal ID:', data.id);
      console.log('Terminal data structure is correct');
    } else {
      console.error('Terminal ID is missing from response');
    }
    
  } catch (error) {
    console.error('Error:', error);
  }
}

testTerminalCreation();
