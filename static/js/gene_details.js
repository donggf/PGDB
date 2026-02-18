document.addEventListener('DOMContentLoaded', function() {
  const toggleButtons = document.querySelectorAll('.toggle-button');
  toggleButtons.forEach(button => {
    button.addEventListener('click', function() {
      const hiddenText = this.previousElementSibling;
      if (hiddenText.style.display === 'none') {
        hiddenText.style.display = 'inline';
        this.textContent = 'Show Less';
      } else {
        hiddenText.style.display = 'none';
        this.textContent = 'Show More';
      }
    });
  });

  document.querySelectorAll('.feedback-btn').forEach(button => {
    button.addEventListener('click', function() {
      const geneId = this.dataset.geneId;
      const feedbackScore = prompt("Please provide feedback, where 1 represents the least credible and 10 represents the most trustworthy.");
      if (feedbackScore && !isNaN(feedbackScore)) {
        fetch('/submit_feedback', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
          body: `gene_id=${encodeURIComponent(geneId)}&feedback_score=${encodeURIComponent(feedbackScore)}`
        })
        .then(response => response.json())
        .then(data => alert("Feedback submitted successfully"))
        .catch(error => console.error('Error:', error));
      }
    });
  });
});
