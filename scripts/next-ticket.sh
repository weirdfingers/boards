#!/bin/bash
# next-ticket.sh
#
# Finds the next incomplete ticket and invokes Claude Code to work on it.
# Uses the work-on-ticket skill to implement the ticket requirements.
# Automatically commits changes if the ticket reaches completed status.

set -e

TICKET_ORDER_FILE="design/cli-revamp-tickets/ticket-order.json"

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "❌ Error: jq is required but not installed."
    echo "   Install with: brew install jq"
    exit 1
fi

# Check if claude command is available
if ! command -v claude &> /dev/null; then
    echo "❌ Error: claude command is not available."
    echo "   Make sure Claude Code CLI is installed and in your PATH."
    exit 1
fi

# Check if ticket order file exists
if [ ! -f "$TICKET_ORDER_FILE" ]; then
    echo "❌ Error: Ticket order file not found: $TICKET_ORDER_FILE"
    exit 1
fi

# Find first non-completed ticket
NEXT_TICKET=$(jq -r '.[] | select(.status != "completed") | .ticket' "$TICKET_ORDER_FILE" | head -n 1)

if [ -z "$NEXT_TICKET" ]; then
    echo "🎉 All tickets are completed!"
    exit 0
fi

# Get the initial status
INITIAL_STATUS=$(jq -r --arg ticket "$NEXT_TICKET" '.[] | select(.ticket == $ticket) | .status' "$TICKET_ORDER_FILE")

echo "📋 Next ticket: $NEXT_TICKET"
echo "📊 Current status: $INITIAL_STATUS"
echo ""

# Handle based on status
if [ "$INITIAL_STATUS" = "not-started" ]; then
    echo "✅ Updating status to 'in-progress'..."

    # Update status to in-progress
    jq --arg ticket "$NEXT_TICKET" \
       '(.[] | select(.ticket == $ticket) | .status) = "in-progress"' \
       "$TICKET_ORDER_FILE" > "${TICKET_ORDER_FILE}.tmp" && \
    mv "${TICKET_ORDER_FILE}.tmp" "$TICKET_ORDER_FILE"

    echo "🤖 Invoking Claude Code to work on ticket..."
    echo ""

    # Invoke Claude Code with the work-on-ticket command
    claude "/work-on-ticket $NEXT_TICKET"

elif [ "$INITIAL_STATUS" = "in-progress" ]; then
    echo "⚠️  Ticket is already in progress."
    echo "🤖 Invoking Claude Code to resume work on ticket..."
    echo ""

    # Invoke Claude Code with the resume-ticket command
    claude "/resume-ticket $NEXT_TICKET"

else
    echo "⚠️  Ticket has unexpected status: $INITIAL_STATUS"
    echo "🤖 Invoking Claude Code to check the ticket..."
    echo ""

    # Invoke Claude Code with the work-on-ticket command
    claude "/project:work-on-ticket $NEXT_TICKET"
fi

# After Claude finishes, check if the ticket was completed
FINAL_STATUS=$(jq -r --arg ticket "$NEXT_TICKET" '.[] | select(.ticket == $ticket) | .status' "$TICKET_ORDER_FILE")

if [ "$FINAL_STATUS" = "completed" ] && [ "$INITIAL_STATUS" != "completed" ]; then
    echo ""
    echo "✅ Ticket completed! Creating git commit..."

    # Extract ticket number and read first line of description for commit message
    TICKET_NUM=$(basename "$NEXT_TICKET" .md)
    DESCRIPTION=$(head -n 3 "$NEXT_TICKET" | tail -n 1)

    # Add all changes
    git add -A

    # Create commit with descriptive message
    git commit -m "Complete ticket $TICKET_NUM

$DESCRIPTION

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"

    echo "✅ Changes committed successfully!"
    echo ""
    echo "📊 Git log:"
    git log -1 --oneline
elif [ "$FINAL_STATUS" = "completed" ]; then
    echo ""
    echo "✅ Ticket was already completed (no new commit needed)"
else
    echo ""
    echo "⚠️  Ticket status: $FINAL_STATUS (not completed yet)"
    echo "   No commit created. Run this script again to continue."
fi
