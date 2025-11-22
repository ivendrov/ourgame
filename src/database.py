"""Database management using Supabase."""
from datetime import date, datetime
from typing import Optional, List, Dict, Any
from supabase import create_client, Client
from src.config import Config
import logging

logger = logging.getLogger(__name__)


class Database:
    """Supabase database interface."""

    def __init__(self):
        """Initialize Supabase client."""
        self.client: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

    # User operations
    async def get_or_create_user(self, discord_id: int, username: str) -> Dict[str, Any]:
        """Get existing user or create new one."""
        try:
            # Use upsert to handle race conditions
            new_user = {
                'discord_id': discord_id,
                'discord_username': username,
            }
            result = self.client.table('users').upsert(
                new_user,
                on_conflict='discord_id'
            ).execute()

            if result.data:
                return result.data[0]

            # Fallback: query if upsert didn't return data
            result = self.client.table('users').select('*').eq('discord_id', discord_id).execute()
            return result.data[0]
        except Exception as e:
            logger.error(f"Error getting/creating user {discord_id}: {e}")
            raise

    async def update_user_journal_channel(self, discord_id: int, channel_id: int, only_if_null: bool = False) -> bool:
        """Update user's journal channel ID.

        Args:
            discord_id: User's Discord ID
            channel_id: Channel ID to set (or None to clear)
            only_if_null: Only update if journal_channel_id is currently null

        Returns:
            True if the update succeeded, False if only_if_null was True and channel was already set
        """
        try:
            query = self.client.table('users').update({
                'journal_channel_id': channel_id
            }).eq('discord_id', discord_id)

            if only_if_null:
                query = query.is_('journal_channel_id', 'null')

            result = query.execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Error updating journal channel for user {discord_id}: {e}")
            raise

    async def get_user_by_discord_id(self, discord_id: int) -> Optional[Dict[str, Any]]:
        """Get user by Discord ID."""
        try:
            result = self.client.table('users').select('*').eq('discord_id', discord_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user {discord_id}: {e}")
            return None

    async def get_all_users_with_journals(self) -> List[Dict[str, Any]]:
        """Get all users who have journal channels."""
        try:
            result = self.client.table('users').select('*').not_.is_('journal_channel_id', 'null').execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting users with journals: {e}")
            return []

    # Journal entry operations
    async def create_journal_entry(self, discord_id: int, username: str, message_id: int,
                                   channel_id: int, content: str, word_count: int) -> None:
        """Create a new journal entry."""
        try:
            user = await self.get_user_by_discord_id(discord_id)
            if not user:
                logger.warning(f"User {discord_id} not found when creating journal entry, creating user")
                user = await self.get_or_create_user(discord_id, username)

            entry = {
                'user_id': user['id'],
                'discord_id': discord_id,
                'discord_username': username,
                'message_id': message_id,
                'channel_id': channel_id,
                'content': content,
                'word_count': word_count,
            }
            self.client.table('journal_entries').insert(entry).execute()
        except Exception as e:
            logger.error(f"Error creating journal entry for user {discord_id}: {e}")
            raise

    async def get_journal_entries_for_date(self, discord_id: int, target_date: date) -> List[Dict[str, Any]]:
        """Get all journal entries for a user on a specific date."""
        try:
            # Format dates for the query with timezone awareness
            start_datetime = Config.TIMEZONE.localize(datetime.combine(target_date, datetime.min.time()))
            end_datetime = Config.TIMEZONE.localize(datetime.combine(target_date, datetime.max.time()))

            result = self.client.table('journal_entries').select('*').eq(
                'discord_id', discord_id
            ).gte('created_at', start_datetime.isoformat()).lte(
                'created_at', end_datetime.isoformat()
            ).execute()

            return result.data
        except Exception as e:
            logger.error(f"Error getting journal entries for user {discord_id} on {target_date}: {e}")
            return []

    async def get_all_journal_entries_for_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Get all journal entries from all users for a specific date."""
        try:
            start_datetime = Config.TIMEZONE.localize(datetime.combine(target_date, datetime.min.time()))
            end_datetime = Config.TIMEZONE.localize(datetime.combine(target_date, datetime.max.time()))

            result = self.client.table('journal_entries').select('*').gte(
                'created_at', start_datetime.isoformat()
            ).lte('created_at', end_datetime.isoformat()).execute()

            return result.data
        except Exception as e:
            logger.error(f"Error getting all journal entries for {target_date}: {e}")
            return []

    # Daily stats operations
    async def get_or_create_daily_stats(self, discord_id: int, target_date: date) -> Dict[str, Any]:
        """Get or create daily stats for a user."""
        try:
            user = await self.get_user_by_discord_id(discord_id)
            if not user:
                raise ValueError(f"User {discord_id} not found")

            # Try to get existing stats
            result = self.client.table('daily_stats').select('*').eq(
                'user_id', user['id']
            ).eq('date', target_date.isoformat()).execute()

            if result.data:
                return result.data[0]

            # Create new stats
            new_stats = {
                'user_id': user['id'],
                'discord_id': discord_id,
                'date': target_date.isoformat(),
                'total_words': 0,
                'has_access': False,
            }
            result = self.client.table('daily_stats').insert(new_stats).execute()
            return result.data[0]
        except Exception as e:
            logger.error(f"Error getting/creating daily stats for user {discord_id}: {e}")
            raise

    async def update_daily_stats(self, discord_id: int, target_date: date,
                                 total_words: int, has_access: bool) -> None:
        """Update daily stats for a user."""
        try:
            user = await self.get_user_by_discord_id(discord_id)
            if not user:
                return

            self.client.table('daily_stats').update({
                'total_words': total_words,
                'has_access': has_access,
                'last_updated': datetime.now().isoformat(),
            }).eq('user_id', user['id']).eq('date', target_date.isoformat()).execute()
        except Exception as e:
            logger.error(f"Error updating daily stats for user {discord_id}: {e}")
            raise

    async def get_daily_stats_for_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Get daily stats for all users on a specific date."""
        try:
            result = self.client.table('daily_stats').select('*').eq(
                'date', target_date.isoformat()
            ).execute()
            return result.data
        except Exception as e:
            logger.error(f"Error getting daily stats for {target_date}: {e}")
            return []
