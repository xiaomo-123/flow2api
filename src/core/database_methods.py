
# Token refresh config methods to be added to Database class
import aiosqlite
from typing import Optional

async def get_token_refresh_config(self) -> Optional['TokenRefreshConfig']:
    """Get token refresh configuration"""
    from .models import TokenRefreshConfig
    async with aiosqlite.connect(self.db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM token_refresh_config WHERE id = 1")
        row = await cursor.fetchone()
        if row:
            return TokenRefreshConfig(**dict(row))
        # Return default if not found
        return TokenRefreshConfig(at_auto_refresh_enabled=True)

async def update_token_refresh_config(self, at_auto_refresh_enabled: bool = None):
    """Update token refresh configuration"""
    async with aiosqlite.connect(self.db_path) as db:
        db.row_factory = aiosqlite.Row
        # Get current values
        cursor = await db.execute("SELECT * FROM token_refresh_config WHERE id = 1")
        row = await cursor.fetchone()

        if row:
            current = dict(row)
            # Use new value if provided, otherwise keep existing
            new_at_auto_refresh_enabled = at_auto_refresh_enabled if at_auto_refresh_enabled is not None else current.get("at_auto_refresh_enabled", True)

            await db.execute("""
                UPDATE token_refresh_config
                SET at_auto_refresh_enabled = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = 1
            """, (new_at_auto_refresh_enabled,))
        else:
            # Insert default row if not exists
            new_at_auto_refresh_enabled = at_auto_refresh_enabled if at_auto_refresh_enabled is not None else True

            await db.execute("""
                INSERT INTO token_refresh_config (id, at_auto_refresh_enabled)
                VALUES (1, ?)
            """, (new_at_auto_refresh_enabled,))
        await db.commit()
