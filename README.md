# Jesse Bot

A Discord Bot written in Python. Not intended for re-use, but you can fork it if you like.

This bot was written as a way to make my personal discord server more interactive, or smarter, in some way.

## Noteworthy Features

- Notification support - currently rudimentary (lots of logic duplicated) but it does the job
  - Supports notifying users when a voice channel they subscribe to is joined
  - Supports notifying users when a trigger phrase is mentioned in a chat visible to them (can be used as a topic notification or content warning system)
- Support for loading and playing back audio files from Firebase storage
  - Some support for audio effects like layering and reversing audio buffer to stack sounds and create audio mayhem
- Chain text through multiple modifier commands
- Automatically joins and leaves voice channels when summoned or when everyone has left
- Link helpers/listeners
  - Automatically download and post linked TikTok videos
  - Automatically wrap types of links or messages

## Design

Generally follows the advised Cog-based Discord.py system.

Document and file storage is handled by Firebase, which is synced locally on startup.

## Setup

1. Requires `.token` API key from Discord developer portal
2. Requires `credentials.json` (service account credentials) and `firebase.json` (API key, auth domain, URL, etc.) from Firebase API credentials
3. Requires Python3.9+
4. Run `pip install -r requirements.txt`
5. Run `python main.py`

To keep the bot alive, run with `screen`, `tmux`, or whatever you prefer.

Requires Discord Members intent.

To create voice channel notifications requires permission to create invites from whatever Discord server it is a part of.
