// Copy to src/config.ts and fill in values. config.ts is gitignored.
export const SUPABASE_URL = 'https://YOUR-PROJECT.supabase.co';
export const SUPABASE_ANON_KEY = 'sb_publishable_...';

// Which Supabase location this TV serves. Pins leaderboard / match
// queries to this venue. Seeded Friendly Bar (Detroit) is the dev
// fallback; production TVs read this from a one-time setup step.
export const LOCATION_ID = '10c079c1-a034-442e-9075-dba4ac9bcf15';
