import gpt5Helper from './gpt5';
import genericModelHelper from './genericmodel';
import type { ModelHelper } from './gpt5';

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