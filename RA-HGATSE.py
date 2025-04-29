# +GAT +SE pro412 保存模型 添加RA
import json
import os
import torch
from torch.nn import Module, Linear, ReLU, Sigmoid
from torch_geometric.nn import GATConv  # 引入 GATConv 模块
from torch_geometric.data import Data
from sklearn.model_selection import KFold
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
from torch.optim import Adam
import torch.nn.functional as F

# 定义 SE 模块
class SEBlock(Module):
    def __init__(self, channels, reduction=16):
        super(SEBlock, self).__init__()
        # 将输入通道数设置为 512，适应 GAT 的输出
        self.fc1 = Linear(channels, channels // reduction, bias=False)
        self.fc2 = Linear(channels // reduction, channels, bias=False)
        self.relu = ReLU()
        self.sigmoid = Sigmoid()

    def forward(self, x):
        # Squeeze: 全局池化 (节点特征的通道聚合)
        z = x.mean(dim=0, keepdim=True)  # 聚合通道信息
        # Excitation: 学习权重
        z = self.fc1(z)
        z = self.relu(z)
        z = self.fc2(z)
        z = self.sigmoid(z)
        # Reweighting: 对每个通道进行加权
        return x * z

# 加载节点和边数据
with open('graph_nodes_probert412.json', 'r') as f:
    node_data = json.load(f)

with open('graph_edges_probert412.json', 'r') as f:
    edge_data = json.load(f)

# 获取节点特征和标签
features = []
labels = []
for node in node_data['nodes']:
    features.append(node['feature'])  # 直接使用 BERT 生成的特征
    if node['type'] == 'document':
        labels.append(node['label'])  # 文档标签

# 转换为 Tensor
features = torch.tensor(features, dtype=torch.float).cuda()  # 节点特征矩阵 (N x D)
labels = torch.tensor(labels, dtype=torch.long).cuda()  # 文档标签 (N,)

# 构造边列表
edge_index = []
edge_weight = []

# 文档-词汇边
for edge in edge_data['doc_word_edges']:
    edge_index.append([edge['source'], edge['target']])
    edge_weight.append(edge['weight'])

# 全局词汇-词汇边
for edge in edge_data['global_word_word_edges']:
    edge_index.append([edge['source'], edge['target']])
    edge_weight.append(edge['weight'])

# 单文档内词汇-词汇边
for edge in edge_data['single_doc_word_word_edges']:
    edge_index.append([edge['source'], edge['target']])
    edge_weight.append(edge['weight'])

# 转换为 Tensor
edge_index = torch.tensor(edge_index, dtype=torch.long).t().contiguous().cuda()  # 边索引 (2 x E)
edge_weight = torch.tensor(edge_weight, dtype=torch.float).cuda()  # 边权重 (E,)

# 构造图数据
data = Data(x=features, edge_index=edge_index, edge_attr=edge_weight)

# 定义 RA-HGNN + GAT + SE 模块模型
class HybridAttentionModel(Module):
    def __init__(self, in_channels, hidden_channels, out_channels, num_heads):
        super(HybridAttentionModel, self).__init__()
        
        # GAT 层
        self.gat1 = GATConv(in_channels, hidden_channels, heads=num_heads, dropout=0.6)
        self.gat2 = GATConv(hidden_channels * num_heads, hidden_channels, heads=num_heads, dropout=0.6)
        
        # 残差连接层
        self.residual = Linear(hidden_channels * num_heads, hidden_channels * num_heads)
        
        # SE 模块
        self.se_block = SEBlock(hidden_channels * num_heads)
        
        # 缩减维度以匹配分类器的输入
        self.fc = Linear(hidden_channels * num_heads, hidden_channels)
        
        # 分类器
        self.classifier = Linear(hidden_channels, out_channels)
        self.relu = ReLU()

    def forward(self, x, edge_index, edge_weight):
        # 第一个GAT层
        x = self.gat1(x, edge_index, edge_weight)
        x = self.relu(x)
        
        # 第二个GAT层 + 残差连接
        gat2_out = self.gat2(x, edge_index, edge_weight)
        residual = self.residual(x)
        x = self.relu(gat2_out + residual)  # 添加残差连接
        
        # SE模块加权
        x = self.se_block(x)
        
        # 降维
        x = self.fc(x)
        
        # 分类
        logits = self.classifier(x)
        return logits

# 计算类别权重
from collections import Counter
label_counts = Counter(labels[:562].tolist())  # 只考虑文档节点的标签
total_samples = sum(label_counts.values())
class_weights = [total_samples / label_counts[label] for label in sorted(label_counts.keys())]

# 转换为 PyTorch Tensor（类别权重）
class_weights = torch.tensor(class_weights, dtype=torch.float).cuda()

# 十折交叉验证
kf = KFold(n_splits=10, shuffle=True, random_state=10)
fold_results = []

# 初始化模型
model = HybridAttentionModel(
    in_channels=features.shape[1],
    hidden_channels=128,
    out_channels=2,  # 二分类
    num_heads=4  # 多头注意力头数
).cuda()
optimizer = Adam(model.parameters(), lr=0.005, weight_decay=0.001)

for train_idx, test_idx in kf.split(range(562)):  # 562 是文档节点数
    # 构造训练集和测试集的掩码
    train_mask = torch.zeros(562, dtype=torch.bool).cuda()
    test_mask = torch.zeros(562, dtype=torch.bool).cuda()
    train_mask[train_idx] = True
    test_mask[test_idx] = True

    # 模型训练
    for epoch in range(200):
        model.train()
        optimizer.zero_grad()
        out = model(data.x, data.edge_index, data.edge_attr)
        
        # 只选取文档节点部分的输出（前 562 个节点）
        out_docs = out[:562]

        # 使用类别权重计算损失
        loss = F.cross_entropy(out_docs[train_mask], labels[train_mask], weight=class_weights)
        loss.backward()
        optimizer.step()

    # 模型测试
    model.eval()
    with torch.no_grad():
        out = model(data.x, data.edge_index, data.edge_attr)
        
        # 只选取文档节点部分的输出（前 562 个节点）
        out_docs = out[:562]
        
        preds = out_docs[test_mask].argmax(dim=1)
        true_labels = labels[test_mask]

        preds_np = preds.cpu().numpy()
        true_labels_np = true_labels.cpu().numpy()
        prob_np = out_docs[test_mask].softmax(dim=1).cpu().numpy()  # 概率分布

        # AUC 仅取正类的概率
        auc = roc_auc_score(true_labels_np, prob_np[:, 1])

        # 计算其他指标
        acc = accuracy_score(true_labels_np, preds_np)
        precision = precision_score(true_labels_np, preds_np, average='weighted')
        recall = recall_score(true_labels_np, preds_np, average='weighted')
        f1 = f1_score(true_labels_np, preds_np, average='weighted')

        # 保存指标
        fold_results.append({'accuracy': acc, 'precision': precision, 'recall': recall, 'f1': f1, 'auc': auc})

# 保存最终模型
save_dir = "RA-HGATSE"
os.makedirs(save_dir, exist_ok=True)
final_model_path = os.path.join(save_dir, "final_model.pt")
torch.save({
    'model_state_dict': model.state_dict(),
    'optimizer_state_dict': optimizer.state_dict(),
}, final_model_path)
print(f"最终模型已保存到 {final_model_path}")

# 计算十折交叉验证的平均值
average_results = {key: sum([result[key] for result in fold_results]) / len(fold_results) for key in fold_results[0]}
print(f"十折交叉验证平均结果: {average_results}")
