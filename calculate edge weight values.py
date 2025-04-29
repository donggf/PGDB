# 计算边权重 probioticbert
import pandas as pd
import json
from transformers import AutoTokenizer, AutoModel
from collections import Counter
from itertools import combinations
import numpy as np
import torch

# 文件路径
xlsx_file = 'data_processed_combined.xlsx'
json_file = 'graph_nodes_probert0.json'
output_file = 'graph_edges_probert0.json'
model_dir = 'probioticbert10/checkpoint-14556'  # 替换为您的模型路径

# 加载 BERT 模型和分词器
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
tokenizer = AutoTokenizer.from_pretrained(model_dir)
model = AutoModel.from_pretrained(model_dir).to(device)

# 读取 Excel 文件和 JSON 文件
df = pd.read_excel(xlsx_file)
with open(json_file, 'r') as f:
    graph_data = json.load(f)

# 获取文档文本和词汇表
documents = df['Processed_Abstract'].tolist()
vocabulary = [node['word'] for node in graph_data['nodes'] if node['type'] == 'word']
word_to_idx = {word: idx for idx, word in enumerate(vocabulary)}  # 构建词汇表索引

# 文档数量和词汇数量
num_docs = len(documents)
vocab_size = len(vocabulary)

# 构建文档-词汇边（BERT 特征）
print("计算文档-词汇边权重中...")
doc_word_edges = []
for doc_id, doc in enumerate(documents):
    inputs = tokenizer(doc, return_tensors='pt', truncation=True, max_length=512, padding='max_length').to(device)
    with torch.no_grad():
        outputs = model(**inputs)
    cls_embedding = outputs.last_hidden_state[:, 0, :].squeeze(0).cpu().numpy()  # 获取 [CLS] 向量

    for word in doc.split():  # 遍历文档中的每个词汇
        if word in word_to_idx:
            word_inputs = tokenizer(word, return_tensors='pt', truncation=True, max_length=512, padding='max_length').to(device)
            with torch.no_grad():
                word_outputs = model(**word_inputs)
            word_embedding = word_outputs.last_hidden_state[:, 0, :].squeeze(0).cpu().numpy()  # 获取词汇 [CLS] 向量
            weight = np.dot(cls_embedding, word_embedding) / (np.linalg.norm(cls_embedding) * np.linalg.norm(word_embedding))  # 计算余弦相似度

            if weight > 0:  # 保留非零权重边
                doc_word_edges.append({
                    "source": doc_id,
                    "target": num_docs + word_to_idx[word],  # 词汇节点 ID 从文档节点后开始
                    "weight": weight
                })

# 构建全局词汇-词汇边（NPMI 权重）
print("计算全局词汇-词汇边权重中...")
word_occurrences = Counter()  # 记录每个词的出现次数
pair_occurrences = Counter()  # 记录词对的共同出现次数
total_windows = 0

for doc in documents:
    words = doc.split()
    total_windows += len(words) - 2  # 窗口总数（假设每窗口3词）
    for i in range(len(words) - 2):  # 滑动窗口生成词对
        window = words[i:i + 3]
        for word in window:
            word_occurrences[word] += 1
        for word1, word2 in combinations(window, 2):
            pair_occurrences[frozenset([word1, word2])] += 1

# 计算 NPMI
word_word_edges = []
for pair, co_occurrence in pair_occurrences.items():
    if len(pair) == 2:  # 确保 pair 包含两个单词
        word1, word2 = list(pair)
        if word1 in word_to_idx and word2 in word_to_idx:
            p_xy = co_occurrence / total_windows
            p_x = word_occurrences[word1] / total_windows
            p_y = word_occurrences[word2] / total_windows
            npmi = (np.log(p_xy / (p_x * p_y)) / -np.log(p_xy)) if p_xy > 0 else 0
            if npmi > 0.5:  # 稀疏化
                word_word_edges.append({
                    "source": num_docs + word_to_idx[word1],
                    "target": num_docs + word_to_idx[word2],
                    "weight": npmi
                })

# 构建单文档内词汇-词汇边（滑动窗口）
print("计算单文档内词汇-词汇边权重中...")
single_doc_word_edges = []
for doc_id, doc in enumerate(documents):
    words = doc.split()
    for i in range(len(words) - 2):  # 滑动窗口生成词对
        window = words[i:i + 3]
        for word1, word2 in combinations(window, 2):
            if word1 in word_to_idx and word2 in word_to_idx:
                single_doc_word_edges.append({
                    "source": num_docs + word_to_idx[word1],
                    "target": num_docs + word_to_idx[word2],
                    "weight": 1.0,  # 滑动窗口的边权重设为 1
                    "document_id": doc_id  # 标明属于哪个文档
                })

# 合并所有边
graph_edges = {
    "doc_word_edges": [],
    "global_word_word_edges": [],
    "single_doc_word_word_edges": []
}

# 转换文档-词汇边
for edge in doc_word_edges:
    edge["weight"] = float(edge["weight"])  # 确保为原生 float 类型
    graph_edges["doc_word_edges"].append(edge)

# 转换全局词汇-词汇边
for edge in word_word_edges:
    edge["weight"] = float(edge["weight"])  # 确保为原生 float 类型
    graph_edges["global_word_word_edges"].append(edge)

# 转换单文档内词汇-词汇边
for edge in single_doc_word_edges:
    edge["weight"] = float(edge["weight"])  # 确保为原生 float 类型
    graph_edges["single_doc_word_word_edges"].append(edge)

# 保存为 JSON 文件
print(f"保存图边到 {output_file} 中...")
with open(output_file, 'w') as f:
    json.dump(graph_edges, f, separators=(',', ':'), ensure_ascii=False)

print(f"图的边已生成并保存到 {output_file}")

