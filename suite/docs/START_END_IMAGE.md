# Start / End image in WanGP (suite note)

| Model | Start (`image_start` / S) | End (`image_end` / E) |
|-------|---------------------------|------------------------|
| **lab_wanmove_*** | Yes — required | No (use tracks) |
| **lab_ti2v5b_fast_*** | Yes — I2V | No (TI2V expand_timesteps ignores last) |
| **FLF2V 14B** | Yes | **Yes** — native first-last |
| **VACE** | Injected frames / aliases | Possible via control |
| **LTX-2.x** | Often | Often |

**Lab e01 path:** start=675 still @ 832×480, end pose via **trajectory**, not `image_end`.  
**Optional A/B later:** FLF2V with start=675 and end=synthetic/open still — only after Move baseline.
