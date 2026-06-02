"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import api, { AllTicksResponse, CorrelationRegime, IntelligenceBias, MacroAnalysis, NewsFed, OHLCVCandle, SmcBias, VolatilityRegime } from "@/lib/api";

const INSTRUMENTS = [
  { sym: "XAUUSD", label: "XAU/USD",  decimals: 2, suffix: "" },
  { sym: "DXY",    label: "DXY",      decimals: 2, suffix: "" },
  { sym: "US10Y",  label: "US 10Y",   decimals: 3, suffix: "%" },
  { sym: "US02Y",  label: "US 2Y",    decimals: 3, suffix: "%" },
  { sym: "SPX",    label: "S&P 500",  decimals: 1, suffix: "" },
  { sym: "NDX",    label: "NDX 100",  decimals: 1, suffix: "" },
  { sym: "VIX",    label: "VIX",      decimals: 2, suffix: "" },
];

function scoreColor(s: number) {
  return s >= 65 ? "text-emerald-400" : s >= 45 ? "text-amber-400" : "text-red-400";
}
function scoreBg(s: number) {
  return s >= 65 ? "bg-emerald-500" : s >= 45 ? "bg-amber-500" : "bg-red-500";
}
function biasColor(b: string) {
  return b === "bullish" ? "text-emerald-400" : b === "bearish" ? "text-red-400" : "text-amber-400";
}
function biasBg(b: string) {
  return b === "bullish"
    ? "border-emerald-500/40 bg-emerald-500/5"
    : b === "bearish"
    ? "border-red-500/40 bg-red-500/5"
    : "border-amber-500/40 bg-amber-500/5";
}
function regimeColor(r: string) {
  const m: Record<string, string> = {
    risk_on: "text-emerald-400", risk_off: "text-red-400", transitional: "text-amber-400",
    hawkish_fed: "text-red-400", dovish_fed: "text-emerald-400",
    recession_risk: "text-red-500", growth_expansion: "text-emerald-500",
    neutral: "text-slate-500", abundant: "text-emerald-400", tight: "text-red-400", normal: "text-slate-400",
  };
  return m[r] ?? "text-slate-400";
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-slate-500 text-xs w-28 shrink-0">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${scoreBg(score)}`} style={{ width: `${score}%` }} />
      </div>
      <span className={`text-xs font-bold w-7 text-right tabular-nums ${scoreColor(score)}`}>{score}</span>
    </div>
  );
}

function Pill({ text }: { text: string }) {
  return (
    <span className={`px-2 py-0.5 rounded border text-[10px] font-bold tracking-widest border-slate-700 ${regimeColor(text)}`}>
      {text.replace(/_/g, " ").toUpperCase()}
    </span>
  );
}

export default function Dashboard() {
  const [ticks, setTicks]       = useState<AllTicksResponse>({});
  const [macro, setMacro]       = useState<MacroAnalysis | null>(null);
  const [smc, setSmc]           = useState<SmcBias | null>(null);
  const [vol, setVol]           = useState<VolatilityRegime | null>(null);
  const [corr, setCorr]         = useState<CorrelationRegime | null>(null);
  const [intel, setIntel]       = useState<IntelligenceBias | null>(null);
  const [news, setNews]         = useState<NewsFed | null>(null);
  const [candles, setCandles]   = useState<OHLCVCandle[]>([]);
  const [selected, setSelected] = useState("XAUUSD");
  const [timeframe, setTf]      = useState("1h");
  const [backendOk, setBackend] = useState(false);
  const [clock, setClock]       = useState("");
  const prevRef                 = useRef<AllTicksResponse>({});
  const dirRef                  = useRef<Record<string, "up" | "down" | "flat">>({});

  const fetchAll = useCallback(async () => {
    try {
      const [t, m, s, v, c, i, n] = await Promise.all([
        api.getAllTicks(),
        api.getMacroAnalysis(),
        api.getSmcBias("XAUUSD", "1h"),
        api.getVolatilityRegime("XAUUSD"),
        api.getCorrelationRegime(),
        api.getIntelligenceBias(),
        api.getNewsFed(),
      ]);
      const dirs: Record<string, "up" | "down" | "flat"> = {};
      for (const sym of Object.keys(t)) {
        const cur = t[sym]?.price;
        const pre = prevRef.current[sym]?.price;
        dirs[sym] = !cur || !pre ? "flat" : cur > pre ? "up" : cur < pre ? "down" : "flat";
      }
      dirRef.current = dirs;
      prevRef.current = t;
      setTicks(t);
      setMacro(m);
      setSmc(s);
      setVol(v);
      setCorr(c);
      setIntel(i);
      setNews(n);
      setBackend(true);
    } catch {
      setBackend(false);
    }
  }, []);

  const fetchCandles = useCallback(async () => {
    try {
      const r = await api.getOHLCV(selected, timeframe, 15);
      setCandles([...r.data].reverse());
    } catch {}
  }, [selected, timeframe]);

  useEffect(() => {
    fetchAll();
    fetchCandles();
    const t1 = setInterval(fetchAll, 8000);
    const t2 = setInterval(fetchCandles, 15000);
    const t3 = setInterval(() => setClock(new Date().toLocaleTimeString("en-US", { hour12: false })), 1000);
    setClock(new Date().toLocaleTimeString("en-US", { hour12: false }));
    return () => { clearInterval(t1); clearInterval(t2); clearInterval(t3); };
  }, [fetchAll, fetchCandles]);

  return (
    <div className="min-h-screen bg-[#0a0e1a] text-sm select-none">

      {/* Header */}
      <header className="flex items-center justify-between px-6 py-2.5 border-b border-slate-800/80 bg-[#0d1220]">
        <div className="flex items-center gap-4">
          <span className="text-amber-400 font-black tracking-wider text-base">◈ TERMINAL TRADING</span>
          <span className="text-slate-700">|</span>
          <span className="text-slate-500 text-xs tracking-widest">GOLD INTELLIGENCE ENGINE</span>
        </div>
        <div className="flex items-center gap-6 text-xs">
          <span className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-full ${backendOk ? "bg-emerald-400 animate-pulse" : "bg-red-500"}`} />
            <span className={backendOk ? "text-emerald-400" : "text-red-400"}>{backendOk ? "LIVE" : "OFFLINE"}</span>
          </span>
          <span className="text-slate-500 tabular-nums">{clock} UTC</span>
        </div>
      </header>

      <div className="p-4 space-y-3">

        {/* Gold Intelligence Panel */}
        {macro && (
          <div className={`border rounded-lg p-4 ${biasBg(macro.gold_bias)}`}>
            <div className="flex items-start justify-between gap-6 flex-wrap">
              <div className="flex items-center gap-8">
                <div>
                  <div className="text-[10px] text-slate-500 tracking-widest mb-1">GOLD BIAS</div>
                  <div className={`text-3xl font-black tracking-wider ${biasColor(macro.gold_bias)}`}>
                    {macro.gold_bias.toUpperCase()}
                  </div>
                  <div className="text-slate-500 text-xs mt-1 tabular-nums">{macro.confidence}% confidence</div>
                </div>
                <div className="h-12 w-px bg-slate-800 hidden md:block" />
                <div className="grid grid-cols-2 gap-x-8 gap-y-1">
                  <div>
                    <div className="text-[10px] text-slate-500 tracking-widest">MACRO SCORE</div>
                    <div className={`text-2xl font-bold tabular-nums ${scoreColor(macro.macro_score)}`}>
                      {macro.macro_score}<span className="text-sm text-slate-600">/100</span>
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-500 tracking-widest">RISK SCORE</div>
                    <div className={`text-2xl font-bold tabular-nums ${scoreColor(100 - macro.risk_score)}`}>
                      {macro.risk_score}<span className="text-sm text-slate-600">/100</span>
                    </div>
                  </div>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                <Pill text={macro.market_regime} />
                <Pill text={macro.macro_regime} />
                <Pill text={macro.liquidity_conditions} />
              </div>
            </div>

            {macro.primary_scenario && (
              <div className="mt-3 pt-3 border-t border-slate-800/60 grid grid-cols-2 gap-6">
                <div>
                  <div className="text-[10px] text-emerald-600 tracking-widest mb-1">PRIMARY SCENARIO</div>
                  <div className="text-slate-300 text-xs leading-relaxed">{macro.primary_scenario}</div>
                </div>
                <div>
                  <div className="text-[10px] text-amber-600 tracking-widest mb-1">ALTERNATE SCENARIO</div>
                  <div className="text-slate-400 text-xs leading-relaxed">{macro.alternate_scenario}</div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Gold Intelligence — Multi-Timeframe */}
        {intel && (
          <div className="border border-slate-800 rounded-lg p-3 bg-slate-900/30">
            <div className="flex items-start justify-between gap-4 flex-wrap">

              {/* Consensus */}
              <div className="flex items-center gap-6">
                <div>
                  <div className="text-[10px] text-slate-500 tracking-widest mb-1">GOLD INTELLIGENCE · CONSENSUS</div>
                  <div className={`text-2xl font-black tracking-wider ${biasColor(intel.consensus_bias)}`}>
                    {intel.consensus_bias.toUpperCase()}
                  </div>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-slate-400 text-xs tabular-nums font-bold">{intel.consensus_score}/100</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border font-bold tracking-widest ${
                      intel.alignment === "aligned"    ? "border-emerald-700 text-emerald-400" :
                      intel.alignment === "conflicted" ? "border-red-700 text-red-400" :
                                                         "border-amber-700 text-amber-400"
                    }`}>{intel.alignment.toUpperCase()}</span>
                    <span className="text-slate-600 text-xs">{intel.confidence}% conf</span>
                  </div>
                </div>
              </div>

              {/* Timeframe bars */}
              <div className="flex gap-3 flex-1 max-w-lg">
                {(["5m", "15m", "1h", "macro"] as const).map((tf) => {
                  const h = intel.timeframes[tf];
                  const pct = h.conviction_score;
                  return (
                    <div key={tf} className="flex-1">
                      <div className="text-[10px] text-slate-500 tracking-widest mb-1 text-center">{tf.toUpperCase()}</div>
                      {/* Vertical bar from 0-100, midpoint=50=neutral */}
                      <div className="relative h-16 bg-slate-800 rounded overflow-hidden">
                        {/* Neutral line */}
                        <div className="absolute w-full h-px bg-slate-600 top-1/2" />
                        {/* Fill from midpoint */}
                        {pct >= 50 ? (
                          <div
                            className={`absolute bottom-1/2 w-full rounded-t ${scoreBg(pct)}`}
                            style={{ height: `${(pct - 50) * 1}%` }}
                          />
                        ) : (
                          <div
                            className="absolute top-1/2 w-full rounded-b bg-red-500"
                            style={{ height: `${(50 - pct) * 1}%` }}
                          />
                        )}
                        {/* Score label */}
                        <div className={`absolute inset-0 flex items-center justify-center text-[10px] font-bold tabular-nums ${
                          biasColor(h.bias)
                        }`}>{pct}</div>
                      </div>
                      <div className={`text-[10px] text-center mt-1 font-bold ${biasColor(h.bias)}`}>
                        {h.bias === "bullish" ? "▲" : h.bias === "bearish" ? "▼" : "—"}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Key insight */}
              <div className="text-xs text-slate-400 max-w-xs leading-relaxed border-l border-slate-800 pl-4">
                <div className="text-[10px] text-slate-500 tracking-widest mb-1">KEY INSIGHT</div>
                {intel.key_insight}
              </div>
            </div>
          </div>
        )}

        {/* Watchlist */}
        <div className="grid grid-cols-7 gap-2">
          {INSTRUMENTS.map(({ sym, label, decimals, suffix }) => {
            const t = ticks[sym];
            const dir = dirRef.current[sym] ?? "flat";
            return (
              <div
                key={sym}
                onClick={() => setSelected(sym)}
                className={`border rounded-lg p-3 cursor-pointer transition-all hover:border-slate-600 ${
                  selected === sym ? "border-amber-500/50 bg-amber-500/5" : "border-slate-800 bg-slate-900/50"
                }`}
              >
                <div className="text-[10px] text-slate-500 tracking-widest mb-1">{label}</div>
                {t ? (
                  <div className={`text-base font-bold leading-tight tabular-nums ${
                    dir === "up" ? "text-emerald-400" : dir === "down" ? "text-red-400" : "text-white"
                  }`}>
                    {t.price.toFixed(decimals)}{suffix}
                  </div>
                ) : (
                  <div className="text-slate-700 text-sm animate-pulse">—</div>
                )}
                <div className="text-[10px] mt-0.5 text-slate-700">
                  {dir === "up" ? "▲" : dir === "down" ? "▼" : "—"}
                </div>
              </div>
            );
          })}
        </div>

        {/* SMC Panel */}
        {smc && (
          <div className="border border-slate-800 rounded-lg p-3 bg-slate-900/30">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-6">
                <div>
                  <div className="text-[10px] text-slate-500 tracking-widest mb-1">SMC STRUCTURE · XAUUSD 1H</div>
                  <div className={`text-lg font-black tracking-wider ${biasColor(smc.structure_bias)}`}>
                    {smc.structure_bias.toUpperCase()}
                    <span className="text-slate-600 text-xs font-normal ml-2">strength {smc.bias_strength.toFixed(0)}</span>
                  </div>
                </div>
                <div className="h-8 w-px bg-slate-800" />
                <div className="flex gap-6 text-xs">
                  {smc.last_choch && (
                    <div>
                      <div className="text-[10px] text-slate-500 tracking-widest">LAST CHoCH</div>
                      <div className={smc.last_choch === "bullish" ? "text-emerald-400" : "text-red-400"}>
                        {smc.last_choch.toUpperCase()}
                      </div>
                    </div>
                  )}
                  {smc.last_bos && (
                    <div>
                      <div className="text-[10px] text-slate-500 tracking-widest">LAST BOS</div>
                      <div className={smc.last_bos === "bullish" ? "text-emerald-400" : "text-red-400"}>
                        {smc.last_bos.toUpperCase()}
                      </div>
                    </div>
                  )}
                  <div>
                    <div className="text-[10px] text-slate-500 tracking-widest">EVENTS</div>
                    <div className="text-white">{smc.event_count}</div>
                  </div>
                </div>
              </div>

              {/* Key levels */}
              <div className="flex gap-6 text-xs tabular-nums">
                {smc.nearest_fvg_above && (
                  <div className="text-right">
                    <div className="text-[10px] text-slate-500 tracking-widest">FVG ABOVE</div>
                    <div className="text-red-400">${smc.nearest_fvg_above.toFixed(2)}</div>
                  </div>
                )}
                {smc.nearest_ob_above && (
                  <div className="text-right">
                    <div className="text-[10px] text-slate-500 tracking-widest">OB ABOVE</div>
                    <div className="text-red-400">${smc.nearest_ob_above.toFixed(2)}</div>
                  </div>
                )}
                {smc.nearest_ob_below && (
                  <div className="text-right">
                    <div className="text-[10px] text-slate-500 tracking-widest">OB BELOW</div>
                    <div className="text-emerald-400">${smc.nearest_ob_below.toFixed(2)}</div>
                  </div>
                )}
                {smc.nearest_fvg_below && (
                  <div className="text-right">
                    <div className="text-[10px] text-slate-500 tracking-widest">FVG BELOW</div>
                    <div className="text-emerald-400">${smc.nearest_fvg_below.toFixed(2)}</div>
                  </div>
                )}
                {!smc.nearest_fvg_above && !smc.nearest_fvg_below && !smc.nearest_ob_above && !smc.nearest_ob_below && (
                  <div className="text-slate-600 text-xs">No nearby key levels</div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Lower panels */}
        <div className="grid grid-cols-4 gap-3">

          {/* Component scores */}
          {macro && (
            <div className="border border-slate-800 rounded-lg p-4 bg-slate-900/30">
              <div className="text-[10px] text-slate-500 tracking-widest mb-3">COMPONENT SCORES</div>
              <div className="space-y-2.5">
                <ScoreBar label="DXY Weakness"  score={macro.components.dxy} />
                <ScoreBar label="Yield Curve"   score={macro.components.yield_curve} />
                <ScoreBar label="Real Rates"    score={macro.components.real_rates} />
                <ScoreBar label="VIX / Fear"    score={macro.components.vix_fear} />
                <ScoreBar label="SPX Stress"    score={macro.components.spx_momentum} />
                <ScoreBar label="Gold Trend"    score={macro.components.gold_momentum} />
              </div>
            </div>
          )}

          {/* Signals */}
          {macro && (
            <div className="border border-slate-800 rounded-lg p-4 bg-slate-900/30 space-y-3">
              <div className="text-[10px] text-slate-500 tracking-widest">SIGNALS</div>
              {macro.key_signals.length === 0 && macro.risk_factors.length === 0 && (
                <div className="text-slate-600 text-xs">No strong signals detected.</div>
              )}
              {macro.key_signals.map((s, i) => (
                <div key={i} className="flex gap-2 text-xs text-emerald-400">
                  <span className="shrink-0">▲</span>
                  <span className="leading-relaxed">{s}</span>
                </div>
              ))}
              {macro.risk_factors.map((s, i) => (
                <div key={i} className="flex gap-2 text-xs text-red-400">
                  <span className="shrink-0">▼</span>
                  <span className="leading-relaxed">{s}</span>
                </div>
              ))}

              <div className="pt-2 border-t border-slate-800/60">
                <div className="text-[10px] text-slate-500 tracking-widest mb-2">SNAPSHOT</div>
                <div className="space-y-1 text-xs tabular-nums">
                  {[
                    ["Yield Curve", `${macro.snapshot.yield_curve >= 0 ? "+" : ""}${macro.snapshot.yield_curve.toFixed(2)}%`],
                    ["Gold/DXY",   macro.snapshot.gold_dxy_ratio.toFixed(2)],
                    ["XAU/USD",   `$${macro.snapshot.xauusd.toFixed(2)}`],
                    ["DXY",        macro.snapshot.dxy.toFixed(2)],
                  ].map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-slate-600">{k}</span>
                      <span className="text-slate-300">{v}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Volatility panel */}
          {vol && (
            <div className="border border-slate-800 rounded-lg p-4 bg-slate-900/30">
              <div className="text-[10px] text-slate-500 tracking-widest mb-3">VOLATILITY · XAUUSD</div>

              {/* Regime badge */}
              <div className="mb-3">
                <div className={`text-lg font-black tracking-wider ${
                  vol.regime === "compression" ? "text-amber-400" :
                  vol.regime === "expansion"   ? "text-red-400" :
                  vol.regime === "high"        ? "text-red-400" :
                  vol.regime === "low"         ? "text-emerald-400" : "text-slate-300"
                }`}>{vol.regime.toUpperCase()}</div>
                <div className="text-slate-500 text-xs">score {vol.regime_score}</div>
              </div>

              {/* Bar metrics */}
              <div className="space-y-2 mb-3">
                <ScoreBar label="Vol Score"    score={vol.regime_score} />
                <ScoreBar label="Compression"  score={vol.compression_score} />
                <ScoreBar label="Expansion"    score={vol.expansion_score} />
              </div>

              {/* Key metrics */}
              <div className="space-y-1 text-xs tabular-nums border-t border-slate-800/60 pt-2">
                {[
                  ["ATR %",     `${vol.atr_pct.toFixed(3)}%`],
                  ["ATR z",     vol.atr_zscore.toFixed(2)],
                  ["RVol 20",   `${vol.realized_vol_20.toFixed(1)}%`],
                ].map(([k, v]) => (
                  <div key={k} className="flex justify-between">
                    <span className="text-slate-600">{k}</span>
                    <span className="text-slate-300">{v}</span>
                  </div>
                ))}
              </div>

              {/* Signals */}
              {vol.signals.length > 0 && (
                <div className="mt-2 pt-2 border-t border-slate-800/60 space-y-1">
                  {vol.signals.slice(0, 2).map((s, i) => (
                    <div key={i} className="text-[10px] text-amber-400 leading-relaxed">{s}</div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* OHLCV table */}
          <div className="border border-slate-800 rounded-lg overflow-hidden bg-slate-900/30">
            <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800">
              <span className="text-[10px] text-slate-500 tracking-widest">{selected} OHLCV</span>
              <div className="flex gap-1.5">
                {["1h", "4h", "1d"].map((tf) => (
                  <span
                    key={tf}
                    onClick={() => setTf(tf)}
                    className={`px-2 py-0.5 rounded cursor-pointer text-[10px] ${
                      timeframe === tf ? "bg-amber-500/20 text-amber-400 border border-amber-500/30" : "text-slate-600 hover:text-slate-400"
                    }`}
                  >
                    {tf.toUpperCase()}
                  </span>
                ))}
              </div>
            </div>
            <div className="overflow-auto" style={{ maxHeight: "220px" }}>
              <table className="w-full text-xs">
                <thead>
                  <tr className="text-slate-600 text-[10px] bg-slate-900">
                    {["TIME", "OPEN", "HIGH", "LOW", "CLOSE", "CHG%"].map((h) => (
                      <th key={h} className={`px-3 py-1.5 font-normal ${h === "TIME" ? "text-left" : "text-right"}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {candles.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-3 py-4 text-center text-slate-700 text-xs animate-pulse">Loading…</td>
                    </tr>
                  )}
                  {candles.map((c, i) => {
                    const chg = ((c.close - c.open) / c.open) * 100;
                    const bull = c.close >= c.open;
                    return (
                      <tr key={i} className="border-t border-slate-800/40 hover:bg-slate-800/20">
                        <td className="px-3 py-1.5 text-slate-600 tabular-nums">
                          {new Date(c.timestamp).toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit" })}
                        </td>
                        <td className="px-3 py-1.5 text-right text-slate-400 tabular-nums">{c.open.toFixed(2)}</td>
                        <td className="px-3 py-1.5 text-right text-emerald-600 tabular-nums">{c.high.toFixed(2)}</td>
                        <td className="px-3 py-1.5 text-right text-red-600 tabular-nums">{c.low.toFixed(2)}</td>
                        <td className={`px-3 py-1.5 text-right font-bold tabular-nums ${bull ? "text-emerald-400" : "text-red-400"}`}>{c.close.toFixed(2)}</td>
                        <td className={`px-3 py-1.5 text-right tabular-nums ${bull ? "text-emerald-500" : "text-red-500"}`}>
                          {chg >= 0 ? "+" : ""}{chg.toFixed(2)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* News / Fed Stance panel */}
        {news && (
          <div className="border border-slate-800 rounded-lg p-3 bg-slate-900/30">
            <div className="flex items-start justify-between gap-6 flex-wrap">
              <div className="flex items-center gap-6">
                <div>
                  <div className="text-[10px] text-slate-500 tracking-widest mb-1">FED STANCE · NEWS ENGINE</div>
                  <div className={`text-lg font-black tracking-wider ${
                    news.fed_stance === "hawkish" ? "text-red-400" :
                    news.fed_stance === "dovish"  ? "text-emerald-400" :
                                                    "text-slate-300"
                  }`}>{news.fed_stance.toUpperCase()}</div>
                  <div className="text-slate-500 text-xs mt-0.5 tabular-nums">
                    score {news.fed_score} · {news.fed_confidence.toFixed(0)}% conf
                  </div>
                </div>
                <div className="h-8 w-px bg-slate-800" />
                <div className="flex gap-5 text-xs">
                  <div>
                    <div className="text-[10px] text-slate-500 tracking-widest">GOLD BIAS</div>
                    <div className={`font-bold ${biasColor(news.news_gold_bias)}`}>
                      {news.news_gold_bias.toUpperCase()}
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-500 tracking-widest">IMPACT</div>
                    <div className={`font-bold tabular-nums ${scoreColor(100 - news.news_impact_score)}`}>
                      {news.news_impact_score}/100
                    </div>
                  </div>
                  <div>
                    <div className="text-[10px] text-slate-500 tracking-widest">RISK EVENTS</div>
                    <div className={`font-bold tabular-nums ${news.risk_event_count > 2 ? "text-red-400" : "text-slate-300"}`}>
                      {news.risk_event_count}
                    </div>
                  </div>
                </div>
              </div>
              {news.last_major_event && (
                <div className="text-xs text-slate-500 max-w-xs">
                  <span className="text-[10px] text-slate-600 tracking-widest block mb-1">LAST MAJOR</span>
                  {news.last_major_event}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Correlation panel */}
        {corr && (
          <div className="border border-slate-800 rounded-lg p-3 bg-slate-900/30">
            <div className="flex items-start justify-between gap-6 flex-wrap">
              <div className="flex items-center gap-6">
                <div>
                  <div className="text-[10px] text-slate-500 tracking-widest mb-1">CORRELATION REGIME</div>
                  <div className={`text-base font-black tracking-wider ${
                    corr.regime === "breakdown" ? "text-red-400" :
                    corr.regime === "stressed"  ? "text-amber-400" : "text-emerald-400"
                  }`}>{corr.regime.toUpperCase()}</div>
                  <div className="text-slate-500 text-xs mt-0.5">score {corr.regime_score.toFixed(0)} · {corr.breakdown_count} breakdown{corr.breakdown_count !== 1 ? "s" : ""}</div>
                </div>
                <div className="h-8 w-px bg-slate-800" />
                {/* Gold correlation matrix */}
                <div className="flex gap-5 text-xs tabular-nums">
                  {[
                    ["vs DXY",   corr.gold_vs_dxy,   -0.65],
                    ["vs VIX",   corr.gold_vs_vix,   +0.45],
                    ["vs SPX",   corr.gold_vs_spx,   -0.10],
                    ["vs US10Y", corr.gold_vs_us10y,  -0.40],
                  ].map(([label, val, expected]) => {
                    if (val === null || val === undefined) return null;
                    const dev = (val as number) - (expected as number);
                    const isBreakdown = Math.abs(dev) > 0.3;
                    return (
                      <div key={label as string}>
                        <div className="text-[10px] text-slate-500 tracking-widest">GOLD {label}</div>
                        <div className={`font-bold ${
                          isBreakdown ? "text-red-400" :
                          (val as number) > 0.1 ? "text-emerald-400" :
                          (val as number) < -0.1 ? "text-red-400" : "text-slate-400"
                        }`}>{(val as number) >= 0 ? "+" : ""}{(val as number).toFixed(2)}</div>
                        <div className={`text-[10px] ${isBreakdown ? "text-red-600" : "text-slate-600"}`}>
                          exp {(expected as number) >= 0 ? "+" : ""}{(expected as number).toFixed(2)}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div className="text-xs text-slate-500 max-w-sm leading-relaxed">
                {corr.dominant_signal}
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex justify-between text-[10px] text-slate-700 px-1">
          <span>localhost:8000 · Mock Provider · auto-refresh 8s</span>
          {macro && <span>Analysis: {new Date(macro.timestamp).toLocaleTimeString("en-US", { hour12: false })}</span>}
        </div>
      </div>
    </div>
  );
}
