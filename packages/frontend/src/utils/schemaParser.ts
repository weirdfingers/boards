/**
 * Utilities for parsing generator JSON Schemas into structured data
 * suitable for dynamic UI generation.
 */

import type { JSONSchema7, JSONSchema7Definition } from "json-schema";
import type {
  ParsedGeneratorSchema,
  ArtifactSlot,
  PromptField,
  SettingsField,
} from "../types/generatorSchema";

/**
 * Checks if a JSON Schema property references an artifact type.
 *
 * Artifacts are identified by $ref paths containing "Artifact" in their name,
 * e.g., "#/$defs/AudioArtifact" or "#/$defs/VideoArtifact".
 *
 * @param property - The JSON Schema property to check
 * @returns True if the property references an artifact type
 */
export function isArtifactReference(
  property: JSONSchema7 | JSONSchema7Definition | undefined
): boolean {
  if (!property || typeof property === "boolean") {
    return false;
  }

  // Direct $ref to artifact
  if (property.$ref && property.$ref.includes("Artifact")) {
    return true;
  }

  // Array with items that reference an artifact
  if (
    property.type === "array" &&
    property.items &&
    typeof property.items === "object" &&
    !Array.isArray(property.items)
  ) {
    const items = property.items as JSONSchema7;
    return !!(items.$ref && items.$ref.includes("Artifact"));
  }

  return false;
}

/**
 * Extracts the artifact type from a $ref path.
 *
 * Examples:
 * - "#/$defs/AudioArtifact" -> "audio"
 * - "#/$defs/VideoArtifact" -> "video"
 * - "#/$defs/ImageArtifact" -> "image"
 * - "#/$defs/TextArtifact" -> "text"
 *
 * @param ref - The $ref string from the JSON Schema
 * @returns The artifact type in lowercase
 */
export function getArtifactType(
  ref: string
): "audio" | "video" | "image" | "text" {
  const match = ref.match(/(Audio|Video|Image|Text)Artifact/);
  if (match) {
    return match[1].toLowerCase() as "audio" | "video" | "image" | "text";
  }

  // Fallback to "image" if pattern doesn't match
  return "image";
}

/**
 * Parses an artifact property into an ArtifactSlot structure.
 *
 * @param name - The property name from the schema
 * @param property - The JSON Schema property definition
 * @param required - Whether this field is in the required array
 * @returns Parsed artifact slot information
 */
export function parseArtifactSlot(
  name: string,
  property: JSONSchema7,
  required: boolean
): ArtifactSlot {
  const title = property.title || name;
  const description = property.description;

  // Check if this is an array of artifacts
  if (property.type === "array" && property.items) {
    const items =
      typeof property.items === "object" && !Array.isArray(property.items)
        ? (property.items as JSONSchema7)
        : undefined;

    const artifactType = items?.$ref ? getArtifactType(items.$ref) : "image";

    return {
      name: title,
      fieldName: name,
      artifactType,
      required,
      description,
      isArray: true,
      minItems: property.minItems,
      maxItems: property.maxItems,
    };
  }

  // Single artifact
  const artifactType = property.$ref ? getArtifactType(property.$ref) : "image";

  return {
    name: title,
    fieldName: name,
    artifactType,
    required,
    description,
    isArray: false,
  };
}

/**
 * Determines if a numeric property should be rendered as a slider.
 *
 * A property is considered a slider if it's a number or integer type
 * and has both minimum and maximum values defined.
 *
 * @param property - The JSON Schema property to check
 * @returns True if this should be a slider
 */
function isSlider(property: JSONSchema7): boolean {
  return (
    (property.type === "number" || property.type === "integer") &&
    property.minimum !== undefined &&
    property.maximum !== undefined
  );
}

/**
 * Parses a settings field into its appropriate type (slider, dropdown, text, number).
 *
 * @param name - The property name from the schema
 * @param property - The JSON Schema property definition
 * @returns Parsed settings field information
 */
export function parseSettingsField(
  name: string,
  property: JSONSchema7
): SettingsField | null {
  const title = property.title || name;
  const description = property.description;

  // Dropdown (enum)
  if (property.enum && Array.isArray(property.enum)) {
    const options = property.enum.map((val) => String(val));
    const defaultValue =
      property.default !== undefined ? String(property.default) : undefined;

    return {
      type: "dropdown",
      fieldName: name,
      title,
      description,
      options,
      default: defaultValue,
    };
  }

  // Slider (number/integer with min/max)
  if (isSlider(property)) {
    const isInteger = property.type === "integer";
    return {
      type: "slider",
      fieldName: name,
      title,
      description,
      min: property.minimum as number,
      max: property.maximum as number,
      step: property.multipleOf,
      default:
        property.default !== undefined
          ? (property.default as number)
          : undefined,
      isInteger,
    };
  }

  // Number input (without slider constraints)
  if (property.type === "number" || property.type === "integer") {
    const isInteger = property.type === "integer";
    return {
      type: "number",
      fieldName: name,
      title,
      description,
      default:
        property.default !== undefined
          ? (property.default as number)
          : undefined,
      min: property.minimum as number | undefined,
      max: property.maximum as number | undefined,
      isInteger,
    };
  }

  // Text input
  if (property.type === "string") {
    return {
      type: "text",
      fieldName: name,
      title,
      description,
      default:
        property.default !== undefined ? String(property.default) : undefined,
      pattern: property.pattern,
    };
  }

  // Unsupported type
  return null;
}

/**
 * Parses a complete generator JSON Schema into structured data for UI generation.
 *
 * This function categorizes schema properties into:
 * - Artifact slots (for selecting existing artifacts)
 * - Prompt field (special text input for generation prompts)
 * - Settings fields (sliders, dropdowns, text inputs, etc.)
 *
 * @param schema - The JSON Schema from the generator's inputSchema field
 * @returns Parsed schema structure ready for dynamic UI generation
 *
 * @example
 * ```typescript
 * const generator = generators[0];
 * const parsed = parseGeneratorSchema(generator.inputSchema);
 *
 * // Render artifact slots
 * parsed.artifactSlots.forEach(slot => {
 *   console.log(`${slot.name}: ${slot.artifactType} (required: ${slot.required})`);
 * });
 *
 * // Render prompt field
 * if (parsed.promptField) {
 *   console.log(`Prompt: ${parsed.promptField.description}`);
 * }
 *
 * // Render settings
 * parsed.settingsFields.forEach(field => {
 *   if (field.type === 'slider') {
 *     console.log(`${field.title}: ${field.min} - ${field.max}`);
 *   }
 * });
 * ```
 */
export function parseGeneratorSchema(
  schema: JSONSchema7
): ParsedGeneratorSchema {
  const artifactSlots: ArtifactSlot[] = [];
  const settingsFields: SettingsField[] = [];
  let promptField: PromptField | null = null;

  if (!schema.properties) {
    return { artifactSlots, promptField, settingsFields };
  }

  const required = schema.required || [];

  for (const [name, propertyDef] of Object.entries(schema.properties)) {
    if (typeof propertyDef === "boolean") {
      continue;
    }

    const property = propertyDef as JSONSchema7;
    const isRequired = required.includes(name);

    // Check if this is an artifact reference
    if (isArtifactReference(property)) {
      const slot = parseArtifactSlot(name, property, isRequired);
      artifactSlots.push(slot);
      continue;
    }

    // Check if this is the prompt field
    if (name === "prompt" && property.type === "string") {
      promptField = {
        fieldName: name,
        description: property.description,
        required: isRequired,
        default:
          property.default !== undefined ? String(property.default) : undefined,
      };
      continue;
    }

    // Everything else goes to settings
    const settingsField = parseSettingsField(name, property);
    if (settingsField) {
      settingsFields.push(settingsField);
    }
  }

  return {
    artifactSlots,
    promptField,
    settingsFields,
  };
}
