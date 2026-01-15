FROM python:3.11-slim

# 明确工作目录
WORKDIR /app

# 先装依赖（利用缓存）
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

# 再复制应用代码
COPY app.py /app/app.py

# Streamlit 使用的端口
EXPOSE 8000

# ⚠️ 关键：用绝对路径启动
CMD ["streamlit", "run", "/app/app.py", "--server.address=0.0.0.0", "--server.port=8000", "--server.headless=true"]
