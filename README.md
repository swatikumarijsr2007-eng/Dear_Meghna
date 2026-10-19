# Dear_Meghna

## Online birthday wishes

The “Send a Wish” form saves messages to the configured Supabase project.

1. In the Supabase SQL Editor for the configured project, run [`supabase/schema.sql`](./supabase/schema.sql).
2. Deploy the site, including [`supabase-config.js`](./supabase-config.js), to your static host. The project URL and public publishable key are already configured there. Never put a `service_role` or secret key in the website.
3. The local `server.py` is not required for hosted wish submissions.

The database accepts public inserts with name and message length limits. Row Level Security is enabled, and anonymous visitors can read only `FinalHBD` wishes so they appear in the Wishboard.