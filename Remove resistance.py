import pandas as pd
import re

# Read all rows from the Excel file
file_path = 'pubmed_selected.xls'

# Use pandas to read the Excel file
data = pd.read_excel(file_path)

# Extract rows that do not contain the word "resistance"
non_resistance_rows = []

for index, row in data.iterrows():
    # Check if the content of the first and second columns contains the word "resistance"
    if not re.search(r'\bresistance\b', str(row[0]), flags=re.IGNORECASE) and \
       not re.search(r'\bresistance\b', str(row[1]), flags=re.IGNORECASE):
        non_resistance_rows.append(row)

# Write rows without "resistance" to a new Excel file
non_resistance_data = pd.DataFrame(non_resistance_rows)
non_resistance_data.to_excel("pubmed_non_resistance.xls", index=False)
