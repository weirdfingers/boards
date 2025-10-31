/**
 * up command - Scaffold and start Baseboards
 */

import { execa } from 'execa';
import fs from 'fs-extra';
import path from 'path';
import chalk from 'chalk';
import ora from 'ora';
import type { ProjectContext, UpOptions } from '../types.js';
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
} from '../utils.js';

export async function up(
  directory: string,
  options: UpOptions
): Promise<void> {
  console.log(chalk.blue.bold('\n🎨 Baseboards CLI\n'));

  // Step 1: Check prerequisites
  const spinner = ora('Checking prerequisites...').start();
  await assertPrerequisites();
  spinner.succeed('Prerequisites OK');

  // Step 2: Resolve project context
  const dir = path.resolve(process.cwd(), directory);
  const name = path.basename(dir);
  const version = getCliVersion();
  const mode = options.prod ? 'prod' : 'dev';

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

  // Step 3: Scaffold if needed
  if (!ctx.isScaffolded) {
    console.log(chalk.cyan(`\n📦 Scaffolding new project: ${chalk.bold(name)}`));
    await scaffoldProject(ctx);
  } else {
    console.log(chalk.green(`\n✅ Project already scaffolded: ${chalk.bold(name)}`));
  }

  // Step 4: Check ports availability
  spinner.start('Checking port availability...');
  ctx.ports.web = await findAvailablePort(ctx.ports.web);
  ctx.ports.api = await findAvailablePort(ctx.ports.api);
  spinner.succeed(`Ports available: web=${ctx.ports.web}, api=${ctx.ports.api}`);

  // Step 5: Ensure environment files
  await ensureEnvFiles(ctx);

  // Step 6: Detect missing API keys
  const apiEnvPath = path.join(ctx.dir, 'packages/api/.env');
  const missingKeys = detectMissingProviderKeys(apiEnvPath);

  if (missingKeys.length > 0) {
    console.log(chalk.yellow('\n⚠️  Provider API keys not configured!'));
    console.log(chalk.gray('   Add at least one API key to packages/api/.env:'));
    console.log(chalk.cyan('   • REPLICATE_API_KEY') + chalk.gray(' - https://replicate.com/account/api-tokens'));
    console.log(chalk.cyan('   • FAL_KEY') + chalk.gray(' - https://fal.ai/dashboard/keys'));
    console.log(chalk.cyan('   • OPENAI_API_KEY') + chalk.gray(' - https://platform.openai.com/api-keys'));
    console.log(chalk.cyan('   • GOOGLE_API_KEY') + chalk.gray(' - https://makersuite.google.com/app/apikey'));
    console.log(chalk.gray('\n   The app will start, but image generation won\'t work without keys.\n'));
  }

  // Step 7: Start Docker Compose
  await startDockerCompose(ctx, options.detached || false);

  // Step 8: Wait for health checks (unless detached)
  if (!options.detached) {
    await waitForHealthy(ctx);
  }

  // Step 9: Print success message
  printSuccessMessage(ctx, options.detached || false, missingKeys.length > 0);
}

/**
 * Scaffold a new project from templates
 */
async function scaffoldProject(ctx: ProjectContext): Promise<void> {
  const templatesDir = getTemplatesDir();
  const spinner = ora('Copying templates...').start();

  // Create project directory
  fs.ensureDirSync(ctx.dir);

  // Copy all templates
  fs.copySync(templatesDir, ctx.dir, {
    overwrite: false,
    errorOnExist: false,
  });

  spinner.succeed('Templates copied');

  // Create data/storage directory
  spinner.start('Creating data directories...');
  fs.ensureDirSync(path.join(ctx.dir, 'data/storage'));
  spinner.succeed('Data directories created');

  console.log(chalk.green('   ✨ Project scaffolded successfully!'));
}

/**
 * Ensure .env files exist and are populated
 */
async function ensureEnvFiles(ctx: ProjectContext): Promise<void> {
  const spinner = ora('Configuring environment...').start();

  // Web .env
  const webEnvPath = path.join(ctx.dir, 'packages/web/.env');
  const webEnvExamplePath = path.join(ctx.dir, 'packages/web/.env.example');

  if (!fs.existsSync(webEnvPath) && fs.existsSync(webEnvExamplePath)) {
    let webEnv = fs.readFileSync(webEnvExamplePath, 'utf-8');
    webEnv = webEnv.replace('http://localhost:8800', `http://localhost:${ctx.ports.api}`);
    fs.writeFileSync(webEnvPath, webEnv);
  }

  // API .env
  const apiEnvPath = path.join(ctx.dir, 'packages/api/.env');
  const apiEnvExamplePath = path.join(ctx.dir, 'packages/api/.env.example');

  if (!fs.existsSync(apiEnvPath) && fs.existsSync(apiEnvExamplePath)) {
    let apiEnv = fs.readFileSync(apiEnvExamplePath, 'utf-8');

    // Generate JWT secret if not present
    if (apiEnv.includes('JWT_SECRET=\n') || apiEnv.includes('JWT_SECRET=\r\n')) {
      const jwtSecret = generateSecret(32);
      apiEnv = apiEnv.replace(/JWT_SECRET=.*$/m, `JWT_SECRET=${jwtSecret}`);
    }

    fs.writeFileSync(apiEnvPath, apiEnv);
  }

  // Docker .env
  const dockerEnvPath = path.join(ctx.dir, 'docker/.env');
  const dockerEnvExamplePath = path.join(ctx.dir, 'docker/env.example');

  if (!fs.existsSync(dockerEnvPath) && fs.existsSync(dockerEnvExamplePath)) {
    let dockerEnv = fs.readFileSync(dockerEnvExamplePath, 'utf-8');

    // Generate database password
    const dbPassword = generatePassword(24);
    dockerEnv = dockerEnv.replace(/POSTGRES_PASSWORD=.*/g, `POSTGRES_PASSWORD=${dbPassword}`);
    dockerEnv = dockerEnv.replace(/REPLACE_WITH_GENERATED_PASSWORD/g, dbPassword);

    // Set ports
    dockerEnv = dockerEnv.replace(/WEB_PORT=.*/g, `WEB_PORT=${ctx.ports.web}`);
    dockerEnv = dockerEnv.replace(/API_PORT=.*/g, `API_PORT=${ctx.ports.api}`);

    // Set version
    dockerEnv = dockerEnv.replace(/VERSION=.*/g, `VERSION=${ctx.version}`);

    // Set project name
    dockerEnv = dockerEnv.replace(/PROJECT_NAME=.*/g, `PROJECT_NAME=${ctx.name}`);

    fs.writeFileSync(dockerEnvPath, dockerEnv);
  }

  spinner.succeed('Environment configured');
}

/**
 * Start Docker Compose
 */
async function startDockerCompose(ctx: ProjectContext, detached: boolean): Promise<void> {
  const spinner = ora('Starting Docker Compose...').start();

  const composeFiles = ['compose.yaml'];
  if (ctx.mode === 'dev') {
    composeFiles.push('compose.dev.yaml');
  }

  const composeArgs = [
    'compose',
    ...composeFiles.flatMap((f) => ['-f', f]),
    'up',
    detached ? '-d' : '',
    '--remove-orphans',
  ].filter(Boolean);

  try {
    if (detached) {
      await execa('docker', composeArgs, {
        cwd: ctx.dir,
        stdio: 'inherit',
      });
      spinner.succeed('Docker Compose started (detached mode)');
    } else {
      spinner.succeed('Docker Compose starting...');
      console.log(chalk.gray('\n─────────────────────────────────────────────────────'));
      console.log(chalk.gray('Starting services... (Ctrl+C to stop)\n'));

      // Run in foreground (this will block)
      await execa('docker', composeArgs, {
        cwd: ctx.dir,
        stdio: 'inherit',
      });
    }
  } catch (error: any) {
    spinner.fail('Failed to start Docker Compose');
    throw error;
  }
}

/**
 * Wait for services to become healthy
 */
async function waitForHealthy(ctx: ProjectContext): Promise<void> {
  const spinner = ora('Waiting for services to be healthy...').start();

  const services = ['db', 'cache', 'api', 'web'];
  const maxWaitMs = 120_000; // 2 minutes

  const checkHealth = async (): Promise<boolean> => {
    try {
      const { stdout } = await execa('docker', [
        'compose',
        'ps',
        '--format',
        'json',
      ], {
        cwd: ctx.dir,
      });

      const containers = stdout
        .split('\n')
        .filter(Boolean)
        .map((line) => JSON.parse(line));

      const allHealthy = services.every((service) => {
        const container = containers.find((c: any) => c.Service === service);
        return container && (container.Health === 'healthy' || container.State === 'running');
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
    spinner.succeed('All services healthy');
  } else {
    spinner.warn('Services taking longer than expected...');
    console.log(chalk.yellow('\n⚠️  Health check timeout. Services may still be starting.'));
    console.log(chalk.gray('   Run'), chalk.cyan('baseboards logs'), chalk.gray('to check progress.'));
  }
}

/**
 * Print success message with URLs and next steps
 */
function printSuccessMessage(ctx: ProjectContext, detached: boolean, hasKeyWarning: boolean): void {
  console.log(chalk.green.bold('\n✨ Baseboards is running!\n'));
  console.log(chalk.cyan('  🌐 Web:'), chalk.underline(`http://localhost:${ctx.ports.web}`));
  console.log(chalk.cyan('  🔌 API:'), chalk.underline(`http://localhost:${ctx.ports.api}`));
  console.log(chalk.cyan('  📊 GraphQL:'), chalk.underline(`http://localhost:${ctx.ports.api}/graphql`));

  if (hasKeyWarning) {
    console.log(chalk.yellow('\n⚠️  Remember to configure provider API keys!'));
    console.log(chalk.gray('   Edit:'), chalk.cyan('packages/api/.env'));
    console.log(chalk.gray('   Docs:'), chalk.cyan('https://baseboards.dev/docs/setup'));
  }

  console.log(chalk.gray('\n📖 Commands:'));
  console.log(chalk.gray('   Stop:'), chalk.cyan('baseboards down'));
  console.log(chalk.gray('   Logs:'), chalk.cyan('baseboards logs'));
  console.log(chalk.gray('   Status:'), chalk.cyan('baseboards status'));
  console.log();
}
