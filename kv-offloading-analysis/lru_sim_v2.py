import collections
import random
import argparse
import sys

class LRUCache:
    def __init__(self, capacity_gb):
        self.capacity = capacity_gb
        self.current_size = 0
        self.cache = collections.OrderedDict()

    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return True
        return False

    def put(self, key, size_gb):
        if size_gb > self.capacity:
            return
        if key in self.cache:
            self.current_size -= self.cache[key]
            self.cache.move_to_end(key)
        self.cache[key] = size_gb
        self.current_size += size_gb
        while self.current_size > self.capacity:
            k, s = self.cache.popitem(last=False)
            self.current_size -= s

def run_simulation(cache_size, num_groups, prefix_size, question_size, output_size, reqs_per_group):
    total_requests = num_groups * reqs_per_group
    workload = []
    for g in range(num_groups):
        for r in range(reqs_per_group):
            workload.append({'group_id': g, 'req_id': g * reqs_per_group + r})
    
    random.shuffle(workload)
    
    cache = LRUCache(cache_size)
    prefix_tokens_hit = 0
    total_prefix_tokens_requested = 0
    
    for req in workload:
        prefix_key = f"p_{req['group_id']}"
        question_key = f"q_{req['req_id']}"
        output_key = f"o_{req['req_id']}"
        
        total_prefix_tokens_requested += prefix_size
        
        # 1. Prefix Access
        if cache.get(prefix_key):
            prefix_tokens_hit += prefix_size
        else:
            cache.put(prefix_key, prefix_size)
            
        # 2. Question/Output Access
        cache.put(question_key, question_size)
        cache.put(output_key, output_size)
        
    pHR = (prefix_tokens_hit / total_prefix_tokens_requested) * 100 if total_prefix_tokens_requested > 0 else 0
    return pHR

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TPU-Aligned LRU Cache Simulator v2 (Fixed HBM + Model Defaults)")
    parser.add_argument("--gsp-num-groups", type=int, required=True)
    parser.add_argument("--gsp-prompts-per-group", type=int, required=True)
    parser.add_argument("--gsp-system-prompt-len", type=int, required=True)
    parser.add_argument("--gsp-question-len", type=int, required=True)
    parser.add_argument("--gsp-output-len", type=int, required=True)
    parser.add_argument("--model", type=str, choices=["32B", "235B", "480B"], required=True)
    parser.add_argument("--utilization", type=float, required=True, help="vLLM GPU memory utilization (e.g. 0.9)")
    parser.add_argument("--cpu-cache-size-gb", type=float, help="CPU cache size (optional, uses model default if omitted)")
    parser.add_argument("--staging-buffer-size-gb", type=float, help="Staging buffer size (optional, uses model default if omitted)")

    args = parser.parse_args()

    # Model specific constants
    token_sizes = {"32B": 262144, "235B": 385024, "480B": 126976}
    model_weights = {"32B": 32, "235B": 235, "480B": 480}
    
    # Model defaults for staging and CPU cache
    default_staging = {"32B": 32.0, "235B": 47.0, "480B": 15.5}
    default_cpu = {"32B": 781.0, "235B": 550.0, "480B": 363.0}

    token_size_bytes = token_sizes[args.model]
    model_size_gb = model_weights[args.model]
    
    # Use user value if provided, else use default
    staging_buffer_gb = args.staging_buffer_size_gb if args.staging_buffer_size_gb is not None else default_staging[args.model]
    cpu_gb = args.cpu_cache_size_gb if args.cpu_cache_size_gb is not None else default_cpu[args.model]

    # Unit translation: Tokens to GB
    prefix_gb = (token_size_bytes * args.gsp_system_prompt_len) / (1024**3)
    question_gb = (token_size_bytes * args.gsp_question_len) / (1024**3)
    output_gb = (token_size_bytes * args.gsp_output_len) / (1024**3)

    # Cache Size Calculations
    total_hbm_gb = 94.75 * 8
    # HBM without offloading = Total * Util - Model - 35GB overhead
    hbm_base_gb = (total_hbm_gb * args.utilization) - model_size_gb - 35
    # HBM with offloading = HBM base - Staging buffer
    hbm_offload_gb = hbm_base_gb - staging_buffer_gb

    print(f"--- TPU-Aligned Simulation Config ({args.model}) ---")
    print(f"Total HBM (Node): {total_hbm_gb:.2f} GB")
    print(f"Prefix Size:      {prefix_gb:.4f} GB")
    print(f"Total Footprint:  {prefix_gb * args.gsp_num_groups:.2f} GB")
    print(f"--------------------------------------------------")
    print(f"Tier 1: HBM Only (Base)      Capacity: {hbm_base_gb:.2f} GB")
    print(f"Tier 2: HBM with Staging     Capacity: {hbm_offload_gb:.2f} GB")
    print(f"Tier 3: CPU Backend (Total)  Capacity: {cpu_gb:.2f} GB")
    print(f"--------------------------------------------------")

    # Run simulations
    hit_base = run_simulation(hbm_base_gb, args.gsp_num_groups, prefix_gb, question_gb, output_gb, args.gsp_prompts_per_group)
    hit_offload = run_simulation(hbm_offload_gb, args.gsp_num_groups, prefix_gb, question_gb, output_gb, args.gsp_prompts_per_group)
    hit_total = run_simulation(cpu_gb, args.gsp_num_groups, prefix_gb, question_gb, output_gb, args.gsp_prompts_per_group)

    print(f"RESULTS:")
    print(f"HBM Hit Rate (No Offload):   {hit_base:.2f}%")
    print(f"HBM Hit Rate (With Offload): {hit_offload:.2f}%")
    print(f"Total System Hit Rate:       {hit_total:.2f}%")
    print(f"--------------------------------------------------")
