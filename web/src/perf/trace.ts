export interface PerformanceTraceOptions {
  isInteractive: () => boolean;
  durationMs?: number;
  now?: () => number;
  requestFrame?: (callback: FrameRequestCallback) => number;
}

export interface PerformanceTraceReport {
  durationMs: number;
  frameCount: number;
  medianFps: number;
  timeToInteractiveMs: number | null;
}

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((first, second) => first - second);
  const middle = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 1) return sorted[middle] ?? 0;
  return ((sorted[middle - 1] ?? 0) + (sorted[middle] ?? 0)) / 2;
}

export async function runPerformanceTrace(
  options: PerformanceTraceOptions,
): Promise<PerformanceTraceReport> {
  const durationMs = options.durationMs ?? 30_000;
  if (durationMs <= 0) throw new Error('Trace duration must be positive.');
  const now = options.now ?? performance.now.bind(performance);
  const requestFrame = options.requestFrame ?? globalThis.requestAnimationFrame;
  if (!requestFrame) throw new Error('Animation frames are unavailable.');

  const startedAt = now();
  const frameTimes: number[] = [];
  let interactiveAt: number | null = options.isInteractive() ? startedAt : null;

  await new Promise<void>((resolve) => {
    const frame = (): void => {
      const current = now();
      frameTimes.push(current);
      if (interactiveAt === null && options.isInteractive())
        interactiveAt = current;
      if (current - startedAt >= durationMs) resolve();
      else requestFrame(frame);
    };
    requestFrame(frame);
  });

  const buckets = new Map<number, number>();
  for (const time of frameTimes) {
    const bucket = Math.min(
      Math.floor((time - startedAt) / 1_000),
      Math.ceil(durationMs / 1_000) - 1,
    );
    buckets.set(bucket, (buckets.get(bucket) ?? 0) + 1);
  }

  return {
    durationMs,
    frameCount: frameTimes.length,
    medianFps: median([...buckets.values()]),
    timeToInteractiveMs:
      interactiveAt === null ? null : Math.max(0, interactiveAt - startedAt),
  };
}
