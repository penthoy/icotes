## Instructions: 
When I said "continue progress" in the prompt, check ##In Progress section in the Project_roadmap.md file, and proceed to work on just In progress section, after finished, move it to Recently finished section, Only if you see it in the ## Tested working section in the Project_roadmap which I'll manually test, move them to the Changelog. if you see previous task that's attempted but still under In progress, it means they're still not working or unfinished after manual testing. so they need to revisit or try another approach, if this happens, first try to assess what was tried previously and why it didn't work, revert any previous change that isn't necessary to always keep the codebase clean, before attempt another approach, make sure you explain what you tried and anything you need the user to help make it work.

When I said "housekeeping" 
1. please update both Working.md and CHANGELOG.md by reading all ## recently finished section from Project_roadmap.md and then clean them up.
2. do cleanups if there were any previously added debug code.
3. Update Optimization.md by reading Agent_optimization.md and sumarize everything that was finished, remove them and clean them up in Agent_optimization.md. Updates in Optimization.md should be brief and to the point so that it is human readable.

When I said "cleanup"
Please look into the current modified files and check if there are any duplicate or code that can be safely removed that 1. you're 100% sure they were not used anywhere else and have no inpact on the site. 2. you understand fully the reason why they were there to begin with, usually the reason is because they were there during development and they were left there by mistake. 3. when you're in Doubt make sure to bring it up your findings.

When I said "optimize":
Please read the Agent_optimization.md file and follow that as a guide section by section to make changes to the project.
Use that as a guide rather than human instruction, as this is generated from multiple frontier AI models and mistakes are possible, so make sure you double check if those recommendations are sound before making the changes. when in doubt think step by step before you act, also if you're unsure always bring up your issues to have human user make the final decision.

## Rules:
When asked to "continue progress" please don't work on anything else other than the In progress section of the Project_roadmap.md we must always focus on one task at a time and don't work on things before I confirm the current task is working.

Don't open Simple Browser with http://localhost as this dev server is a remote server and it cannot be accessed from localhost, currently you can visit https://bold-mahavira8-wnl6g.view-3.tempo-dev.app/ instead with simple browser instead of localhost

## Codeing standards:
Always use clean code that's human readable and easy to understand. so that its possible for human and AI to work on the same code base

Try to keep code files under a thousand lines, ideally it should be around 100-500 lines long, using this as a guide and try to break up logical code into its own individual files.

Always comment the code, and make sure they're properly commented.

Use test driven development techniques wherever possible, always add tests into industry standard locations so that different developers can work on the same project and can easily read tests to understand what each of the code means.

