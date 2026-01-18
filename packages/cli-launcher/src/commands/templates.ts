/**
 * templates command - List available templates
 */

import chalk from "chalk";
import { getCliVersion } from "../utils.js";
import {
  fetchTemplateManifest,
  clearCache,
  type TemplateManifest,
  type TemplateInfo,
} from "../utils/template-downloader.js";

interface TemplatesOptions {
  refresh?: boolean;
  version?: string;
}

/**
 * Format bytes to human-readable size
 */
function formatSize(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  } else if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(1)} KB`;
  } else {
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
}

/**
 * Display a single template
 */
function displayTemplate(template: TemplateInfo, isRecommended: boolean): void {
  // Template name (bold)
  const name = chalk.bold(template.name);
  const recommended = isRecommended ? chalk.cyan(" (recommended)") : "";
  console.log(`\n${name}${recommended}`);

  // Description
  console.log(`  ${template.description}`);

  // Frameworks
  const frameworks = template.frameworks.join(", ");
  console.log(`  ${chalk.gray("Frameworks:")} ${frameworks}`);

  // Features
  const features = template.features.join(", ");
  console.log(`  ${chalk.gray("Features:")} ${features}`);

  // Size
  const size = formatSize(template.size);
  console.log(`  ${chalk.gray("Size:")} ${size}`);
}

/**
 * List available templates
 */
export async function templates(options: TemplatesOptions): Promise<void> {
  try {
    // Clear cache if --refresh flag is provided
    if (options.refresh) {
      console.log(chalk.blue("🔄 Clearing cache and refreshing templates...\n"));
      await clearCache();
    }

    // Determine version to use
    const version = options.version || getCliVersion();

    // Fetch manifest
    let manifest: TemplateManifest;
    try {
      manifest = await fetchTemplateManifest(version);
    } catch (error: any) {
      // Network error - try to use cached version if available
      if (error.message.includes("Failed to fetch")) {
        console.error(
          chalk.red("\n❌ Network error:"),
          "Unable to fetch template list"
        );
        console.log(
          chalk.yellow("\n💡 Tip:"),
          "Check your internet connection or try again later"
        );
        process.exit(1);
      }

      // Version not found
      if (error.message.includes("not found")) {
        console.error(
          chalk.red("\n❌ Version not found:"),
          `Version ${version} does not exist`
        );
        console.log(
          chalk.yellow("\n💡 Tip:"),
          "Check available versions at:",
          chalk.cyan("https://github.com/weirdfingers/boards/releases")
        );
        process.exit(1);
      }

      // Other errors
      throw error;
    }

    // No templates available
    if (!manifest.templates || manifest.templates.length === 0) {
      console.log(
        chalk.yellow("\n⚠️  No templates available for version"),
        manifest.version
      );
      process.exit(0);
    }

    // Display header
    console.log(
      chalk.blue.bold(`\n📦 Available templates for v${manifest.version}:`)
    );

    // Display each template
    // Mark "baseboards" as recommended
    for (const template of manifest.templates) {
      const isRecommended = template.name === "baseboards";
      displayTemplate(template, isRecommended);
    }

    console.log(); // Empty line at end
  } catch (error: any) {
    console.error(chalk.red("\n❌ Error:"), error.message || "Unknown error");

    console.error(
      chalk.yellow("\n💡 Try running:"),
      chalk.cyan("baseboards doctor")
    );
    process.exit(1);
  }
}
