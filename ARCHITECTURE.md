# 6YEARSOFPAIN — Visual Architecture

Open this file on GitHub (phone or desktop) — all diagrams render automatically.

> **The big idea:** one M5 candle enters the top, falls through 8 sequential "doors."
> Each door is a gate run by one or more Gemini agents. If a door blocks, the candle
> is dropped and we move to the next. If it passes all gates, a trade is entered,
> managed, and logged.

---

## 1. The whole system at a glance

```mermaid
flowchart TD
    DATA[(CSV data\nM5 / M1 / OrderFlow)] --> LOAD[data_loader.py\nload + index]
    LOAD --> MAIN[main.py\nmain candle loop]

    MAIN --> FLOW[[Flow Reader\nbackground thread\nstarts at candle TOP]]

    MAIN --> D1[Door 1\nPre-session]
    D1 --> D2[Door 2\nCandle Advance]
    D2 --> D3[Door 3\nPossibility Tree]
    D3 --> D4[Door 4\nEntry]
    D4 --> D5[Door 5\nManagement]
    D5 --> D6[Door 6\nTrade Log]
    D6 --> D7[Door 7\nEnd of Day]
    D7 --> D8[Door 8\nSession Summary]

    FLOW -.collected after D2.-> D3
    FLOW -.veto / boost.-> D4
    FLOW -.forced exit.-> D5

    D6 --> LEDGER[(LEDGER.md)]
    D8 --> LEDGER

    classDef door fill:#1f2937,stroke:#60a5fa,color:#fff
    classDef flow fill:#3b1f1f,stroke:#f87171,color:#fff
    classDef store fill:#1f3b2f,stroke:#34d399,color:#fff
    class D1,D2,D3,D4,D5,D6,D7,D8 door
    class FLOW flow
    class DATA,LEDGER,LOAD store
```

---

## 2. The 8 doors — what each one decides

```mermaid
flowchart LR
    subgraph ONCE_PER_DAY
        D1[Door 1\nPre-session\nH1 Commander sets\nthe daily mandate]
    end

    subgraph EVERY_CANDLE
        D2[Door 2\nWho won this candle?\nM5 Sniper + M1 Trigger]
        D3[Door 3\nBuild possibility tree\n+ conviction score]
        D4{Door 4\nAll gates pass?\nconviction >= 6?}
        D5[Door 5\nManage open trade\nSL / TP / early exit]
    end

    subgraph ON_EVENTS
        D6[Door 6\nLog closed trade\n+ post-mortem]
        D7[Door 7\nEnd-of-day review]
        D8[Door 8\nSession summary]
    end

    D1 --> D2 --> D3 --> D4
    D4 -->|YES enter| D5
    D4 -->|NO| NEXT[next candle]
    D5 -->|trade closed| D6
    D2 -->|day changed| D7
```

---

## 3. Which agent runs in which door

5 Gemini agents, each a different timeframe / role.

```mermaid
flowchart TD
    subgraph AGENTS[5 Gemini Agents]
        A1[H1 Commander\nH4+H1 strategic mandate]
        A2[M15 Scout\nM15 momentum trim]
        A3[M5 Sniper\nM5 structure + setup]
        A4[M1 Trigger\nM1 execution timing]
        A5[Flow Reader\norder-flow real intent]
    end

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
    class A1,A2,A3,A4,A5 agent
```

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
    DL -->|aggregate_to_hours| H1H4[H1/H4 in-memory]
    DL -->|aggregate_to_m15| M15[M15 in-memory]

    H1H4 --> MAIN
    M15 --> MAIN

    MAIN --> DOORS[gates/door1..8]
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
| Agents | 5 (H1, M15, M5, M1, Flow Reader) |
| Doors | 8 sequential gates |
| Conviction floor | 6 (flow on) / 7 (flow off) |
| Flow boost / penalty | +2.0 / -2.5 max |
| Flow veto strength | ≥7 opposing |
| Max trades | 30 total, 24/day |
| Kill switch | 5 consecutive losses → day halt |
| Min R:R | 1.5 |
| Data | 100k M5 candles, 288 order-flow bars (2025-06-17) |

See **DOORS.md** for a deep dive on every single door (all questions, all gates, per-door diagrams).
See **CLAUDE.md** for full file map and run instructions.
