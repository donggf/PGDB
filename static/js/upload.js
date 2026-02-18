document.addEventListener('DOMContentLoaded', function() {
    var fileInput = document.getElementById('fileInput');
    var uploadButton = document.getElementById('uploadButton');
    var blastTypeRadios = document.getElementsByName('blast_type');

    // 移除已有的事件监听器以避免重复绑定
    fileInput.removeEventListener('change', handleFileInputChange);
    uploadButton.removeEventListener('click', handleUploadButtonClick);

    // 添加新的事件监听器
    fileInput.addEventListener('change', handleFileInputChange);
    uploadButton.addEventListener('click', handleUploadButtonClick);

    // 添加单选按钮事件监听器
    for (const radio of blastTypeRadios) {
        radio.addEventListener('change', handleBlastTypeChange);
    }

    highlightCurrentNavLink();
});

let selectedBlastType = 'blastp'; // 初始化选中的 BLAST 类型

function handleBlastTypeChange(event) {
    selectedBlastType = event.target.value;
}

function handleFileInputChange(event) {
    updateFileList(event.target.files);
}

function handleUploadButtonClick() {
    var fileInput = document.getElementById('fileInput');
    if (fileInput.files.length > 0) {
        console.log("Preparing to upload: ", fileInput.files);
        const resultsContainer = document.getElementById('resultsContainer');
        resultsContainer.style.display = 'block'; // 显示结果容器
        const processingMessage = document.createElement('p');
        processingMessage.id = 'processingMessage';
        processingMessage.textContent = 'Processing...';
        const resultsDataContainer = document.getElementById('resultsData');
        resultsDataContainer.innerHTML = ''; // 清除之前的结果
        resultsDataContainer.appendChild(processingMessage);
        uploadFile(fileInput.files[0], selectedBlastType); // 传递选中的 BLAST 类型
    } else {
        alert("Please select a file before uploading."); // 弹出提示框
        console.log("Please select a file first.");
    }
}

function highlightCurrentNavLink() {
    var path = window.location.pathname;
    var page = path.split("/").pop();
    var links = document.querySelectorAll(".navbar a");
    links.forEach(function(link) {
        if (link.getAttribute("href") === page) {
            link.classList.add("active");
        }
    });
}

function updateFileList(files) {
    var fileList = document.getElementById('uploadedFiles');
    fileList.innerHTML = '';
    Array.from(files).forEach(function(file, index) {
        var li = document.createElement('li');
        li.textContent = `File ${index + 1}: ${file.name} (${file.size} bytes)`;
        fileList.appendChild(li);
    });
}

function uploadFile(file, blastType) {
    var formData = new FormData();
    formData.append('blast_input_file', file);
    formData.append('blast_type', blastType); // 将选中的 BLAST 类型添加到表单数据中

    fetch('/upload_model_input', {
        method: 'POST',
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        displayResults(data.results);
        document.getElementById('processingMessage').textContent = 'Processing complete!';
    })
    .catch(error => {
        console.error('Error during processing:', error);
        document.getElementById('processingMessage').textContent = 'An error occurred during processing: ' + error.message;
    });
}

function displayResults(results) {
    console.log("Received results:", results);  // 添加此行以查看返回的结果
    const resultsDataContainer = document.getElementById('resultsData');
    resultsDataContainer.innerHTML = ''; // 清空之前的结果

    if (!results || results.length === 0) {
        resultsDataContainer.innerHTML = "<p>No results found.</p>";
        return;
    }

    let tablesByQseqid = {};
    // 分组结果
    results.forEach(result => {
        const qseqid = result.qseqid;
        if (!tablesByQseqid[qseqid]) {
            tablesByQseqid[qseqid] = [];
        }
        tablesByQseqid[qseqid].push(result);
    });

    // 为每个qseqid创建一个表
    Object.keys(tablesByQseqid).forEach(qseqid => {
        const table = document.createElement('table');
        table.classList.add('results-table');
        const thead = document.createElement('thead');
        const tbody = document.createElement('tbody');
        const headerRow = document.createElement('tr');
        const headers = ['qseqid', 'sseqid', 'length', 'pident', 'evalue'];
        headers.forEach(header => {
            const th = document.createElement('th');
            th.textContent = header;
            headerRow.appendChild(th);
        });
        thead.appendChild(headerRow);
        table.appendChild(thead);

        tablesByQseqid[qseqid].forEach(result => {
            const row = document.createElement('tr');
            headers.forEach(header => {
                const td = document.createElement('td');
                if (header === 'sseqid') {
                    const parts = result[header].split('|');
                    const geneId = parts[0];
                    const geneName = parts[1];
                    const geneIdLink = document.createElement('a');
                    geneIdLink.href = `/gene_id/${geneId}`; // 使用gene_id作为链接到详细页面
                    geneIdLink.textContent = geneId;
                    const geneNameLink = document.createElement('a');
                    geneNameLink.href = `/gene/${geneName}`; // 使用gene_name作为链接
                    geneNameLink.textContent = geneName;
                    td.appendChild(geneIdLink);
                    td.appendChild(document.createTextNode('|'));
                    td.appendChild(geneNameLink);
                } else {
                    td.textContent = result[header];
                }
                row.appendChild(td);
            });
            tbody.appendChild(row);
        });
        table.appendChild(tbody);
        resultsDataContainer.appendChild(table);
    });
}