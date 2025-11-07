/**
 * Types for parsed generator input schemas.
 *
 * These types represent the structured output from parsing a JSON Schema
 * that defines a generator's input parameters. They enable dynamic UI generation
 * by categorizing schema properties into artifacts, prompts, and settings.
 */

/**
 * Represents a slot for an artifact input (single or array).
 *
 * Artifact slots appear as UI elements that allow users to select
 * existing artifacts from their board.
 */
export interface ArtifactSlot {
  /** Display name for the artifact slot (from schema title) */
  name: string;

  /** Field name used as the key in form data */
  fieldName: string;

  /** Type of artifact: 'audio', 'video', 'image', or 'text' */
  artifactType: "audio" | "video" | "image" | "text";

  /** Whether this field is required in the input schema */
  required: boolean;

  /** Description of what this artifact is used for */
  description?: string;

  /** Whether this slot accepts multiple artifacts (array) */
  isArray: boolean;

  /** Minimum number of items required (for arrays) */
  minItems?: number;

  /** Maximum number of items allowed (for arrays) */
  maxItems?: number;
}

/**
 * Represents the prompt field if present in the schema.
 *
 * The prompt is typically rendered as a textarea for user input.
 */
export interface PromptField {
  /** Field name (typically "prompt") */
  fieldName: string;

  /** Description of how the prompt is used */
  description?: string;

  /** Whether the prompt is required */
  required: boolean;

  /** Default value for the prompt */
  default?: string;
}

/**
 * A slider input for numeric values with min/max bounds.
 */
export interface SliderField {
  type: "slider";

  /** Field name used as the key in form data */
  fieldName: string;

  /** Display title for the slider */
  title: string;

  /** Description of what this setting controls */
  description?: string;

  /** Minimum allowed value */
  min: number;

  /** Maximum allowed value */
  max: number;

  /** Step increment for the slider */
  step?: number;

  /** Default value */
  default?: number;

  /** Whether the value is an integer (vs float) */
  isInteger: boolean;
}

/**
 * A dropdown selector for enumerated string values.
 */
export interface DropdownField {
  type: "dropdown";

  /** Field name used as the key in form data */
  fieldName: string;

  /** Display title for the dropdown */
  title: string;

  /** Description of what this setting controls */
  description?: string;

  /** Available options to select from */
  options: string[];

  /** Default selected option */
  default?: string;
}

/**
 * A text input field for string values.
 */
export interface TextInputField {
  type: "text";

  /** Field name used as the key in form data */
  fieldName: string;

  /** Display title for the input */
  title: string;

  /** Description of what this setting is for */
  description?: string;

  /** Default value */
  default?: string;

  /** Regex pattern for validation */
  pattern?: string;
}

/**
 * A number input field for numeric values without slider constraints.
 */
export interface NumberInputField {
  type: "number";

  /** Field name used as the key in form data */
  fieldName: string;

  /** Display title for the input */
  title: string;

  /** Description of what this setting is for */
  description?: string;

  /** Default value */
  default?: number;

  /** Minimum value (optional, for validation) */
  min?: number;

  /** Maximum value (optional, for validation) */
  max?: number;

  /** Whether the value must be an integer */
  isInteger: boolean;
}

/**
 * Union type for all possible settings field types.
 */
export type SettingsField =
  | SliderField
  | DropdownField
  | TextInputField
  | NumberInputField;

/**
 * Complete parsed structure of a generator's input schema.
 *
 * This structure enables applications to build dynamic UIs that match
 * the generator's input requirements.
 */
export interface ParsedGeneratorSchema {
  /** Artifact input slots (for selecting existing artifacts) */
  artifactSlots: ArtifactSlot[];

  /** The prompt field, if present in the schema */
  promptField: PromptField | null;

  /** Additional settings fields (sliders, dropdowns, etc.) */
  settingsFields: SettingsField[];
}
