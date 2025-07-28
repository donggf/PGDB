## File Descriptions:

*   **Crawling PubMed Papers.py**: This script is used to **crawl and retrieve paper data** from the PubMed database.
*   **Merge two files based on DOI.py**: This script takes two input files and **merges them based on the Digital Object Identifier (DOI)**, ensuring that duplicate entries are removed in the process.
*   **Remove resistance.py**: This script filters the collected data to **remove studies primarily focused on drug resistance**.
*   **Screening articles containing gene names.py**: This script processes the articles to **select only those whose abstracts explicitly mention specific probiotic gene names**.
*   **data_delete.xlsx**: This Excel file contains the **training dataset used for classification tasks**.
*   **probiotic2.xlsx**: This Excel file serves as the **pre-training dataset for the probioticBERT model**.
*   **pubmed_8449.xlsx**: This Excel file contains **8,449 research papers data crawled from PubMed** database.
*   **wos_7380.xls**: This Excel file contains **7,380 research papers data exported from the Web of Science** platform.
*   **probioticBERT.py**: This script contains the Python code for **building and defining the probioticBERT language model**.
*   **RA-HGATSE.py**: This script contains the Python code for **building and defining the RA-HGATSE model**.
*   **participle_remove stop words.py**: This script performs text preprocessing steps, specifically **word segmentation (tokenization) and the removal of common stop words**.
*   **calculate node characteristic values.py**: This script is designed to **compute characteristic feature values for nodes**, likely within a graph structure derived from the data.
*   **calculate edge weight values.py**: This script is responsible for **calculating the weight values for edges** connecting nodes in a graph structure.
*   app.py: The backend code file for the platform, responsible for handling server logic and routing requests.
*   /static: Contains the platform's front-end assets, including CSS, JavaScript, and image files used for the user interface.
*   /templates: Stores the platform's front-end HTML files, responsible for rendering the structure and layout of the web pages.
