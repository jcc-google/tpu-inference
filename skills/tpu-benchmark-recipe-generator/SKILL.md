---
name: tpu-benchmark-recipe-generator
description: Generate high-fidelity Kubernetes JobSet recipes for TPU inference benchmarks. Use when creating performance comparison jobs for models like Qwen3-235B to ensure accurate memory modeling and native lifecycle management.
---

# TPU Benchmark Recipe Generator

This skill provides the procedural knowledge to generate production-ready Kubernetes JobSet recipes for TPU inference benchmarking.

## Core Best Practices

### 1. JobSet Lifecycle (successPolicy)
Always use the native Kubernetes `successPolicy` to manage the lifecycle of benchmark jobs. This ensures that the vLLM server is automatically cleaned up when the benchmark client finishes.

**Pattern:**
```yaml
spec:
  successPolicy:
    operator: All
    targetReplicatedJobs:
      - sglang-client # The name of the benchmark container
```

### 2. Memory Modeling (v7x-8 Node)
To prevent OOM and maximize prefix cache stability, use these calibrated constants:
- **Total Node HBM**: 758 GB (94.75 GB * 8)
- **Fixed System Overhead**: 35 GB
- **HBM Cache Formula**: `(758 * GPU_MEM_UTIL) - Model_Weight_GB - 35`
- **Pre-mapped Buffer Optimization**: 
    - `TPU_PREMAPPED_BUFFER_SIZE`: `17179869184` (16 GB)
    - `TPU_PREMAPPED_BUFFER_TRANSFER_THRESHOLD_BYTES`: `17179869184` (16 GB)

### 3. Model Defaults
| Model | Model Weight | Staging Buffer | CPU Cache (DRAM) |
| :--- | :--- | :--- | :--- |
| **32B** | 32 GB | 32.0 GB | 781.0 GB |
| **235B** | 235 GB | 47.0 GB | 550.0 GB |
| **480B** | 480 GB | 15.5 GB | 363.0 GB |

## Workflow

1.  **Define Traffic Pattern**: Identify Groups, Prompts/Group, and Output Length.
2.  **Calculate Coverage**: Ensure `Persistent Footprint < (HBM + DRAM)`.
3.  **Apply Success Policy**: Ensure `targetReplicatedJobs` points to the benchmark client.
4.  **Validate Block Size**: Default to `512` for all high-performance tests.
