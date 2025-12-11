"""Proxy management module"""
from typing import Optional
from ..core.database import Database
from ..core.models import ProxyConfig

class ProxyManager:
    """Proxy configuration manager"""

    def __init__(self, db: Database):
        self.db = db

    async def get_proxy_url(self) -> Optional[str]:
        """Get proxy URL if enabled, otherwise return None"""
        config = await self.db.get_proxy_config()
        if config and config.enabled and config.proxy_url:
            return config.proxy_url
        return None

    async def update_proxy_config(self, enabled: bool, proxy_url: Optional[str]):
        """Update proxy configuration"""
        await self.db.update_proxy_config(enabled, proxy_url)

    async def get_proxy_config(self) -> ProxyConfig:
        """Get proxy configuration"""
        return await self.db.get_proxy_config()

    async def print_proxy_status(self):
        """打印当前代理配置状态"""
        print("=" * 50)
        print("代理配置状态")
        print("=" * 50)

        config = await self.db.get_proxy_config()

        if not config:
            print("状态: 未配置")
            print("原因: 数据库中无代理配置")
            return

        if not config.enabled:
            print("状态: 已禁用")
            print("配置: enabled = False")
            return

        if not config.proxy_url:
            print("状态: 已启用但未配置代理地址")
            print("配置: enabled = True, proxy_url = None")
            return

        print("状态: 已启用")
        print(f"代理地址: {config.proxy_url}")

        # 尝试测试代理连接
        try:
            import curl_cffi
            from curl_cffi.requests import AsyncSession

            test_url = "https://httpbin.org/ip"
            print(f"测试代理连接: {test_url}")

            async with AsyncSession() as session:
                response = await session.get(
                    test_url,
                    proxy=config.proxy_url,
                    timeout=10,
                    impersonate="chrome110"
                )

                if response.status_code == 200:
                    print(f"代理测试成功: {response.json()}")
                else:
                    print(f"代理测试失败: HTTP {response.status_code}")
        except Exception as e:
            print(f"代理测试异常: {e}")

    async def get_proxy_info(self) -> dict:
        """获取代理信息"""
        config = await self.db.get_proxy_config()

        if not config:
            return {
                "enabled": False,
                "proxy_url": None,
                "status": "未配置",
                "reason": "数据库中无代理配置"
            }

        if not config.enabled:
            return {
                "enabled": False,
                "proxy_url": config.proxy_url,
                "status": "已禁用",
                "reason": "enabled = False"
            }

        if not config.proxy_url:
            return {
                "enabled": True,
                "proxy_url": None,
                "status": "已启用但未配置代理地址",
                "reason": "enabled = True, proxy_url = None"
            }

        return {
            "enabled": True,
            "proxy_url": config.proxy_url,
            "status": "已启用",
            "reason": None
        }
