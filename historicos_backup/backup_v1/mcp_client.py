import asyncio
import os
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class LocalMCPClient:
    """
    Cliente MCP que gerencia o ciclo de vida do servidor mcp_server.py
    rodando localmente em um subprocesso de comunicação por STDIO.
    """
    def __init__(self, server_script_path=None):
        if server_script_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            server_script_path = os.path.join(base_dir, "mcp_server.py")
            
        self.server_params = StdioServerParameters(
            command=sys.executable,
            args=[server_script_path],
            env=os.environ.copy()
        )
        self._session = None
        self._client_context = None

    async def __aenter__(self):
        # Inicializa o transporte stdio com o subprocesso
        self._client_context = stdio_client(self.server_params)
        read_stream, write_stream = await self._client_context.__aenter__()
        
        # Inicializa a sessão MCP
        self._session = ClientSession(read_stream, write_stream)
        await self._session.__aenter__()
        
        # Envia a requisição de inicialização (handshake MCP)
        await self._session.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Encerra ordenadamente a sessão e o transporte
        if self._session:
            await self._session.__aexit__(exc_type, exc_val, exc_tb)
        if self._client_context:
            await self._client_context.__aexit__(exc_type, exc_val, exc_tb)

    async def list_tools(self):
        """Retorna a lista de ferramentas declaradas pelo servidor MCP."""
        if not self._session:
            raise RuntimeError("Sessão MCP não iniciada. Utilize o cliente dentro de 'async with'.")
        result = await self._session.list_tools()
        return result.tools

    async def call_tool(self, tool_name: str, arguments: dict) -> str:
        """Executa uma ferramenta no servidor MCP e retorna o resultado em texto."""
        if not self._session:
            raise RuntimeError("Sessão MCP não iniciada. Utilize o cliente dentro de 'async with'.")
        
        # Executa a chamada JSON-RPC da ferramenta
        result = await self._session.call_tool(tool_name, arguments)
        
        # O resultado vem como uma lista de blocos de conteúdo, extraímos o texto do primeiro
        if hasattr(result, 'content') and len(result.content) > 0:
            return result.content[0].text
        return str(result)
