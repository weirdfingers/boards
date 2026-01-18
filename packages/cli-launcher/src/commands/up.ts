/**
 * up command - Scaffold and start Baseboards
 */

import { execa } from "execa";
import fs from "fs-extra";
import path from "path";
import chalk from "chalk";
import ora from "ora";
import prompts from "prompts";
import type { ProjectContext, UpOptions } from "../types.js";
import {
  assertPrerequisites,
  findAvailablePort,
  generatePassword,
  generateSecret,
  getCliVersion,
  isScaffolded,
  parsePortsOption,
  detectMissingProviderKeys,
  waitFor,
  promptPackageManager,
  type PackageManager,
} from "../utils.js";
import { detectMonorepoRoot } from "../utils/monorepo-detection.js";
import {
  copyFrontendPackage,
  updatePackageJsonForDevPackages,
} from "../utils/package-copy.js";
import {
  downloadTemplate,
  fetchTemplateManifest,
} from "../utils/template-downloader.js";

/**
 * Validate that a template name is available by fetching the manifest.
 * @param templateName Template name to validate
 * @param version CLI version
 */
async function validateTemplate(
  templateName: string,
  version: string
): Promise<void> {
  const manifest = await fetchTemplateManifest(version);
  const availableTemplates = manifest.templates.map(t => t.name);

  if (!availableTemplates.includes(templateName)) {
    throw new Error(
      `Template '${templateName}' not found. Available templates: ${availableTemplates.join(", ")}`
    );
  }
}

/**
 * Install frontend dependencies using the selected package manager.
 * Only runs in app-dev mode after backend services are healthy.
 * Prompts user to select their package manager if not already set.
 *
 * @param ctx Project context
 * @throws Error if installation fails
 */
async function installFrontendDependencies(ctx: ProjectContext): Promise<void> {
  const webDir = path.join(ctx.dir, "web");

  // Check if package.json exists
  const packageJsonPath = path.join(webDir, "package.json");
  if (!fs.existsSync(packageJsonPath)) {
    console.log(chalk.yellow("\n⚠️  No package.json found in web directory, skipping dependency installation"));
    return;
  }

  // Prompt for package manager if not already set
  if (!ctx.packageManager) {
    ctx.packageManager = await promptPackageManager();
  }

  const packageManager = ctx.packageManager;

  // Show progress
  console.log(chalk.cyan(`\n📦 Installing frontend dependencies with ${packageManager}...`));

  // Determine install command (all package managers use "install")
  const installCmd = "install";

  // Run install
  try {
    await execa(packageManager, [installCmd], {
      cwd: webDir,
      stdio: "inherit", // Show install output to user
    });
    console.log(chalk.green("✅ Dependencies installed successfully\n"));
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    console.error(chalk.red(`\n❌ Failed to install dependencies: ${errorMessage}`));

    // Provide helpful error messages
    console.log(chalk.yellow("\nTroubleshooting:"));
    console.log(chalk.gray("  • Check that package.json is valid:"), chalk.cyan(`${webDir}/package.json`));
    console.log(chalk.gray(`  • Ensure ${packageManager} is installed:`), chalk.cyan(`${packageManager} --version`));
    console.log(chalk.gray("  • Try running the install manually:"), chalk.cyan(`cd ${webDir} && ${packageManager} install`));

    throw error;
  }
}

/**
 * Prompts user to select a frontend template from available options.
 * Fetches template manifest and displays interactive selection.
 * @param version CLI version to fetch templates for
 * @returns Selected template name
 */
async function promptTemplateSelection(version: string): Promise<string> {
  try {
    // Fetch manifest
    const manifest = await fetchTemplateManifest(version);

    // Build choices
    const choices = manifest.templates.map((template) => ({
      title:
        template.name === "baseboards"
          ? `${template.name}    ${template.description} (recommended)`
          : `${template.name}         ${template.description}`,
      value: template.name,
    }));

    // Prompt user
    const { selectedTemplate } = await prompts({
      type: "select",
      name: "selectedTemplate",
      message: "Select a frontend template:",
      choices: choices,
      initial: 0, // Default to first (baseboards)
    });

    // Handle cancellation
    if (!selectedTemplate) {
      console.log("\nTemplate selection cancelled");
      process.exit(0);
    }

    return selectedTemplate;
  } catch (error) {
    console.error("Failed to fetch template list. Check your internet connection.");
    console.log("Falling back to default template: baseboards");
    return "baseboards"; // Graceful fallback
  }
}

export async function up(directory: string, options: UpOptions): Promise<void> {
  console.log(chalk.blue.bold("\n🎨 Baseboards CLI\n"));

  // Step 1: Check prerequisites
  const spinner = ora("Checking prerequisites...").start();
  await assertPrerequisites();
  spinner.succeed("Prerequisites OK");

  // Step 2: Resolve project context
  const dir = path.resolve(process.cwd(), directory);
  const name = path.basename(dir);
  const version = getCliVersion();

  // Parse custom ports
  let customPorts = {};
  if (options.ports) {
    customPorts = parsePortsOption(options.ports);
  }

  // Default ports
  const defaultPorts = {
    web: 3300,
    api: 8800,
    db: 5432,
    redis: 6379,
    ...customPorts,
  };

  const appDev = options.appDev || false;
  const devPackages = options.devPackages || false;

  // Validate: --dev-packages requires --app-dev
  if (devPackages && !appDev) {
    throw new Error(
      '--dev-packages requires --app-dev mode. ' +
      'Docker-based web service cannot use local package sources.'
    );
  }

  // Validate: --dev-packages requires running from monorepo
  let monorepoRoot: string | undefined;
  if (devPackages) {
    const detectedRoot = await detectMonorepoRoot();
    if (!detectedRoot) {
      throw new Error(
        '--dev-packages requires running from within the Boards monorepo.\n\n' +
        'This feature is for Boards contributors testing unpublished package changes.\n' +
        'Clone the monorepo and run: cd boards && pnpm cli up <dir> --app-dev --dev-packages\n\n' +
        'If you want to develop apps using the published package, use --app-dev without --dev-packages.'
      );
    }
    monorepoRoot = detectedRoot;
  }

  // Step 2.5: Determine template to use
  let selectedTemplate: string;

  if (options.template) {
    // Explicit flag provided
    await validateTemplate(options.template, version);
    selectedTemplate = options.template;
  } else {
    // Interactive selection
    selectedTemplate = await promptTemplateSelection(version);
  }

  const ctx: ProjectContext = {
    dir,
    name,
    isScaffolded: isScaffolded(dir),
    ports: defaultPorts,
    version,
    appDev,
    devPackages,
    template: selectedTemplate,
    monorepoRoot,
  };

  // Track if this is a fresh scaffold to prompt for API keys later
  const isFreshScaffold = !ctx.isScaffolded;

  // Step 3: Handle existing volumes if needed
  // If user wants fresh start OR if scaffolding fresh but volumes exist
  if (options.fresh || !ctx.isScaffolded) {
    const hasExistingVolumes = await checkForExistingVolumes();

    if (hasExistingVolumes) {
      if (options.fresh) {
        // --fresh flag provided, clean up without prompting
        await cleanupDockerVolumes(ctx);
      } else if (!ctx.isScaffolded) {
        // Scaffolding fresh but volumes exist - prompt user
        console.log(
          chalk.yellow(
            "\n⚠️  Existing Docker volumes detected from a previous installation"
          )
        );
        console.log(
          chalk.gray(
            "   To avoid password mismatch errors, you can start fresh or cancel."
          )
        );
        console.log(
          chalk.gray(
            "   Starting fresh will delete ALL existing data (boards, generated images, users)."
          )
        );

        const response = await prompts({
          type: "confirm",
          name: "cleanVolumes",
          message: "Delete existing volumes and start fresh?",
          initial: true,
        });

        if (response.cleanVolumes === undefined) {
          // User cancelled (Ctrl+C)
          console.log(chalk.yellow("\n⚠️  Cancelled by user"));
          process.exit(0);
        }

        if (response.cleanVolumes) {
          await cleanupDockerVolumes(ctx);
        } else {
          console.log(
            chalk.yellow(
              "\n⚠️  Proceeding without cleaning volumes. If you encounter password errors:"
            )
          );
          console.log(
            chalk.cyan("   baseboards up --fresh") +
              chalk.gray(" (start fresh)")
          );
          console.log(
            chalk.cyan("   baseboards down --volumes && baseboards up") +
              chalk.gray(" (manual cleanup)")
          );
        }
      }
    }
  }

  // Step 4: Scaffold if needed
  if (!ctx.isScaffolded) {
    console.log(
      chalk.cyan(`\n📦 Scaffolding new project: ${chalk.bold(name)}`)
    );
    await scaffoldProject(ctx);
  } else {
    console.log(
      chalk.green(`\n✅ Project already scaffolded: ${chalk.bold(name)}`)
    );
  }

  // Step 4.5: Copy and link dev packages if requested
  if (ctx.devPackages && ctx.monorepoRoot) {
    const spinner = ora("Copying @weirdfingers/boards source from monorepo...").start();
    try {
      const targetFrontend = path.join(ctx.dir, "frontend");
      await copyFrontendPackage(ctx.monorepoRoot, targetFrontend);
      spinner.succeed("Package source copied");

      spinner.start("Linking local package...");
      const webDir = path.join(ctx.dir, "web");
      await updatePackageJsonForDevPackages(webDir);
      spinner.succeed("Local package linked successfully");
    } catch (error) {
      spinner.fail("Failed to setup dev-packages mode");
      throw error;
    }
  }

  // Step 5: Check ports availability
  spinner.start("Checking port availability...");
  ctx.ports.web = await findAvailablePort(ctx.ports.web);
  ctx.ports.api = await findAvailablePort(ctx.ports.api);
  spinner.succeed(
    `Ports available: web=${ctx.ports.web}, api=${ctx.ports.api}`
  );

  // Step 5: Ensure environment files
  await ensureEnvFiles(ctx);

  // Step 5.5: Prompt for API keys (only on fresh scaffold)
  if (isFreshScaffold) {
    await promptForApiKeys(ctx);
  }

  // Step 6: Detect missing API keys
  const apiEnvPath = path.join(ctx.dir, "api/.env");
  const missingKeys = detectMissingProviderKeys(apiEnvPath);

  if (missingKeys.length > 0) {
    console.log(chalk.yellow("\n⚠️  Provider API keys not configured!"));
    console.log(chalk.gray("   Add at least one API key to api/.env:"));
    console.log(
      chalk.cyan("   • REPLICATE_API_TOKEN") +
        chalk.gray(" - https://replicate.com/account/api-tokens")
    );
    console.log(
      chalk.cyan("   • FAL_KEY") +
        chalk.gray(" - https://fal.ai/dashboard/keys")
    );
    console.log(
      chalk.cyan("   • KIE_API_KEY") + chalk.gray(" - https://kie.ai/dashboard")
    );
    console.log(
      chalk.cyan("   • OPENAI_API_KEY") +
        chalk.gray(" - https://platform.openai.com/api-keys")
    );
    console.log(
      chalk.cyan("   • GOOGLE_API_KEY") +
        chalk.gray(" - https://makersuite.google.com/app/apikey")
    );
    console.log(
      chalk.gray(
        "\n   The app will start, but image generation won't work without keys.\n"
      )
    );
  }

  // Step 7: Start Docker Compose (always detached initially)
  await startDockerCompose(ctx);

  // Step 8: Wait for health checks
  await waitForHealthy(ctx);

  // Step 9: Run database migrations
  await runMigrations(ctx);

  // Step 9.5: Install frontend dependencies in app-dev mode
  if (ctx.appDev) {
    await installFrontendDependencies(ctx);
  }

  // Step 10: Print success message
  printSuccessMessage(ctx, !options.attach, missingKeys.length > 0);

  // Step 11: Attach to logs if --attach flag is provided
  if (options.attach) {
    try {
      await attachToLogs(ctx);
    } catch (error: unknown) {
      // Handle Ctrl+C gracefully
      const maybeProcError = error as { signal?: string; exitCode?: number };
      if (
        maybeProcError.signal === "SIGINT" ||
        maybeProcError.exitCode === 130
      ) {
        console.log(chalk.yellow("\n\n⚠️  Interrupted - services stopped"));
        process.exit(0);
      }
      throw error;
    }
  }
}

/**
 * Scaffold a new project by downloading the template
 */
async function scaffoldProject(ctx: ProjectContext): Promise<void> {
  // Create project directory
  fs.ensureDirSync(ctx.dir);

  // Download template (with progress indicators)
  await downloadTemplate(ctx.template, ctx.version, ctx.dir);

  // Create data/storage directory (needed for runtime)
  const spinner = ora("Creating data directories...").start();
  fs.ensureDirSync(path.join(ctx.dir, "data/storage"));
  spinner.succeed("Data directories created");

  console.log(chalk.green("   ✨ Project scaffolded successfully!"));
}

/**
 * Ensure .env files exist and are populated
 */
async function ensureEnvFiles(ctx: ProjectContext): Promise<void> {
  const spinner = ora("Configuring environment...").start();

  // Web .env
  const webEnvPath = path.join(ctx.dir, "web/.env");
  const webEnvExamplePath = path.join(ctx.dir, "web/.env.example");

  if (!fs.existsSync(webEnvPath) && fs.existsSync(webEnvExamplePath)) {
    let webEnv = fs.readFileSync(webEnvExamplePath, "utf-8");
    webEnv = webEnv.replace(
      "http://localhost:8800",
      `http://localhost:${ctx.ports.api}`
    );
    fs.writeFileSync(webEnvPath, webEnv);
  }

  // API .env
  const apiEnvPath = path.join(ctx.dir, "api/.env");
  const apiEnvExamplePath = path.join(ctx.dir, "api/.env.example");

  if (!fs.existsSync(apiEnvPath) && fs.existsSync(apiEnvExamplePath)) {
    let apiEnv = fs.readFileSync(apiEnvExamplePath, "utf-8");

    // Generate JWT secret if not present
    if (
      apiEnv.includes("BOARDS_JWT_SECRET=\n") ||
      apiEnv.includes("BOARDS_JWT_SECRET=\r\n")
    ) {
      const jwtSecret = generateSecret(32);
      apiEnv = apiEnv.replace(
        /BOARDS_JWT_SECRET=.*$/m,
        `BOARDS_JWT_SECRET=${jwtSecret}`
      );
    }

    fs.writeFileSync(apiEnvPath, apiEnv);
  }

  // Docker .env
  const dockerEnvPath = path.join(ctx.dir, "docker/.env");
  const dockerEnvExamplePath = path.join(ctx.dir, "docker/env.example");

  if (!fs.existsSync(dockerEnvPath) && fs.existsSync(dockerEnvExamplePath)) {
    let dockerEnv = fs.readFileSync(dockerEnvExamplePath, "utf-8");

    // Generate database password
    const dbPassword = generatePassword(24);
    // URL-encode the password for use in database URLs
    const dbPasswordEncoded = encodeURIComponent(dbPassword);

    dockerEnv = dockerEnv.replace(
      /POSTGRES_PASSWORD=.*/g,
      `POSTGRES_PASSWORD=${dbPassword}`
    );
    dockerEnv = dockerEnv.replace(
      /REPLACE_WITH_GENERATED_PASSWORD/g,
      dbPasswordEncoded
    );

    // Set ports
    dockerEnv = dockerEnv.replace(/WEB_PORT=.*/g, `WEB_PORT=${ctx.ports.web}`);
    dockerEnv = dockerEnv.replace(/API_PORT=.*/g, `API_PORT=${ctx.ports.api}`);

    // Set version
    dockerEnv = dockerEnv.replace(/VERSION=.*/g, `VERSION=${ctx.version}`);

    // Set project name
    dockerEnv = dockerEnv.replace(
      /PROJECT_NAME=.*/g,
      `PROJECT_NAME=${ctx.name}`
    );

    fs.writeFileSync(dockerEnvPath, dockerEnv);
  }

  spinner.succeed("Environment configured");
}

/**
 * Prompt user for API keys during initial scaffold
 */
async function promptForApiKeys(ctx: ProjectContext): Promise<void> {
  console.log(chalk.cyan("\n🔑 API Key Configuration"));
  console.log(chalk.gray("Add API keys to enable image generation providers"));
  console.log(chalk.gray("Press Enter to skip any key\n"));

  const response = await prompts([
    {
      type: "password",
      name: "REPLICATE_API_TOKEN",
      message: "Replicate API Key (https://replicate.com/account/api-tokens):",
      initial: "",
    },
    {
      type: "password",
      name: "FAL_KEY",
      message: "Fal AI API Key (https://fal.ai/dashboard/keys):",
      initial: "",
    },
    {
      type: "password",
      name: "KIE_API_KEY",
      message: "Kie AI API Key (https://kie.ai/dashboard):",
      initial: "",
    },
    {
      type: "password",
      name: "OPENAI_API_KEY",
      message: "OpenAI API Key (https://platform.openai.com/api-keys):",
      initial: "",
    },
  ]);

  // Build the API keys dictionary (only include non-empty keys)
  const apiKeys: Record<string, string> = {};

  if (response.REPLICATE_API_TOKEN && response.REPLICATE_API_TOKEN.trim()) {
    apiKeys.REPLICATE_API_TOKEN = response.REPLICATE_API_TOKEN.trim();
  }

  if (response.FAL_KEY && response.FAL_KEY.trim()) {
    apiKeys.FAL_KEY = response.FAL_KEY.trim();
  }

  if (response.KIE_API_KEY && response.KIE_API_KEY.trim()) {
    apiKeys.KIE_API_KEY = response.KIE_API_KEY.trim();
  }

  if (response.OPENAI_API_KEY && response.OPENAI_API_KEY.trim()) {
    apiKeys.OPENAI_API_KEY = response.OPENAI_API_KEY.trim();
  }

  // Only write if we have at least one key
  if (Object.keys(apiKeys).length > 0) {
    // Read current api/.env
    const apiEnvPath = path.join(ctx.dir, "api/.env");
    let apiEnv = fs.readFileSync(apiEnvPath, "utf-8");

    // Format as JSON string for the environment variable
    const jsonKeys = JSON.stringify(apiKeys);

    // Update or add BOARDS_GENERATOR_API_KEYS
    if (apiEnv.includes("BOARDS_GENERATOR_API_KEYS=")) {
      apiEnv = apiEnv.replace(
        /BOARDS_GENERATOR_API_KEYS=.*$/m,
        `BOARDS_GENERATOR_API_KEYS=${jsonKeys}`
      );
    } else {
      // Add it after the JWT secret section
      apiEnv = apiEnv.replace(
        /(BOARDS_JWT_SECRET=.*\n)/,
        `$1\n# Generator API Keys (JSON format)\nBOARDS_GENERATOR_API_KEYS=${jsonKeys}\n`
      );
    }

    fs.writeFileSync(apiEnvPath, apiEnv);

    console.log(chalk.green("\n✅ API keys saved to api/.env"));
    console.log(
      chalk.gray("   You can edit this file anytime to add/update keys\n")
    );
  } else {
    console.log(chalk.yellow("\n⚠️  No API keys provided"));
    console.log(chalk.gray("   You can add them later by editing api/.env\n"));
  }
}

/**
 * Get list of compose files to load.
 * Always loads base compose.yaml (backend services).
 * Conditionally loads compose.web.yaml (web service overlay).
 *
 * In app-dev mode (--app-dev flag), only backend services are started in Docker,
 * allowing the frontend to be run locally for faster development iteration.
 *
 * @param ctx Project context
 * @returns Array of compose file names relative to project directory
 */
function getComposeFiles(ctx: ProjectContext): string[] {
  const files = ["compose.yaml"]; // Always load base

  // Only add web overlay if NOT in app-dev mode
  if (!ctx.appDev) {
    files.push("compose.web.yaml");
  }

  return files;
}

/**
 * Get base docker compose arguments for all compose commands.
 * Includes env file configuration and compose file list (which varies based on app-dev mode).
 *
 * @param ctx Project context
 * @returns Array of docker compose base arguments
 */
function getComposeBaseArgs(ctx: ProjectContext): string[] {
  // IMPORTANT: use docker/.env for compose interpolation (e.g. PROJECT_NAME, ports)
  // and keep it in sync with env_file usage inside compose.yaml.
  return [
    "compose",
    "--env-file",
    "docker/.env",
    ...getComposeFiles(ctx).flatMap((f) => ["-f", f]),
  ];
}

/**
 * Start Docker Compose (always in detached mode)
 */
async function startDockerCompose(ctx: ProjectContext): Promise<void> {
  const spinner = ora("Starting Docker Compose...").start();

  // Check that all compose files exist before starting
  const composeFiles = getComposeFiles(ctx);
  for (const file of composeFiles) {
    const filePath = path.join(ctx.dir, file);
    if (!fs.existsSync(filePath)) {
      spinner.fail(`Compose file not found: ${file}`);
      throw new Error(`Compose file not found: ${file}`);
    }
  }

  const composeArgs = [
    ...getComposeBaseArgs(ctx),
    "up",
    "-d",
    "--build",
    "--remove-orphans",
  ];

  try {
    await execa("docker", composeArgs, {
      cwd: ctx.dir,
      stdio: "inherit",
    });
    spinner.succeed("Docker Compose started");
  } catch (error: unknown) {
    spinner.fail("Failed to start Docker Compose");
    throw error;
  }
}

/**
 * Attach to Docker Compose logs (foreground)
 */
async function attachToLogs(ctx: ProjectContext): Promise<void> {
  console.log(
    chalk.gray("\n─────────────────────────────────────────────────────")
  );
  console.log(chalk.gray("Streaming logs... (Press Ctrl+C to stop)\n"));

  const composeArgs = [...getComposeBaseArgs(ctx), "logs", "-f"];

  await execa("docker", composeArgs, {
    cwd: ctx.dir,
    stdio: "inherit",
  });
}

/**
 * Wait for services to become healthy.
 * In app-dev mode, only waits for backend services (no web service).
 */
async function waitForHealthy(ctx: ProjectContext): Promise<void> {
  const spinner = ora("Waiting for services to be healthy...").start();

  // In app-dev mode, only wait for backend services (web runs locally)
  const services = ["db", "cache", "api", "worker"];
  if (!ctx.appDev) {
    services.push("web");
  }
  const maxWaitMs = 120_000; // 2 minutes

  type ComposePsEntry = {
    Service?: string;
    Health?: string;
    State?: string;
  };

  const checkHealth = async (): Promise<boolean> => {
    try {
      const { stdout } = await execa(
        "docker",
        [...getComposeBaseArgs(ctx), "ps", "--format", "json"],
        {
          cwd: ctx.dir,
        }
      );

      const containers = stdout
        .split("\n")
        .filter(Boolean)
        .map((line) => JSON.parse(line) as ComposePsEntry);

      const allHealthy = services.every((service) => {
        const container = containers.find((c) => c.Service === service);
        return (
          container &&
          (container.Health === "healthy" || container.State === "running")
        );
      });

      return allHealthy;
    } catch {
      return false;
    }
  };

  const success = await waitFor(checkHealth, {
    timeoutMs: maxWaitMs,
    intervalMs: 2000,
    onProgress: (elapsed) => {
      const seconds = Math.floor(elapsed / 1000);
      spinner.text = `Waiting for services to be healthy... (${seconds}s)`;
    },
  });

  if (success) {
    spinner.succeed("All services healthy");
  } else {
    spinner.warn("Services taking longer than expected...");
    console.log(
      chalk.yellow(
        "\n⚠️  Health check timeout. Services may still be starting."
      )
    );
    console.log(
      chalk.gray("   Run"),
      chalk.cyan("baseboards logs"),
      chalk.gray("to check progress.")
    );
  }
}

/**
 * Run database migrations
 */
async function runMigrations(ctx: ProjectContext): Promise<void> {
  const spinner = ora("Running database migrations...").start();

  try {
    await execa(
      "docker",
      [
        ...getComposeBaseArgs(ctx),
        "exec",
        "-T",
        "api",
        "alembic",
        "upgrade",
        "head",
      ],
      {
        cwd: ctx.dir,
      }
    );
    spinner.succeed("Database migrations complete");
  } catch (error) {
    spinner.fail("Database migrations failed");

    // Check if this is a password authentication error
    const errorMessage = error instanceof Error ? error.message : String(error);
    const isPasswordError =
      errorMessage.includes("password authentication failed") ||
      errorMessage.includes("InvalidPasswordError");

    if (isPasswordError) {
      console.log(
        chalk.red(
          "\n❌ Database password mismatch - cannot connect to existing database"
        )
      );
      console.log(
        chalk.yellow(
          "   Existing database volumes have a different password than the current configuration."
        )
      );
      console.log(chalk.yellow("\n   To fix this, choose one of:"));
      console.log(
        chalk.cyan("   1. Start fresh (deletes data):") +
          chalk.gray(" baseboards down --volumes && baseboards up")
      );
      console.log(
        chalk.cyan("   2. Start fresh automatically:") +
          chalk.gray(" baseboards up --fresh")
      );
      console.log(
        chalk.gray(
          "\n   This usually happens when project files were deleted but Docker volumes remain."
        )
      );
    } else {
      console.log(
        chalk.yellow(
          "\n⚠️  Database migrations failed. You may need to run them manually:"
        )
      );
      console.log(
        chalk.cyan("   docker compose exec api alembic upgrade head")
      );
      console.log(chalk.gray("\n   Error details:"));
      console.log(chalk.gray("   " + errorMessage));
    }

    // Don't throw - app can still start
  }
}

/**
 * Get the dev command for the selected package manager.
 * @param pm Package manager (pnpm, npm, yarn, or bun)
 * @returns The command to start the dev server
 */
function getDevCommand(pm: PackageManager): string {
  const commands: Record<PackageManager, string> = {
    pnpm: "pnpm dev",
    npm: "npm run dev",
    yarn: "yarn dev",
    bun: "bun dev",
  };
  return commands[pm];
}

/**
 * Print success message for default mode (all services in Docker).
 * Shows all service URLs including web, API, and GraphQL.
 * @param ctx Project context
 * @param hasKeyWarning Whether to show API key warning
 */
function printDefaultSuccessMessage(
  ctx: ProjectContext,
  hasKeyWarning: boolean
): void {
  console.log(chalk.green.bold("\n✅ Baseboards is running!\n"));
  console.log(
    chalk.cyan("   Web:     "),
    chalk.underline(`http://localhost:${ctx.ports.web}`)
  );
  console.log(
    chalk.cyan("   API:     "),
    chalk.underline(`http://localhost:${ctx.ports.api}`)
  );
  console.log(
    chalk.cyan("   GraphQL: "),
    chalk.underline(`http://localhost:${ctx.ports.api}/graphql`)
  );

  if (hasKeyWarning) {
    console.log(chalk.yellow("\n⚠️  Remember to configure provider API keys!"));
    console.log(chalk.gray("   Edit:"), chalk.cyan("api/.env"));
    console.log(
      chalk.gray("   Docs:"),
      chalk.cyan("https://baseboards.dev/docs/setup")
    );
  }

  console.log(chalk.gray("\nView logs:"), chalk.cyan(`baseboards logs ${ctx.name} -f`));
  console.log(chalk.gray("Stop:     "), chalk.cyan(`baseboards down ${ctx.name}`));
  console.log();
}

/**
 * Print success message for app-dev mode (backend in Docker, frontend local).
 * Shows backend service URLs and instructions for starting the frontend locally.
 * @param ctx Project context
 * @param hasKeyWarning Whether to show API key warning
 */
function printAppDevSuccessMessage(
  ctx: ProjectContext,
  hasKeyWarning: boolean
): void {
  console.log(chalk.green.bold("\n✅ Backend services are running!\n"));
  console.log(
    chalk.cyan("   API:     "),
    chalk.underline(`http://localhost:${ctx.ports.api}`)
  );
  console.log(
    chalk.cyan("   GraphQL: "),
    chalk.underline(`http://localhost:${ctx.ports.api}/graphql`)
  );

  // Show frontend startup instructions
  console.log(chalk.cyan("\nTo start the frontend:\n"));

  // Calculate relative path from current directory to web directory
  const relativeWebPath = path.relative(process.cwd(), path.join(ctx.dir, "web"));
  const cdCommand = relativeWebPath || "web";

  // Get the package manager command (default to pnpm if not set)
  const packageManager = ctx.packageManager || "pnpm";
  const devCommand = getDevCommand(packageManager);

  console.log(chalk.cyan(`   cd ${cdCommand}`));
  console.log(chalk.cyan(`   ${devCommand}`));

  console.log(chalk.gray("\nThe frontend will be available at"), chalk.underline("http://localhost:3000"));

  if (hasKeyWarning) {
    console.log(chalk.yellow("\n⚠️  Remember to configure provider API keys!"));
    console.log(chalk.gray("   Edit:"), chalk.cyan("api/.env"));
  }

  console.log(chalk.gray("\nView logs:"), chalk.cyan(`baseboards logs ${ctx.name} -f`));
  console.log(chalk.gray("Stop:     "), chalk.cyan(`baseboards down ${ctx.name}`));
  console.log();
}

/**
 * Print success message for dev-packages mode (backend in Docker, frontend local with linked packages).
 * Shows backend URLs and workflow for developing with local package sources.
 * @param ctx Project context
 * @param hasKeyWarning Whether to show API key warning
 */
function printDevPackagesSuccessMessage(
  ctx: ProjectContext,
  hasKeyWarning: boolean
): void {
  console.log(chalk.green.bold("\n✅ Backend services are running!"));
  console.log(chalk.green.bold("✅ Local @weirdfingers/boards package linked!\n"));
  console.log(
    chalk.cyan("   API:     "),
    chalk.underline(`http://localhost:${ctx.ports.api}`)
  );
  console.log(
    chalk.cyan("   GraphQL: "),
    chalk.underline(`http://localhost:${ctx.ports.api}/graphql`)
  );

  console.log(chalk.cyan("\n📦 Package development workflow:\n"));
  console.log(chalk.gray("   1. Edit package source:"));
  console.log(chalk.cyan(`      ${ctx.dir}/frontend/src/`));
  console.log(chalk.gray("\n   2. Start the frontend:"));
  console.log(chalk.cyan(`      cd ${ctx.dir}/web`));
  console.log(chalk.cyan(`      pnpm install`));
  console.log(chalk.cyan(`      pnpm dev`));
  console.log(chalk.gray("\n   3. Changes to the package will hot-reload automatically"));
  console.log(chalk.gray(`\n   Frontend will be available at http://localhost:3000`));

  if (hasKeyWarning) {
    console.log(chalk.yellow("\n⚠️  Remember to configure provider API keys!"));
    console.log(chalk.gray("   Edit:"), chalk.cyan("api/.env"));
  }

  console.log(chalk.gray("\nView logs:"), chalk.cyan(`baseboards logs ${ctx.name} -f`));
  console.log(chalk.gray("Stop:     "), chalk.cyan(`baseboards down ${ctx.name}`));
  console.log();
}

/**
 * Print success message with URLs and next steps.
 * Dispatches to appropriate message function based on mode (default, app-dev, or dev-packages).
 * @param ctx Project context
 * @param detached Whether services are running in detached mode (unused but kept for compatibility)
 * @param hasKeyWarning Whether to show API key configuration warning
 */
function printSuccessMessage(
  ctx: ProjectContext,
  detached: boolean,
  hasKeyWarning: boolean
): void {
  // Dev-packages mode takes precedence (it implies app-dev)
  if (ctx.devPackages && ctx.appDev) {
    printDevPackagesSuccessMessage(ctx, hasKeyWarning);
  } else if (ctx.appDev) {
    // App-dev mode without dev-packages
    printAppDevSuccessMessage(ctx, hasKeyWarning);
  } else {
    // Default mode - all services in Docker
    printDefaultSuccessMessage(ctx, hasKeyWarning);
  }
}

/**
 * Check if Docker volumes exist for this project
 */
async function checkForExistingVolumes(): Promise<boolean> {
  try {
    const { stdout } = await execa("docker", [
      "volume",
      "ls",
      "--format",
      "{{.Name}}",
    ]);
    const volumes = stdout.split("\n").filter(Boolean);

    // Check for the project-specific database volume
    // Volume name format: baseboards_db-data
    // NOTE: We use "baseboards" (not ctx.name) because the compose.yaml template
    // sets `name: ${PROJECT_NAME:-baseboards}` and the PROJECT_NAME env var is only
    // read from docker/.env for service env vars, not for the compose project name itself.
    // So all Baseboards installations use the same "baseboards" project name.
    const projectVolumeName = "baseboards_db-data";
    return volumes.includes(projectVolumeName);
  } catch {
    // If docker command fails, assume no volumes exist
    return false;
  }
}

/**
 * Clean up Docker volumes for this project
 */
async function cleanupDockerVolumes(ctx: ProjectContext): Promise<void> {
  const spinner = ora("Cleaning up Docker volumes...").start();

  try {
    // If compose files exist, use docker compose down -v
    if (ctx.isScaffolded) {
      await execa("docker", [...getComposeBaseArgs(ctx), "down", "-v"], {
        cwd: ctx.dir,
      });
    } else {
      // If no compose files yet, manually remove the volume by name
      // This handles the case where project was deleted but volumes remain
      const volumesToRemove = ["baseboards_db-data", "baseboards_api-storage"];

      for (const volumeName of volumesToRemove) {
        try {
          await execa("docker", ["volume", "rm", volumeName]);
          spinner.text = `Removing volume ${volumeName}...`;
        } catch {
          // Volume might not exist, that's okay - it may have been manually removed
          // or never created in the first place
        }
      }
    }
    spinner.succeed("Docker volumes cleaned up");
  } catch (error) {
    spinner.fail("Failed to clean up volumes");
    console.log(
      chalk.yellow(
        "\n⚠️  Could not clean up volumes automatically. Try manually:"
      )
    );
    console.log(chalk.cyan("   docker volume rm baseboards_db-data"));
    throw error;
  }
}
