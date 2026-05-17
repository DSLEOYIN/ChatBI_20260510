# 使用 Python 3.11 的精简版镜像，体积小且运行快
FROM python:3.11-slim

# 设置容器内的工作目录
WORKDIR /app

# 复制依赖文件并安装（使用 --no-cache-dir 保持镜像小巧）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制我们的核心代码
COPY server.py .

# 设置环境变量占位符
ENV TAVILY_API_KEY=""

# 容器启动命令，直接运行 server.py，它会自动挂起并监听标准输入输出流
ENTRYPOINT ["python", "server.py"]