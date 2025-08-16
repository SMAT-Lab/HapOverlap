import os
import json
from tabulate import tabulate
import matplotlib.pyplot as plt

def stat_yes_labels(directory):
    app_yes_counts = {}  # {app: yes_count}
    app_samples = {}     # {app: [(filename, sample, label)]}
    for filename in os.listdir(directory):
        if filename.endswith('.json'):
            filepath = os.path.join(directory, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for app, samples in data.items():
                            yes_count = 0
                            sample_list = []
                            if isinstance(samples, dict):
                                for sample, info in samples.items():
                                    if isinstance(info, dict) and 'ai' in info and isinstance(info['ai'], dict):
                                        label = info['ai'].get('label', 'N/A')
                                        if label == 'Yes':
                                            yes_count += 1
                                        sample_list.append((filename, sample, label))
                            if yes_count > 0:
                                app_yes_counts[app] = yes_count
                                app_samples[app] = sample_list
            except Exception as e:
                print(f"{filename} 解析出错: {e}")
    return app_yes_counts, app_samples

if __name__ == "__main__":
    directory = "annotations_2"
    app_yes_counts, app_samples = stat_yes_labels(directory)

    # 输出表格
    table = []
    for app, samples in app_samples.items():
        for filename, sample, label in samples:
            if label == 'Yes':
                table.append([app, filename, sample, label])
    headers = ["应用名", "文件名", "Sample", "AI Label"]
    print(tabulate(table, headers=headers, tablefmt="grid"))

    # 绘制柱状图
    if app_yes_counts:
        plt.figure(figsize=(10, 6))
        apps = list(app_yes_counts.keys())
        yes_counts = [app_yes_counts[app] for app in apps]
        plt.bar(apps, yes_counts, color='skyblue')
        plt.xlabel('应用名')
        plt.ylabel('AI Label为Yes的数量')
        plt.title('每个应用下AI Label为Yes的样本数')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.show()
    else:
        print("没有AI Label为Yes的应用。")