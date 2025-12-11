
import asyncio
import aiosqlite
from datetime import datetime
from typing import Optional

class TokenRefreshScheduler:
    """Token refresh scheduler service"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.task: Optional[asyncio.Task] = None
        self.enabled = False
        # 从配置获取刷新间隔
        from ..core.config import config
        self.refresh_interval = config.token_refresh_interval

    async def start(self):
        """Start the token refresh scheduler"""
        if self.enabled:
            return  # Already running

        self.enabled = True
        self.task = asyncio.create_task(self._run_scheduler())
        print("Token refresh scheduler started")

    async def stop(self):
        """Stop the token refresh scheduler"""
        if not self.enabled:
            return  # Already stopped

        self.enabled = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
            self.task = None
        print("Token refresh scheduler stopped")

    async def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.enabled:
            try:
                # Update tokens table
                await self._update_tokens()

                # Sleep for configured interval
                # 分段睡眠，以便及时响应停止请求
                sleep_segments = 60  # 分成60段，每段1秒
                segment_duration = self.refresh_interval / sleep_segments
                for _ in range(sleep_segments):
                    if not self.enabled:
                        break
                    await asyncio.sleep(segment_duration)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in token refresh scheduler: {e}")
                # Wait for a minute before retrying
                for _ in range(60):
                    if not self.enabled:
                        break
                    await asyncio.sleep(1)

    async def _update_tokens(self):
        """Update all active tokens using token manager logic"""
        from ..services.flow_client import FlowClient
        from ..services.proxy_manager import ProxyManager
        from ..core.database import Database
        from datetime import datetime

        # 初始化必要的组件
        db = Database()
        proxy_manager = ProxyManager(db)
        flow_client = FlowClient(proxy_manager)

        # 直接使用数据库连接获取活跃令牌
        async with aiosqlite.connect(self.db_path) as db_conn:
            cursor = await db_conn.execute("SELECT id, st FROM tokens WHERE is_active = 1")
            active_tokens = await cursor.fetchall()

            # 依次刷新每个令牌
            for token_id, st in active_tokens:
                try:
                    print(f"Token refresh: Refreshing token {token_id}")

                    if not st:  # 如果ST不存在
                        print(f"Token refresh: Token {token_id} has no ST, skipping")
                        continue

                    # 使用FlowClient刷新AT
                    result = await flow_client.st_to_at(st)
                    new_at = result["access_token"]
                    expires = result.get("expires")

                    # 解析过期时间
                    new_at_expires = None
                    if expires:
                        try:
                            new_at_expires = datetime.fromisoformat(expires.replace('Z', '+00:00'))
                        except:
                            pass

                    # 更新数据库
                    await db_conn.execute(
                        "UPDATE tokens SET at = ?, at_expires = ?, last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (new_at, new_at_expires, token_id)
                    )

                    # 同时刷新credits
                    try:
                        credits_result = await flow_client.get_credits(new_at)
                        await db_conn.execute(
                            "UPDATE tokens SET credits = ? WHERE id = ?",
                            (credits_result.get("credits", 0), token_id)
                        )
                    except:
                        pass  # 忽略获取credits的错误

                    await db_conn.commit()
                    print(f"Token refresh: Successfully refreshed token {token_id}")

                except Exception as e:
                    print(f"Token refresh: Failed to refresh token {token_id} - {str(e)}")
                    # 刷新失败，禁用令牌
                    try:
                        await db_conn.execute(
                            "UPDATE tokens SET is_active = 0 WHERE id = ?",
                            (token_id,)
                        )
                        await db_conn.commit()
                        print(f"Token refresh: Disabled token {token_id} due to refresh failure")
                    except Exception as disable_error:
                        print(f"Token refresh: Failed to disable token {token_id} - {str(disable_error)}")

            print(f"Token refresh: Completed refresh cycle at {datetime.now()}")
