# FoodDNA UI Redesign — Start Here

This folder is the current FoodDNA source baseline prepared for the Antigravity UI redesign task.

## Open the correct workspace

1. Extract this ZIP to a new folder on your computer.
2. In Antigravity, choose **Open Folder** and select the inner `fooddna18` folder (the folder containing `backend`, `frontend`, `database`, `docs`, `tests`, and `requirements.txt`).
3. Open `docs/FoodDNA_UI_REDESIGN_PROMPT_WITH_RUN_GUIDE.md`, copy its entire contents into Antigravity, and ask it to implement the redesign now rather than only proposing a plan.
4. The visual reference is included at `design-reference/FoodDNA_UI_Reference_Collage.png`. Attach this image to the Antigravity conversation if the interface allows it.

## Safety notes

- This ZIP intentionally does not include `.env` or database credentials. Do not add secrets to the prompt or project archive.
- Keep your current working folder and its `.env` file as a backup. Apply the redesigned project in a separate folder first.
- Do not run migrations against your real `fooddna` database. Verify the actual database configuration and inspect scripts before executing database-changing commands.
- The source baseline contains existing code and tests, but a complete browser-based validation of every workflow is not implied by the presence of those files.

## What Antigravity must do

Inspect this source first, preserve existing functionality, redesign the actual pages to match the reference, fix compatible defects and validation inconsistencies, add beginner-friendly Windows setup/run instructions based on the real project, run and report checks accurately, and create a verified final archive without secrets or virtual environments.
