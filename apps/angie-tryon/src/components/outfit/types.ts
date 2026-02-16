export type SlotType =
  | "model"
  | "insideTop"
  | "outsideTop"
  | "bottoms"
  | "shoes"
  | "socks"
  | "hat";

export interface SlotValue {
  id: string;
  name: string;
  thumbnailUrl: string;
}

export const SLOT_CONFIGS: { type: SlotType; label: string }[] = [
  { type: "model", label: "Model" },
  { type: "insideTop", label: "Inside Top" },
  { type: "outsideTop", label: "Outside Top" },
  { type: "bottoms", label: "Bottoms" },
  { type: "shoes", label: "Shoes" },
  { type: "socks", label: "Socks" },
  { type: "hat", label: "Hat" },
];
