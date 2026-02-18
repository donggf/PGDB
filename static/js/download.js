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
  });

  