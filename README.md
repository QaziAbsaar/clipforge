# ClipForge v0.6

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
- Face tracking keeps the speaker in the vertical frame (heuristic: works best with clear, front-facing faces).
- 8 caption styles, 1080p / 2K (1440x2560) / 4K (2160x3840), music, one sound effect.
- Approve = the clip is made and downloads to your browser's Downloads folder automatically.
  (The first time, the browser may ask to allow multiple downloads - say yes.)
- Go live: paste a Twitch or Kick channel link. ClipForge records it, watches the sound and (Twitch) chat,
  and cuts a clip whenever something big happens. "Clip it now" cuts the last moments by hand.

## Good to know
- Platforms have no "likes" on live streams. ClipForge uses chat bursts (Twitch), crowd/streamer volume and
  reaction words ("clip that", "no way") instead. Kick chat is not supported: Kick uses sound only.
- Kick video needs Chrome or Edge installed (Streamlink opens it briefly to get the stream).
- Only clip streams/videos you have the right to use.
- 2K/4K rendering is slow on a laptop. Clips are only made when you approve them, so nothing is wasted.
- Settings: speech accuracy (Fast/Better/Best) and an optional AI scoring key (Anthropic). With a key, an AI editor
  also reads each clip's transcript (sent to Anthropic). Without it, built-in scoring is used.

## Share with a team / put online
See the earlier notes: set CLIPFORGE_PASSWORD (+ CLIPFORGE_HOST=0.0.0.0), or use docker compose up -d --build on a
server with a domain (Caddy gives HTTPS). Live Kick clipping needs a desktop browser, so run live mode on a PC.
