export interface TrendSeries {
    label: string;
    values: number[];
    color: string;
}

export function TrendChart({ labels, series, valueSuffix = "", height = 176 }: { labels: string[]; series: TrendSeries[]; valueSuffix?: string; height?: number }) {
    const values = series.flatMap((item) => item.values);
    const minimum = Math.min(...values);
    const maximum = Math.max(...values);
    const span = Math.max(1, maximum - minimum);
    const points = (items: number[]) => items.map((value, index) => `${items.length === 1 ? 50 : (index / (items.length - 1)) * 100},${88 - ((value - minimum) / span) * 72}`).join(" ");
    return <div><div className="mb-3 flex flex-wrap gap-4">{series.map((item) => <span key={item.label} className="inline-flex items-center gap-1.5 text-[11px] text-zinc-500"><span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />{item.label}</span>)}</div><div className="relative w-full" style={{ height }}><svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-full w-full overflow-visible" role="img" aria-label={series.map((item) => `${item.label}: ${item.values.at(-1)}${valueSuffix}`).join(", ")}><line x1="0" y1="16" x2="100" y2="16" stroke="#e4e4e7" strokeWidth="0.5" /><line x1="0" y1="52" x2="100" y2="52" stroke="#e4e4e7" strokeWidth="0.5" /><line x1="0" y1="88" x2="100" y2="88" stroke="#e4e4e7" strokeWidth="0.5" />{series.map((item) => <polyline key={item.label} points={points(item.values)} fill="none" stroke={item.color} strokeWidth="2" vectorEffect="non-scaling-stroke" strokeLinecap="round" strokeLinejoin="round" />)}</svg></div><div className="mt-2 flex justify-between gap-2 text-[10px] text-zinc-400">{labels.map((label) => <span key={label} className="truncate">{label}</span>)}</div></div>;
}
