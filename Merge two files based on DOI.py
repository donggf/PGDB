import pandas as pd

# Define file paths
pubmed_file_path = 'pubmed_non_resistance.xls'
wos_file_path = 'wos_non_resistance.xls'

# Read Excel files
pubmed_df = pd.read_excel(pubmed_file_path)
wos_df = pd.read_excel(wos_file_path)

# Combine the two dataframes and remove duplicates
combined_df = pd.concat([pubmed_df, wos_df]).drop_duplicates(subset='DOI')

# Drop rows where the DOI column is empty
combined_df.dropna(subset=['DOI'], inplace=True)

# Save to a new file
combined_df.to_excel('combined_non_resistance.xlsx', index=False)
