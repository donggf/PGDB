document.addEventListener("DOMContentLoaded", function() {
    // 获取当前页面的URL路径
    var path = window.location.pathname;
    // 提取文件名
    var page = path.split("/").pop();
  
    // 获取所有导航链接
    var links = document.querySelectorAll(".navbar a");
  
    // 循环所有链接，查找与当前页面文件名匹配的链接
    links.forEach(function(link) {
        if (link.getAttribute("href") === page) {
            // 为匹配的链接添加高亮的class
            link.classList.add("active");
        }
    });
  
    // 获取文件输入元素和与之关联的标签元素
    var fileInput = document.getElementById('sequence_file');
    var fileLabel = document.querySelector("label[for='sequence_file']");
  
    // 监听文件输入的变化
    fileInput.addEventListener('change', function(event) {
        if (this.files.length > 0) {
            // 如果有文件被选择，更新标签以显示文件名
            fileLabel.textContent = 'Selected: ' + this.files[0].name;
        } else {
            // 如果没有文件被选择，恢复标签的原始文本
            fileLabel.textContent = 'Choose File';
        }
    });
  
    var form = document.querySelector("form"); // 获取表单元素
    form.addEventListener("submit", function(event) {
        event.preventDefault(); // 阻止表单的默认提交行为

        // 检查必填字段是否已全部填写（除了amino_acid_sequence，稍后单独检查）
        var missingFields = [];
        var requiredFields = ['name', 'email', 'gene_name', 'function_description', 'species', 'exact_strain', 'doi'];
        requiredFields.forEach(function(fieldName) {
            var input = document.querySelector(`[name="${fieldName}"]`);
            if (!input || !input.value.trim()) {
                missingFields.push(fieldName.replace('_', ' '));  // 将字段名称格式化为可读形式
            }
        });

        // 检查amino_acid_sequence是否通过文件上传或数据框填写
        var aminoAcidInput = document.querySelector("[name='amino_acid_sequence']");
        if (!fileInput.files.length && (!aminoAcidInput || !aminoAcidInput.value.trim())) {
            missingFields.push('amino acid sequence');
        }

        if (missingFields.length > 0) {
            alert('Please fill in the following required fields: ' + missingFields.join(', '));
            return; // 如果有必填字段未填写，中止提交
        }

        var formData = new FormData(form); // 创建 FormData 对象，自动从表单中收集数据
        // 使用 fetch API 异步提交表单数据到服务器
        fetch('/submit_data', {
            method: 'POST',
            body: formData  // 直接传递 FormData 对象
        })
        .then(response => response.json()) // 解析响应为JSON
        .then(data => {
            alert(data.message); // 根据响应处理结果，例如显示提交成功消息
            form.reset(); // 清空表单
            fileLabel.textContent = 'Choose File'; // 重置自定义文件上传按钮文本
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Submission failed'); // 处理错误情况，例如显示提交失败消息
        });
    });
});
