import { ChatMessage as ChatMessageType } from '../../../types/chatTypes';
import { ToolCallData } from '../ToolCallWidget';
import { GPT5ModelHelper } from './gpt5';

// Reuse GPT5ModelHelper behavior as a baseline but with minimal assumptions
class GenericModelHelper extends GPT5ModelHelper {
	// Override anything that is GPT-5 specific if needed later. For now, we keep it as baseline.
}

const genericModelHelper = new GenericModelHelper();
export default genericModelHelper; 