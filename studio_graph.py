# studio_graph.py

from argupaper.agents.chat.graph import ChatAgentRuntime
from argupaper.config import load_config

# 这里替换成你项目里真实的 Config 构造方式
# 例如你的 CLI 里怎么加载 Config，这里就怎么写
config = load_config(require_pdf_api_key=False)

runtime = ChatAgentRuntime(config)

graph = runtime.graph