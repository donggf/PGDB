document.addEventListener("DOMContentLoaded", function() {
    fetch('/browse_data')
    .then(response => response.json())
    .then(data => {
        const tbody = document.querySelector('.container table tbody');
        tbody.innerHTML = ''; // 清空现有的表格体内容

        // 收集所有的species内容
        const allSpecies = new Set();
        data.forEach(row => {
            if (row['species']) {
                allSpecies.add(row['species']);
            }
        });

        // 构建正则表达式匹配所有的species词汇
        const speciesRegex = new RegExp(Array.from(allSpecies).join("|"), "i");

        data.forEach(row => {
            const tr = document.createElement('tr');
            const fields = ['gene_id', 'gene_name', 'function_description', 'species', 'exact_strain', 'doi', 'Strict'];
            fields.forEach(field => {
                const td = document.createElement('td');
                
                if (field === 'gene_name') {
                    // 处理gene_name，使前三个字母斜体，最后一个字母正常
                    const link = document.createElement('a');
                    link.href = `/gene/${row[field]}`; // 设置链接
                    link.target = "_blank";  // 在新标签页中打开
                    const formattedName = `<i>${row[field].slice(0, 3)}</i>${row[field].slice(3)}`;
                    link.innerHTML = formattedName; // 使用innerHTML设置内容
                    td.appendChild(link);
                } else if (field === 'exact_strain' && row[field]) {
                    // 处理exact_strain，使其包含的任何species部分斜体
                    let formattedStrain = row[field].replace(speciesRegex, match => `<i>${match}</i>`);
                    td.innerHTML = formattedStrain; // 设置部分斜体
                } else {
                    td.textContent = row[field] || '';
                }
                
                // 为species应用斜体样式
                if (field === 'species') {
                    td.innerHTML = `<i>${td.textContent}</i>`;
                }
                
                tr.appendChild(td);
            });
            tbody.appendChild(tr);
        });
    })
    .catch(error => console.error('Error loading data:', error));
});

// 保持导航链接高亮的逻辑
document.addEventListener("DOMContentLoaded", function() {
    var path = window.location.pathname;
    var page = path.split("/").pop();

    var links = document.querySelectorAll(".navbar a");

    links.forEach(function(link) {
        if (link.getAttribute("href") === page) {
            link.classList.add("active");
        }
    });
});
