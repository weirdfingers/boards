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
