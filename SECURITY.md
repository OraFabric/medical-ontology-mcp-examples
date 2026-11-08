# Security

## Keys

Never commit an API key. This repository's `.gitignore` excludes `.env`, `*.local.json`
and the common client config files, and secret scanning is enabled — both are a safety
net, not a plan.

If a key does get committed:

1. treat it as compromised the moment it is pushed, even if you force-push over it;
2. rotate it in the developer console at <https://orafabric.com>;
3. tell us in the issue so we can check for abuse.

Rotating is the only remediation. Removing the commit from history does not un-leak it.

## Reporting a vulnerability

Do not open a public issue for a security problem. Report it through the contact channel
on <https://orafabric.com> with:

- what the issue is and what an attacker could do with it,
- reproduction steps or a minimal request,
- whether it involves authentication, billing, data exposure or the MCP transport.

We will acknowledge and keep you informed of the fix. Please give us a reasonable window
before publishing.

## Scope

In scope for this repository:

- example code that leaks a key, logs a request body containing article text, or writes
  credentials to disk in a world-readable location;
- a client that silently downgrades transport security;
- a prompt pack that would cause an integrator to expose patient data to the service.

Out of scope here (report through the website): the service itself, the knowledge base,
authentication and billing.

## Data handling reminder

Retrieval packs contain article sentences and metadata. Do not log full packs in
production, do not send them to third-party analytics, and do not commit them as fixtures.
Log tool names, argument hashes, finding ids and counts instead.
