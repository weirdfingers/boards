#!/usr/bin/env node

/**
 * Baseboards CLI
 *
 * Main entry point for the @weirdfingers/baseboards command-line interface.
 * Provides commands to scaffold, run, and manage Baseboards installations.
 */

import { Command } from "commander";
import { readFileSync } from "fs";
import { fileURLToPath } from "url";
import { dirname, join } from "path";
import chalk from "chalk";

// Import commands
import { up } from "./commands/up.js";
import { down } from "./commands/down.js";
import { logs } from "./commands/logs.js";
import { status } from "./commands/status.js";
import { clean } from "./commands/clean.js";
import { update } from "./commands/update.js";
import { upgrade } from "./commands/upgrade.js";
import { doctor } from "./commands/doctor.js";
import { templates } from "./commands/templates.js";
import {
  TemplateDownloadError,
  displayError,
} from "./utils/template-downloader.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Read package.json for version
const packageJson = JSON.parse(
  readFileSync(join(__dirname, "../package.json"), "utf-8")
);

const program = new Command();

program
  .name("baseboards")
  .description(
    "🎨 One-command launcher for the Boards image generation platform"
  )
  .version(packageJson.version, "-v, --version", "Output the current version");

// up command
program
  .command("up")
  .description("Start Baseboards (scaffolds if needed)")
  .argument("[directory]", "Project directory", ".")
  .option("--attach", "Attach to logs (runs in foreground)")
  .option("--ports <ports>", "Custom ports (e.g., web=3300 api=8800)")
  .option("--fresh", "Clean up existing volumes before starting")
  .option("--app-dev", "Run frontend locally instead of in Docker")
  .option("--dev-packages", "Include unpublished @weirdfingers/boards source (requires --app-dev)")
  .option("--template <name>", "Frontend template to use (baseboards, basic)")
  .action(up);

// down command
program
  .command("down")
  .description("Stop Baseboards")
  .argument("[directory]", "Project directory", ".")
  .option("--volumes", "Also remove volumes")
  .action(down);

// logs command
program
  .command("logs")
  .description("View logs from services")
  .argument("[directory]", "Project directory", ".")
  .argument(
    "[services...]",
    "Services to show logs for (web, api, db, cache)",
    []
  )
  .option("-f, --follow", "Follow log output")
  .option("--since <time>", "Show logs since timestamp (e.g., 1h, 30m)")
  .option("--tail <lines>", "Number of lines to show from end", "100")
  .action(logs);

// status command
program
  .command("status")
  .description("Show status of services")
  .argument("[directory]", "Project directory", ".")
  .action(status);

// clean command
program
  .command("clean")
  .description("Clean up Docker resources")
  .argument("[directory]", "Project directory", ".")
  .option("--hard", "Remove volumes and images (WARNING: deletes data)")
  .action(clean);

// update command (deprecated - use upgrade instead)
program
  .command("update")
  .description("Update Baseboards to latest version (deprecated - use upgrade)")
  .argument("[directory]", "Project directory", ".")
  .option("--force", "Force update without safety checks")
  .option("--version <version>", "Update to specific version")
  .action(update);

// upgrade command
program
  .command("upgrade")
  .description("Upgrade Baseboards to a specific or latest version")
  .argument("[directory]", "Project directory", ".")
  .option("--version <version>", "Upgrade to specific version (default: latest)")
  .option("--dry-run", "Preview upgrade without making changes")
  .option("--force", "Skip confirmation prompts and compatibility warnings")
  .addHelpText('after', `
Examples:
  $ baseboards upgrade                      Upgrade to latest version
  $ baseboards upgrade --version 0.8.0      Upgrade to specific version
  $ baseboards upgrade --dry-run            Preview what would be upgraded
  $ baseboards upgrade --force              Skip confirmation prompts
  $ baseboards upgrade --dry-run --version 0.8.0
                                            Preview upgrade to specific version
`)
  .action(upgrade);

// doctor command
program
  .command("doctor")
  .description("Run diagnostics and show system info")
  .argument("[directory]", "Project directory", ".")
  .action(doctor);

// templates command
program
  .command("templates")
  .description("List available templates")
  .option("--refresh", "Clear cache and re-fetch templates")
  .option("--version <version>", "Show templates for specific version")
  .action(templates);

// Parse without exitOverride - let commander handle exits naturally
try {
  await program.parseAsync(process.argv);
} catch (error: unknown) {
  // Check if this is a template download error with custom formatting
  if (error instanceof TemplateDownloadError) {
    displayError(error);
    process.exit(1);
  }

  const err = error as { message?: string; stderr?: string };
  // Actual error (not help/version)
  console.error(chalk.red("\n❌ Error:"), err.message || "Unknown error");

  if (err.stderr) {
    console.error(chalk.gray("\nDetails:"));
    console.error(chalk.gray(err.stderr));
  }

  console.error(
    chalk.yellow("\n💡 Try running:"),
    chalk.cyan("baseboards doctor")
  );
  console.error(
    chalk.yellow("📖 Documentation:"),
    chalk.cyan("https://baseboards.dev/docs")
  );

  process.exit(1);
}
