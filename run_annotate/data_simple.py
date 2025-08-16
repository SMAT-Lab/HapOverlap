import os
import json
import shutil

benchmark_path = 'Benchmark/benchmark_full.json'
source_root = 'overlap_visualizations_3_sampled_complete'
target_root = 'simple_benchmark_vis'

with open(benchmark_path, 'r', encoding='utf-8') as f:
    benchmark = json.load(f)

for app, samples in benchmark.items():
    app_src_dir = os.path.join(source_root, app)
    app_dst_dir = os.path.join(target_root, app)
    if not os.path.exists(app_src_dir):
        print(f"源目录不存在: {app_src_dir}")
        continue
    os.makedirs(app_dst_dir, exist_ok=True)
    sample_prefixes = set(samples.keys())
    for fname in os.listdir(app_src_dir):
        for sample in sample_prefixes:
            if fname.startswith(sample):
                src_file = os.path.join(app_src_dir, fname)
                dst_file = os.path.join(app_dst_dir, fname)
                if os.path.isfile(src_file):
                    shutil.copy2(src_file, dst_file)
                break  # 一个文件只匹配一个sample前缀即可
    print(f"已复制 {app_src_dir} -> {app_dst_dir}")

print("全部抽取完成！") 