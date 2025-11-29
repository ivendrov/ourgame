#!/usr/bin/env python3
"""Migration script to update journal channel descriptions.

This script updates all journal channel topics from the old language
to clarify that journals are not private and can be accessed through AI commands.
"""
import discord
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
GUILD_ID = int(os.getenv('GUILD_ID'))


async def migrate_channel_descriptions():
    """Update all journal channel descriptions."""
    # Create bot client with minimal intents
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f'Logged in as {client.user}')

        # Get the guild
        guild = client.get_guild(GUILD_ID)
        if not guild:
            print(f'Error: Guild {GUILD_ID} not found')
            await client.close()
            return

        print(f'Found guild: {guild.name}')

        # Find all journal channels
        journal_channels = [
            channel for channel in guild.text_channels
            if channel.name.startswith('journal-')
        ]

        print(f'Found {len(journal_channels)} journal channels')

        # Update each channel
        updated = 0
        errors = 0

        for channel in journal_channels:
            try:
                # Extract username from channel name
                username = channel.name.replace('journal-', '').replace('-', ' ')

                # New topic
                new_topic = f"Personal journal for {username}. All entries can be read by other journalers through AI commands."

                # Update the channel
                await channel.edit(topic=new_topic)
                print(f'✓ Updated: {channel.name}')
                updated += 1

                # Add a small delay to avoid rate limits
                await asyncio.sleep(1)

            except Exception as e:
                print(f'✗ Error updating {channel.name}: {e}')
                errors += 1

        print(f'\nMigration complete:')
        print(f'  - Updated: {updated} channels')
        print(f'  - Errors: {errors} channels')

        await client.close()

    # Start the bot
    try:
        await client.start(DISCORD_BOT_TOKEN)
    except KeyboardInterrupt:
        await client.close()


if __name__ == '__main__':
    print('Starting channel description migration...')
    asyncio.run(migrate_channel_descriptions())
