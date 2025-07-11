## Instructions: 
When I said "continue progress" in the prompt, check ##In Progress section in the roadmap.md file, and proceed to work on just In progress section, after finished, move it to Recently finished section, Only if you see it in the ## Tested working section in the roadmap which I'll manually test, move them to the Changelog. if you see previous task that's attempted but still under In progress, it means they're still not working or unfinished after manual testing. so they need to revisit or try another approach, if this happens, first try to assess what was tried previously and why it didn't work, revert any previous change that isn't necessary to always keep the codebase clean, before attempt another approach, make sure you explain what you tried and anything you need the user to help make it work.

Please read Agent_dev_workflow.md to learn how to iterate.

- When I said "housekeeping" 
1. please update both Working.md and CHANGELOG.md by reading all ## recently finished section from Project_roadmap.md and then clean them up.
2. do cleanups if there were any previously added debug code.
3. Update Optimization.md by reading Agent_optimization.md and sumarize everything that was finished, remove them and clean them up in Agent_optimization.md. Updates in Optimization.md should be brief and to the point so that it is human readable.

- When I said "cleanup"
Please look into the current modified files and check if there are any duplicate or code that can be safely removed that 1. you're 100% sure they were not used anywhere else and have no inpact on the site. 2. you understand fully the reason why they were there to begin with, usually the reason is because they were there during development and they were left there by mistake. 3. when you're in Doubt make sure to bring it up your findings.

- When I said "optimize":
Please read the Agent_optimization.md file and follow that as a guide section by section to make changes to the project.
Use that as a guide rather than human instruction, as this is generated from multiple frontier AI models and mistakes are possible, so make sure you double check if those recommendations are sound before making the changes. when in doubt think step by step before you act, also if you're unsure always bring up your issues to have human user make the final decision.

- When I said "distill":
Create a file under docs folder with the prefix: experience_distilation_xxx.md where xxx is a name for you to decide based on a one word that can best sumarized our current conversational session it could be a topic or a theme, inside this file please sumarize all your experiences in this current session based on the following topics: what you have learned about this code base and how we are approaching and coding this repo so far based on our conversations in this session, what was tried, what mistakes are made, and what was done well, the purpose for this doc is for future AIs to learn from your experience, so that you can continue to improve, this is a postmortem, try to be concise and to the point, don't repeat yourself so that you can save context lengths to fullfill the purpose of distillation. but don't be overly vague either, it should contain enough information for your future self to best receive your knowledge.

## Rules:
When asked to "continue progress" please don't work on anything else other than the In progress section of the roadmap.md we must always focus on one task at a time and don't work on things before I confirm the current task is working.

use the start-dev.sh to run the dev server, and start.sh to run production server.

## Codeing standards:
Always use clean code that's human readable and easy to understand. so that its possible for human and AI to work on the same code base

Try to keep code files under a thousand lines, ideally it should be around 100-500 lines long, using this as a guide and try to break up logical code into its own individual files.

Always comment the code, and make sure they're properly commented.

Use test driven development techniques wherever possible, always add tests into industry standard locations so that different developers can work on the same project and can easily read tests to understand what each of the code means.

