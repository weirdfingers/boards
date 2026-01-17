# Work on Ticket

This skill implements a ticket from the CLI revamp project by reading the ticket file, understanding the requirements, and completing the work described.

## Overview

This skill is designed to work with tickets in the `design/cli-revamp-tickets/` directory. Each ticket is a markdown file with structured sections:

- **Description**: What needs to be done
- **Dependencies**: Other tickets that must be completed first
- **Files to Create/Modify**: Specific files affected
- **Testing**: How to verify the implementation
- **Acceptance Criteria**: Checklist of requirements

The skill automates the process of implementing a ticket from start to finish, including running tests and updating the ticket status.

## Instructions

### Step 0: Check if Resuming (--resume flag)

**If the `--resume` flag is present:**

Before proceeding with the normal workflow, assess what progress has already been made:

1. **Read the ticket file** to understand what should have been done

2. **Check git status** to see what files have been modified:
   ```bash
   git status --short
   ```

3. **Check which files exist** from the "Files to Create/Modify" section:
   - For each file listed, check if it exists
   - If it exists, read it to understand what's been implemented

4. **Compare against acceptance criteria**:
   - Review each acceptance criteria checkbox
   - Determine which ones appear to be satisfied based on the current state
   - Note which ones are incomplete or unclear

5. **Check if tests have been run**:
   - Look for test output or logs
   - Check if any test commands from the Testing section were executed

6. **Present findings to the user**:
   Show a clear summary:
   ```
   ## Progress Assessment for [ticket-name]

   ### Files Modified:
   - ✅ file1.ts (created/modified)
   - ❌ file2.ts (not found)

   ### Acceptance Criteria Status:
   - ✅ Criterion 1 appears complete
   - ⚠️  Criterion 2 partially complete
   - ❌ Criterion 3 not started

   ### Tests:
   - ❌ No test results found

   ### Git Status:
   [show relevant git changes]
   ```

7. **Ask the user how to proceed** using AskUserQuestion:
   - "Continue from where it left off" (default, recommended)
   - "Re-run tests only"
   - "Start over from scratch"
   - "Mark as complete (if everything looks done)"
   - "Abort and keep current state"

Then proceed based on the user's choice.

**If no `--resume` flag:**

Continue with Step 1 below.

### Step 1: Read and Understand the Ticket

Read the ticket file specified in the arguments (or prompt the user if not provided):

```
The ticket file path should be something like: design/cli-revamp-tickets/CLI-X.Y.md
```

Parse the ticket structure and understand:
- What needs to be implemented
- Which files need to be created or modified
- What the acceptance criteria are
- What dependencies exist (if any)

### Step 2: Check Dependencies

If the ticket has dependencies listed in the **Dependencies** section:
- Read `design/cli-revamp-tickets/ticket-order.json`
- Verify that all dependency tickets have `"status": "completed"`
- If dependencies are not completed, inform the user and ask if they want to:
  - Work on the dependencies first
  - Skip dependency checking and proceed anyway
  - Abort

### Step 3: Plan the Implementation

Based on the ticket requirements:
- Identify all files that need to be created or modified
- Read existing files to understand the current codebase structure
- Create a plan for implementing the changes
- If the implementation is complex, use the TodoWrite tool to track subtasks

### Step 4: Implement the Changes

Follow the ticket's **Files to Create/Modify** section and **Acceptance Criteria**:
- Create new files as needed
- Modify existing files as required
- Follow the project's code style and conventions (see CLAUDE.md)
- Ensure all acceptance criteria checkboxes would be satisfied

### Step 5: Run Tests

Execute the tests specified in the **Testing** section:
- Run the exact commands listed in the Testing section
- Verify that all tests pass
- If tests fail, debug and fix the issues
- Re-run tests until they pass

### Step 6: Update Ticket Status

Once all acceptance criteria are met and tests pass:
- Update `design/cli-revamp-tickets/ticket-order.json`
- Change the status for this ticket from its current status to `"completed"`
- Use the Edit tool to make this change

### Step 7: Summary

Provide a summary of what was completed:
- List the files created or modified
- Confirm all acceptance criteria were met
- Show the test results
- Indicate that the ticket status has been updated to completed

## Arguments

- **ticket_path**: Path to the ticket file (e.g., `design/cli-revamp-tickets/CLI-2.4.md`)
- **--skip-deps**: (Optional) Skip dependency checking
- **--resume**: (Optional) Resume work on a ticket that's already in-progress

## Example Usage

```
/work-on-ticket design/cli-revamp-tickets/CLI-2.4.md
```

Or with options:

```
/work-on-ticket design/cli-revamp-tickets/CLI-2.4.md --skip-deps
```

## Notes

- Always read the project's CLAUDE.md file for code conventions
- Follow the existing code patterns in the repository
- Don't commit changes to git unless explicitly instructed by the user
- Be thorough in testing before marking a ticket as completed
