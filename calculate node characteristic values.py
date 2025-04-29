# 计算节点 probioticbert
import pandas as pd
import json
import torch
from transformers import AutoTokenizer, AutoModel

# 文件路径
input_file = 'data_processed_combined.xlsx'
output_file = 'graph_nodes_probert0.json'
model_dir = 'probioticbert10/checkpoint-14556'  # 替换为您的模型路径

# 加载 BERT 模型和分词器
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
tokenizer = AutoTokenizer.from_pretrained(model_dir)
model = AutoModel.from_pretrained(model_dir).to(device)

# 读取 Excel 文件
df = pd.read_excel(input_file)

# 获取文档 ID、预处理后的文本和标签
document_ids = df['id'].tolist()  # 文档 ID
documents = df['Processed_Abstract'].tolist()  # 文本内容
labels = df['label'].tolist()  # 文档标签

# 提取文档特征
print("提取文档特征中...")
doc_features = []
for doc in documents:
    inputs = tokenizer(doc, return_tensors='pt', truncation=True, max_length=512, padding='max_length').to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze(0).cpu().numpy()  # 获取 [CLS] 向量
    doc_features.append(cls_embedding)

# 构建词汇表
print("构建词汇表并提取词汇特征中...")
vocabulary = set(word for doc in documents for word in doc.split())
vocabulary = sorted(list(vocabulary))  # 确保词汇表有固定顺序

# 提取词汇特征
word_features = {}
for word in vocabulary:
    inputs = tokenizer(word, return_tensors='pt', truncation=True, max_length=512, padding='max_length').to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze(0).cpu().numpy()  # 获取 [CLS] 向量
    word_features[word] = cls_embedding

# 构造 JSON 数据结构
print("构建节点数据中...")
data = {"nodes": []}

# 添加文档节点及其特征和标签
for doc_id, (doc_feature, label) in enumerate(zip(doc_features, labels)):
    data["nodes"].append({
        "id": doc_id,
        "type": "document",
        "feature": doc_feature.tolist(),  # 转为列表保存
        "label": label  # 添加标签
    })

# 添加词汇节点及其特征
for word_idx, word in enumerate(vocabulary):
    data["nodes"].append({
        "id": len(document_ids) + word_idx,  # 词汇节点 ID 从文档节点后开始
        "type": "word",
        "feature": word_features[word].tolist(),  # 词汇特征向量
        "word": word  # 新增字段，表示该节点的词汇
    })

# 保存为 JSON 文件（单行格式）
print(f"保存节点数据到 {output_file} 中...")
with open(output_file, 'w') as f:
    json.dump(data, f, separators=(',', ':'), ensure_ascii=False)

print(f"节点数据已保存到 {output_file}")
