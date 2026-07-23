# Setup — Getting Started

> Work through this top to bottom after `git clone`.

## Order

1. [docker.md](docker.md) — populate `docker/envs/.env` (copy `.env.sovereign`, fill the
   `__SET_ME__` values), create the network, start the stack, seed the graph
   (hardware prerequisites: any x86_64 Linux host with Docker, 16 GB RAM — see the
   README Quickstart)

## Prerequisites

| What | Version | Check |
|---|---|---|
| Linux host (aarch64 or x86_64) | — | `uname -m` |
| Python | 3.12+ | `python3 --version` |
| Docker + Compose plugin | 24.x+ | `docker --version` |
| git | — | `git --version` |

Node.js and a package manager are **not** required on the host: the dashboard
builds inside its container (multi-stage Dockerfile). Python is only needed for
the seed/migration scripts, installed into a project venv.

## Remote Access (optional)

```bash
# Add to ~/.ssh/config on your workstation
Host lex
  HostName <your-host-or-ip>
  User <your-user>

# Connect:
ssh lex
```

## Quick Start (after git clone)

```bash
cp docker/envs/.env.sovereign docker/envs/.env   # then fill in your secrets
```

Then follow [docker.md](docker.md): create the `docker_lex-net` network, start
the stack with the sovereign profile, pull the model, and run `make seed-all`.

Once the stack is up:
- `http://<your-host>:3000` — Dashboard (projects, scans, generated documents)
