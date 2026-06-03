# 6YEARSOFPAIN — Visual Architecture

Open this file on GitHub (phone or desktop) — all diagrams render automatically.

> **The big idea:** one M5 candle enters the top, falls through sequential "doors."
> Each door is a gate run by one or more Gemini agents. If a door blocks, the candle
> is dropped. If it passes all gates, a trade is entered, managed, and logged.
> Two always-on layers wrap the doors: the **POI engine** (reaction-zone map) and the
> **stage funnel** (narrow the hour, only enter in stage 4).

**Updated 2026-06-03** — added **Door 0** (Cartographer / warm-start), the **POI engine**
(dual-scored reaction zones), the **stage funnel**, and fixed the **future-candle leak**.

---

## 1. The whole system at a glance

```mermaid
flowchart TD
    DATA[(CSV data\nM5 / M1 / OrderFlow)] --> LOAD[data_loader.py\nload + index\nNO-LEAK higher-TF]
    LOAD --> MAIN[main.py\nmain candle loop]

    POIE[[POI engine\ndual-scored map\nrebuilt hourly]] -.armed POIs.-> MAIN
    STAGE[[stage funnel\n4x15-min\nentry only stage 4]] -.gates entry.-> MAIN
    FLOW[[Flow Reader\nbackground thread]] -.veto/boost/exit.-> MAIN

    MAIN --> D0[Door 0\nBootstrap / Map\nCartographer]
    D0 --> D1[Door 1\nPre-session]
    D1 --> D2[Door 2\nCandle Advance]
    D2 --> D3[Door 3\nPossibility Tree]
    D3 --> D4[Door 4\nEntry]
    D4 --> D5[Door 5\nManagement]
    D5 --> D6[Door 6\nTrade Log]
    D6 --> D7[Door 7\nEnd of Day]
    D7 --> D8[Door 8\nSession Summary]

    D0 -.cycle map seeds.-> D1
    D0 -.cycle map seeds.-> D3
    D6 --> LEDGER[(LEDGER.md)]
    D8 --> LEDGER

    classDef door fill:#1f2937,stroke:#60a5fa,color:#fff
    classDef flow fill:#3b1f1f,stroke:#f87171,color:#fff
    classDef store fill:#1f3b2f,stroke:#34d399,color:#fff
    classDef layer fill:#2a1f3b,stroke:#a78bfa,color:#fff
    class D0,D1,D2,D3,D4,D5,D6,D7,D8 door
    class FLOW,POIE,STAGE layer
    class DATA,LEDGER,LOAD store
```

---

## 2. The doors — what each one decides

```mermaid
flowchart LR
    subgraph ONCE_PER_DAY
        D0[Door 0\nDraw the cycle map\nCartographer · warm-start]
        D1[Door 1\nPre-session\nH1 Commander mandate]
    end

    subgraph EVERY_CANDLE
        D2[Door 2\nWho won this candle?\nM5 Sniper + M1 Trigger]
        D3[Door 3\nBuild + NARROW tree\nstage-aware]
        D4{Door 4\nGates pass + conv >= 6\nAND stage == 4?}
        D5[Door 5\nManage open trade\nSL / TP / early exit]
    end

    subgraph ON_EVENTS
        D6[Door 6\nLog closed trade\n+ post-mortem]
        D7[Door 7\nEnd-of-day review]
        D8[Door 8\nSession summary]
    end

    D0 --> D1 --> D2 --> D3 --> D4
    D4 -->|YES enter| D5
    D4 -->|NO / not stage 4| NEXT[next candle]
    D5 -->|trade closed| D6
    D2 -->|day changed| D7
```

---

## 2b. The three analytical engines (the vision)

The system is really **three gather→narrow→story engines** + execution, not just an entry machine:

```mermaid
flowchart TD
    subgraph DIRECTION[Engine A — DIRECTION]
        DIR[Door 0 Cartographer + Door 1\nH4/H1 → overall control + stories]
    end
    subgraph POI[Engine B — POI · keystone]
        P[poi_engine.py\n4H/1H/15m → dual-scored reaction zones]
    end
    subgraph ENTRY[Engine C — ENTRY]
        E[Doors 2-4 + stage funnel\n15m→5m→1m + order flow → the trade]
    end
    DIR --> POI --> ENTRY
    POI -.armed zones.-> DIR
    POI -.armed zones.-> ENTRY
```

---

## 3. Which agent runs in which door

5 Gemini agents, each a different timeframe / role.

```mermaid
flowchart TD
    subgraph AGENTS[6 Gemini Agents]
        A0[Cartographer\nH4/H1+POI → cycle map]
        A1[H1 Commander\nH4+H1 strategic mandate]
        A2[M15 Scout\nM15 momentum trim]
        A3[M5 Sniper\nM5 structure + setup]
        A4[M1 Trigger\nM1 execution timing]
        A5[Flow Reader\norder-flow real intent]
    end

    A0 --> D0[Door 0]
    A1 --> D1[Door 1]
    A3 --> D2[Door 2]
    A4 --> D2
    A3 --> D3[Door 3]
    A2 --> D3
    A3 --> D4[Door 4]
    A4 --> D4
    A4 --> D5[Door 5]
    A5 -.background.-> D3
    A5 -.background.-> D4
    A5 -.background.-> D5

    classDef agent fill:#2a1f3b,stroke:#a78bfa,color:#fff
    class A0,A1,A2,A3,A4,A5 agent
```

> Plus the Bull + Bear debate agents inside Door 4 (use the `default` system prompt).

---

## 4. Data flow — file by file

```mermaid
flowchart LR
    M5[(m5.csv\n100k candles)] --> DL[data_loader.py]
    M1[(m1.csv)] --> DL
    OF[(orderflow_5m_2025-06-17.csv\n288 bars, 25 cols)] --> DL

    DL -->|candle_to_dict| MAIN[main.py loop]
    DL -->|build_m1_index O1| MAIN
    DL -->|build_orderflow_index O1| MAIN
    DL -->|_agg_tail NO-LEAK| HTF[H1/H4/M15 in-progress\nbuilt backward from idx]

    HTF --> MAIN
    MAIN --> POIE[poi_engine.py\ndual-scored map]
    MAIN --> STG[stage_funnel.py\nstage gate]
    POIE --> MAIN
    STG --> MAIN

    MAIN --> DOORS[gates/door0..8]
    DOORS --> CC[claude_client.py\nGemini Flash]
    DOORS --> FL[flow_layer.py\nveto/boost/exit]
    CC --> GEMINI((Gemini 2.5 Flash))
```

---

## 5. The flow-threading trick (why it's fast now)

The Flow Reader is slow (~60-90s). Instead of blocking, it runs in a background
thread that **starts before Door 2** and is **collected after Door 2** — so it
overlaps with the required agents instead of adding on top.

```mermaid
sequenceDiagram
    participant M as main.py
    participant F as Flow Reader (bg thread)
    participant D2 as Door 2 (M5+M1)
    participant D3 as Door 3
    participant D4 as Door 4

    M->>F: start flow read (candle TOP)
    M->>D2: run M5 Sniper + M1 Trigger
    Note over F,D2: both run AT THE SAME TIME
    D2-->>M: done (~30s)
    M->>F: collect result (waits ~10-20s more)
    F-->>M: flow verdict (ALWAYS completes, no skip)
    M->>D3: inject flow -> conviction modifier
    M->>D4: flow veto + boost
```

---

## 6. Door 4 — the entry decision (the gauntlet)

```mermaid
flowchart TD
    SIG[Door 3 signal\nconviction >= 6?] -->|no| DROP[no trade]
    SIG -->|yes| G1{Gate 1\ntrade limits ok?}
    G1 -->|no| DROP
    G1 -->|yes| G2{Gate 2\nH1 mandate aligned?}
    G2 -->|no| DROP
    G2 -->|yes| G25{Gate 2.5\nFLOW veto?\nopposing strength >= 7?}
    G25 -->|vetoed| DROP
    G25 -->|clear| G3{Gate 3\nM1 not ABORT?}
    G3 -->|abort| DROP
    G3 -->|ok| BB[Bull + Bear\nparallel debate]
    BB --> CHK{15-item checklist\nall pass?}
    CHK -->|no| DROP
    CHK -->|yes| SIZE[Half-Kelly sizing]
    SIZE --> ENTER[ENTER TRADE\nstore flow context]

    classDef bad fill:#3b1f1f,stroke:#f87171,color:#fff
    classDef good fill:#1f3b2f,stroke:#34d399,color:#fff
    class DROP bad
    class ENTER good
```

---

## 7. Order flow layer (additive — behind one switch)

Everything order-flow lives behind `config.ORDERFLOW_ENABLED`.
**Off = byte-for-byte the original 4-agent behavior.**

```mermaid
flowchart LR
    SW{ORDERFLOW_ENABLED}
    SW -->|False| ORIG[Original 4-agent system\nconviction floor 7\nno flow]
    SW -->|True| NEW[5-agent system\nconviction floor 6\nflow veto + boost + exit]

    NEW --> V[flow_layer.veto\nblock into walls]
    NEW --> B[flow_layer.conviction_modifier\n+2.0 / -2.5]
    NEW --> E[flow_layer.exit_signal\nforced early exit]

    classDef orig fill:#1f2937,stroke:#9ca3af,color:#fff
    classDef new fill:#2a1f3b,stroke:#a78bfa,color:#fff
    class ORIG orig
    class NEW,V,B,E new
```

---

## Quick reference

| Thing | Value |
|---|---|
| Brain | Gemini 2.5 Flash |
| Agents | 6 (Cartographer, H1, M15, M5, M1, Flow Reader) + Bull/Bear in Door 4 |
| Doors | Door 0 + 8 gates |
| Engines | Direction (D0/D1), POI (keystone), Entry (D2-4 + funnel) |
| POI scores | structural 0-10 + crowd 0-10 → CLEAN/QUIET/FIGHT/IGNORE |
| Stage funnel | 4×15-min per hour, entry only in stage 4 |
| Conviction floor | 6 (flow on) / 7 (flow off) |
| Flow boost / penalty | +2.0 / -2.5 max · veto ≥7 opposing |
| Max trades | 30 total, 24/day · Kill switch 5 losses · Min R:R 1.5 |
| Look-ahead | NONE — higher-TF in-progress candle built only up to now |
| Data | 100k M5 candles, 288 order-flow bars (2025-06-17) |
| Switches | POI_ENABLED · STAGE_FUNNEL_ENABLED · ORDERFLOW_ENABLED (off = original) |

See **DOORS.md** for a deep dive on every single door (all questions, all gates, per-door diagrams).
See **CLAUDE.md** for full file map and run instructions.
