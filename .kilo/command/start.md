---
description: Start WanGP cockpit (profile 4 + sage)
---

**WSL**

```bash
cd /home/nick/AI/Projects/WanGP-Lab
bash suite/scripts/install_bridge.sh   # once
bash suite/scripts/start_wangp_ui.sh
```

**Windows Desktop**

```bash
bash suite/scripts/install_windows_shortcut.sh
# double-click Desktop: WanGP-Lab.lnk
```

UI: http://localhost:7860  
Lab Bridge tab · `lab_wanmove_e01` / `lab_ti2v5b_fast_e01`  
Do not start UI while headless Move owns the GPU (unless `--force`).
