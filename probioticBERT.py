# 1.2 更改模型加载方法AutoTokenizer,加载了biobert-config,保存全了,使用BertForPreTraining,动态掩码、学习率调度和fp16，增加sop任务，保存最佳，（100，412）
import pandas as pd
from transformers import AutoTokenizer, BertForPreTraining, Trainer, TrainingArguments, DataCollatorForLanguageModeling, AutoConfig
from datasets import Dataset
import random
import numpy as np
import torch
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials
import json

# 设置随机种子
def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

set_seed(10)

# 强制使用CUDA 
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch.backends.mps.is_available = lambda: False
torch.backends.mps.is_built = lambda: False

print(f"Using device: {device}")

# 读取Excel文件
df = pd.read_excel('probiotic2.xlsx')

# 提取 'Abstract' 列作为训练数据
abstracts = df['Abstract'].tolist()

# 准备数据集用于NSP和SOP任务
data = {'text': [], 'next_sentence_label': [], 'sentence_order_label': []}
for i in range(len(abstracts) - 1):
    # NSP任务
    data['text'].append(abstracts[i] + " [SEP] " + abstracts[i+1])  
    data['next_sentence_label'].append(1)
    data['sentence_order_label'].append(1)  # 添加SOP标签
    
    data['text'].append(abstracts[i] + " [SEP] " + abstracts[random.randint(0, len(abstracts) - 1)])
    data['next_sentence_label'].append(0)
    data['sentence_order_label'].append(1)  # 添加SOP标签
    
    # SOP任务
    sentences = abstracts[i].split('. ')
    if len(sentences) > 1:
        data['text'].append(sentences[0] + " [SEP] " + sentences[1])
        data['next_sentence_label'].append(1)  # 添加NSP标签
        data['sentence_order_label'].append(1)
        
        data['text'].append(sentences[1] + " [SEP] " + sentences[0]) 
        data['next_sentence_label'].append(1)  # 添加NSP标签
        data['sentence_order_label'].append(0)

dataset = Dataset.from_dict(data)

# 数据集划分为训练集和验证集
dataset = dataset.train_test_split(test_size=0.1, seed=10)
train_dataset = dataset['train'] 
eval_dataset = dataset['test']

# 加载BioBERT的tokenizer
tokenizer = AutoTokenizer.from_pretrained('./biobert-model')  # 确保此路径指向包含tokenizer文件的目录

# 数据预处理函数:tokenization和padding
def preprocess_function(examples):
    # 对文本进行tokenize
    tokenized_texts = tokenizer(examples['text'], truncation=True, padding='max_length', max_length=512)
    
    # 处理文本长度
    for i in range(len(tokenized_texts['input_ids'])):
        input_ids = tokenized_texts['input_ids'][i]
        if len(input_ids) > 512:
            # 如果长度超过512,取前100个和后412个token
            input_ids = input_ids[:100] + input_ids[-412:]
            tokenized_texts['token_type_ids'][i] = tokenized_texts['token_type_ids'][i][:100] + tokenized_texts['token_type_ids'][i][-412:]
            tokenized_texts['attention_mask'][i] = tokenized_texts['attention_mask'][i][:100] + tokenized_texts['attention_mask'][i][-412:]
        
    tokenized_texts['next_sentence_label'] = examples['next_sentence_label']
    tokenized_texts['sentence_order_label'] = examples['sentence_order_label']
    return tokenized_texts

# 处理数据集
tokenized_train_dataset = train_dataset.map(preprocess_function, batched=True, remove_columns=train_dataset.column_names)
tokenized_eval_dataset = eval_dataset.map(preprocess_function, batched=True, remove_columns=eval_dataset.column_names)

# 加载模型配置
config = AutoConfig.from_pretrained('./biobert-model')

# 定义超参数搜索空间
space = {
    'learning_rate': hp.loguniform('learning_rate', np.log(1e-5), np.log(1e-3)),
    'mlm_probability': hp.uniform('mlm_probability', 0.1, 0.3)  
}

# 动态掩码数据收集器
class DynamicMaskingCollator(DataCollatorForLanguageModeling):
    def __call__(self, examples):
        # 每次调用时重新设置mlm_probability
        self.mlm_probability = random.uniform(0.1, 0.3)
        return super().__call__(examples)

best_eval_loss = float('inf')  # 初始化最佳评估损失为无穷大
best_params = None  # 初始化最佳超参数为None

def objective(params):
    global best_eval_loss, best_params  # 声明全局变量
    
    # 使用动态掩码数据收集器  
    data_collator = DynamicMaskingCollator(
        tokenizer=tokenizer,
        mlm=True,
        mlm_probability=params['mlm_probability']
    )

    # 使用 BertForPreTraining 替代 BertForMaskedLM
    model = BertForPreTraining.from_pretrained('./biobert-model', config=config, ignore_mismatched_sizes=True)
    model.to(device)

    # 训练参数
    training_args = TrainingArguments(
        output_dir='./probioticbert10',  # 将所有输出保存在这个目录
        overwrite_output_dir=True,           # 如果输出目录存在,覆盖它  
        num_train_epochs=3,                  # 训练轮数
        per_device_train_batch_size=8,       # 每个设备的训练批次大小
        per_device_eval_batch_size=8,        # 每个设备的评估批次大小
        learning_rate=params['learning_rate'],  # 学习率
        lr_scheduler_type='linear',          # 学习率调度器类型
        weight_decay=0.01,                   # 权重衰减
        eval_strategy="epoch",               # 每个epoch结束时进行评估
        save_strategy="epoch",               # 每个epoch结束时保存模型
        load_best_model_at_end=True,         # 训练结束后加载最佳模型
        metric_for_best_model='eval_loss',   # 选择最佳模型的评估指标
        save_total_limit=1,                  # 限制保存的模型数量,以节省空间
        fp16=True,                           # 启用fp16混合精度训练
        warmup_ratio=0.1,                    # 预热比例
    )

    # Trainer API进行训练
    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=data_collator,
        train_dataset=tokenized_train_dataset,
        eval_dataset=tokenized_eval_dataset
    )

    # 开始训练
    trainer.train()
    
    # 评估模型的好坏
    eval_results = trainer.evaluate()
    eval_loss = eval_results['eval_loss']
    
    # 如果当前评估损失更小,则更新最佳评估损失和最佳超参数,并保存所有组件
    if eval_loss < best_eval_loss:
        best_eval_loss = eval_loss
        best_params = params
        save_all(trainer, model, tokenizer, './probioticbert10', params)
    
    return {'loss': eval_loss, 'status': STATUS_OK}

def save_all(trainer, model, tokenizer, output_dir, best_params):
    # 保存模型和tokenizer
    trainer.save_model(output_dir)
    
    # 确保tokenizer被保存(虽然save_model通常会做这个)
    tokenizer.save_pretrained(output_dir)
    
    # 保存训练状态
    trainer.save_state()
    
    # 保存最佳超参数
    with open(f"{output_dir}/best_hyperparameters.json", "w") as f:
        json.dump(best_params, f)
    
    print(f"All components saved to {output_dir}")

# 使用Hyperopt进行超参数优化
trials = Trials()
fmin(fn=objective, space=space, algo=tpe.suggest, max_evals=10, trials=trials)

print("Best hyperparameters:", best_params)
print("Best evaluation loss:", best_eval_loss)