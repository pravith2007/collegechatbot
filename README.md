# KEC AI Assistant – Tamil College Chatbot
### Multilingual RAG System, Web Scraper, and Android Mobile Application (Capacitor)

Official Source: **https://kongu.ac.in/** (Kongu Engineering College)

---

## 📱 Mobile Android Application & PWA Overview

The KEC AI Assistant has been packaged into a native Android application using **Capacitor** with:
- **Mobile-First Responsive UI:** Optimized for Android phones, tablets, and desktops (`100dvh` viewport, safe area insets, no horizontal overflow).
- **Fixed Bottom Input Bar:** Message input and send button remain anchored and visible when the Android on-screen keyboard appears.
- **Tamil Virtual Keyboard:** Responsive touch-friendly on-screen keyboard for native Tamil typing on any mobile device.
- **Voice Recognition (STT):** Tamil and English speech recognition with automatic fallback when speech recognition is unavailable in specific WebViews.
- **Connection Status Indicator:** Displays live RAG connectivity (`RAG Online` / `Offline Backup`) in real-time.
- **Clear Chat Option:** One-tap conversation reset with confirmation.
- **Progressive Web App (PWA):** Web manifest (`manifest.json`), theme color `#1e40af`, and standalone mobile display mode.

> [!IMPORTANT]
> **Architecture Clarification:**
> The Android APK packages the **React + TypeScript frontend**. The **Flask backend** (with ChromaDB, KONGU.txt knowledge base, and Ollama LLM) runs on your host machine or cloud server. The Android app communicates with the Flask backend over Wi-Fi / HTTPS. The Python server and Ollama are **not** bundled inside the APK.

---

## 🌟 Architecture & Workflow

```
[Official KEC Website (kongu.ac.in)]
                │
                ▼
[Web Scraper & Change Detector (web_scraper.py)] ──▶ Updates [project/public/KONGU.txt]
                │
                ▼
[Text Chunker & ChromaDB Embeddings (rag_pipeline.py)]
                │
                ▼
   ┌───────────────────────────────────────────────┐
   │       Flask Backend Service (Port 8000)       │
   │    /api/chat  |  /api/health  |  /api/admin    │
   └──────────────────────┬────────────────────────┘
                          │ (REST API via Wi-Fi / HTTPS)
                          ▼
   ┌───────────────────────────────────────────────┐
   │      Android Mobile App (Capacitor)           │
   │  • App Name: KEC AI Assistant                 │
   │  • Package: com.kec.aiassistant               │
   │  • Responsive UI + Tamil Keyboard + Voice STT │
   │  • PWA Manifest & Android Native Shell        │
   └───────────────────────────────────────────────┘
```

---

## 📁 Project Directory Structure

```
college-chat-bot/
├── backend/
│   ├── app.py                # Flask Backend API (Endpoints for Chat & Admin Sync)
│   ├── web_scraper.py        # KECWebScraper (robots.txt, HTML/PDF extraction, KONGU.txt updater)
│   ├── text_chunker.py       # TextChunker (Tamil boundary preservation, stable chunk IDs)
│   ├── rag_pipeline.py       # RAGPipeline (ChromaDB incremental upsert, Ollama/OpenAI RAG)
│   ├── scheduler.py          # KECSyncScheduler (APScheduler 24-hr periodic background sync)
│   ├── config.py             # Central configuration (URLs, timeouts, paths)
│   ├── storage.py            # Persistent sync metadata and document registry
│   ├── requirements.txt      # Python dependencies
│   ├── .env.example          # Safe environment variables template
│   ├── tests/
│   │   └── test_pipeline.py  # Comprehensive 16-point automated test suite
│   └── data/                 # Persistent storage (chroma_db/ and chunks.jsonl)
├── project/
│   ├── android/              # Capacitor Android Studio Project
│   │   ├── app/
│   │   │   ├── build.gradle  # Android application build configuration
│   │   │   └── src/main/
│   │   │       ├── AndroidManifest.xml # Permissions (INTERNET, RECORD_AUDIO, usesCleartextTraffic)
│   │   │       └── res/      # App icons, strings, styles
│   │   ├── build.gradle      # Root Gradle configuration
│   │   └── local.properties  # Android SDK directory location
│   ├── capacitor.config.ts   # Capacitor configuration (com.kec.aiassistant)
│   ├── public/
│   │   ├── KONGU.txt         # Primary college knowledge base (auto-updated by scraper)
│   │   ├── KONGU.txt.bak     # Automatic backup of previous knowledge base
│   │   └── manifest.json     # PWA manifest
│   ├── src/
│   │   ├── App.tsx           # Mobile-responsive Chatbot UI + connection status + clear chat
│   │   ├── components/
│   │   │   ├── AdminDashboard.tsx  # Authenticated Sync & Scraper Admin Dashboard
│   │   │   └── TamilKeyboard.tsx   # Mobile touch-responsive Tamil virtual keyboard
│   │   └── data/
│   │       └── knowledgeBase.ts    # Curated backup knowledge base
│   ├── .env.example          # Frontend API base URL template (VITE_API_BASE_URL)
│   ├── package.json          # Dependencies & Capacitor scripts
│   └── vite.config.ts        # Vite configuration (port 7000)
└── README.md
```

---

## ⚙️ Prerequisites

1. **Node.js**: v18 or v20+ with npm.
2. **Python**: Python 3.10+ with `pip`.
3. **Android Studio**: Android Studio Jellyfish / Koala / Ladybug or newer.
4. **Android SDK**: Android SDK Platform 34 or 35 + Android SDK Build-Tools 35.
5. **Java Development Kit (JDK)**: JDK 17 or JDK 21 (Android Studio includes a compatible JDK in `C:\Program Files\Android\Android Studio\jbr`).

---

## 🚀 Step-by-Step Setup & Execution

### 1. Run the Flask Backend

In a terminal, start the Python backend:

```bash
cd backend
pip install -r requirements.txt
python app.py
```
- **Backend URL:** `http://localhost:8000`
- **Health Check:** `http://localhost:8000/api/health`

### 2. Configure the Frontend API URL for Android

> [!WARNING]
> On an Android device or emulator, `localhost` refers to the **phone itself**, not your computer!

To allow your Android phone to connect to your backend:
1. Find your computer's local IP address on Wi-Fi:
   - On Windows: Run `ipconfig` (look for `IPv4 Address`, e.g., `192.168.1.15`).
2. In `project/`, create or edit `.env`:
   ```env
   VITE_API_BASE_URL=http://192.168.1.15:8000
   ```
   *(Replace `192.168.1.15` with your actual PC's IP address).*
3. Ensure your phone and PC are connected to the **same Wi-Fi network**.

### 3. Run the Frontend in Development Mode

```bash
cd project
npm install
npm run dev
```
- **Web App URL:** `http://localhost:7000`

---

## 📦 Building and Packaging for Android with Capacitor

### 1. Build the React Frontend
Compiles the TypeScript and Tailwind CSS assets into `project/dist`:
```bash
npm run build
```

### 2. Synchronize Web Assets with Android Project
Copies web assets and syncs plugins to the native `android/` project:
```bash
npx cap sync android
```
*(Or use `npm run cap:sync` / `npm run cap:build`).*

### 3. Open in Android Studio
To inspect, debug, or run on an emulator/device directly from Android Studio:
```bash
npx cap open android
```

---

## 🔨 How to Generate the Debug APK

### Option A: Command Line (Fastest)

Run the Gradle build command using Android Studio's bundled JDK 21:

**On Windows (PowerShell):**
```powershell
cd project\android
$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"
.\gradlew.bat assembleDebug
```

**Output APK Location:**
```
project\android\app\build\outputs\apk\debug\app-debug.apk
```
*(File size is approximately 4.07 MB).*

### Option B: Using Android Studio GUI

1. Run:
   ```bash
   cd project
   npx cap open android
   ```
2. Wait for Android Studio to index and perform Gradle sync.
3. In the top menu bar, click:
   **Build** ➔ **Build Bundle(s) / APK(s)** ➔ **Build APK(s)**.
4. When finished, a notification popup will say:
   `APK(s) generated successfully for module 'app'`. Click **locate** to open the folder with `app-debug.apk`.

---

## 📲 How to Install the APK on Your Android Phone

### Method 1: Direct Transfer via USB
1. Connect your Android phone to your PC via USB cable.
2. Select **File Transfer / MTP** mode on your phone.
3. Copy `app-debug.apk` to your phone's **Downloads** folder.
4. On your phone, open the **Files** app, tap `app-debug.apk`, and tap **Install**.
   *(Enable "Install unknown apps" if prompted).*

### Method 2: Via ADB (Android Debug Bridge)
If your phone has USB Debugging enabled:
```bash
adb install -r project\android\app\build\outputs\apk\debug\app-debug.apk
```

### Method 3: Cloud / Messaging
Upload `app-debug.apk` to Google Drive or send it to yourself via WhatsApp/Telegram and open the APK file directly on your phone to install.

---

## 🔧 Troubleshooting Android & Connection Issues

| Issue | Cause | Solution |
| :--- | :--- | :--- |
| **"Offline Backup" indicator active** | Phone cannot reach the Flask server IP | 1. Ensure phone and PC are on the same Wi-Fi.<br>2. Confirm `VITE_API_BASE_URL` in `.env` is set to your PC's IP (`http://192.168.x.x:8000`), not `localhost`.<br>3. Check Windows Firewall: allow inbound connections on port 8000.<br>4. Re-run `npm run build` and `npx cap sync android` after changing `.env`. |
| **Cleartext HTTP blocked** | Android defaults to HTTPS | `AndroidManifest.xml` already has `android:usesCleartextTraffic="true"` enabled for local development. For public production, deploy backend behind HTTPS. |
| **Speech recognition error** | WebView lacks Web Speech API | The app automatically displays an informative notice and allows effortless fallback to on-screen Tamil virtual keyboard or standard typing. |
| **Microphone permission prompt** | Voice STT requires audio input | Grant microphone permission when prompted by the app. |
| **Gradle JDK error** | Default Java version incompatible with Gradle | Set `$env:JAVA_HOME = "C:\Program Files\Android\Android Studio\jbr"` before running `.\gradlew.bat`. |

---

## 🔄 Services That Must Remain Running

For the full AI chatbot and live knowledge synchronization experience:
1. **Flask Backend (`python backend/app.py`)**:
   - Must run on your host computer or cloud server (e.g., Render, Railway, AWS, DigitalOcean).
   - Hosts the ChromaDB vector database, RAG pipeline, and 24-hr scheduler.
2. **Ollama LLM (`ollama serve`)**:
   - Must run on the server if using local LLM inference (e.g., `llama3` or `mistral`).
   - If using OpenAI, ensure `OPENAI_API_KEY` is set in `backend/.env`.

---

## 🧪 Verification & Automated Testing

Run the comprehensive 16-point backend test suite:
```bash
python backend/tests/test_pipeline.py
```

All 16 tests validate:
- HTML scraper & robots.txt filtering
- SHA-256 change detection
- Safe atomic `KONGU.txt` updates & backups
- Tamil Unicode chunking & stable IDs
- ChromaDB upsert deduplication
- Multilingual retrieval (Tamil & English)
- Error & 404 resilience
