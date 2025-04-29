# 数据预处理 分词 去停用词
import pandas as pd
import spacy
from nltk.corpus import stopwords
import nltk

# 下载 NLTK 所需的资源
nltk.download('stopwords')

# 加载 spaCy 模型
nlp = spacy.load("en_core_web_sm")

# 获取 NLTK 的停用词表
stop_words = set(stopwords.words('english'))

# 数据预处理函数
def preprocess_text(text):
    """
    结合 spaCy 和 NLTK 的文本预处理：
    - 使用 spaCy 分词
    - 使用 NLTK 停用词表去掉停用词
    - 转为小写，仅保留字母单词
    """
    if pd.isnull(text):  # 如果文本为空，返回空字符串
        return ''
    # 使用 spaCy 分词
    doc = nlp(text)
    # 去停用词，仅保留字母单词
    filtered_words = [token.text.lower() for token in doc if token.is_alpha and token.text.lower() not in stop_words]
    return ' '.join(filtered_words)

# 读取 Excel 文件
input_file = 'data_delete_num.xlsx'
df = pd.read_excel(input_file)

# 对 Abstract 列进行预处理，添加新列 'Processed_Abstract'
df['Processed_Abstract'] = df['Abstract'].apply(preprocess_text)

# 输出到新的 Excel 文件
output_file = 'data_processed_combined.xlsx'
df.to_excel(output_file, index=False)

print(f"预处理完成，结果已保存到 {output_file}")
