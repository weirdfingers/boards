/**
 * doctor command - Run diagnostics
 */

import path from 'path';
import fs from 'fs-extra';
import chalk from 'chalk';
import { checkPrerequisites, isScaffolded, detectMissingProviderKeys, getCliVersion } from '../utils.js';

export async function doctor(directory: string): Promise<void> {
  const dir = path.resolve(process.cwd(), directory);

  console.log(chalk.blue.bold('\n🩺 Baseboards Diagnostics\n'));

  // CLI Version
  console.log(chalk.cyan('CLI Version:'), getCliVersion());

  // Prerequisites
  console.log(chalk.cyan('\n📋 Prerequisites:'));
  const prereqs = await checkPrerequisites();

  console.log(
    chalk.gray('  Node.js:'),
    prereqs.node.installed
      ? prereqs.node.satisfies
        ? chalk.green(`✓ v${prereqs.node.version}`)
        : chalk.yellow(`⚠️  v${prereqs.node.version} (need v20+)`)
      : chalk.red('✗ Not installed')
  );

  console.log(
    chalk.gray('  Docker:'),
    prereqs.docker.installed
      ? chalk.green(`✓ v${prereqs.docker.version}`)
      : chalk.red('✗ Not installed')
  );

  if (prereqs.docker.composeVersion) {
    console.log(
      chalk.gray('  Docker Compose:'),
      chalk.green(`✓ v${prereqs.docker.composeVersion}`)
    );
  } else if (prereqs.docker.installed) {
    console.log(chalk.gray('  Docker Compose:'), chalk.red('✗ Not available'));
  }

  console.log(chalk.gray('  Platform:'), prereqs.platform.name);
  if (prereqs.platform.isWSL) {
    console.log(chalk.gray('  WSL:'), chalk.blue('✓ Detected'));
  }

  // Project info
  console.log(chalk.cyan('\n📂 Project:'));
  const scaffolded = isScaffolded(dir);
  console.log(
    chalk.gray('  Scaffolded:'),
    scaffolded ? chalk.green('✓ Yes') : chalk.yellow('✗ No')
  );

  if (scaffolded) {
    console.log(chalk.gray('  Directory:'), dir);

    // Check for key files
    const webPkg = path.join(dir, 'packages/web/package.json');
    const apiPkg = path.join(dir, 'packages/api/pyproject.toml');
    const composeFile = path.join(dir, 'compose.yaml');

    console.log(
      chalk.gray('  Web package:'),
      fs.existsSync(webPkg) ? chalk.green('✓') : chalk.red('✗')
    );
    console.log(
      chalk.gray('  API package:'),
      fs.existsSync(apiPkg) ? chalk.green('✓') : chalk.red('✗')
    );
    console.log(
      chalk.gray('  Compose file:'),
      fs.existsSync(composeFile) ? chalk.green('✓') : chalk.red('✗')
    );

    // Check .env files
    console.log(chalk.cyan('\n🔐 Environment:'));
    const webEnv = path.join(dir, 'packages/web/.env');
    const apiEnv = path.join(dir, 'packages/api/.env');
    const dockerEnv = path.join(dir, 'docker/.env');

    console.log(
      chalk.gray('  Web .env:'),
      fs.existsSync(webEnv) ? chalk.green('✓') : chalk.yellow('✗ Missing')
    );
    console.log(
      chalk.gray('  API .env:'),
      fs.existsSync(apiEnv) ? chalk.green('✓') : chalk.yellow('✗ Missing')
    );
    console.log(
      chalk.gray('  Docker .env:'),
      fs.existsSync(dockerEnv) ? chalk.green('✓') : chalk.yellow('✗ Missing')
    );

    // Check provider keys
    if (fs.existsSync(apiEnv)) {
      const missingKeys = detectMissingProviderKeys(apiEnv);
      if (missingKeys.length > 0) {
        console.log(
          chalk.gray('  Provider keys:'),
          chalk.yellow(`⚠️  ${missingKeys.length} missing`)
        );
        console.log(chalk.gray('    Missing:'), missingKeys.map(k => chalk.cyan(k)).join(', '));
      } else {
        console.log(chalk.gray('  Provider keys:'), chalk.green('✓ Configured'));
      }
    }

    // Check config files
    console.log(chalk.cyan('\n⚙️  Configuration:'));
    const generatorsYaml = path.join(dir, 'packages/api/config/generators.yaml');
    const storageYaml = path.join(dir, 'packages/api/config/storage_config.yaml');

    console.log(
      chalk.gray('  generators.yaml:'),
      fs.existsSync(generatorsYaml) ? chalk.green('✓') : chalk.yellow('✗ Missing')
    );
    console.log(
      chalk.gray('  storage_config.yaml:'),
      fs.existsSync(storageYaml) ? chalk.green('✓') : chalk.yellow('✗ Missing')
    );

    // Check storage directory
    const storageDir = path.join(dir, 'data/storage');
    console.log(
      chalk.gray('  Storage directory:'),
      fs.existsSync(storageDir) ? chalk.green('✓') : chalk.yellow('✗ Missing')
    );
  }

  // Recommendations
  console.log(chalk.cyan('\n💡 Recommendations:'));
  const recommendations: string[] = [];

  if (!prereqs.node.satisfies) {
    recommendations.push('Upgrade Node.js to v20 or higher');
  }

  if (!prereqs.docker.installed) {
    recommendations.push('Install Docker Desktop: https://docs.docker.com/get-docker/');
  } else if (!prereqs.docker.composeVersion) {
    recommendations.push('Update Docker to get Compose v2');
  }

  if (!scaffolded) {
    recommendations.push('Run ' + chalk.cyan('baseboards up') + ' to scaffold a project');
  }

  if (recommendations.length === 0) {
    console.log(chalk.green('  ✓ Everything looks good!'));
  } else {
    recommendations.forEach((rec) => console.log(chalk.yellow('  •'), rec));
  }

  console.log();
}
