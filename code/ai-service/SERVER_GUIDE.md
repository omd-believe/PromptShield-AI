# PromptShield AI — Beginner-Friendly Server Guide

Welcome to your local AI server guide! This guide explains how your laptop powers AI compression for the PromptShield project, how everything connects together, and how to manage the system using the `promptshield` command.

---

## 1. Architecture: How Does It Work?

Here is the high-level flow of an optimization request:

```text
[ User in Browser ]
        |
        v
[ Vercel React Frontend ]
        |
        v
[ Render Spring Boot Backend ]  (Cloud Server)
        |
        v  (Encrypted Cloudflare Tunnel via Internet)
[ Your Fedora Laptop ]
        |
        v
[ FastAPI AI Service ]  (Port 8000)
        |
        v
[ NVIDIA RTX 3050 Laptop GPU ]  (LLMLingua-2 Model)
```

### Key Concepts Explained in Plain English

1. **What is an AI server?**  
   An AI server is a program that accepts text input, passes it through an artificial intelligence model running in memory, and sends back the result. In PromptShield, the AI service removes filler phrases, compresses prompt length using **LLMLingua-2**, and masks sensitive personal data (PII) like emails and names.

2. **Why does my laptop act as the AI server?**  
   Cloud GPU servers (such as AWS, Azure, or Render GPU instances) can cost hundreds of dollars every month. Your HP Victus laptop has a dedicated **NVIDIA RTX 3050 (6 GB VRAM)** graphics card. Running inference directly on your laptop provides fast GPU acceleration for free!

3. **What does Cloudflare Tunnel do?**  
   Your laptop is behind your home or mobile Wi-Fi router. Typically, servers on the internet (like Render) cannot reach your laptop without port forwarding or a public static IP. Cloudflare Tunnel opens an encrypted, outbound connection from your laptop to Cloudflare's global network, giving your laptop a public web address (e.g. `https://xyz.trycloudflare.com`) without exposing your home IP or opening incoming router ports.

---

## 2. The `promptshield` Management Tool

You do not need to memorize long Linux or systemd commands. Everything can be controlled using the `promptshield` command in your terminal.

| Task | Command |
| :--- | :--- |
| **Check server status** | `promptshield status` |
| **Start everything** | `promptshield start` |
| **Stop everything** | `promptshield stop` |
| **Restart everything** | `promptshield restart` |
| **View current tunnel URL** | `promptshield url` |
| **Monitor GPU & VRAM** | `promptshield gpu` |
| **Run diagnostic tests** | `promptshield test` |
| **View live AI logs** | `promptshield logs ai` |
| **View live tunnel logs** | `promptshield logs tunnel` |
| **Show help menu** | `promptshield help` |

---

## 3. Step-by-Step Daily Workflows

### How to Start the Server
Open your terminal and run:
```bash
promptshield start
```
What happens automatically:
1. Starts the FastAPI AI service in the background.
2. Checks that the local health check passes at `http://127.0.0.1:8000/health`.
3. Starts the Cloudflare Tunnel.
4. Waits for the public tunnel address to be generated and prints it.

### How to Stop the Server
When you want to stop background AI processing:
```bash
promptshield stop
```
This safely shuts down Cloudflare Tunnel first, then shuts down FastAPI. Your laptop will no longer process remote requests. (Automatic startup is preserved for your next login).

### How to Restart
```bash
promptshield restart
```
This safely stops both services, boots them back up, and outputs your new Cloudflare URL.

### How to Check if the Server is Online
Run:
```bash
promptshield status
```
You will see a live dashboard:
```text
================================
      PROMPTSHIELD SERVER       
================================

AI Service       : RUNNING
Cloudflare       : RUNNING
Local API        : HEALTHY
GPU              : NVIDIA GeForce RTX 3050 6GB Laptop GPU
Tunnel URL       : https://example.trycloudflare.com

Overall Status   : ONLINE
================================
```

### How to Monitor GPU Usage
To verify that your graphics card is active, check memory usage, or monitor temperature:
```bash
promptshield gpu
```

---

## 4. Laptop Lifecycle & Power Management

Because your laptop is the inference server, keep these physical considerations in mind:

### 1. What happens if I close my laptop lid?
- **By default in Linux**, closing the laptop lid triggers system **suspend / sleep**.
- While suspended, the CPU and GPU are paused and Wi-Fi disconnects. Any request sent from the Render backend will time out.
- **To allow closing the lid while keeping the server running**:  
  In Fedora GNOME settings, or in `/etc/systemd/logind.conf`, you can set `HandleLidSwitch=ignore` when connected to AC power. Alternatively, keep the laptop lid open when serving requests.

### 2. What happens if I shut down or restart my laptop?
- When powered off, the server cannot accept requests.
- When you turn your laptop back on and it connects to Wi-Fi:
  - Thanks to **user lingering** (`loginctl enable-linger omd24`), systemd boots the AI service and Cloudflare Tunnel automatically in the background even before you log into the desktop!
  - However, because a Quick Tunnel generates a new random URL upon each start, you must check the new URL and update Render (see below).

### 3. How to recover after an internet disconnection
If your Wi-Fi disconnects and reconnects:
1. Cloudflared automatically attempts to reconnect.
2. If the tunnel reconnects with a new URL, check it with:
   ```bash
   promptshield url
   ```
3. Update `AI_SERVICE_URL` in the Render dashboard if the URL has changed.

---

## 5. Connecting Render to Your Laptop

Whenever you restart the tunnel or start fresh, Cloudflare Quick Tunnel creates a new URL:

1. View the active URL:
   ```bash
   promptshield url
   ```
2. Open your [Render Dashboard](https://dashboard.render.com).
3. Click on your Spring Boot backend service (`promptshield-backend`).
4. Go to **Environment** in the left sidebar.
5. Update:
   - **`AI_SERVICE_URL`**: `https://<active-url>.trycloudflare.com` *(no trailing slash)*
6. Click **Save Changes**. Render will redeploy in 1–2 minutes.

---

## 6. How to Enable or Disable Automatic Startup

Automatic startup is currently configured using systemd user services.

- **To disable automatic startup on boot**:
  ```bash
  systemctl --user disable promptshield-ai.service
  systemctl --user disable promptshield-tunnel.service
  ```
  *(The services will now only run when you explicitly type `promptshield start`).*

- **To re-enable automatic startup on boot**:
  ```bash
  systemctl --user enable promptshield-ai.service
  systemctl --user enable promptshield-tunnel.service
  ```

---

## 7. Troubleshooting & Common Errors

### "AI Service: STOPPED" or "Local API: OFFLINE"
- Run `promptshield start`.
- Inspect errors: `promptshield logs ai`.
- Check if port 8000 is blocked: `ss -tulpn | grep 8000`.

### "Tunnel URL: NOT CONNECTED" or DNS Failure
- Verify your laptop has internet access (`ping -c 3 1.1.1.1`).
- Restart the tunnel: `systemctl --user restart promptshield-tunnel.service`.
- Check tunnel logs: `promptshield logs tunnel`.

### Backend reports "500 AI service unavailable"
- Run `promptshield test`.
- Verify that `AI_SERVICE_URL` in Render matches the exact output of `promptshield url`.
- Verify that `AI_SERVICE_API_KEY` on Render matches the key in your laptop's `.env` file.

### Desktop Launcher
A desktop shortcut named **PromptShield Server Manager** is available in your GNOME application list and on your Desktop. Clicking it launches the terminal and immediately displays the live server status!

