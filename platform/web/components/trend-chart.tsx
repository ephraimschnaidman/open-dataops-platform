"use client";

import { useState } from "react";

export interface TrendSeries {
    label: string;
    values: Array<number | null>;
    color: string;
}

interface ChartPoint {
    key: string;
    detail: string;
    x: number;
    y: number;
}

export function TrendChart({ labels, series, valueSuffix = "", height = 176, threshold }: { labels: string[]; series: TrendSeries[]; valueSuffix?: string; height?: number; threshold?: { value: number; label: string } }) {
    const [activePoint, setActivePoint] = useState<ChartPoint | null>(null);
    const values = series.flatMap((item) => item.values).filter((value): value is number => value !== null);
    if (threshold) values.push(threshold.value);
    const minimum = values.length ? Math.min(...values) : 0;
    const maximum = values.length ? Math.max(...values) : 1;
    const span = Math.max(1, maximum - minimum);
    const x = (index: number, length: number) => length === 1 ? 50 : (index / (length - 1)) * 100;
    const y = (value: number) => 88 - ((value - minimum) / span) * 72;
    const segments = (items: Array<number | null>) => items.reduce<Array<Array<{ value: number; index: number }>>>((groups, value, index) => {
        if (value === null) return [...groups, []];
        const last = groups.at(-1);
        if (!last) return [[{ value, index }]];
        last.push({ value, index });
        return groups;
    }, [[]]).filter((group) => group.length);
    const thresholdY = threshold ? y(threshold.value) : null;
    const points = series.flatMap((item) => item.values.flatMap((value, index): ChartPoint[] => {
        if (value === null) return [];
        const label = labels[index] ?? `Point ${index + 1}`;
        const detail = `${label} · ${item.label}: ${value}${valueSuffix}${threshold ? ` · ${threshold.label}` : ""}`;
        return [{ key: `${item.label}-point-${index}`, detail, x: x(index, item.values.length), y: y(value) }];
    }));
    const tooltipTransform = activePoint && activePoint.x < 15 ? "translate(0, -100%)" : activePoint && activePoint.x > 85 ? "translate(-100%, -100%)" : "translate(-50%, -100%)";

    return <div><div className="mb-3 flex flex-wrap gap-4">{series.map((item) => <span key={item.label} className="inline-flex items-center gap-1.5 text-[11px] text-zinc-500"><span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />{item.label}</span>)}{threshold && <span className="inline-flex items-center gap-1.5 text-[11px] text-zinc-500"><span className="w-3 border-t border-dashed border-zinc-400" />{threshold.label}</span>}</div><div className="relative w-full" style={{ height }}><svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-full w-full overflow-visible" role="img" aria-label={series.map((item) => `${item.label}: ${item.values.at(-1) ?? "no data"}${valueSuffix}`).join(", ")} onPointerLeave={() => setActivePoint(null)}><line x1="0" y1="16" x2="100" y2="16" stroke="#e4e4e7" strokeWidth="0.5" /><line x1="0" y1="52" x2="100" y2="52" stroke="#e4e4e7" strokeWidth="0.5" /><line x1="0" y1="88" x2="100" y2="88" stroke="#e4e4e7" strokeWidth="0.5" />{thresholdY !== null && <line x1="0" y1={thresholdY} x2="100" y2={thresholdY} stroke="#a1a1aa" strokeWidth="1" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />}{series.flatMap((item) => segments(item.values).map((segment, segmentIndex) => <polyline key={`${item.label}-${segmentIndex}`} points={segment.map((point) => `${x(point.index, item.values.length)},${y(point.value)}`).join(" ")} fill="none" stroke={item.color} strokeWidth="2" vectorEffect="non-scaling-stroke" strokeLinecap="round" strokeLinejoin="round" />))}{series.flatMap((item) => item.values.flatMap((value, index) => { if (value === null) return []; const point = points.find((candidate) => candidate.key === `${item.label}-point-${index}`)!; const active = activePoint?.key === point.key; return [<g key={point.key}><circle cx={point.x} cy={point.y} r="4" fill={active ? item.color : "transparent"} fillOpacity={active ? "0.14" : "0"} stroke={active ? item.color : "transparent"} strokeWidth="0.6" vectorEffect="non-scaling-stroke" tabIndex={0} aria-label={point.detail} onPointerEnter={() => setActivePoint(point)} onFocus={() => setActivePoint(point)} onBlur={() => setActivePoint(null)} className="cursor-crosshair outline-none" /><circle cx={point.x} cy={point.y} r="1.25" fill={item.color} vectorEffect="non-scaling-stroke" aria-hidden="true" /></g>]; }))}</svg>{activePoint && <div role="tooltip" className="pointer-events-none absolute z-10 max-w-64 whitespace-nowrap rounded-md bg-zinc-900 px-2.5 py-1.5 text-[10px] font-medium text-white shadow-panel" style={{ left: `${activePoint.x}%`, top: `${activePoint.y}%`, transform: tooltipTransform }}>{activePoint.detail}</div>}</div><div className="mt-2 flex justify-between gap-2 text-[10px] text-zinc-400">{labels.map((label) => <span key={label} className="truncate">{label}</span>)}</div></div>;
}
