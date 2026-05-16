# NemoClaw Network Policy

Allow outbound access from the NemoClaw/OpenShell sandbox to:

- Supabase REST/Auth/Storage/Realtime: `<project-ref>.supabase.co`, `*.supabase.co`
- Apify API: `api.apify.com`
- Vercel API and hosted deployments: `api.vercel.com`, `*.vercel.app`
- Resend API: `api.resend.com`
- Discord webhook and bot API: `discord.com`, `discordapp.com`
- Google Calendar/OAuth APIs: `www.googleapis.com`, `oauth2.googleapis.com`
- Vapi APIs, only if the stretch task is attempted: `api.vapi.ai`
- NemoClaw/OpenShell inference route for Nemotron: `inference.local`

Task 0 live follow-up: replace `<project-ref>.supabase.co` with the real
Supabase project host and add any account-specific hostnames exposed by the
NemoClaw/Brev runtime.
