# KV Offloading Recipes

## Recipe Structure
Recipes are Go template files rendered by the CLI.

### TPU Node Selection
Ensure the following are set to match the desired TPU topology:
```yaml
nodeSelector:
  cloud.google.com/gke-tpu-topology: "2x2x1"
  cloud.google.com/gke-tpu-accelerator: "tpu7x"
```

### Resource Requests (Critical)
Always request enough memory and ephemeral storage. 
**Note**: TPU nodes typically only have **17.5Gi** of allocatable user space. Requesting more than this will keep the Pod in `Pending`.
```yaml
resources:
  limits:
    google.com/tpu: 4
    memory: "900Gi"
    ephemeral-storage: "10Gi" # Stay under 17.5Gi limit
```

### Custom Library Injection (Manual)
To bypass GCS authentication issues, use a wait loop in an `initContainer`:
```yaml
initContainers:
  - name: fetch-libtpu
    image: google/cloud-sdk:slim
    command: ["/bin/bash", "-c"]
    args:
      - |
        mkdir -p /mnt/data/bin
        while [ ! -f /mnt/data/bin/libtpu.so ]; do sleep 5; done
        # Ensure file is complete (e.g., 782307808 bytes for our custom lib)
        while [ $(stat -c%s /mnt/data/bin/libtpu.so) -lt 782307808 ]; do sleep 5; done
        echo "Library complete, continuing"
    volumeMounts:
      - name: huggingface-storage
        mountPath: /mnt/data
```
**Injection Command**: `cat libtpu.so | kubectl exec -i <pod> -c fetch-libtpu -- bash -c 'cat > /mnt/data/bin/libtpu.so'`

### Full Tracing Configuration (Verified)
To guarantee high-quality traces in Perfetto:
1. **Server Environment**:
   - `LD_PRELOAD: "/app/repo/results/bin/libtpu.so"` (Force load custom library)
   - `TPU_PJRT_EVENT_TRACE_ENABLE: "1"`
   - `TPU_STDERR_LOG_LEVEL: "0"`
   - `TPU_VMODULE: "tpu_pjrt_client=1,pjrt_stream_executor_client=1"`
2. **Log Persistence**:
   - Redirect `vllm serve` output to the SSD volume to avoid Kubernetes log rotation.
   - Command: `vllm serve ... 2>&1 | tee /app/repo/results/vllm_server_full.log`
3. **Client Command**:
   - Add `--print-requests` to the benchmark script (requires `sglang-oai-chat` backend).
4. **High-level Markers**:
   - Use `printf "trace-event: name=... ts=... dur=... pid=benchmark tid=main\n"` in the script.

## Performance Tuning Best Practices (Latest)

### 1. JobSet Lifecycle (successPolicy)
Always use the native Kubernetes `successPolicy` to manage the lifecycle of benchmark jobs. This ensures the vLLM server shuts down automatically when the benchmark client completes, releasing expensive TPU resources.

**Pattern:**
```yaml
spec:
  successPolicy:
    operator: All
    targetReplicatedJobs:
      - sglang-client # or the name of the benchmark container
```

### 2. Physical Memory Modeling (v7x-8 Node)
To maximize prefix cache stability and prevent OOMs, use these calibrated constants for your capacity planning:
- **Total Node HBM**: 758 GB (94.75 GB * 8 chips).
- **Fixed System Overhead**: 35 GB.
- **KV Cache Formula**: `(758 * GPU_MEM_UTIL) - Model_Weight_GB - 35`.
- **Pre-mapped Buffer Optimization**: 
    - `TPU_PREMAPPED_BUFFER_SIZE`: `17179869184` (16 GB)
    - `TPU_PREMAPPED_BUFFER_TRANSFER_THRESHOLD_BYTES`: `17179869184` (16 GB)
    - *Note: Using 16 GB thresholds (instead of 64 GB) provides a better balance between transfer acceleration and CPU-TPU synchronization overhead for most prefix sizes.*

### 3. Model-Specific Memory Defaults
| Model | Model Weight | Staging Buffer | CPU Cache (DRAM) |
| :--- | :--- | :--- | :--- |
| **32B** | 32 GB | 32.0 GB | 781.0 GB |
| **235B** | 235 GB | 47.0 GB | 550.0 GB |
| **480B** | 480 GB | 15.5 GB | 363.0 GB |

