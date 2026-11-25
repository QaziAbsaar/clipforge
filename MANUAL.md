# ClipForge user manual

ClipForge finds the best moments in a long video or a live stream and turns them into vertical clips for
YouTube Shorts, TikTok and Facebook Reels. This manual covers every screen and button, where to find it and how to use it.

Contents
1. Start ClipForge
2. The screen at a glance
3. Add a video
4. Go live and the watch list
5. Your videos
6. The clip list
7. The editor (studio)
8. Approve and download
9. Settings
10. Clients
11. Learn from your views
12. Problems and fixes
13. For the person who runs the server

---

## 1. Start ClipForge

**Windows installer (easiest)**
1. Download `ClipForge-Setup-x.y.z.exe` from https://github.com/QaziAbsaar/clipforge/releases/latest.
2. Run it. It needs no admin rights. FFmpeg, yt-dlp and Streamlink are included.
3. If Windows says "Windows protected your PC", press **More info**, then **Run anyway**. The installer is not signed.
4. Open **ClipForge** from the Start menu or the Desktop shortcut.
5. To update, run the newer installer. Your clips and settings are kept.

**Windows from the source folder**
1. Extract the zip to a normal folder, for example `C:\ClipForge`. Do not run it from inside the zip.
2. Double-click `Install-Windows.bat` once. It installs Python, FFmpeg and the packages, and puts a ClipForge
   shortcut on the Desktop. It needs internet and Windows 10 or 11.
3. Open the Desktop shortcut (or `run_web.bat`). ClipForge opens in its own window.
4. Keep the black window open while you work. Closing it stops ClipForge.

**Linux / Mac:** `python -m clipforge_web` from the project folder, then open the address it prints.

If something is missing (FFmpeg, a model, a key), a **yellow bar** at the top of the page tells you what and how to fix it.

If a password is set, you see a **sign-in page** first. Type the password. **Sign out** is at the top right.

---

## 2. The screen at a glance

| Place | What is there |
|---|---|
| Top bar, right | **Your videos** (go back to the library), **Settings**, **Sign out** (only when a password is set) |
| Left column | **Client** picker, **Add a video**, **Go live**, and the list of **Your videos** |
| Middle | The selected video: progress, moment map and the list of clips |
| Editor | Opens over the middle when you press **✏️ Edit** on a clip |

Short messages (saved, errors) show for a few seconds at the bottom of the screen.

---

## 3. Add a video

Find it in the left column, card **Add a video**.

**From a link**
1. Paste one or more links into the box, one per line (YouTube, Twitch VODs, Kick VODs and most video sites).
2. Set the options:
   - **Clips**: how many clips to find (1 to 100). Start with 20.
   - **Seconds**: the length of each clip (8 to 90). 15 to 30 works well for Shorts.
   - **Quality**:
     - **Quick: HD only for clips** (fastest): it downloads a small copy to find the moments, then gets HD only for the clips you approve.
     - **Full 1080p** or **Full 4K**: it downloads the whole video at that quality.
3. Press **Add links**.

**From your PC**
1. Press **Upload files** and pick one or more video files (mp4, mkv, mov and others).
2. A progress bar shows the upload. The video then appears in **Your videos**.

**What happens next:** ClipForge downloads the video and transcribes the speech. It listens for loud moments, reads the
chat replay (YouTube) and looks for big action on screen. It also spots GTA screens such as **WASTED**, **BUSTED** and
**MISSION FAILED**. The middle shows each step and a percent. Press **Cancel** to stop.

Rule of thumb: a 20-minute video gives about 100 clips at about 12 seconds each.

**Missed a live? Past streams of a channel**
1. Open **Missed a live? Past streams of a channel** under the Add a video card.
2. Paste a channel link (`twitch.tv/name` or `youtube.com/@name`) and press **Show**.
3. Press the button next to a past stream to add it like a normal link.

**Age-restricted (18+) YouTube videos** need cookies. See **Settings > Age-restricted / YouTube Cookies**.
The badge at the top right of the Add a video card shows the cookie status. Click it to open Settings.

---

## 4. Go live and the watch list

Find it in the left column, card **Go live**.

**Clip a live stream now**
1. Paste a live link: `twitch.tv/name`, `kick.com/name` or `youtube.com/@name/live`.
2. Press **Start clipping the stream**.
3. The live panel shows:
   - **Sound** and **Chat** meters (chat is read live only on Twitch);
   - how long it has recorded.
4. ClipForge cuts a clip by itself when something big happens (a loud moment, a chat burst, words like "clip that").
5. Press **Clip it now** to cut the last moments yourself.
6. Press **Stop recording** to finish. When it stops, the recording is treated like a normal video and you can edit its clips.

**Watch list: record channels when they go live**
1. Open **Watch list** under the Go live card.
2. Type the channels you follow, one link per line, and press **Save watch list**.
3. ClipForge checks them every minute. It starts recording when a channel goes live and stops when the stream ends.
4. The status line under each channel shows offline / recording.
5. If you stop a recording yourself, that channel stays stopped until it goes offline.
6. At most 6 recordings run at once. Keep ClipForge open.

Notes
- Kick needs Chrome or Edge installed (ClipForge opens it briefly to get the stream).
- Only clip streams you have the right to use: your own streams, streamers who hired you, or clips you change a lot.

---

## 5. Your videos

- The left column lists every video. Click one to open it.
- **Your videos** in the top bar shows them all as cards with thumbnails.
- Each video shows its length, number of clips and how many are approved. A red **LIVE** badge means it is recording now.
- **✕** removes a video, its clips and its saved files. It asks first.
- If a video failed, the middle says **This one didn't work** with the reason. Press **Try again**.

---

## 6. The clip list

Open a video to see its clips. Find it in the middle of the screen.

**Top of the page**
- **← All videos** goes back to the library.
- The title line shows the length and source. If the streamer is known, a pill shows their clipping rules
  (**Clipping allowed**, **Has clip tips**, **No clipping** or **Rules unknown**). Click the pill to change it.

**Find clips again** (not for live recordings)
- Change **Clips (up to 100)** or **Length (s)**, and press **Find clips again**. It is fast, because the video is already analyzed.
- **Chat log (optional)**: upload a chat log (.txt, .log or .csv) if the chat replay was not downloaded. Chat bursts then count as a signal.

**Moment map**
- The wave shows the excitement across the whole video.
- Each marker is a picked clip: blue = new, green = approved, grey = rejected. Click a marker to open that clip.

**Each clip row**
- **#rank** and a **score ring**. Green is strong, yellow is medium, red is weak.
- The title, the time in the video, the length and the state: Approved, Waiting, Preparing %, Ready,
  **Saved to Downloads ✓**, Failed or Rejected. **⚠️ Check quality** means the finished file has a problem (for example, silence or a black picture).
- Small bars show why it scored:
  - **Sound**: loud moments;
  - **Action**: big changes on screen;
  - **Speech**: funny or hype words;
  - **Chat**: chat reactions;
  - **Replays**: parts that viewers rewatched;
  - **AI**: only with an AI key.
- Clips that show a GTA event (WASTED, BUSTED, a chase, a crash) get a label and score higher.
- **✏️ Edit** opens the editor.

**Buttons above the list**
- **Select all / Deselect all**, or tick the box on each clip.
- **Approve selected** makes the ticked clips.
- **Approve all** makes every clip.
- **Download .ZIP** downloads all finished clips in one file.

---

## 7. The editor (studio)

Press **✏️ Edit** on a clip. Every change is saved by itself. The preview on the right shows the result.

### Top bar of the editor
- **← Back to Clips** closes the editor.
- **Title box**: the clip's title. It is used for the post text and the voice-over.
- **Aspect ratio**:
  - **📱 9:16**: Shorts, TikTok, Reels;
  - **⬛ 1:1**: square;
  - **🖥️ 16:9**: landscape.
- **Resolution**: **1080p**, **2K** or **4K**. 2K and 4K are slow on a laptop.
- **Discard** rejects the clip.
- **🚀 Approve & Export** makes the clip and downloads it.

### Playback and timeline (bottom of the editor)
- **⏪ / ⏩** go 0.5 s back or forward. **▶** plays and pauses (or press **Space**).
- **Loop** repeats the clip. **Sound** turns preview sound on or off.
- **🔍 Clip View / 🌐 Whole Video** zooms the timeline into the clip or out to the whole video.
- Change the start and end:
  - **[ Set In** or the **[** key: the clip starts at the playhead;
  - **Set Out ]** or the **]** key: the clip ends at the playhead;
  - **◀ −1s** starts 1 second earlier. **+1s ▶** ends 1 second later;
  - **−5s / +5s** make the clip 5 seconds shorter or longer;
  - type exact **start**, **end** or **length** in seconds into the three small boxes;
  - **✂️ Cut Here** cuts the clip at the playhead.
- Timeline tracks, from top to bottom:
  - **⏱️ Time**: click it to move the playhead.
  - **🎬 Video & Cam**: the clip itself.
  - **🏷️ Hook Card**: the yellow bar shows when the hook text is on screen. See the Hook Text tab.
  - **💬 Subtitles**: the captions.
  - **🎵 SFX & Audio**: sound effects. Drag them to move them.

### Tab 🎛️ Cam & Layout
**Framing Mode** chooses how a landscape video becomes vertical:

| Mode | What it does | Use it when |
|---|---|---|
| **🎮 Dual-Cam Split** | Streamer cam on top, gameplay underneath | Streams with a facecam (default for gaming) |
| **🎮 Floating Cam (Draggable)** | Gameplay fills the vertical frame; the streamer cam floats on top | You want more gameplay on screen |
| **Follow Face** | The crop follows the person's face | Full camera shots, podcasts, IRL |
| **Center Crop** | Cuts the middle of the frame | The action is in the center |
| **Blurred Fit** | The whole frame, with a blurred copy behind it | Nothing may be cut off |

Settings for **Dual-Cam Split**
- **Split Ratio**: 50/50, 45/55, 40/60, 35/65 or 60/40 (cam part / gameplay part).
- **🔄 Swap** puts gameplay on top and the streamer underneath, or back again.

Settings for the streamer cam (Dual-Cam and Floating Cam)
1. **Select Where Streamer Is in the Video**: pick the corner where the facecam is in the original video
   (Top-Left, Top-Right, Bottom-Left, Bottom-Right, Top-Center, Bottom-Center).
2. For an exact fit, press **🎯 Drag & Select Streamer Box on Video**:
   - drag the blue box over the facecam;
   - drag the corner dot to resize it;
   - the corner buttons and **🎯 Center** move the box fast;
   - **Auto-detect** finds the face for you;
   - press **✓ Apply Streamer Box** to keep it, or **Cancel**.
3. **Streamer Cam Zoom**: 🔍− / 1.0x / 🔍+. **Streamer Framing Pan (X / Y)** moves the picture inside the cam box.
4. **Cam Frame Shape**: **⬛ Rectangle Frame** or **⭕ Circle Frame**.
5. In **Floating Cam**, drag the cam on the preview to place it anywhere.

Gameplay settings (Dual-Cam and Floating Cam)
- **Gameplay Screen Zoom**: 🔍− / 1.0x / 🔍+.
- **Gameplay Screen Pan (X / Y)**: chooses which part of the landscape gameplay shows in the vertical frame.
  In Floating Cam this is how you keep the car or the action in view.

If no facecam is found, Floating Cam still shows the gameplay full frame and floats the corner you picked.

### Tab 🏷️ Hook Text
The hook is the big headline that makes people stop scrolling, for example "WAIT TILL THE END 😱".

1. Type it in **Hook / Viral Headline Text**, or press a ready-made button (**Peak stream 😂💀**,
   **WAIT TILL THE END 😱**, **BRO DID NOT 💀** …).
2. **When it shows**: by default it shows for the whole clip.
   - To show it only part of the time, drag the yellow **Hook Card** bar on the timeline. Drag the middle to move it. Drag either end to make it shorter or longer (at least 0.5 s).
   - The line above the button shows the current times.
   - **Whole clip** puts it back to the full clip.
   - In the preview the text is dim (when paused) or hidden (when playing) outside its time.
3. **Text Size**: 🔍− / 1.0x / 🔍+.
4. **Font Design**: Impact, Montserrat, Arial Black, Poppins or Comic.
5. **Title Card Position**: **Top Hook**, **Center Screen** or **Bottom Hook**. You can also drag the text anywhere on the preview.
6. **Text Background Style**:
   - **No Box (Transparent)**;
   - **Yellow (No Box)**;
   - **White Card**;
   - **Dark Box**;
   - **Neon**;
   - **Hidden** (turns the hook off).

### Tab 💬 Subtitles
- **Caption Style Preset**: pick a style. Word-by-word highlighted captions are made from the speech.
- **Burn captions**: turn the captions on or off in the final video.
- **⚡ 3s Hook Zoom**: a short zoom at the start to grab attention.
- **🤬 Censor swear words**: hides swear words in the captions.
- **Subtitle Size** (🔍− / 1.0x / 🔍+) and **Subtitle Font Design**.
- **📥 Download Subtitles (.SRT)**: a subtitle file for YouTube or other editors.
- **Word-by-word Subtitles** list: each caption line is a text box. Type in it to fix a wrong word.
- **Translate Captions**: pick a language (Spanish, Portuguese, French, German, Italian, Hindi, Arabic, Russian, Turkish, English).
  - It is translated when you export. The preview still shows the spoken words.
  - It needs an AI key (see Settings).
- **Voice-over (Read aloud at the start)**: type a line, or press **Use title**. A computer voice reads it at the start of the clip, in the caption language. The game sound goes quieter while it talks.
  - The first time you use a language, ClipForge downloads its voice once.
  - It needs the extras installed. Without them, the editor tells you so.
- **Views after posting**: type how many views the clip got after you posted it. See part 11.

### Tab 🎵 Audio & SFX
- **Music**: pick a background track (from the `audio_library/music` folder or your imports).
- **Intro Hook SFX**: a sound at the very start.
- **Peak SFX (Deep 808/Boom)**: a sound at the big moment. **Auto Deep Drop** picks one for you.
- **⚡ Auto-add Smart SFX**: puts fitting sounds on the timeline. When a GTA fail (WASTED, BUSTED) is seen, it adds a sad trombone.
  When a GTA win (MISSION PASSED) is seen, it adds an airhorn.
- **Add at playhead** (or **➕ Add SFX** on the timeline) adds the chosen sound where the playhead is.
- Built-in sounds:
  - airhorn, bass drop, boom, camera click, ding, glitch, heartbeat, hit, pop;
  - record scratch, riser, sad trombone, siren, sub bass drop, vine boom, whoosh.

### Tab 📁 PC Import
- **Import Audio / Effects from PC**: choose **Sound Effect (SFX)** or **Music Track**, then pick a file (.mp3, .wav, .m4a, .aac, .ogg, up to 50 MB).
- It shows under **Recently Added Sounds** and in the Music / SFX lists for every clip.

### Tab ✨ Ask AI & Post
- **Change Clip in Plain Words**: type a change and press **Change** (or Enter). Examples:
  - "end 2 s earlier";
  - "start 3 s later";
  - "title: Watch this";
  - "split layout";
  - "4k".
- **Ready-to-Paste Post Text**: the title, the streamer credit and hashtags. Press **Copy Post Text** and paste it when you upload.
- **Download Cover Image**: a thumbnail picture for the post (shows when available).

---

## 8. Approve and download

- Press **🚀 Approve & Export** in the editor, or **Approve selected / Approve all** in the clip list.
- The clip shows **Waiting**, then **Preparing %**, then **Ready**. When it is done, it downloads to your browser's **Downloads** folder by itself (**Saved to Downloads ✓**).
- The first time, the browser may ask to allow several downloads. Say yes.
- A copy also stays in `data/exports/`. Files there are never deleted automatically.
- Changed your mind after approving? Edit the clip and approve it again to make a new version.

---

## 9. Settings

Press **Settings** in the top bar.

- **Speech accuracy**:
  - **Fast (base)**;
  - **Better (small)**;
  - **Best, slow (medium)**.

  Better and Best catch more words but take longer.
- **AI scoring key (optional)**: an Anthropic API key. With a key, an AI editor reads each clip's words to judge humor,
  surprise and whether the clip is complete. It also translates captions. The words are sent to Anthropic. Press **Test key** to check it.
  Without a key, the built-in scoring is used.
- **Learn from your channel**: your YouTube channel or TikTok link, then **Get views**. See part 11.
- **Age-restricted / YouTube Cookies**: pick the browser you are signed in to YouTube with (Chrome, Edge, Firefox,
  Brave, Opera), or press **Upload cookies.txt**. **Remove cookies** deletes them.
- **Data Storage & Auto-Cleanup**:
  - shows how much space each kind of file uses;
  - **Auto-delete temporary cache**: after 1, 2 (recommended), 3 or 7 days, or never;
  - **🧹 Clean Now** deletes the temporary files now.

  Your finished clips are never deleted.
- Press **Save**, then **Close**.

---

## 10. Clients

Use clients if you make clips for more than one streamer.

1. In the left column, open the **Client** list and choose **+ New client…**. Type a name.
2. While a client is selected, new videos belong to that client, and the list shows only that client's videos.
   **All clients** shows everything.
3. **Client settings** (under the picker):
   - **Name**;
   - **Default caption style**;
   - **Default music**.

   Press **Save**. **Delete** removes the client but keeps its videos.

---

## 11. Learn from your views

ClipForge can rank new clips like the ones that got the most views.

1. Post your clips with the titles ClipForge gave them.
2. Give it the view counts in one of two ways:
   - **Settings > Learn from your channel**: paste your channel (`youtube.com/@you/shorts` or `tiktok.com/@you`) and press **Get views**. It matches your posts to clips by title.
   - Type the number by hand in the editor, **Subtitles** tab, **Views after posting**.
3. Once 6 or more clips have views, new clips get a learned score. Their reason says
   "Like the clips that got the most views…". Run **Find clips again** on older videos to use it.

---

## 12. Problems and fixes

| Problem | Fix |
|---|---|
| Yellow bar at the top | Read it. It says what is missing and how to fix it. |
| A link does not download | Check the link in your browser. For 18+ videos, set cookies in Settings. Press **Try again**. |
| "Please sign in again" | Your sign-in ran out. Type the password again. |
| No clips downloaded | Allow multiple downloads in the browser, or press **Download .ZIP**. The files are also in `data/exports/`. |
| The facecam is in the wrong place | Editor > Cam & Layout > pick the corner, or **🎯 Drag & Select Streamer Box on Video**. |
| Gameplay cut off in Floating Cam | Use **Gameplay Screen Pan (X / Y)** and **Gameplay Screen Zoom**. |
| The hook text shows for the whole clip | Drag the yellow Hook Card bar's ends on the timeline. |
| Translate or AI does nothing | Add an AI key in Settings and press **Test key**. |
| No voice-over option | Install the extras: `pip install --no-deps -r requirements-extras.txt`. |
| Kick live does not start | Install Chrome or Edge. |
| ⚠️ Check quality on a clip | Open the clip, watch it, fix the framing or the times, and approve again. |
| Disk is filling up | Settings > **🧹 Clean Now**, or remove old videos with **✕**. |
| Exporting is slow | Use 1080p. 2K and 4K take much longer on a laptop. |

---

## 13. For the person who runs the server

- **Password for a team:** set `CLIPFORGE_PASSWORD`, and `CLIPFORGE_HOST=0.0.0.0` to open it on your network.
  Without a password, ClipForge only answers on this PC.
- **Online with HTTPS:** `docker compose up -d --build` on a server with a domain (Caddy gives HTTPS).
  Run live Kick clipping on a desktop PC, because it needs a browser.
- **NVIDIA GPU:** set `CLIPFORGE_DEVICE=cuda` for much faster speech-to-text.
- **More live recordings at once:** `CLIPFORGE_MAX_LIVE` (default 6).
- **Your own sounds:** put files in `audio_library/music` and `audio_library/sfx`, or use the PC Import tab.
- **Extras** (GTA screen reading, voice-over): `pip install --no-deps -r requirements-extras.txt`.
  The Windows installer and Docker already do this.
- Only post clips you have the right to use. Reposting other people's streams can get copyright strikes.
