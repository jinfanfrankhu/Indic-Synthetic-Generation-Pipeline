// Satisfy TypeScript for global CSS side-effect imports (e.g. `import "./globals.css"`).
// TS 5.6+ flags side-effect imports that resolve to no module/declaration, and Next's
// auto-generated next-env.d.ts is gitignored (regenerated per machine), so declare it
// ourselves. Next handles the actual CSS bundling — this is types-only.
declare module "*.css";
