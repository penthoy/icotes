/**
 * Model Helper Abstractions
 * 
 * Exports model-specific helpers and their interfaces.
 * Supports GPT-5 and a Generic fallback.
 */

export { default as gpt5Helper, GPT5ModelHelper, type ModelHelper } from './gpt5';
export { default as genericModelHelper } from './genericmodel';
export { getActiveModelHelper, setActiveModelId, getActiveModelId } from './router'; 