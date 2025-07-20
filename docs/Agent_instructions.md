## Instructions: 
When I said "continue progress(#)" in the prompt, check ##In Progress section in the roadmap.md file, and proceed to work on just In progress section, after finished, move it to Recently finished section, If there's a # after continue progress, only work on the number assigned, as other agent or person will be working on the other in progress items asynchronusly, if you work on it you'll clash with another person/agent; always keep the codebase clean, before attempt another approach, make sure you explain what you tried and anything you need the user to help make it work.


Please read Agent_dev_workflow.md to learn how to iterate.

Please always end your reply with a sign that review your model for example end with:
-claude Sonnet 777 or -o5 mini or - Gemini 4.5 pro, make sure you're certain what you are, if you're unsure do -unknown

- When I said "housekeeping" 
1. please update both Working.md and CHANGELOG.md by reading all ## recently finished section from Project_roadmap.md and then clean them up.
2. do cleanups if there were any previously added debug code.

- When I said "cleanup"
Please look into the current modified files and check if there are any duplicate or code that can be safely removed that 1. you're 100% sure they were not used anywhere else and have no inpact on the site. 2. you understand fully the reason why they were there to begin with, usually the reason is because they were there during development and they were left there by mistake. 3. when you're in Doubt make sure to bring it up your findings.

- When I said "optimize":
Please read the Agent_optimization.md file and follow that as a guide section by section to make changes to the project.
Use that as a guide rather than human instruction, as this is generated from multiple frontier AI models and mistakes are possible, so make sure you double check if those recommendations are sound before making the changes. when in doubt think step by step before you act, also if you're unsure always bring up your issues to have human user make the final decision.

- When I said "distill":
Create a file under docs folder with the prefix: experience_distilation_xxx.md where xxx is a name for you to decide based on a one word that can best sumarized our current conversational session it could be a topic or a theme, inside this file please sumarize all your experiences in this current session based on the following topics: what you have learned about this code base and how we are approaching and coding this repo so far based on our conversations in this session, what was tried, what mistakes are made, and what was done well, the purpose for this doc is for future AIs to learn from your experience, so that you can continue to improve, this is a postmortem, try to be concise and to the point, don't repeat yourself so that you can save context lengths to fullfill the purpose of distillation. but don't be overly vague either, it should contain enough information for your future self to best receive your knowledge.

- when I said "audit":


- When I said "fix build errors":
run "npm run build" and fix all build errors

- When Start my prompt with "cc:":
It means try to use claude code, claude code is a flagship coding agent that can execute on your behave, think of it as your assistant, you use it by running claude on the commandline, and then you'll be able to talk to it to make requests. when I type prompt starting with cc: what I want you to do is take full advantage of this tool. but you should always be the manager and be in control, try to check for outputs and ensure the agent did what it said it did.

## Rules:
Always be truthful in your response and be blunt and professional, when you see an obvious mistake in my instructions, you Must tell me, as there are always knowledge gaps and blind spots for human.
if you see potential issue in the code or design tell me bluntly and truthfully.

When asked to "continue progress" please don't work on anything else other than the In progress section of the roadmap.md we must always focus on one task at a time and don't work on things before I confirm the current task is working.

## Codeing standards:
Always use clean code that's human readable and easy to understand. so that its possible for human and AI to work on the same code base

Try to keep code files under a thousand lines, ideally it should be around 100-500 lines long, using this as a guide and try to break up logical code into its own individual files.

Always comment the code, and make sure they're properly commented.

Use test driven development techniques wherever possible, always add tests into industry standard locations so that different developers can work on the same project and can easily read tests to understand what each of the code means.

