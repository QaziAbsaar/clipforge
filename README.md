# ClipForge v0.7

## Run it (Windows)
1. Extract the zip to a normal folder (not from inside the zip), e.g. C:\ClipForge.
2. Double-click Install-Windows.bat once (installs Python 3.12 + FFmpeg if missing, then the packages, and puts a
   ClipForge shortcut on the Desktop). Needs internet + Windows 10/11 with winget.
3. Open the Desktop shortcut (or run_web.bat). ClipForge opens in its own window. Keep the black window running.
A yellow bar at the top tells you if something is missing.

## What it does
- Add a video (link or file) -> it is analyzed automatically: loud moments, crowd/chat reactions, speech.
- Up to 100 ranked clips per video, each with a score, the reason, a title and word-by-word captions.
  Rule of thumb: a 20-minute video fits about 100 clips at ~12 seconds each.
- Vertical 9:16 output for Facebook Reels, YouTube Shorts and TikTok (1080x1920 by default).
- Gaming layout (default): gameplay fills the frame and the streamer's facecam sits in a small box at the top centre.
  "Facecam + gameplay split" puts the facecam in the top 40% instead. With no facecam the whole gameplay is
  shown over a blurred fill; with a full camera shot the crop follows the face.
- Finds big on-screen action (crashes, explosions) from picture changes, plus GTA and gaming words in speech and chat.
- YouTube links: the chat replay is downloaded automatically and used as a signal.
- 8 caption styles, 1080p / 2K (1440x2560) / 4K (2160x3840), music, one sound effect.
- Approve = the clip is made and downloads to your browser's Downloads folder automatically.
  (The first time, the browser may ask to allow multiple downloads - say yes.)
- Go live: paste a Twitch, Kick or YouTube Live link. ClipForge records it, watches the sound and (Twitch) chat,
  and cuts a clip whenever something big happens. "Clip it now" cuts the last moments by hand.
- Watch list (under Go live): list the channels you follow, one link per line. ClipForge checks them every minute and
  starts recording when one goes live, and finishes by itself when the stream ends. Stopping a recording by hand keeps
  it stopped until that channel goes offline. At most 6 recordings run at once (set CLIPFORGE_MAX_LIVE to change it).
- Several videos are clipped at the same time: 3 tasks (download, find clips, render) run at once. Set
  CLIPFORGE_WORKERS to change it. Speech-to-text still runs one video at a time to keep the computer responsive.

## Good to know
- Platforms have no "likes" on live streams. ClipForge uses chat bursts (Twitch), crowd/streamer volume and
  reaction words ("clip that", "no way") instead. Kick and YouTube Live chat are not read live yet: they use sound and picture only.
- Kick video needs Chrome or Edge installed (Streamlink opens it briefly to get the stream).
- Only clip streams/videos you have the right to use.
- 2K/4K rendering is slow on a laptop. Clips are only made when you approve them, so nothing is wasted.
- Settings: speech accuracy (Fast/Better/Best) and an optional AI scoring key (Anthropic). With a key, an AI editor
  also reads each clip's transcript (sent to Anthropic). Without it, built-in scoring is used.

## Share with a team / put online
See the earlier notes: set CLIPFORGE_PASSWORD (+ CLIPFORGE_HOST=0.0.0.0), or use docker compose up -d --build on a
server with a domain (Caddy gives HTTPS). Live Kick clipping needs a desktop browser, so run live mode on a PC.

## Faster on a gaming PC
Set CLIPFORGE_DEVICE=cuda to transcribe on an NVIDIA GPU (much faster when several streams run at once).

## Tests
python tests/test_live_watch.py (needs FFmpeg, no internet).
