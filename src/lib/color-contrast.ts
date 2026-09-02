const hexToRgb = (hex: string): [number, number, number] => {
  const normalized = hex.replace("#", "");
  if (!/^[0-9a-f]{6}$/i.test(normalized)) throw new Error(`Unsupported color: ${hex}`);
  return [0, 2, 4].map((offset) => Number.parseInt(normalized.slice(offset, offset + 2), 16)) as [number, number, number];
};

const linearChannel = (channel: number) => {
  const value = channel / 255;
  return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
};

export const relativeLuminance = (hex: string) => {
  const [red, green, blue] = hexToRgb(hex).map(linearChannel);
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
};

export const contrastRatio = (left: string, right: string) => {
  const [lighter, darker] = [relativeLuminance(left), relativeLuminance(right)].sort((a, b) => b - a);
  return (lighter + 0.05) / (darker + 0.05);
};

export const contrastingTextColor = (background: string, light = "#f8faf6", dark = "#10140f") =>
  contrastRatio(background, light) >= contrastRatio(background, dark) ? light : dark;
