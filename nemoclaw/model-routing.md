# Nemotron Routing

Default route inside NemoClaw/OpenShell:

- `NEMOTRON_BASE_URL=https://inference.local/v1`
- `NEMOTRON_MODEL=nvidia/nemotron-3-super-120b-a12b`

Local fallback outside the sandbox:

- `NEMOTRON_BASE_URL=https://integrate.api.nvidia.com/v1`
- `NVIDIA_API_KEY` must be set.

Prefer the NemoClaw/OpenShell route for the real demo.
