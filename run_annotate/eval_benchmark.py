import os
import json

benchmark_path = 'Benchmark/benchmark_full.json'
anno_dir = 'anno_human_ai_2'

with open(benchmark_path, 'r', encoding='utf-8') as f:
    benchmark = json.load(f)

# Ground truth: 只要有一个模型文件中 human.label == '高成本渲染组件遮挡'，就算作正例
all_samples = set()
ground_truth = set()

for filename in os.listdir(anno_dir):
    if not filename.endswith('.json'):
        continue
    filepath = os.path.join(anno_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for app, samples in data.items():
        for sample, info in samples.items():
            if app not in benchmark or sample not in benchmark[app]:
                continue
            all_samples.add((app, sample))
            if info.get('human', {}).get('label') == '高成本渲染组件遮挡':
                ground_truth.add((app, sample))

# 针对每个模型单独评估
results = {}
for filename in os.listdir(anno_dir):
    if not filename.endswith('.json'):
        continue
    model_name = filename.replace('.json', '')
    filepath = os.path.join(anno_dir, filename)
    ai_predict = set()
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for app, samples in data.items():
        for sample, info in samples.items():
            if app not in benchmark or sample not in benchmark[app]:
                continue
            if info.get('ai', {}).get('label') == 'Yes':
                ai_predict.add((app, sample))
    TP = len(ground_truth & ai_predict)
    FP = len(ai_predict - ground_truth)
    FN = len(ground_truth - ai_predict)
    TN = len(all_samples - ground_truth - ai_predict)
    P = len(ground_truth)
    N = len(all_samples) - P
    accuracy = (TP + TN) / (P + N) if (P + N) > 0 else 0
    precision = TP / (TP + FP) if (TP + FP) > 0 else 0
    recall = TP / P if P > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    false_positive_rate = FP / N if N > 0 else 0
    results[model_name] = {
        'TP': TP, 'FP': FP, 'FN': FN, 'TN': TN,
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'false_positive_rate': false_positive_rate,
        'predict_yes': len(ai_predict),
        'total': len(all_samples)
    }

for model, res in results.items():
    print(f"\n模型: {model}")
    print(f"  总样本数: {res['total']}")
    print(f"  TP(命中): {res['TP']}")
    print(f"  FP(误报): {res['FP']}")
    print(f"  FN(漏报): {res['FN']}")
    print(f"  TN(真负): {res['TN']}")
    print(f"  AI预测为Yes数: {res['predict_yes']}")
    print(f"  准确率(Accuracy): {res['accuracy']:.4f}")
    print(f"  精确率(Precision): {res['precision']:.4f}")
    print(f"  召回率(Recall): {res['recall']:.4f}")
    print(f"  F1分数: {res['f1']:.4f}")
    print(f"  误报率(False Positive Rate): {res['false_positive_rate']:.4f}") 