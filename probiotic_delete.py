# 取差集，排除标题大小写和标点的干扰
import pandas as pd
import string

def normalize_text(text):
    # 移除标点符号
    text = text.translate(str.maketrans('', '', string.punctuation))
    # 转换为小写
    return text.lower()

# 读取文件
all_df = pd.read_excel('probiotic.xlsx')
delete_df = pd.read_excel('data_delete1.xlsx')

# 标准化Article Title列
all_df['Normalized Title'] = all_df['Article Title'].apply(normalize_text)
delete_df['Normalized Title'] = delete_df['Article Title'].apply(normalize_text)

# 获取需要删除的标准化标题列表
delete_titles = delete_df['Normalized Title'].tolist()

# 过滤all_df，删除标准化标题在delete_titles列表中的行
filtered_all_df = all_df[~all_df['Normalized Title'].isin(delete_titles)]

# 删除临时使用的Normalized Title列
filtered_all_df = filtered_all_df.drop(columns=['Normalized Title'])

# 将结果保存到新文件
filtered_all_df.to_excel('probiotic_delete.xlsx', index=False)

print("新文件probiotic_delete.xlsx已生成，且不包含Normalized Title列。")
