import type { PerformanceTraceReport } from './trace';

export function formatPerformanceReport(
  report: PerformanceTraceReport,
): string {
  const interactive =
    report.timeToInteractiveMs === null
      ? 'not interactive'
      : `${Math.round(report.timeToInteractiveMs)} ms to interactive`;
  return [
    `${(report.durationMs / 1_000).toFixed(1)} s trace`,
    `${report.medianFps.toFixed(1)} median FPS`,
    interactive,
    `${report.frameCount} frames`,
  ].join(' — ');
}
