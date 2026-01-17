# Resume Work on Ticket

You are being asked to resume work on an in-progress ticket from the CLI revamp project. Follow the work-on-ticket skill instructions from `.claude/skills/work-on-ticket.md` with the **--resume flag behavior**.

The ticket to resume is: $ARGUMENTS

**Instructions:**
1. Read the ticket file at the path provided in $ARGUMENTS
2. Follow Step 0 (--resume flag) from the work-on-ticket skill:
   - Check git status
   - Check which files exist
   - Compare against acceptance criteria
   - Present findings to the user
   - Ask how to proceed using AskUserQuestion
3. Based on user choice, continue implementation
4. Run tests as needed
5. Update the ticket status to "completed" in `design/cli-revamp-tickets/ticket-order.json` when done
