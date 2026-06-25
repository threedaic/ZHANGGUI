"""
统一外部 API 调用客户端
- 自动重试 (tenacity)
- 超时控制
- 统一日志
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger


class HTTPClient:
    """所有外部 API 调用统一走这里。"""

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict | None = None,
        json_body: dict | None = None,
        data: dict | None = None,
        content: bytes | None = None,
        params: dict | None = None,
        raise_on_error: bool = True,
    ) -> httpx.Response:
        client = await self._get_client()
        logger.info(f"[HTTP] {method} {url}")
        resp = await client.request(
            method, url, headers=headers, json=json_body, data=data, content=content, params=params
        )

        # 对于云打印等外部服务，不自动抛出异常，让调用方自行检查响应
        if raise_on_error:
            resp.raise_for_status()

        # 记录非200响应的日志
        if resp.status_code != 200:
            logger.warning(f"[HTTP] {method} {url} 返回状态码 {resp.status_code}, 响应体: {resp.text[:500]}")
        else:
            logger.info(f"[HTTP] {method} {url} 响应: {resp.text[:500]}")

        return resp

    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("POST", url, **kwargs)

    async def put(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("PUT", url, **kwargs)

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


# 全局单例，供所有业务模块使用
http_client = HTTPClient()
