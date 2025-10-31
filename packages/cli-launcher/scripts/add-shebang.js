#!/usr/bin/env node

/**
 * Add shebang to built CLI file
 *
 * This script runs after tsup build to add the shebang line
 * and make the file executable. We do this post-build because
 * adding shebang via tsup banner can cause issues with Node ESM.
 */

import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const distFile = path.join(__dirname, "../dist/index.js");

if (!fs.existsSync(distFile)) {
  console.error("❌ dist/index.js not found!");
  process.exit(1);
}

// Read the file
let content = fs.readFileSync(distFile, "utf8");

// Check if shebang already exists
if (!content.startsWith("#!/usr/bin/env node")) {
  // Add shebang at the beginning
  content = `#!/usr/bin/env node\n${content}`;

  // Write it back
  fs.writeFileSync(distFile, content);
  console.log("✅ Added shebang to dist/index.js");
} else {
  console.log("✅ Shebang already present in dist/index.js");
}

// Make it executable
fs.chmodSync(distFile, "755");
