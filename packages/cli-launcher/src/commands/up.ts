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
  getTemplatesDir,
  isScaffolded,
  parsePortsOption,
  detectMissingProviderKeys,
  waitFor,
} from "../utils.js";

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
  const mode = options.prod ? "prod" : "dev";

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

  const ctx: ProjectContext = {
    dir,
    name,
    isScaffolded: isScaffolded(dir),
    ports: defaultPorts,
    mode,
    version,
  };

  // Track if this is a fresh scaffold to prompt for API keys later
  const isFreshScaffold = !ctx.isScaffolded;

  // Step 3: Scaffold if needed
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

  // Step 4: Check ports availability
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
  await startDockerCompose(ctx, true);

  // Step 8: Wait for health checks
  await waitForHealthy(ctx);

  // Step 9: Run database migrations
  await runMigrations(ctx);

  // Step 10: Print success message
  printSuccessMessage(ctx, options.detached || false, missingKeys.length > 0);

  // Step 11: Attach to logs if not detached
  if (!options.detached) {
    try {
      await attachToLogs(ctx);
    } catch (error: any) {
      // Handle Ctrl+C gracefully
      if (error.signal === "SIGINT" || error.exitCode === 130) {
        console.log(chalk.yellow("\n\n⚠️  Interrupted - services stopped"));
        process.exit(0);
      }
      throw error;
    }
  }
}

/**
 * Scaffold a new project from templates
 */
async function scaffoldProject(ctx: ProjectContext): Promise<void> {
  const templatesDir = getTemplatesDir();
  const spinner = ora("Copying templates...").start();

  // Create project directory
  fs.ensureDirSync(ctx.dir);

  // Copy web and api directly to root
  fs.copySync(path.join(templatesDir, "web"), path.join(ctx.dir, "web"));
  fs.copySync(path.join(templatesDir, "api"), path.join(ctx.dir, "api"));

  // Copy root files (compose, docker, README, .gitignore)
  const rootFiles = [
    "compose.yaml",
    "compose.dev.yaml",
    "README.md",
    ".gitignore",
  ];
  for (const file of rootFiles) {
    const src = path.join(templatesDir, file);
    const dest = path.join(ctx.dir, file);
    if (fs.existsSync(src)) {
      fs.copySync(src, dest);
    }
  }

  // Copy docker directory
  fs.copySync(path.join(templatesDir, "docker"), path.join(ctx.dir, "docker"));

  spinner.succeed("Templates copied");

  // Create data/storage directory
  spinner.start("Creating data directories...");
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
      type: "text",
      name: "REPLICATE_API_TOKEN",
      message: "Replicate API Key (https://replicate.com/account/api-tokens):",
      initial: "",
    },
    {
      type: "text",
      name: "FAL_KEY",
      message: "Fal AI API Key (https://fal.ai/dashboard/keys):",
      initial: "",
    },
    {
      type: "text",
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
 * Start Docker Compose (always in detached mode)
 */
async function startDockerCompose(
  ctx: ProjectContext,
  detached: boolean
): Promise<void> {
  const spinner = ora("Starting Docker Compose...").start();

  const composeFiles = ["compose.yaml"];
  if (ctx.mode === "dev") {
    composeFiles.push("compose.dev.yaml");
  }

  const composeArgs = [
    "compose",
    ...composeFiles.flatMap((f) => ["-f", f]),
    "up",
    "-d",
    "--remove-orphans",
  ];

  try {
    await execa("docker", composeArgs, {
      cwd: ctx.dir,
      stdio: "inherit",
    });
    spinner.succeed("Docker Compose started");
  } catch (error: any) {
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

  const composeFiles = ["compose.yaml"];
  if (ctx.mode === "dev") {
    composeFiles.push("compose.dev.yaml");
  }

  const composeArgs = [
    "compose",
    ...composeFiles.flatMap((f) => ["-f", f]),
    "logs",
    "-f",
  ];

  await execa("docker", composeArgs, {
    cwd: ctx.dir,
    stdio: "inherit",
  });
}

/**
 * Wait for services to become healthy
 */
async function waitForHealthy(ctx: ProjectContext): Promise<void> {
  const spinner = ora("Waiting for services to be healthy...").start();

  const services = ["db", "cache", "api", "worker", "web"];
  const maxWaitMs = 120_000; // 2 minutes

  const checkHealth = async (): Promise<boolean> => {
    try {
      const { stdout } = await execa(
        "docker",
        ["compose", "ps", "--format", "json"],
        {
          cwd: ctx.dir,
        }
      );

      const containers = stdout
        .split("\n")
        .filter(Boolean)
        .map((line) => JSON.parse(line));

      const allHealthy = services.every((service) => {
        const container = containers.find((c: any) => c.Service === service);
        return (
          container &&
          (container.Health === "healthy" || container.State === "running")
        );
      });

      return allHealthy;
    } catch (e) {
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
      ["compose", "exec", "-T", "api", "alembic", "upgrade", "head"],
      {
        cwd: ctx.dir,
      }
    );
    spinner.succeed("Database migrations complete");
  } catch (error) {
    spinner.fail("Database migrations failed");
    console.log(
      chalk.yellow(
        "\n⚠️  Database migrations failed. You may need to run them manually:"
      )
    );
    console.log(error);
    console.log(chalk.cyan("   docker compose exec api alembic upgrade head"));
    // Don't throw - app can still start
  }
}

/**
 * Print success message with URLs and next steps
 */
function printSuccessMessage(
  ctx: ProjectContext,
  detached: boolean,
  hasKeyWarning: boolean
): void {
  console.log(chalk.green.bold("\n✨ Baseboards is running!\n"));
  console.log(
    chalk.cyan("  🌐 Web:"),
    chalk.underline(`http://localhost:${ctx.ports.web}`)
  );
  console.log(
    chalk.cyan("  🔌 API:"),
    chalk.underline(`http://localhost:${ctx.ports.api}`)
  );
  console.log(
    chalk.cyan("  📊 GraphQL:"),
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

  console.log(chalk.gray("\n📖 Commands:"));
  console.log(chalk.gray("   Stop:"), chalk.cyan("baseboards down"));
  console.log(chalk.gray("   Logs:"), chalk.cyan("baseboards logs"));
  console.log(chalk.gray("   Status:"), chalk.cyan("baseboards status"));
  console.log();
}
