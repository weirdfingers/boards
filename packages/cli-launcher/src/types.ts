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

  /** Environment: dev or prod */
  mode: 'dev' | 'prod';

  /** CLI version */
  version: string;

  /**
   * Whether to run frontend locally instead of in Docker.
   * When true, web service is not started in Docker Compose.
   */
  appDev: boolean;
}

export interface UpOptions {
  dev?: boolean;
  prod?: boolean;
  attach?: boolean;
  ports?: string;
  fresh?: boolean;
  appDev?: boolean;
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

export interface UpdateOptions {
  force?: boolean;
  version?: string;
}

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
