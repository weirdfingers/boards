/**
 * Shared types for the Baseboards CLI
 */

export interface ProjectContext {
  /** Absolute path to project directory */
  dir: string;

  /** Project name (derived from directory) */
  name: string;

  /** Whether project is already scaffolded */
  isScaffolded: boolean;

  /** Ports configuration */
  ports: {
    web: number;
    api: number;
    db: number;
    redis: number;
  };

  /** CLI version */
  version: string;

  /**
   * Whether to run frontend locally instead of in Docker.
   * When true, web service is not started in Docker Compose.
   */
  appDev: boolean;

  /**
   * Whether to include unpublished @weirdfingers/boards package source.
   * Only works when CLI runs from within the Boards monorepo.
   * When true, packages/frontend is copied to project and linked via file: dependency.
   * Requires appDev to be true.
   */
  devPackages: boolean;

  /**
   * Name of the frontend template to use for scaffolding.
   * Examples: "baseboards", "basic"
   */
  template: string;

  /**
   * Absolute path to monorepo root directory.
   * Only set when devPackages is true and monorepo is detected.
   */
  monorepoRoot?: string;

  /**
   * Selected package manager for frontend development.
   * Only set in app-dev mode after user selects their preferred package manager.
   */
  packageManager?: "pnpm" | "npm" | "yarn" | "bun";
}

export interface UpOptions {
  attach?: boolean;
  ports?: string;
  fresh?: boolean;
  appDev?: boolean;
  devPackages?: boolean;
  template?: string;
}

export interface DownOptions {
  volumes?: boolean;
}

export interface LogsOptions {
  follow?: boolean;
  since?: string;
  tail?: string;
}

export interface CleanOptions {
  hard?: boolean;
}

export interface UpgradeOptions {
  version?: string;
  dryRun?: boolean;
  force?: boolean;
}

export type ProjectMode = 'default' | 'app-dev';

export interface Prerequisites {
  docker: {
    installed: boolean;
    version?: string;
    composeVersion?: string;
  };
  node: {
    installed: boolean;
    version?: string;
    satisfies: boolean;
  };
  platform: {
    name: string;
    isWSL?: boolean;
  };
}

export interface HealthStatus {
  service: string;
  status: 'healthy' | 'unhealthy' | 'starting' | 'stopped';
  uptime?: string;
}
