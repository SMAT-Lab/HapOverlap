import os
import json

input_dir = 'anno_human_ai_2'
output_dir = 'Benchmark'
os.makedirs(output_dir, exist_ok=True)

# {(app, sample): {'ai': set([model1, model2]), 'human': True/False}}
benchmark = {}

for filename in os.listdir(input_dir):
    if not filename.endswith('.json'):
        continue
    model_name = filename.replace('.json', '')
    filepath = os.path.join(input_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for app, samples in data.items():
        for sample, info in samples.items():
            key = (app, sample)
            ai_label = info.get('ai', {}).get('label')
            human_label = info.get('human', {}).get('label')
            if ai_label == 'Yes':
                benchmark.setdefault(key, {'ai': set(), 'human': False})['ai'].add(model_name)
            if human_label == '高成本渲染组件遮挡':
                benchmark.setdefault(key, {'ai': set(), 'human': False})['human'] = True

# 分类统计
only_ai = []
only_human = []
both = []
for key, v in benchmark.items():
    app, sample = key
    if v['ai'] and not v['human']:
        only_ai.append({'app': app, 'sample': sample, 'models': sorted(list(v['ai']))})
    elif v['human'] and not v['ai']:
        only_human.append({'app': app, 'sample': sample})
    elif v['human'] and v['ai']:
        both.append({'app': app, 'sample': sample, 'models': sorted(list(v['ai']))})

# 输出到json
stat_path = os.path.join(output_dir, 'benchmark_stat.json')
full_path = os.path.join(output_dir, 'benchmark_full.json')

# benchmark_full: {app: {sample: {ai: [...], human: bool}}}
benchmark_full = {}
for (app, sample), v in benchmark.items():
    if app not in benchmark_full:
        benchmark_full[app] = {}
    benchmark_full[app][sample] = {
        'ai': sorted(list(v['ai'])),
        'human': v['human']
    }

with open(stat_path, 'w', encoding='utf-8') as f:
    json.dump({'only_ai': only_ai, 'only_human': only_human, 'both': both}, f, ensure_ascii=False, indent=2)
with open(full_path, 'w', encoding='utf-8') as f:
    json.dump(benchmark_full, f, ensure_ascii=False, indent=2, sort_keys=True)

print(f"已输出统计到 {stat_path} 和 {full_path}")
print(f"总benchmark条目数: {len(benchmark)}")
print(f"只出现在某个model中的: {len(only_ai)}")
print(f"只出现在Human判断中的: {len(only_human)}")
print(f"同时出现在Human和至少一个model中的: {len(both)}")
