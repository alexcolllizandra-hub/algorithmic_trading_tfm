"use client";

import { createChart, ColorType, type IChartApi, type UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef } from "react";

import { useChartColors } from "@/components/charts/theme";
import type { OhlcvBar } from "@/lib/api-types";

export function CandlestickChart({ bars }: { bars: OhlcvBar[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const c = useChartColors();

  useEffect(() => {
    if (!ref.current) return;
    const chart = createChart(ref.current, {
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: c.axis,
      },
      grid: { vertLines: { color: c.grid }, horzLines: { color: c.grid } },
      rightPriceScale: { borderColor: c.grid },
      timeScale: { borderColor: c.grid, timeVisible: true },
      autoSize: true,
    });
    chartRef.current = chart;
    const series = chart.addCandlestickSeries({
      upColor: c.positive,
      downColor: c.negative,
      borderUpColor: c.positive,
      borderDownColor: c.negative,
      wickUpColor: c.positive,
      wickDownColor: c.negative,
    });
    series.setData(
      bars.map((b) => ({
        time: (Date.parse(b.open_time) / 1000) as UTCTimestamp,
        open: b.open,
        high: b.high,
        low: b.low,
        close: b.close,
      }))
    );
    chart.timeScale().fitContent();
    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [bars, c]);

  return <div ref={ref} className="h-[420px] w-full" />;
}
