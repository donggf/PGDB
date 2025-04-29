import requests
from bs4 import BeautifulSoup
import pandas as pd

# Prompt user to input keyword and number of pages
keyword = input('Please enter the English keyword you want to search for and press Enter: ')
num_pages = input('Please enter the number of pages you want to view and press Enter: ')
article_count = 1  # Article counter

# Create an empty DataFrame to store data
df = pd.DataFrame(columns=['Article Title', 'Abstract', 'DOI'])

for j in range(1, int(num_pages) + 1):  # Iterate through the specified number of pages
    url = 'https://pubmed.ncbi.nlm.nih.gov/?term=' + keyword + '&page=' + str(j)
    response = requests.get(url)

    # Check HTTP response status
    if response.status_code == 200:
        print(f'Processing page {j}...')
    else:
        print(f'Page {j} request failed (Status code: {response.status_code})')
        continue

    parser = BeautifulSoup(response.text, 'html.parser')
    content = parser.find_all('div', class_='docsum-content')

    for i in content:
        title = i.find('a', class_='docsum-title').text.strip()
        pmid = i.find('a')['href']
        detail_url = 'https://pubmed.ncbi.nlm.nih.gov' + pmid
        detail_response = requests.get(detail_url)
        parser2 = BeautifulSoup(detail_response.text, 'html.parser')

        # Try to get the abstract
        try:
            abstract = parser2.find('div', class_='abstract-content selected').text.strip()
        except AttributeError:
            abstract = 'Unable to retrieve the abstract'

        # Try to get the DOI number
        try:
            doi_span = parser2.find('span', class_='identifier doi')
            doi_link = doi_span.find('a', class_='id-link')
            doi_number = doi_link.get_text(strip=True)
        except AttributeError:
            doi_number = 'DOI not available'

        # Combine title, abstract, and DOI number into a paragraph
        paragraph = {'Article Title': title, 'Abstract': abstract, 'DOI': doi_number}

        # Add the paragraph to the DataFrame
        df = pd.concat([df, pd.DataFrame([paragraph])], ignore_index=True)

        print(f'Article {article_count}: Title: {title}, Abstract retrieved, DOI: {doi_number}')
        article_count += 1

# Save the DataFrame as an Excel file
df.to_excel("pubmed_results.xlsx", index=False)

print('Scraping complete, results saved to Excel file.')
