# Building Generator UIs

The Boards toolkit provides utilities for building dynamic UIs that adapt to each generator's input schema. This guide shows how to use `useGenerators()` and the schema parsing utilities to create custom generator interfaces.

## Overview

Every generator ships with a JSON Schema describing its input parameters. The toolkit provides:

1. **`useGenerators()`** - Hook to fetch available generators with their schemas
2. **`parseGeneratorSchema()`** - Utility to parse JSON Schema into structured data
3. **TypeScript types** - Full type definitions for all schema field types

This enables you to build UIs that automatically adapt to any generator's requirements.

## Using useGenerators()

The `useGenerators()` hook fetches all available generators:

```typescript
import { useGenerators } from "@weirdfingers/boards";

function MyGeneratorPicker() {
  const { generators, loading, error } = useGenerators();

  if (loading) return <div>Loading generators...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <div>
      {generators.map((gen) => (
        <div key={gen.name}>
          <h3>{gen.name}</h3>
          <p>{gen.description}</p>
          <p>Artifact type: {gen.artifactType}</p>
        </div>
      ))}
    </div>
  );
}
```

### Generator Type

Each generator has the following structure:

```typescript
interface Generator {
  name: string;              // Unique generator identifier
  description: string;       // Human-readable description
  artifactType: ArtifactType; // "image" | "video" | "audio" | "text"
  inputSchema: JSONSchema7;   // JSON Schema for input parameters
}
```

### Filtering by Artifact Type

You can filter generators by the type of artifact they produce:

```typescript
const { generators } = useGenerators({ artifactType: "image" });
```

## Parsing Input Schemas

The `parseGeneratorSchema()` utility transforms JSON Schema into structured data for UI rendering:

```typescript
import { parseGeneratorSchema } from "@weirdfingers/boards";

const generator = generators[0];
const parsed = parseGeneratorSchema(generator.inputSchema);

console.log(parsed);
// {
//   artifactSlots: [...],   // Artifact input slots
//   promptField: {...},     // Prompt field (if present)
//   settingsFields: [...]   // Additional settings
// }
```

### Parsed Schema Structure

```typescript
interface ParsedGeneratorSchema {
  artifactSlots: ArtifactSlot[];
  promptField: PromptField | null;
  settingsFields: SettingsField[];
}
```

## Rendering Artifact Slots

Artifact slots let users select existing artifacts from their board as inputs:

```typescript
import { parseGeneratorSchema, type ArtifactSlot } from "@weirdfingers/boards";

function ArtifactSlotRenderer({ slot }: { slot: ArtifactSlot }) {
  return (
    <div>
      <label>
        {slot.name}
        {slot.required && <span>*</span>}
      </label>
      {slot.description && <p>{slot.description}</p>}

      {slot.isArray ? (
        <div>
          Select {slot.minItems || 1} to {slot.maxItems || "any"}{" "}
          {slot.artifactType} files
        </div>
      ) : (
        <div>Select a {slot.artifactType} file</div>
      )}
    </div>
  );
}
```

### ArtifactSlot Type

```typescript
interface ArtifactSlot {
  name: string;                                    // Display name
  fieldName: string;                               // Form field name
  artifactType: "audio" | "video" | "image" | "text";
  required: boolean;
  description?: string;
  isArray: boolean;                                // Multiple artifacts?
  minItems?: number;                               // Min array length
  maxItems?: number;                               // Max array length
}
```

### Complete Artifact Slot Example

```typescript
function ArtifactInputSlots({
  slots,
  selectedArtifacts,
  availableArtifacts,
  onSelectArtifact,
}: {
  slots: ArtifactSlot[];
  selectedArtifacts: Map<string, Artifact>;
  availableArtifacts: Artifact[];
  onSelectArtifact: (fieldName: string, artifact: Artifact | null) => void;
}) {
  return (
    <div>
      {slots.map((slot) => (
        <div key={slot.fieldName}>
          <label>
            {slot.name}
            {slot.required && <span className="required">*</span>}
          </label>

          {slot.description && (
            <p className="description">{slot.description}</p>
          )}

          {/* Filter available artifacts by type */}
          <select
            value={selectedArtifacts.get(slot.fieldName)?.id || ""}
            onChange={(e) => {
              const artifact = availableArtifacts.find(
                (a) => a.id === e.target.value
              );
              onSelectArtifact(slot.fieldName, artifact || null);
            }}
            required={slot.required}
          >
            <option value="">
              Select {slot.artifactType}...
            </option>
            {availableArtifacts
              .filter((a) => a.artifactType === slot.artifactType)
              .map((artifact) => (
                <option key={artifact.id} value={artifact.id}>
                  {artifact.id}
                </option>
              ))}
          </select>
        </div>
      ))}
    </div>
  );
}
```

## Rendering Prompt Field

The prompt field is a special text input for generation instructions:

```typescript
function PromptInput({ promptField }: { promptField: PromptField | null }) {
  if (!promptField) return null;

  return (
    <div>
      <textarea
        placeholder={promptField.description || "Enter your prompt..."}
        required={promptField.required}
        defaultValue={promptField.default}
      />
    </div>
  );
}
```

### PromptField Type

```typescript
interface PromptField {
  fieldName: string;      // Usually "prompt"
  description?: string;
  required: boolean;
  default?: string;
}
```

## Rendering Settings Fields

Settings fields include sliders, dropdowns, text inputs, and number inputs:

```typescript
import type { SettingsField } from "@weirdfingers/boards";

function SettingsPanel({ fields }: { fields: SettingsField[] }) {
  return (
    <div>
      {fields.map((field) => (
        <div key={field.fieldName}>
          {field.type === "slider" && <SliderInput field={field} />}
          {field.type === "dropdown" && <DropdownInput field={field} />}
          {field.type === "text" && <TextInput field={field} />}
          {field.type === "number" && <NumberInput field={field} />}
        </div>
      ))}
    </div>
  );
}
```

### Slider Field

```typescript
import type { SliderField } from "@weirdfingers/boards";

function SliderInput({ field }: { field: SliderField }) {
  return (
    <div>
      <label>{field.title}</label>
      {field.description && <p>{field.description}</p>}

      <input
        type="range"
        min={field.min}
        max={field.max}
        step={field.step || (field.isInteger ? 1 : 0.01)}
        defaultValue={field.default || field.min}
      />
    </div>
  );
}

// SliderField type:
interface SliderField {
  type: "slider";
  fieldName: string;
  title: string;
  description?: string;
  min: number;
  max: number;
  step?: number;
  default?: number;
  isInteger: boolean;
}
```

### Dropdown Field

```typescript
import type { DropdownField } from "@weirdfingers/boards";

function DropdownInput({ field }: { field: DropdownField }) {
  return (
    <div>
      <label>{field.title}</label>
      {field.description && <p>{field.description}</p>}

      <select defaultValue={field.default || field.options[0]}>
        {field.options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </div>
  );
}

// DropdownField type:
interface DropdownField {
  type: "dropdown";
  fieldName: string;
  title: string;
  description?: string;
  options: string[];
  default?: string;
}
```

### Text Input Field

```typescript
import type { TextInputField } from "@weirdfingers/boards";

function TextInput({ field }: { field: TextInputField }) {
  return (
    <div>
      <label>{field.title}</label>
      {field.description && <p>{field.description}</p>}

      <input
        type="text"
        defaultValue={field.default || ""}
        pattern={field.pattern}
      />
    </div>
  );
}

// TextInputField type:
interface TextInputField {
  type: "text";
  fieldName: string;
  title: string;
  description?: string;
  default?: string;
  pattern?: string;  // Regex pattern for validation
}
```

### Number Input Field

```typescript
import type { NumberInputField } from "@weirdfingers/boards";

function NumberInput({ field }: { field: NumberInputField }) {
  return (
    <div>
      <label>{field.title}</label>
      {field.description && <p>{field.description}</p>}

      <input
        type="number"
        defaultValue={field.default}
        min={field.min}
        max={field.max}
        step={field.isInteger ? 1 : "any"}
      />
    </div>
  );
}

// NumberInputField type:
interface NumberInputField {
  type: "number";
  fieldName: string;
  title: string;
  description?: string;
  default?: number;
  min?: number;
  max?: number;
  isInteger: boolean;
}
```

## Complete Example

Here's a full example of a generator input component:

```typescript
"use client";

import { useState, useMemo } from "react";
import { parseGeneratorSchema, useGenerators } from "@weirdfingers/boards";

export function GeneratorInput() {
  const { generators, loading } = useGenerators();
  const [selectedGenerator, setSelectedGenerator] = useState(generators[0]);
  const [formData, setFormData] = useState({});

  // Parse the selected generator's schema
  const parsedSchema = useMemo(() => {
    if (!selectedGenerator) return null;
    return parseGeneratorSchema(selectedGenerator.inputSchema);
  }, [selectedGenerator]);

  if (loading) return <div>Loading...</div>;
  if (!parsedSchema) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Submitting:", formData);
    // Submit to your generation API
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Generator selector */}
      <select
        value={selectedGenerator?.name}
        onChange={(e) =>
          setSelectedGenerator(
            generators.find((g) => g.name === e.target.value) || null
          )
        }
      >
        {generators.map((gen) => (
          <option key={gen.name} value={gen.name}>
            {gen.description}
          </option>
        ))}
      </select>

      {/* Artifact slots */}
      {parsedSchema.artifactSlots.map((slot) => (
        <div key={slot.fieldName}>
          <label>
            {slot.name}
            {slot.required && "*"}
          </label>
          {slot.description && <p>{slot.description}</p>}
          {/* Your artifact selector UI here */}
        </div>
      ))}

      {/* Prompt field */}
      {parsedSchema.promptField && (
        <div>
          <textarea
            placeholder={parsedSchema.promptField.description}
            required={parsedSchema.promptField.required}
            onChange={(e) =>
              setFormData({
                ...formData,
                [parsedSchema.promptField!.fieldName]: e.target.value,
              })
            }
          />
        </div>
      )}

      {/* Settings */}
      {parsedSchema.settingsFields.length > 0 && (
        <details>
          <summary>Settings</summary>
          {parsedSchema.settingsFields.map((field) => (
            <div key={field.fieldName}>
              {field.type === "slider" && (
                <>
                  <label>{field.title}</label>
                  <input
                    type="range"
                    min={field.min}
                    max={field.max}
                    step={field.step || 0.01}
                    defaultValue={field.default || field.min}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        [field.fieldName]: parseFloat(e.target.value),
                      })
                    }
                  />
                </>
              )}
              {field.type === "dropdown" && (
                <>
                  <label>{field.title}</label>
                  <select
                    defaultValue={field.default}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        [field.fieldName]: e.target.value,
                      })
                    }
                  >
                    {field.options.map((opt) => (
                      <option key={opt} value={opt}>
                        {opt}
                      </option>
                    ))}
                  </select>
                </>
              )}
            </div>
          ))}
        </details>
      )}

      <button type="submit">Generate</button>
    </form>
  );
}
```

## Generator Selection Context

The `GeneratorSelectionProvider` is a React context that manages generator selection state across your application. This eliminates prop drilling and provides helpful utilities for checking artifact compatibility.

### Why Use Generator Selection Context?

When building complex UIs with multiple components that need to know about the currently selected generator (e.g., artifact grids, input forms, validation), passing props through every component becomes unwieldy. The context provides:

1. **Shared state** - Selected generator accessible anywhere in the tree
2. **Parsed schema** - Automatically parses the generator's input schema
3. **Compatibility helpers** - Check if artifacts can be used with the selected generator
4. **No prop drilling** - Access generator state without passing props through intermediate components

### Setting Up the Provider

Wrap your application (or a section of it) with the `GeneratorSelectionProvider`:

```typescript
import { GeneratorSelectionProvider } from "@weirdfingers/boards";

export default function BoardPage() {
  return (
    <GeneratorSelectionProvider>
      <GeneratorSelector />
      <ArtifactGrid />
      <GenerationInput />
    </GeneratorSelectionProvider>
  );
}
```

### Using the Hook

Access the generator selection context with the `useGeneratorSelection()` hook:

```typescript
import { useGeneratorSelection } from "@weirdfingers/boards";

function MyComponent() {
  const {
    selectedGenerator,
    setSelectedGenerator,
    parsedSchema,
    artifactSlots,
    canArtifactBeAdded,
  } = useGeneratorSelection();

  if (!selectedGenerator) {
    return <div>No generator selected</div>;
  }

  return (
    <div>
      <h2>{selectedGenerator.name}</h2>
      <p>Requires {artifactSlots.length} artifact inputs</p>
    </div>
  );
}
```

### Context API Reference

#### `selectedGenerator`

The currently selected generator, or `null` if none is selected.

```typescript
selectedGenerator: GeneratorInfo | null
```

#### `setSelectedGenerator`

Function to update the selected generator.

```typescript
setSelectedGenerator: (generator: GeneratorInfo | null) => void

// Example usage:
const handleSelect = (generator: GeneratorInfo) => {
  setSelectedGenerator(generator);
};
```

#### `parsedSchema`

The parsed input schema of the selected generator, or `null` if no generator is selected.

```typescript
parsedSchema: ParsedGeneratorSchema | null

// Access artifact slots, prompt field, and settings:
if (parsedSchema) {
  console.log(parsedSchema.artifactSlots);
  console.log(parsedSchema.promptField);
  console.log(parsedSchema.settingsFields);
}
```

#### `artifactSlots`

Convenient access to just the artifact slots from the parsed schema.

```typescript
artifactSlots: ArtifactSlotInfo[]

// Each slot contains:
interface ArtifactSlotInfo {
  fieldName: string;
  artifactType: string;
  required: boolean;
}
```

#### `canArtifactBeAdded`

Helper function to check if an artifact type can be added to any **available (empty)** slot in the selected generator's inputs. Returns `false` if all compatible slots are already filled.

```typescript
canArtifactBeAdded: (artifactType: string) => boolean

// Example usage:
const imageArtifact = { artifactType: "image", /* ... */ };
const canAdd = canArtifactBeAdded(imageArtifact.artifactType);

if (canAdd) {
  console.log("This artifact can be added to an empty slot");
} else {
  console.log("No compatible slots available or all slots are full");
}
```

This method checks both:
- Whether the generator has slots accepting this artifact type
- Whether at least one compatible slot is empty (not already filled)

#### `selectedArtifacts`

Map of currently selected artifacts for the generator's input slots. Keys are slot field names, values are `Artifact` objects.

```typescript
selectedArtifacts: Map<string, Artifact>

// Artifact interface:
interface Artifact {
  id: string;
  artifactType: string;
  storageUrl?: string | null;
  thumbnailUrl?: string | null;
}

// Example usage:
const videoSlotArtifact = selectedArtifacts.get("video");
if (videoSlotArtifact) {
  console.log("Video artifact selected:", videoSlotArtifact.id);
}
```

#### `setSelectedArtifacts`

Function to update the entire artifacts map. Useful for bulk updates or clearing selections.

```typescript
setSelectedArtifacts: (artifacts: Map<string, Artifact>) => void

// Example usage:
const newArtifacts = new Map(selectedArtifacts);
newArtifacts.set("audio", audioArtifact);
setSelectedArtifacts(newArtifacts);
```

#### `addArtifactToSlot`

Automatically adds an artifact to the first compatible empty slot. Returns `true` if successful, `false` if no compatible slot was found.

```typescript
addArtifactToSlot: (artifact: Artifact) => boolean

// Example usage:
const artifact = {
  id: "123",
  artifactType: "IMAGE",
  storageUrl: "https://...",
  thumbnailUrl: "https://...",
};

const success = addArtifactToSlot(artifact);
if (success) {
  console.log("Artifact added to compatible slot");
} else {
  console.log("No compatible slots available");
}
```

This method:
- Finds the first empty slot that accepts the artifact's type
- Case-insensitive type matching (e.g., "IMAGE" matches "image")
- Returns `false` if all compatible slots are full or no compatible slots exist

#### `removeArtifactFromSlot`

Removes an artifact from a specific slot by field name.

```typescript
removeArtifactFromSlot: (slotName: string) => void

// Example usage:
removeArtifactFromSlot("video"); // Removes artifact from "video" slot
```

#### `clearAllArtifacts`

Clears all selected artifacts from all slots.

```typescript
clearAllArtifacts: () => void

// Example usage:
clearAllArtifacts(); // Removes all artifact selections
```

**Note:** Artifacts are automatically cleared when the selected generator changes to prevent invalid state.

### Complete Integration Example

Here's how to integrate the context across multiple components:

#### Generator Selector Component

```typescript
import { useGeneratorSelection } from "@weirdfingers/boards";

function GeneratorSelector({ generators }: { generators: GeneratorInfo[] }) {
  const { selectedGenerator, setSelectedGenerator } = useGeneratorSelection();

  return (
    <select
      value={selectedGenerator?.name || ""}
      onChange={(e) => {
        const generator = generators.find((g) => g.name === e.target.value);
        setSelectedGenerator(generator || null);
      }}
    >
      <option value="">Select a generator...</option>
      {generators.map((gen) => (
        <option key={gen.name} value={gen.name}>
          {gen.description}
        </option>
      ))}
    </select>
  );
}
```

#### Artifact Grid with Compatibility Checking

```typescript
import { useGeneratorSelection } from "@weirdfingers/boards";

function ArtifactGrid({ artifacts }: { artifacts: Artifact[] }) {
  const { canArtifactBeAdded, addArtifactToSlot } = useGeneratorSelection();

  const handleAddArtifact = (artifact: Artifact) => {
    const success = addArtifactToSlot(artifact);
    if (success) {
      // Optionally scroll to the generation input to show the user
      const inputElement = document.querySelector('.generation-input');
      inputElement?.scrollIntoView({ behavior: 'smooth' });
    } else {
      alert("No compatible slots available");
    }
  };

  return (
    <div className="grid">
      {artifacts.map((artifact) => {
        const isCompatible = canArtifactBeAdded(artifact.artifactType);

        return (
          <div
            key={artifact.id}
            className={isCompatible ? "compatible" : "incompatible"}
          >
            <img src={artifact.thumbnailUrl} alt="" />
            {isCompatible && (
              <button onClick={() => handleAddArtifact(artifact)}>
                Add to generator inputs
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}
```

#### Generation Input Form

```typescript
import { useGeneratorSelection } from "@weirdfingers/boards";

function GenerationInputForm() {
  const {
    selectedGenerator,
    parsedSchema,
    artifactSlots,
    selectedArtifacts,
    setSelectedArtifacts,
    removeArtifactFromSlot,
  } = useGeneratorSelection();

  if (!selectedGenerator || !parsedSchema) {
    return <div>Select a generator to begin</div>;
  }

  const handleSelectArtifact = (slotName: string, artifact: Artifact | null) => {
    const newArtifacts = new Map(selectedArtifacts);
    if (artifact) {
      newArtifacts.set(slotName, artifact);
    } else {
      newArtifacts.delete(slotName);
    }
    setSelectedArtifacts(newArtifacts);
  };

  return (
    <form>
      {/* Render artifact input slots */}
      {artifactSlots.map((slot) => {
        const artifact = selectedArtifacts.get(slot.fieldName);

        return (
          <div key={slot.fieldName}>
            <label>
              {slot.fieldName} ({slot.artifactType})
              {slot.required && <span>*</span>}
            </label>

            {artifact ? (
              <div>
                <img src={artifact.thumbnailUrl || artifact.storageUrl} alt="" />
                <button
                  type="button"
                  onClick={() => removeArtifactFromSlot(slot.fieldName)}
                >
                  Remove
                </button>
              </div>
            ) : (
              <div>No {slot.artifactType.toLowerCase()} selected</div>
            )}
          </div>
        );
      })}

      {/* Render prompt field */}
      {parsedSchema.promptField && (
        <textarea
          placeholder={parsedSchema.promptField.description}
          required={parsedSchema.promptField.required}
        />
      )}

      {/* Render settings */}
      {parsedSchema.settingsFields.map((field) => (
        <div key={field.fieldName}>
          {/* Render field based on type */}
        </div>
      ))}

      <button type="submit">Generate {selectedGenerator.artifactType}</button>
    </form>
  );
}
```

### Benefits in Complex UIs

The context is especially valuable when building:

- **Multi-section layouts** - Generator selector in header, inputs in sidebar, artifacts in main area
- **Drag-and-drop interfaces** - Check compatibility when dragging artifacts to input slots
- **Dynamic form validation** - Validate based on currently selected generator's requirements
- **Conditional UI elements** - Show/hide features based on generator capabilities

### TypeScript Support

All context types are fully typed:

```typescript
import type {
  GeneratorInfo,
  GeneratorSelectionContextValue,
  ArtifactSlotInfo,
  Artifact,
} from "@weirdfingers/boards";

// Context value type:
interface GeneratorSelectionContextValue {
  selectedGenerator: GeneratorInfo | null;
  setSelectedGenerator: (generator: GeneratorInfo | null) => void;
  parsedSchema: ParsedGeneratorSchema | null;
  artifactSlots: ArtifactSlotInfo[];
  canArtifactBeAdded: (artifactType: string) => boolean;
  selectedArtifacts: Map<string, Artifact>;
  setSelectedArtifacts: (artifacts: Map<string, Artifact>) => void;
  addArtifactToSlot: (artifact: Artifact) => boolean;
  removeArtifactFromSlot: (slotName: string) => void;
  clearAllArtifacts: () => void;
}
```

## Form Validation

Use the schema information to validate form inputs:

```typescript
function validateForm(
  parsedSchema: ParsedGeneratorSchema,
  formData: Record<string, unknown>,
  selectedArtifacts: Map<string, Artifact>
): string[] {
  const errors: string[] = [];

  // Check required artifact slots
  for (const slot of parsedSchema.artifactSlots) {
    if (slot.required && !selectedArtifacts.has(slot.fieldName)) {
      errors.push(`${slot.name} is required`);
    }

    // Check array constraints
    if (slot.isArray) {
      const artifacts = selectedArtifacts.get(slot.fieldName);
      if (Array.isArray(artifacts)) {
        if (slot.minItems && artifacts.length < slot.minItems) {
          errors.push(
            `${slot.name} requires at least ${slot.minItems} items`
          );
        }
        if (slot.maxItems && artifacts.length > slot.maxItems) {
          errors.push(`${slot.name} allows at most ${slot.maxItems} items`);
        }
      }
    }
  }

  // Check required prompt
  if (parsedSchema.promptField?.required) {
    const promptValue = formData[parsedSchema.promptField.fieldName];
    if (!promptValue || String(promptValue).trim() === "") {
      errors.push("Prompt is required");
    }
  }

  return errors;
}
```

## TypeScript Support

All types are exported from `@weirdfingers/boards`:

```typescript
import type {
  Generator,
  JSONSchema7,
  ParsedGeneratorSchema,
  ArtifactSlot,
  PromptField,
  SettingsField,
  SliderField,
  DropdownField,
  TextInputField,
  NumberInputField,
} from "@weirdfingers/boards";
```

## See Also

- [Generator Input Schemas](../generators/input-schemas.md) - Backend schema design
- [UI Examples](./ui-examples.md) - More UI component examples
- [Getting Started](./getting-started.md) - Frontend setup guide
