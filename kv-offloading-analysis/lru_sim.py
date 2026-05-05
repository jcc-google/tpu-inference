import collections
import random
import argparse
import sys

class LRUCache:
    def __init__(self, capacity):
        self.capacity = capacity
        self.current_size = 0
        self.cache = collections.OrderedDict()

    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return True
        return False

    def put(self, key, size):
        if size > self.capacity:
            return
        if key in self.cache:
            self.current_size -= self.cache[key]
            self.cache.move_to_end(key)
        self.cache[key] = size
        self.current_size += size
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
    prefix_hits = 0
    
    # Tracking write-back sizes
    prefix_write_back = 0
    question_write_back = 0
    output_write_back = 0
    
    total_prefix_tokens_hit = 0
    total_tokens_requested = 0
    
    for req in workload:
        prefix_key = f"p_{req['group_id']}"
        question_key = f"q_{req['req_id']}"
        output_key = f"o_{req['req_id']}"
        
        # 1. Prefix Access
        if cache.get(prefix_key):
            prefix_hits += 1
            total_prefix_tokens_hit += prefix_size
            # Hit: No write-back
        else:
            cache.put(prefix_key, prefix_size)
            prefix_write_back += prefix_size
            
        # 2. Question/Output Access (always misses and writes)
        cache.put(question_key, question_size)
        question_write_back += question_size
        
        cache.put(output_key, output_size)
        output_write_back += output_size
        
        total_tokens_requested += (prefix_size + question_size + output_size)
        
    pHR = (prefix_hits / total_requests) * 100 if total_requests > 0 else 0
    tHR = (total_prefix_tokens_hit / total_tokens_requested) * 100 if total_tokens_requested > 0 else 0
    
    metrics = {
        "prefix_hit_rate": pHR,
        "token_hit_rate": tHR,
        "prefix_write": prefix_write_back,
        "question_write": question_write_back,
        "output_write": output_write_back,
        "total_requests": total_requests,
        "total_tokens_requested": total_tokens_requested
    }
    return metrics

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate LRU cache for KV Offloading.")
    parser.add_argument("--cache-size", type=float, required=True, help="Total capacity of the cache.")
    parser.add_argument("--num-groups", type=int, required=True, help="Number of distinct groups (shared prefixes).")
    parser.add_argument("--prefix-size", type=float, required=True, help="Size of each prefix.")
    parser.add_argument("--question-size", type=float, required=True, help="Size of each unique question.")
    parser.add_argument("--output-size", type=float, required=True, help="Size of each unique output.")
    parser.add_argument("--req-per-group", type=int, required=True, help="Number of requests per group.")

    args = parser.parse_args()
    
    m = run_simulation(
        args.cache_size, 
        args.num_groups, 
        args.prefix_size, 
        args.question_size, 
        args.output_size, 
        args.req_per_group
    )
    
    total_write = m['prefix_write'] + m['question_write'] + m['output_write']
    
    print("--- LRU Cache Simulation Results ---")
    print(f"Cache Size:          {args.cache_size:,.2f}")
    print(f"Total Requests:      {m['total_requests']}")
    print(f"------------------------------------")
    print(f"Prefix Hit Rate:     {m['prefix_hit_rate']:.2f}%")
    print(f"Token Hit Rate:      {m['token_hit_rate']:.2f}%")
    print(f"------------------------------------")
    print(f"Data Written to Cache (Write-back):")
    print(f"  - Prefix:          {m['prefix_write']:,.2f}")
    print(f"  - Question:        {m['question_write']:,.2f}")
    print(f"  - Output:          {m['output_write']:,.2f}")
    print(f"  - TOTAL WRITTEN:   {total_write:,.2f}")
    print(f"------------------------------------")
    print(f"Total Data Requested: {m['total_tokens_requested']:,.2f}")
