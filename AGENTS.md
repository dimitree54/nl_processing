## Project Context
- This is a UV + pyproject managed Python repo. All commands run through `uv`.
- All secrets are managed through `doppler` envs
- The repo has multi-package structure. When working on new features - you will work with one (or if needed several packages). Do not over-explore unrelated packages. Each package has its own docs, tests, linters and so on.
- Before and after the task, `make check` of the affected modules must be 100% green. This is non-negotiable.
- We write production software. Always prefer proper solutions over quick hacks. No compromises. No workarounds.

## Documentation driven repo
All code should always be 100% in sync with docs. We write code based on the docs, never otherwise. We do not change docs to match code. If during work you find that some existing code is not documented or contradicts with docs - stop your work and report to user.

# Core development principles:
- Fail fast on unexpected situations
  - Zero fallbacks tolerance - fail fast, no defaults, no fallbacks.
- Zero legacy tolerance - make full proper refactorings
- No errors hiding
  - If something does not work because of the problem in users library or tg_auto_test or demo_ui - do not work around it. Stop and report to user.
  - Properly fix linter warnings, do not hide them. If needed - do proper refactoring. Do not be lazy. Choose proper solutions over easy.
  
## File size limit
We have linter limiting files to be no more than 200 lines. 
It means that when approaching the limit - plan logical file decomposition refactoring. 
NEVER try to save lines by re-formatting - decompose the file.
NEVER try to compact code - decompose the file.
NEVER use suboptimal, but more compact solutions just to fit in 200 lines - decompose the file and use the optimal solution.
NEVER try to make several things in one line to save space - decompose the file.
It is just a strong signal for refactoring. In fact, the optimal length is below 180. So the file above 180 lines is already a weak signal for refactoring.

# Concurrent modifications
If you notice that some files are unexpectedly modified (not by you) - do not rever these changes,
probably the user is working on the same file. If it is blocking you - stop and contact the user to sync. Or if these changes are not breaking for you - proceed. But never revert unexpected changes!