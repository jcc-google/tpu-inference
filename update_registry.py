new_recipes = [
    {"groups": 600, "prompts": 15},
    {"groups": 450, "prompts": 30},
    {"groups": 150, "prompts": 30},
    {"groups": 200, "prompts": 50}
]

with open("registry_patch.yml", "w") as f:
    for r in new_recipes:
        for mode in ["base", "offload"]:
            name = f"qwen3-235b-{mode}-{r['groups']}g-{r['prompts']}p"
            f.write(f"- name: \"{name}\"\n")
            f.write(f"  owner: \"chenjincheng_google_com\"\n")
            f.write(f"  k8s_file: \"recipes/perf_comparison/{name}.yml\"\n")
