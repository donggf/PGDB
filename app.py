# 跑本地模型, 适应新，为服务器适配
from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import os
from werkzeug.utils import secure_filename
import pandas as pd
import torch
from transformers import AutoConfig, AutoTokenizer, AutoModelForSequenceClassification
from torch import nn
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from flask import send_from_directory, Flask
import subprocess 
from Bio import SeqIO
from datetime import datetime
from uuid import uuid4




app = Flask(__name__)

# 配置数据库连接
#app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:12345678@127.0.0.1:3306/test'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://flask:12345678@127.0.0.1:3306/flask'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# 初始化数据库实例
db = SQLAlchemy(app)

# index页面
@app.route('/')
def index():
    # 渲染并返回主页
    return render_template('index.html')


@app.route('/search')
def search():
    query = request.args.get('query')
    search_field = request.args.get('search_field', 'gene_name')  # 默认搜索字段为gene_name

    # 当用户选择function_description时，实际上在abstract字段上搜索
    if search_field == 'function_description':
        search_field = 'abstract'

    if search_field not in ['gene_name', 'abstract', 'species', 'doi']:
        return jsonify([]), 400  # 如果提供了不正确的字段名，返回空列表和400错误

    # 安全地构建查询语句
    sql_query = text(f"""
    SELECT gene_id, article_title, abstract, unique_id, sequence_source, gene_name, function_description, species, exact_strain, doi, amino_acid_sequence, nucleotide_sequence, Strict, evaluate 
    FROM data 
    WHERE {search_field} LIKE :query
    """)

    results = db.session.execute(sql_query, {'query': f'%{query}%'}).fetchall()

    results_list = []
    for row in results:
        results_list.append({
            'gene_id': row[0],
            'article_title':row[1],
            'abstract':row[2],
            'unique_id': row[3],
            'sequence_source': row[4],
            'gene_name': row[5],
            'function_description': row[6],
            'species': row[7],
            'exact_strain': row[8],
            'doi': row[9],
            'amino_acid_sequence': row[10],
            'nucleotide_sequence':row[11],
            'Strict': row[12],
            'evaluate': row[13]
        })

    return jsonify(results_list)



# browse页面 
@app.route('/browse')
def browse():
    # 直接渲染并返回browse.html页面
    return render_template('browse.html')

@app.route('/browse_data')
def browse_data():
    sql_query = text("""
    SELECT gene_id,  gene_name, function_description, species, exact_strain, doi, Strict
    FROM data
    """)
    results = db.session.execute(sql_query).fetchall()

    results_list = []
    for row in results:
        results_list.append({
            'gene_id': row[0],
            'gene_name': row[1],
            'function_description': row[2],
            'species': row[3],
            'exact_strain': row[4],
            'doi': row[5],
            'Strict': row[6],
        })

    return jsonify(results_list)



# submit页面
class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    email = db.Column(db.String(255), nullable=False)
    institution = db.Column(db.String(255))
    gene_id = db.Column(db.String(255))
    unique_id = db.Column(db.String(255))
    sequence_source = db.Column(db.String(255))
    gene_name = db.Column(db.String(255), nullable=False)
    function_description = db.Column(db.String(255), nullable=False)
    species = db.Column(db.String(255), nullable=False)
    exact_strain = db.Column(db.String(255), nullable=False)
    doi = db.Column(db.String(255), nullable=False)
    amino_acid_sequence = db.Column(db.Text(length=4294967295), nullable=False)
    strict = db.Column(db.String(255))

# 确保在启动应用前创建了所有数据库表
with app.app_context():
    db.create_all()


@app.route('/submit')
def submit():
    return render_template('submit.html')

@app.route('/submit_data', methods=['POST'])
def submit_data():
    amino_file = request.files.get('sequence_file')

    if amino_file and amino_file.filename != '':
        # 读取氨基酸序列文件内容
        amino_acid_sequence = amino_file.read().decode('utf-8')
    else:
        # 使用表单提交的序列
        amino_acid_sequence = request.form['amino_acid_sequence']

  
        
    new_submission = Submission(
        name=request.form.get('name', ''),
        email=request.form.get('email', ''),
        institution=request.form.get('institution', ''),
        gene_id=request.form.get('gene_id', ''),
        unique_id=request.form.get('unique_id', ''),
        sequence_source=request.form.get('sequence_source', ''),
        gene_name=request.form.get('gene_name', ''),
        function_description=request.form.get('function_description', ''),
        species=request.form.get('species', ''),
        exact_strain=request.form.get('exact_strain', ''),
        doi=request.form.get('doi', ''),
        amino_acid_sequence=amino_acid_sequence,
        strict=request.form.get('strict', '0')
    )
    
    db.session.add(new_submission)
    db.session.commit()

    return jsonify({'message': 'Data submitted successfully'}), 200



# blast页面
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

@app.route('/blast')
def blast():
    return render_template('blast.html')

@app.route('/upload_model_input', methods=['POST'])
def upload_file():
    if 'blast_input_file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['blast_input_file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Generate a unique filename for the uploaded file
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    unique_id = uuid4().hex
    filename = f"{timestamp}_{unique_id}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    # Generate a unique filename for the results
    results_filename = f"{timestamp}_{unique_id}_results.txt"
    results_path = os.path.join(app.config['RESULTS_FOLDER'], results_filename)

    # 用户选择的BLAST类型
    blast_type = request.form.get('blast_type', 'blastp')

    # 根据BLAST类型选择数据库
    db_path = "/www/wwwroot/probioticgene/pgdb_blast_db" if blast_type in ['blastp', 'blastx'] else "/www/wwwroot/probioticgene/pgdb_blast_nucleotide_db"

    # 调用相应的BLAST程序
    subprocess.run([
        f"/www/wwwroot/probioticgene/ncbi-blast-2.15.0+/bin/{blast_type}",
        "-query", filepath,
        "-db", db_path,
        "-out", results_path,
        "-evalue", "1e-10",
        "-outfmt", "7 qseqid sseqid qlen slen pident length mismatch gapopen qstart qend sstart send evalue bitscore"
    ], check=True)

    filtered_results = filter_blast_results(results_path, 60, 40)

    return jsonify({'results': filtered_results})

def filter_blast_results(filename, min_length_percentage, min_identity_percentage):
    """筛选 BLAST 结果，基于比对长度百分比和身份百分比"""
    filtered_results = []
    with open(filename, 'r') as file:
        for line in file:
            parts = line.strip().split()
            if parts[0].startswith('#'):
                continue
            identity = float(parts[4])
            alignment_length = int(parts[5])
            query_total_length = int(parts[2])

            if (alignment_length >= min_length_percentage * query_total_length / 100.0 and
                identity >= min_identity_percentage):
                filtered_results.append({
                    'qseqid': parts[0],
                    'sseqid': parts[1],
                    'pident': parts[4],
                    'length': parts[5],
                    'evalue': parts[12]
                })

    return filtered_results


# download页面
@app.route('/download')
def download():
    return render_template('download.html')

# tutorial页面
@app.route('/tutorial')
def tutorial():
    return render_template('tutorial.html')

# about页面
@app.route('/about')
def about():
    return render_template('about.html')



# 详细基因页面
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gene_id = db.Column(db.String(255), nullable=False)  # 外键已去除
    feedback_score = db.Column(db.Integer, nullable=False)

    def __init__(self, gene_id, feedback_score):
        self.gene_id = gene_id
        self.feedback_score = feedback_score

# 确保在启动应用前创建了所有数据库表
with app.app_context():
    db.create_all()
 
@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    gene_id = request.form.get('gene_id')
    feedback_score = request.form.get('feedback_score')
    if not gene_id or not feedback_score:
        return jsonify({'error': 'Missing gene_id or feedback_score'}), 400
    try:
        feedback_score = int(feedback_score)
    except ValueError:
        return jsonify({'error': 'Invalid feedback_score'}), 400

    feedback = Feedback(gene_id=gene_id, feedback_score=feedback_score)
    db.session.add(feedback)
    db.session.commit()

    return jsonify({'message': 'Feedback submitted successfully'}), 200


@app.route('/gene/<gene_name>')
def gene_details(gene_name):
    # 使用 LIKE 操作符来实现模糊匹配
    sql_query = text("""
    SELECT gene_id, article_title, abstract, unique_id, sequence_source, gene_name, function_description, species, exact_strain, doi, amino_acid_sequence, nucleotide_sequence, Strict, evaluate 
    FROM data 
    WHERE gene_name LIKE :gene_name
    """)
    # 添加 '%' 通配符以匹配任何包含gene_name的字符串
    results = db.session.execute(sql_query, {'gene_name': f"%{gene_name}%"}).fetchall()
    genes = []
    for result in results:
        genes.append({
            'gene_id': result[0],
            'article_title': result[1],
            'abstract': result[2],
            'unique_id': result[3],
            'sequence_source': result[4],
            'gene_name': result[5],
            'function_description': result[6],
            'species': result[7],
            'exact_strain': result[8],
            'doi': result[9],
            'amino_acid_sequence': result[10],
            'nucleotide_sequence': result[11],
            'Strict': result[12],
            'evaluate': result[13]
        })
    if genes:
        # 传递 genes 列表和 gene_name 到模板
        return render_template('gene_details.html', genes=genes, gene_name=gene_name)
    else:
        return "<h1>Gene not found</h1>", 404
    

    
@app.route('/gene_id/<gene_id>')
def gene_id_details(gene_id):
    # 这里可以编写查询数据库的逻辑，使用 gene_id 作为查询参数
    sql_query = text("""
    SELECT gene_id, article_title, abstract, unique_id, sequence_source, gene_name, function_description, species, exact_strain, doi, amino_acid_sequence, nucleotide_sequence, Strict, evaluate 
    FROM data 
    WHERE gene_id = :gene_id
    """)
    result = db.session.execute(sql_query, {'gene_id': gene_id}).fetchone()
    if result:
        gene = {
            'gene_id': result[0],
            'article_title': result[1],
            'abstract': result[2],
            'unique_id': result[3],
            'sequence_source': result[4],
            'gene_name': result[5],
            'function_description': result[6],
            'species': result[7],
            'exact_strain': result[8],
            'doi': result[9],
            'amino_acid_sequence': result[10],
            'nucleotide_sequence': result[11],
            'Strict': result[12],
            'evaluate': result[13]
        }
        return render_template('gene_id_details.html', gene=gene)
    else:
        return "<h1>Gene ID not found</h1>", 404

import os
import uuid
from flask import Flask, render_template, request, jsonify, send_file
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import spacy
from nltk.corpus import stopwords
import nltk
import json
import torch
from transformers import AutoTokenizer, AutoModel
from collections import Counter
from itertools import combinations
import numpy as np
from torch.nn import Module, Linear, ReLU, Sigmoid
from torch_geometric.nn import GATConv
from torch_geometric.data import Data

# 检查是否有可用的 GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

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

# 定义 RA-HGNN + GAT + SE 模块模型
class HybridAttentionModel(Module):
    def __init__(self, in_channels, hidden_channels, out_channels, num_heads):
        super(HybridAttentionModel, self).__init__()
        
        # GAT 层
        self.gat1 = GATConv(in_channels, hidden_channels, heads=num_heads, dropout=0.6)
        self.gat2 = GATConv(hidden_channels * num_heads, hidden_channels, heads=num_heads, dropout=0.6)
        
        # SE 模块
        self.se_block = SEBlock(hidden_channels * num_heads)  # 输出维度为 hidden_channels * num_heads
        
        # 缩减维度以匹配分类器的输入
        self.fc = Linear(hidden_channels * num_heads, hidden_channels)  # 将 GAT 的输出维度缩减为 hidden_channels
        
        # 分类器
        self.classifier = Linear(hidden_channels, out_channels)
        self.relu = ReLU()

    def forward(self, x, edge_index, edge_weight):
        # GAT 层
        x = self.gat1(x, edge_index, edge_weight)
        x = self.relu(x)
        x = self.gat2(x, edge_index, edge_weight)
        
        # 添加 SE 模块进行加权
        x = self.se_block(x)
        
        # 使用 fc 层缩减输出维度
        x = self.fc(x)
        
        # 分类器
        logits = self.classifier(x)
        return logits

# model页面
@app.route('/model')
def model():
    return render_template('model.html')
  
# 接收用户查询的 POST 请求
@app.route('/model/retrieval', methods=['POST'])
def retrieval():
    data = request.json
    query = data.get('query', '')

    # 处理接收到的查询
    print(f"Received search query: {query}")

    # 生成唯一的用户ID
    user_id = str(uuid.uuid4())

    # 爬全部页码数据
    关键字 = query
    g = 1  # 篇章计数

    # 创建一个空的 DataFrame 用于存储数据
    df = pd.DataFrame(columns=['Article Title', 'Abstract', 'DOI'])

    页码 = 1  # 从第一页开始

    while True:  # 不断请求直到没有更多数据
        网址 = f'https://pubmed.ncbi.nlm.nih.gov/?term={关键字}&page={页码}'
        获取网址 = requests.get(网址)

        # 检查HTTP响应状态
        if 获取网址.status_code == 200:
            print(f'正在处理第 {页码} 页...')
        else:
            print(f'第 {页码} 页请求失败 (状态码: {获取网址.status_code})，停止爬取。')
            break

        解析器 = BeautifulSoup(获取网址.text, 'html.parser')
        内容 = 解析器.find_all('div', class_='docsum-content')

        if not 内容:  # 如果没有更多内容，停止爬取
            print('没有更多数据，爬取完成。')
            break

        for i in 内容:
            标题 = i.find('a', class_='docsum-title').text.strip()
            PMID = i.find('a')['href']
            详细网址 = 'https://pubmed.ncbi.nlm.nih.gov' + PMID
            详细 = requests.get(详细网址)
            解析器2 = BeautifulSoup(详细.text, 'html.parser')

            # 尝试获取摘要
            try:
                摘要 = 解析器2.find('div', class_='abstract-content selected').text.strip()
            except AttributeError:
                摘要 = '无法获取该篇摘要'

            # 尝试获取DOI号
            try:
                doi_span = 解析器2.find('span', class_='identifier doi')
                doi_link = doi_span.find('a', class_='id-link')
                doi_number = doi_link.get_text(strip=True)
            except AttributeError:
                doi_number = 'DOI号不可用'

            # 将标题、摘要、DOI号等信息拼接成一个段落
            段落 = {'Article Title': 标题, 'Abstract': 摘要, 'DOI': doi_number}

            # 将段落添加到 DataFrame
            df = pd.concat([df, pd.DataFrame([段落])], ignore_index=True)

            print(f'第{g}篇 标题是: {标题}，摘要已获取，DOI号: {doi_number}')
            g += 1

        页码 += 1  # 继续下一页

    # 获取名为 "Abstract" 的列的数据
    column_data = df["Abstract"]

    # 提取每行摘要中的匹配单词和包含匹配单词的整行信息
    matched_rows = []
    gene_names = []

    for index, row in df.iterrows():
        matches = re.findall(r'\b[a-z]{3}[A-Z]\b', str(row["Abstract"]))
        if matches:
            matched_rows.append(row)
            gene_names.extend(matches)

    # 将匹配到的基因名称去重
    unique_gene_names = list(set(gene_names))

    # 将包含匹配单词的整行信息写入新的 Excel 文件
    matched_data = pd.DataFrame(matched_rows)

    # 创建新的 'id' 列，序号从 0 开始递增
    matched_data.insert(0, 'id', range(len(matched_data)))

    # 保存为 Excel 文件
    matched_data.to_excel(f"savedrecs_selected_{user_id}.xlsx", index=False)

    print('处理完成，结果已保存到 Excel 文件中。')

    # 数据预处理 分词 去停用词
    # 设置 NLTK 数据路径为当前目录的 "stopwords" 文件夹
    nltk.data.path.append("/www/wwwroot/probioticgene/stopwords")

    # 加载 NLTK 的停用词表
    stop_words_file = "/www/wwwroot/probioticgene/nltk_stopwords.txt"  # 停用词表文件名
    with open(stop_words_file, "r") as f:
        stop_words = set(f.read().splitlines())

    print(f"停用词表已加载，共 {len(stop_words)} 个词。")

    # 加载 spaCy 模型
    spacy_model_path = "/www/wwwroot/probioticgene/en_core_web_sm"  # spaCy 模型文件夹名
    nlp = spacy.load(spacy_model_path)

    print("spaCy 模型已成功加载。")

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
    input_file = f'savedrecs_selected_{user_id}.xlsx'
    df = pd.read_excel(input_file)

    # 对 Abstract 列进行预处理，添加新列 'Processed_Abstract'
    df['Processed_Abstract'] = df['Abstract'].apply(preprocess_text)

    # 输出到新的 Excel 文件
    output_file = f'data_processed_combined_{user_id}.xlsx'
    df.to_excel(output_file, index=False)

    print(f"预处理完成，结果已保存到 {output_file}")

    # 计算节点 probioticbert分类后412
    # 文件路径
    input_file = f'data_processed_combined_{user_id}.xlsx'
    output_file = f'graph_nodes_probert412_{user_id}.json'
    model_dir = 'probiotic/best_model'  # 替换为您的模型路径

    # 加载 BERT 模型和分词器
    tokenizer = AutoTokenizer.from_pretrained(model_dir)
    model = AutoModel.from_pretrained(model_dir).to(device)

    # 读取 Excel 文件
    df = pd.read_excel(input_file)

    # 获取文档 ID、预处理后的文本和标签
    document_ids = df['id'].tolist()  # 文档 ID
    documents = df['Processed_Abstract'].tolist()  # 文本内容

    # 提取文档特征
    print("提取文档特征中...")
    doc_features = []
    for doc in documents:
        encoded = tokenizer.encode_plus(
            doc,
            add_special_tokens=True,
            return_attention_mask=True,
            max_length=None,
            return_tensors='pt'
        )
        input_ids = encoded['input_ids'].squeeze()
        attention_mask = encoded['attention_mask'].squeeze()

        if len(input_ids) <= 512:
            padding_length = 512 - len(input_ids)
            input_ids = torch.cat([input_ids, torch.tensor([tokenizer.pad_token_id] * padding_length, dtype=torch.long)])
            attention_mask = torch.cat([attention_mask, torch.tensor([0] * padding_length, dtype=torch.long)])
        else:
            input_ids = torch.cat([input_ids[:100], input_ids[-412:]])
            attention_mask = torch.cat([attention_mask[:100], attention_mask[-412:]])

        inputs = {
            'input_ids': input_ids.unsqueeze(0).to(device),
            'attention_mask': attention_mask.unsqueeze(0).to(device)
        }

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

    # 添加文档节点及其特征（不包括标签）
    for doc_id, doc_feature in enumerate(doc_features):
        data["nodes"].append({
            "id": doc_id,
            "type": "document",
            "feature": doc_feature.tolist()  # 转为列表保存
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

    # 计算边权重 probioticbert分类后412 
    # 文件路径
    xlsx_file = f'data_processed_combined_{user_id}.xlsx'
    json_file = f'graph_nodes_probert412_{user_id}.json'
    output_file = f'graph_edges_probert412_{user_id}.json'

    # 读取 Excel 文件
    df = pd.read_excel(xlsx_file)

    # 读取 JSON 文件
    with open(json_file, 'r') as f:
        graph_data = json.load(f)

    # 提取文档和词汇节点
    doc_nodes = [node for node in graph_data['nodes'] if node['type'] == 'document']
    word_nodes = [node for node in graph_data['nodes'] if node['type'] == 'word']

    # 构建词汇到节点 ID 的映射
    word_to_node = {node['word']: node['id'] for node in word_nodes}

    # 构建边
    print("构建边中...")
    edges = []
    edge_weights = []

    for doc_node in doc_nodes:
        doc_id = doc_node['id']
        doc_text = df.loc[doc_id, 'Processed_Abstract']  # 获取对应的预处理后的文本

        # 统计文档中每个词的出现次数
        word_counts = Counter(doc_text.split())

        # 遍历文档中的每个词
        for word, count in word_counts.items():
            if word in word_to_node:
                word_node_id = word_to_node[word]
                edges.append([doc_node['id'], word_node_id])  # 添加文档到词汇的边
                edge_weights.append(count)  # 边的权重为词频

    # 构造 JSON 数据结构
    print("构建边数据中...")
    data = {"edges": []}

    for (src, dst), weight in zip(edges, edge_weights):
        data["edges"].append({
            "source": src,
            "target": dst,
            "weight": weight
        })

    # 保存为 JSON 文件（单行格式）
    print(f"保存边数据到 {output_file} 中...")
    with open(output_file, 'w') as f:
        json.dump(data, f, separators=(',', ':'), ensure_ascii=False)

    print(f"边数据已保存到 {output_file}")

    # 构建图数据 probioticbert分类后412
    # 文件路径
    node_file = f'graph_nodes_probert412_{user_id}.json'
    edge_file = f'graph_edges_probert412_{user_id}.json'

    # 读取节点数据
    with open(node_file, 'r') as f:
        node_data = json.load(f)

    # 读取边数据
    with open(edge_file, 'r') as f:
        edge_data = json.load(f)

    # 提取节点特征
    node_features = []
    for node in node_data['nodes']:
        node_features.append(node['feature'])

    node_features = torch.tensor(node_features, dtype=torch.float)

    # 提取边
    edges_src = []
    edges_dst = []
    edge_weights = []

    for edge in edge_data['edges']:
        edges_src.append(edge['source'])
        edges_dst.append(edge['target'])
        edge_weights.append(edge['weight'])

    edge_index = torch.tensor([edges_src, edges_dst], dtype=torch.long)
    edge_weights = torch.tensor(edge_weights, dtype=torch.float)

    # 构建 PyTorch Geometric 数据对象
    data = Data(x=node_features, edge_index=edge_index, edge_attr=edge_weights)

    print("图数据已构建完成。")

    # 模型训练和预测 probioticbert分类后412
    # 加载保存的模型
    save_dir = "RA-HGATSE"
    final_model_path = os.path.join(save_dir, "final_model.pt")
    checkpoint = torch.load(final_model_path, map_location=device)

    # 初始化模型
    model = HybridAttentionModel(
        in_channels=node_features.shape[1],
        hidden_channels=128,
        out_channels=2,  # 二分类
        num_heads=4  # 多头注意力头数
    ).to(device)
    model.load_state_dict(checkpoint['model_state_dict'])
    model.eval()

    # 进行预测
    with torch.no_grad():
        out = model(data.x, data.edge_index, data.edge_attr)
        # 取所有节点的预测结果
        predictions = out.softmax(dim=1).cpu().numpy()
        predicted_labels = predictions.argmax(axis=1)

    # 加载原始文件并追加预测结果
    data_file = f'savedrecs_selected_{user_id}.xlsx'
    data_df = pd.read_excel(data_file)
    prediction_df = pd.DataFrame({
        "Class_0_Prob": predictions[:, 0],
        "Class_1_Prob": predictions[:, 1],
        "Prediction": predicted_labels
    })
    data_df = pd.concat([data_df, prediction_df], axis=1)

    # 检查 "id" 列是否存在空值，并删除包含空值的行
    if "id" in data_df.columns:
        data_df = data_df.dropna(subset=["id"])

    # 保存预测结果到新的 Excel 文件
    output_file = f'data_with_predictions_{user_id}.xlsx'
    data_df.to_excel(output_file, index=False)

    print(f"预测完成，结果已保存到 {output_file}")
#     print(user_id)

    predictions_data = get_predictions(user_id)

    if predictions_data is not None:
        # 将 DataFrame 转换为字典列表，并确保处理 NaN 值
        predictions_list = predictions_data.replace({np.nan: None}).to_dict(orient='records')
        
        # 确保所有必需的列都存在
        for row in predictions_list:
            for col in ["id", "Article Title", "Abstract", "DOI", "Prediction"]:
                if col not in row:
                    row[col] = None
        
        return jsonify({
            'status': 'success',
            'query': query,
            'output_file': output_file,
            'user_id': user_id,
            'predictions': predictions_list
        })
    else:
        return jsonify({
            'status': 'error',
            'message': 'No predictions available'
        }), 404

# 读取预测结果并返回给前端
def get_predictions(user_id):
    try:
        output_file = f'data_with_predictions_{user_id}.xlsx'
        if not os.path.exists(output_file):
            print(f"File not found: {output_file}")
            return None

        # 读取 Excel 文件
        prediction_df = pd.read_excel(output_file)
        
        # 确保所有必需的列都存在
        required_columns = ["id", "Article Title", "Abstract", "DOI", "Prediction"]
        for col in required_columns:
            if col not in prediction_df.columns:
                prediction_df[col] = None
                
        # 只选择需要的列
        prediction_df = prediction_df[required_columns]
        
        # 重置索引以确保 id 列正确
        prediction_df = prediction_df.reset_index(drop=True)
        prediction_df['id'] = prediction_df.index
        
        print(f"Successfully loaded predictions with shape: {prediction_df.shape}")
        return prediction_df
        
    except Exception as e:
        print(f"Error in get_predictions: {str(e)}")
        return None

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8080,threaded=True)

# print(results_list)