// 添加事件监听器到按钮
document.getElementById('submitBtn').addEventListener('click', function () {
    // 获取用户输入的日期
    const startDate = document.getElementById('startDate').value || '2023-01-01';
    const endDate = document.getElementById('endDate').value || '3000';

    // 将日期格式化为 YYYY/MM/DD
    const formattedStartDate = startDate.replace(/-/g, '/');
    const formattedEndDate = endDate.replace(/-/g, '/');

    // 生成 PubMed 高级检索式
    const searchQuery = `(((((probiotic gene[Title/Abstract]) NOT (review[Title])) NOT (comprehensive[Title])) NOT (analysis[Title])) NOT (resistance[Title/Abstract])) AND (("${formattedStartDate}"[Date - Publication] : "${formattedEndDate}"[Date - Publication]))`;

    // 显示加载中的提示
    const resultDiv = document.getElementById('result');
    const predictionsDiv = document.getElementById('predictions');
    
    resultDiv.innerHTML = '<div class="loading">The processing time may take a little longer.We appreciate your patience!<br>Processing...</div>';
    predictionsDiv.innerHTML = '';

    // 向后端发送请求
    fetch('/model/retrieval', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ query: searchQuery })
    })
    .then(response => response.json())
    .then(data => {
        console.log('Raw response data:', data);
        console.log('Predictions array:', data.predictions);
    
        console.log('Received data:', data); // 调试用

        resultDiv.innerHTML = `
            <div class="success-message">
                <p>Query processed successfully</p>
                <p>User ID: ${data.user_id}</p>
            </div>
        `;

        // 检查并显示预测结果
        if (data.predictions && Array.isArray(data.predictions)) {
            const table = document.createElement('table');
            table.className = 'predictions-table';
            
            // 创建表头
            const thead = document.createElement('thead');
            thead.innerHTML = `
                <tr>
                    <th>ID</th>
                    <th>Article Title</th>
                    <th>Abstract</th>
                    <th>DOI</th>
                    <th>Prediction</th>
                </tr>
            `;
            table.appendChild(thead);

            // 创建表体
            const tbody = document.createElement('tbody');
            data.predictions.forEach(row => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${row.id ?? ''}</td>
                    <td class="title-cell">${row['Article Title'] ?? ''}</td>
                    <td class="abstract-cell">
                        <div class="abstract-content">${row.Abstract ?? ''}</div>
                    </td>
                    <td>${row.DOI ?? ''}</td>
                    <td>${row.Prediction ?? ''}</td>
                `;
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);

            predictionsDiv.innerHTML = '';
            predictionsDiv.appendChild(table);
        } else {
            predictionsDiv.innerHTML = '<p class="no-data">No prediction results available.</p>';
        }
    })
    .catch(error => {
        console.error('Error:', error); // 调试用
        resultDiv.innerHTML = `
            <div class="error-message">
                Error: ${error.message || 'Failed to process request'}
            </div>
        `;
        predictionsDiv.innerHTML = '';
    });
});

// 添加必要的样式
const styles = `
    .loading {
        text-align: center;
        padding: 20px;
        color: #666;
    }

    .success-message {
        padding: 10px;
        background-color: #e8f5e9;
        border-radius: 4px;
        margin-bottom: 20px;
    }

    .error-message {
        padding: 10px;
        background-color: #ffebee;
        border-radius: 4px;
        color: #c62828;
    }

    /* 修改 predictions-table 的容器样式 */
    #predictions {
        max-height: 600px;  /* 设置最大高度，超过后显示滚动条 */
        overflow-y: auto;   /* 添加垂直滚动条 */
        margin: 20px 0;     /* 添加一些边距 */
    }

    .predictions-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 0;      /* 改为 0，因为外层容器已经有边距 */
        font-size: 14px;
    }

    /* 固定表头 */
    .predictions-table thead {
        position: sticky;
        top: 0;
        background-color: #f5f5f5;
        z-index: 1;
    }

    .predictions-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 20px;
        font-size: 14px;
    }

    .predictions-table th,
    .predictions-table td {
        border: 1px solid #ddd;
        padding: 12px;
        text-align: left;
    }

    .predictions-table th {
        background-color: #f5f5f5;
        font-weight: bold;
    }

    .predictions-table .title-cell {
        max-width: 300px;
    }

    .predictions-table .abstract-cell {
        max-width: 400px;
    }

    .abstract-content {
        max-height: 100px;
        overflow-y: auto;
        white-space: pre-wrap;
    }

    .predictions-table tr:nth-child(even) {
        background-color: #f9f9f9;
    }

    .predictions-table tr:hover {
        background-color: #f5f5f5;
    }

    .no-data {
        text-align: center;
        color: #666;
        padding: 20px;
    }
`;

// 添加样式到页面
const styleSheet = document.createElement('style');
styleSheet.textContent = styles;
document.head.appendChild(styleSheet);