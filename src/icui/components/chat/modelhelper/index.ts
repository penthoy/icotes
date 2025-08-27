/**
 * Model Helper Abstractions
 * 
 * Exports model-specific helpers and their interfaces.
 * Uses a Generic model helper as the primary implementation.
 */

export { default as genericModelHelper, GenericModelHelper, type ModelHelper } from './genericmodel';
// Legacy GPT-5 helper - now aliased to generic helper
export { default as gpt5Helper } from './genericmodel';
export { getActiveModelHelper, setActiveModelId, getActiveModelId } from './router'; 