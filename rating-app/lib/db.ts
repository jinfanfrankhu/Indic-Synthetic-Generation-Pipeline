import { neon } from "@neondatabase/serverless";

// Create the client lazily, per request — not at module import. `next build`
// imports the route module to collect metadata, and neon() throws on an empty
// connection string, so a top-level client would fail the build before the env
// var is wired. Calling this inside the handler keeps the build clean.
export function getSql() {
  const url = process.env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL is not set");
  return neon(url);
}
