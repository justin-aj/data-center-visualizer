export const sceneStyle = {
  sky: '#dce7ef',
  ground: '#eee8dc',
  contextBuilding: '#aaa39a',
  contextOutline: '#413d38',
  openSpace: '#789476',
  road: '#c7ad86',
  water: '#668da8',
  proposal: '#9f5638',
  proposalOutline: '#48271b',
  shadow: '#647383',
  uiText: '#1e2a31',
  uiSurface: '#f7f3ea',
  focus: '#174f78',
  badgeText: '#fffaf2',
} as const;

function linearChannel(channel: number): number {
  const srgb = channel / 255;
  return srgb <= 0.04045 ? srgb / 12.92 : ((srgb + 0.055) / 1.055) ** 2.4;
}

export function relativeLuminance(hex: string): number {
  if (!/^#[\da-f]{6}$/i.test(hex)) {
    throw new Error(`Expected a six-digit hex color, received "${hex}".`);
  }

  const channels = [
    Number.parseInt(hex.slice(1, 3), 16),
    Number.parseInt(hex.slice(3, 5), 16),
    Number.parseInt(hex.slice(5, 7), 16),
  ];

  const [red = 0, green = 0, blue = 0] = channels.map(linearChannel);
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

export function contrastRatio(first: string, second: string): number {
  const firstLuminance = relativeLuminance(first);
  const secondLuminance = relativeLuminance(second);
  const lighter = Math.max(firstLuminance, secondLuminance);
  const darker = Math.min(firstLuminance, secondLuminance);
  return (lighter + 0.05) / (darker + 0.05);
}
