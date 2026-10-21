import { Item, ItemCategory } from "../types/item";
import { OutfitItem } from "../types/outfit";

// Where a category sits on the canvas by default (item center, 0..1) and its
// layer. The editor (plan 06) lets users move things; this is the start.
const SLOTS: Record<ItemCategory | "other", { x: number; y: number; z: number; scale: number }> = {
  outerwear: { x: 0.5, y: 0.3, z: 3, scale: 1.15 },
  top: { x: 0.5, y: 0.28, z: 2, scale: 1 },
  dress: { x: 0.5, y: 0.42, z: 2, scale: 1.3 },
  bottom: { x: 0.5, y: 0.6, z: 1, scale: 1.05 },
  shoes: { x: 0.5, y: 0.88, z: 0, scale: 0.6 },
  accessory: { x: 0.82, y: 0.14, z: 4, scale: 0.45 },
  other: { x: 0.18, y: 0.5, z: 0, scale: 0.6 },
};

// Spreads items that share a slot side by side.
export function defaultLayout(items: Item[]): OutfitItem[] {
  const perSlot: Record<string, number> = {};
  return items.map((item) => {
    const slotName = item.categories[0] ?? "other";
    const slot = SLOTS[slotName];
    const n = perSlot[slotName] ?? 0;
    perSlot[slotName] = n + 1;
    const dx = n === 0 ? 0 : (n % 2 === 1 ? 1 : -1) * Math.ceil(n / 2) * 0.22;
    return {
      item_id: item._id,
      z_index: slot.z,
      transform: {
        translate: { x: Math.min(0.9, Math.max(0.1, slot.x + dx)), y: slot.y },
        scale: { x: slot.scale, y: slot.scale },
        rotation: 0,
        flip_horizontal: false,
        flip_vertical: false,
      },
      visible: true,
      opacity: 1,
    };
  });
}
