import genericModelHelper from './genericmodel';
import type { ModelHelper } from './genericmodel';

// For backward compatibility, alias the generic helper as gpt5Helper
const gpt5Helper = genericModelHelper;

let ACTIVE_MODEL_ID = 'gpt5';

export function setActiveModelId(modelId: string): void {
	ACTIVE_MODEL_ID = modelId;
}

export function getActiveModelId(): string {
	return ACTIVE_MODEL_ID;
}

export function getActiveModelHelper(): ModelHelper {
	switch (ACTIVE_MODEL_ID.toLowerCase()) {
		case 'gpt5':
			return gpt5Helper;
		default:
			return genericModelHelper;
	}
} 