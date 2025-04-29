import pandas as pd
import re

# Read all rows from the second column of the Excel file
file_path = 'savedrecs.xls'
column_number = 1  # Index of the second column (0-based index)

# Use pandas to read the Excel file
data = pd.read_excel(file_path)

# Get the data from the second column
column_data = data.iloc[:, column_number]

# Extract matching words from each row's abstract and the entire row containing matching words
matched_rows = []
gene_names = []

for index, row in data.iterrows():
    matches = re.findall(r'\b[a-z]{3}[A-Z]\b', str(row[column_number]))
    if matches:
        matched_rows.append(row)
        gene_names.extend(matches)

# Remove duplicate gene names
unique_gene_names = list(set(gene_names))

# Write the entire rows containing matching words to a new Excel file
matched_data = pd.DataFrame(matched_rows)
matched_data.to_excel("savedrecs_selected.xls", index=False)
