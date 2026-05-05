---
name: cloud-devkit-gke
description: Guide for developing and using the Cloud-Devkit GKE environment, including KV Offloading recipes, CLI updates, and job management.
---

# Cloud-Devkit GKE Development & Usage

This skill provides procedural knowledge for working with the Cloud-Devkit project, specifically for running large-scale ML jobs on GKE.

## GKE Environment Overview

The environment consists of:
- **JobSet API**: Orchestrates groups of related Kubernetes Jobs (e.g., multi-node TPU training).
- **MongoDB**: Tracks job metadata and status persistently.
- **GCS (Google Cloud Storage)**: Archives logs and stores specialized tools like `libtpu.so`.
- **cdk-vm**: The primary developer VM where the `cdk` CLI is built and used.

For deep architecture details, see [gke_architecture.md](references/gke_architecture.md).

## Development Workflow

### Updating and Testing the CLI
When modifying the `cdk` CLI (e.g., in `cli/` or `lib/`):
1. **Build**: `make build-cli` (creates `bin/cdk`).
2. **Install**: `sudo cp bin/cdk /usr/local/bin/cdk` to make it globally available.
3. **Verify**: Run `cdk job list` or other commands to ensure the changes are active.

For detailed dev instructions, see [cli_development.md](references/cli_development.md).

## KV Offloading Project

### Writing Recipes
KV Offloading recipes require specific configurations to handle massive context and custom TPU libraries:
- **TPU Topology**: Specified in `nodeSelector` (e.g., `2x2x1` for 4 chips).
- **Custom libtpu.so**: Injected via `initContainers` or manually via `kubectl cp`.
- **Tracing**: Enabled by setting `TPU_PJRT_EVENT_TRACE_ENABLE=1` and using `--print-requests` in the benchmark.

For recipe templates and guidelines, see [kv_offloading_recipes.md](references/kv_offloading_recipes.md).

## Common Troubleshooting

- **ContainerCreating**: Usually indicates a large image pull or a failed `hostPath` mount.
- **Evicted**: Often caused by low `ephemeral-storage`. Request at least `10Gi` in the pod spec.
- **403 Forbidden (GCS)**: Check Workload Identity bindings and GCS IAM permissions.
