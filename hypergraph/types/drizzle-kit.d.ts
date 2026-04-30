declare module "drizzle-kit" {
  export interface DrizzleConfig {
    schema: string;
    out: string;
    dialect: "sqlite";
    dbCredentials: {
      url: string;
    };
  }

  export function defineConfig(config: DrizzleConfig): DrizzleConfig;
}
