// static/script.js (最终交互修正版)
document.addEventListener('DOMContentLoaded', function() {
    
    // 我们只选择那些不在'disabled-group'里的标签选项的<label>元素进行监听
    document.querySelectorAll('.label-group:not(.disabled-group) .label-option label').forEach(label => {
        label.addEventListener('click', function(event) {
            
            // 浏览器会自动因为for属性处理radio的选中，我们只需处理后续逻辑
            // 延迟一小段时间确保DOM更新完毕
            setTimeout(() => {
                const labelOptionDiv = this.closest('.label-option');
                const sampleContainer = this.closest('.sample-container');
                const group = this.closest('.label-group');

                // 更新UI：移除同组其他选项的'selected'样式，并为当前项添加
                group.querySelectorAll('.label-option').forEach(opt => {
                    opt.classList.remove('selected');
                });
                labelOptionDiv.classList.add('selected');

                // 标记为人工标注
                sampleContainer.classList.remove('ai-annotated');
                sampleContainer.classList.add('human-annotated');
                
                // 触发保存逻辑
                handleAnnotation(this);
            }, 0);
        });
    });

    async function handleAnnotation(labelElement) {
        const sampleContainer = labelElement.closest('.sample-container');
        const appName = sampleContainer.dataset.appName;
        const sampleId = sampleContainer.dataset.sampleId;
        // labelId直接从被点击的<label>的data属性获取
        const labelId = labelElement.dataset.labelId;

        try {
            const response = await fetch('/annotate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    app_name: appName,
                    sample_id: sampleId,
                    label: labelId,
                }),
            });
            const result = await response.json();
            if (result.status === 'success') {
                console.log("人工标注已保存:", appName, sampleId, "->", labelId);
            } else {
                alert('保存失败: ' + result.message);
            }
        } catch (error) {
            console.error('网络或服务器错误:', error);
            alert('网络或服务器错误，保存失败。');
        }
    }
});