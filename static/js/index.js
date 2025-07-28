document.addEventListener("DOMContentLoaded", function() {
  // 页面加载完毕后的处理逻辑
  var path = window.location.pathname;
  var page = path.split("/").pop();
  var links = document.querySelectorAll(".navbar a");

  links.forEach(function(link) {
    if (link.getAttribute("href") === page) {
      link.classList.add("active");
    }
  });

  var searchResultsDiv = document.getElementById('search-results-div');
  if (!searchResultsDiv || searchResultsDiv.children.length === 0) {
    var searchResultsContainer = document.querySelector('.search-results');
    if (searchResultsContainer) {
      searchResultsContainer.style.display = 'none';
    }
  }

  var searchForm = document.querySelector('.search-container form');
  searchForm.addEventListener('submit', function(event) {
    event.preventDefault();
    var searchField = searchForm.querySelector('select[name="search_field"]').value;
    var queryInput = searchForm.querySelector('input[name="query"]');
    var query = queryInput.value.trim();

    if (query) {
      var xhr = new XMLHttpRequest();
      xhr.open('GET', `/search?search_field=${encodeURIComponent(searchField)}&query=${encodeURIComponent(query)}`);
      xhr.onload = function() {
        if (xhr.status === 200) {
          var results = JSON.parse(xhr.responseText);
          var searchResultsContainer = document.querySelector('.search-results');
          if (searchResultsContainer) {
            searchResultsContainer.style.display = '';
          }
          displaySearchResults(results);
        } else {
          console.error('Error:', xhr.statusText);
        }
      };
      xhr.send();
    }
  });

  function displaySearchResults(results) {
    searchResultsDiv.innerHTML = '';

    var overviewSection = document.querySelector('.content');
    if (overviewSection) overviewSection.style.display = 'none';
    document.getElementById('overviewImage').style.display = 'none';

    // 以 gene_name 为组织数据，并处理下划线加数字的情况以及按照特定格式处理大小写
    const groupedByGeneName = results.reduce((acc, result) => {
      // 规范化基因名
      const normalizedGeneName = normalizeGeneName(result.gene_name.replace(/_\d+$/, ''));
      if (!acc[normalizedGeneName]) {
        acc[normalizedGeneName] = [];
      }
      acc[normalizedGeneName].push(result);
      return acc;
    }, {});

    // 显示每个 gene_name 的结果
    for (const geneName in groupedByGeneName) {
      const geneSection = document.createElement('div');
      geneSection.classList.add('gene-section');
      const geneTitle = document.createElement('h1');
      geneTitle.innerHTML = `<a href="/gene/${geneName}" target="_blank">${geneName}</a>`;
      geneSection.appendChild(geneTitle);

      groupedByGeneName[geneName].forEach((result, index) => {
        var item = document.createElement('div');
        item.classList.add('search-item');
        item.innerHTML = '<h4>Report' + (index + 1) + ':' + '</h4>' +
                         '<p>' + 'Unique_id: ' + result.unique_id + '</p>' +
                         '<p>' + 'Function_description: ' + result.function_description + '</p>' +
                         '<p>' + 'Species: ' + result.species + '</p>' +
                         '<p>' + 'DOI: ' + result.doi + '</p>';
        geneSection.appendChild(item);
      });

      searchResultsDiv.appendChild(geneSection);
    }
  }

  // 函数用于规范化基因名格式
  function normalizeGeneName(geneName) {
    if (geneName.length > 3) {
      return geneName.substring(0, 3).toLowerCase() + geneName.substring(3).toUpperCase();
    }
    return geneName.toLowerCase(); // 如果基因名长度小于或等于3，全部转为小写
  }
});
