---
id: at-xmtg
status: open
deps: [at-v8t7]
links: []
created: 2026-02-02T07:02:27Z
type: task
priority: 1
assignee: cdiddy77
parent: at-2kjb
tags: [frontend, state]
---
# Manage outfit selection state

Track current selections for all outfit slots. Implement validation logic. Handle reset functionality. Sync with local storage (at-v8t7).

## Details

### State Shape

```typescript
interface OutfitSelections {
  model: string | null;          // generation ID — REQUIRED
  insideTop: string | null;      // generation ID — optional
  outsideTop: string | null;     // generation ID — optional
  bottoms: string | null;        // generation ID — optional
  shoes: string | null;          // generation ID — optional
  socks: string | null;          // generation ID — optional
  hat: string | null;            // generation ID — optional
}
```

### Validation Rules

- **Model**: Required — must be non-null to enable generation
- **Garments**: At least one of the 6 garment slots must be non-null
- Generate button is disabled unless both conditions are met

### Actions

- **setSlot(slot, generationId)**: Set a specific slot's selection
- **clearSlot(slot)**: Clear a specific slot
- **resetAll()**: Clear all selections
- **isValid()**: Returns true if model + at least one garment selected

### Mapping to Generator Input

The selection state maps directly to `OutfitGeneratorInput` fields:
- `model` → `model_image`
- `insideTop` → `inside_top_image`
- `outsideTop` → `outside_top_image`
- `bottoms` → `bottoms_image`
- `shoes` → `shoes_image`
- `socks` → `socks_image`
- `hat` → `hat_image`

Null values are sent as null (the generator skips them).

## Acceptance Criteria

- [ ] All 7 slots tracked in state (model + 6 garments)
- [ ] Validation: model required + at least one garment required
- [ ] `isValid()` correctly enables/disables generation
- [ ] Reset clears all selections
- [ ] State syncs with local storage (persists across sessions)
- [ ] State maps cleanly to `OutfitGeneratorInput` for at-ii1g
