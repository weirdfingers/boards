# Test Image Generation Flow

Run an end-to-end test of the image generation workflow using Playwright.

**Instructions:**

1. Navigate to http://localhost:3300 using `mcp__playwright__browser_navigate`

2. Take a snapshot to see the page structure using `mcp__playwright__browser_snapshot`

3. Click the "Create Board" button to create a new board

4. Wait for navigation to the board page and take another snapshot

5. Click the generator selector dropdown (button with text "Select Generator")

6. In the search input (placeholder "Search generators..."), type "fal-nano-banana"

7. Click on the "fal-nano-banana" option in the dropdown

8. Find the prompt textarea (placeholder contains "Describe what you want to generate") and type: "something amazing"

9. Click the generate button (button with title containing "Generate")

10. Wait 15 seconds using `mcp__playwright__browser_wait_for` with time parameter

11. Take a final snapshot and check for generated images

12. **Report the result:**
    - SUCCESS: If an image element with alt="Generated image" is visible
    - FAILURE: If no image is found or an error message is displayed
    - Include any error messages observed

**Key Playwright MCP Tools:**
- `mcp__playwright__browser_navigate` - Navigate to URL
- `mcp__playwright__browser_snapshot` - Get accessibility snapshot (better than screenshot for finding elements)
- `mcp__playwright__browser_click` - Click elements (requires element description and ref from snapshot)
- `mcp__playwright__browser_type` - Type text into inputs
- `mcp__playwright__browser_wait_for` - Wait for text or time

**Important Notes:**
- Always take a snapshot before interacting to get current element refs
- Use element descriptions and refs from the latest snapshot for clicks/types
- The generate button may be disabled until generator and prompt are set
- Generation may fail if the backend/worker is not running
