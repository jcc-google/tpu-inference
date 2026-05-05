import os

def generate_recipe(groups, prompts, output_len, threshold, is_offload, name):
    kv_config = "'{\"kv_connector\":\"TPUOffloadConnector\",\"kv_connector_module_path\":\"tpu_inference.offload.tpu_offload_connector\",\"kv_role\":\"kv_both\"}'" if is_offload else "''"
    
    offload_envs = ""
    if is_offload:
        offload_envs = """
                    - name: TPU_OFFLOAD_NUM_CPU_CHUNKS
                      value: "3000"
                    - name: TPU_OFFLOAD_NUM_STAGING_BLOCKS
                      value: "256"
                    - name: TPU_OFFLOAD_DECODE_SAVE
                      value: "0"
                    - name: TPU_OFFLOAD_SWAP_OP_TYPE
                      value: "jax" """

    # Max concurrency logic based on prompts/group to match previous runs
    concurrency = 250
    if groups == 450: concurrency = 150
    if groups == 150: concurrency = 80
    if groups == 200: concurrency = 100
    if groups == 50: concurrency = 250

    recipe = f"""apiVersion: jobset.x-k8s.io/v1alpha2
kind: JobSet
metadata:
  name: {name}
  namespace: cloud-devkit-jobs
spec:
  replicatedJobs:
    - name: {"offload" if is_offload else "base"}-run
      replicas: 1
      template:
        spec:
          backoffLimit: 0
          template:
            spec:
              restartPolicy: Never
              nodeSelector:
                cloud.google.com/gke-tpu-topology: "2x2x1"
                cloud.google.com/gke-tpu-accelerator: "tpu7x"

              volumes:
                - name: shared-signal
                  emptyDir: {{}}
                - name: dshm
                  emptyDir:
                    medium: Memory
                    sizeLimit: "300Gi"
                - name: huggingface-storage
                  ephemeral:
                    volumeClaimTemplate:
                      spec:
                        storageClassName: "premium-rwo"
                        accessModes: [ "ReadWriteOnce" ]
                        resources:
                          requests:
                            storage: 384Gi

              containers:
                - name: vllm-server
                  image: us-central1-docker.pkg.dev/cloud-tpu-inference-test/vllm-tpu-rdna/vllm-tpu:sangamjindal-vllm-offload-apr-27
                  imagePullPolicy: Always
                  env:
                    - name: EXP_MODEL_NAME
                      value: "Qwen/Qwen3-235B-A22B-Instruct-2507-FP8"
                    - name: EXP_GPU_MEM_UTIL
                      value: "0.9"
                    - name: BASE_RESULTS_DIR
                      value: "/root/cloud-devkit/results"
                    - name: MODEL_IMPL_TYPE
                      value: "vllm"
                    - name: VLLM_LOGGING_LEVEL
                      value: "INFO"
                    - name: TPU_PREMAPPED_BUFFER_SIZE
                      value: "17179869184"
                    - name: TPU_PREMAPPED_BUFFER_TRANSFER_THRESHOLD_BYTES
                      value: "{threshold}"
                    - name: JAX_PJRT_CLIENT_CREATE_OPTIONS
                      value: "pinned_host_allocation_mode:recycle"
                    {offload_envs}
                    - name: TORCH_HOME
                      value: "$(BASE_RESULTS_DIR)/torch"
                    - name: JAX_COMPILATION_CACHE_DIR
                      value: "$(BASE_RESULTS_DIR)/jax_cache"
                    - name: HF_HOME
                      value: "$(BASE_RESULTS_DIR)/huggingface"
                    - name: VLLM_CACHE_ROOT
                      value: "$(BASE_RESULTS_DIR)/vllm"
                    - name: VLLM_TORCH_PROFILER_DIR
                      value: "$(BASE_RESULTS_DIR)/profile"
                    - name: TMPDIR
                      value: "$(BASE_RESULTS_DIR)/tmp"

                  volumeMounts:
                    - name: shared-signal
                      mountPath: /tmp/signal
                    - name: huggingface-storage
                      mountPath: /root/cloud-devkit/results
                    - name: dshm
                      mountPath: /dev/shm
                    - name: huggingface-storage
                      mountPath: /root/.cache
                      subPath: root_cache
                    - name: huggingface-storage
                      mountPath: /tmp/ray
                      subPath: ray_spill
                    - name: huggingface-storage
                      mountPath: /tmp/jax
                      subPath: jax_dump
                    - name: huggingface-storage
                      mountPath: /tmp/tpu_logs
                      subPath: tpu_logs

                  command: [ "/bin/bash", "-c" ]
                  args:
                    - |
                      mkdir -p ${{BASE_RESULTS_DIR}}/ray ${{BASE_RESULTS_DIR}}/tmp ${{BASE_RESULTS_DIR}}/.cache
                      cd /root/cloud-devkit/tpu-inference
                      (
                        while [ ! -f /tmp/signal/done ]; do sleep 2; done
                        echo "Benchmark finished! Sending kill signal to vLLM..."
                        pkill -9 -f "vllm serve"
                      ) &
                      echo "Starting vLLM serving ${{EXP_MODEL_NAME}}..."
                      export PYTHONUNBUFFERED=1
                      vllm serve ${{EXP_MODEL_NAME}} \\
                          --disable-hybrid-kv-cache-manager \\
                          --enable-chunked-prefill \\
                          --enable_prefix_caching \\
                          --gpu-memory-utilization ${{EXP_GPU_MEM_UTIL}} \\
                          --kv-transfer-config {kv_config} \\
                          --port 8000 \\
                          --seed 42 \\
                          --tensor-parallel-size 8 \\
                          --async-scheduling \\
                          --kv-cache-dtype fp8 \\
                          --max-model-len 262144 \\
                          --block-size 512
                      exit 0

                  resources:
                    limits:
                      google.com/tpu: 4
                      memory: "900Gi"
                    requests:
                      google.com/tpu: 4
                      memory: "900Gi"

                - name: sglang-client
                  image: us-central1-docker.pkg.dev/cloud-tpu-inference-test/vllm-tpu-rdna/vllm-tpu:sangamjindal-vllm-offload-apr-27
                  imagePullPolicy: Always
                  env:
                    - name: EXP_MODEL_NAME
                      value: "Qwen/Qwen3-235B-A22B-Instruct-2507-FP8"
                    - name: BASE_RESULTS_DIR
                      value: "/root/cloud-devkit/results"
                    - name: BASELINE_HOST
                      value: "localhost"
                    - name: BASELINE_PORT
                      value: "8000"
                    - name: PYTHONPATH
                      value: "/root/cloud-devkit/sglang/python"
                  volumeMounts:
                    - name: shared-signal
                      mountPath: /tmp/signal
                    - name: huggingface-storage
                      mountPath: /root/cloud-devkit/results
                    - name: dshm
                      mountPath: /dev/shm
                  command: [ "/bin/bash", "-c" ]
                  args:
                    - |
                      until curl -s http://localhost:8000/v1/models; do sleep 5; done
                      cd /root/cloud-devkit/sglang
                      python3 /root/cloud-devkit/sglang/python/sglang/bench_serving.py \\
                          --host="$BASELINE_HOST" \\
                          --port="$BASELINE_PORT" \\
                          --dataset-name="generated-shared-prefix" \\
                          --model="$EXP_MODEL_NAME" \\
                          --tokenizer="$EXP_MODEL_NAME" \\
                          --backend=vllm \\
                          --gsp-num-groups="{groups}" \\
                          --gsp-prompts-per-group="{prompts}" \\
                          --gsp-system-prompt-len="8192" \\
                          --gsp-question-len="128" \\
                          --gsp-output-len="{output_len}" \\
                          --request-rate="800" \\
                          --max-concurrency="{concurrency}" \\
                          --seed 42
                      touch /tmp/signal/done
                      exit 0
"""
    return recipe

jobs = []

# 1. Baseline for o2k (Offload is already running as j-6ade8bd8 and j-d748f3e2)
jobs.append({"g": 50, "p": 200, "o": 2048, "t": 17179869184, "off": False, "n": "qwen3-235b-base-50g-200p-o2k"})

# 2. Pairs for 4GB Threshold
configs_4g = [
    {"g": 600, "p": 15},
    {"g": 450, "p": 30},
    {"g": 150, "p": 30},
    {"g": 200, "p": 50}
]

for c in configs_4g:
    for off in [True, False]:
        mode = "offload" if off else "base"
        name = f"qwen3-235b-{mode}-{c['g']}g-{c['p']}p-t4g"
        jobs.append({"g": c['g'], "p": c['p'], "o": 256, "t": 4294967296, "off": off, "n": name})

with open("registry_patch_new.yml", "w") as rf:
    for j in jobs:
        content = generate_recipe(j['g'], j['p'], j['o'], j['t'], j['off'], j['n'])
        with open(f"{j['n']}.yml", "w") as f:
            f.write(content)
        rf.write(f"- name: \"{j['n']}\"\n")
        rf.write(f"  owner: \"chenjincheng_google_com\"\n")
        rf.write(f"  k8s_file: \"recipes/perf_comparison/{j['n']}.yml\"\n")
