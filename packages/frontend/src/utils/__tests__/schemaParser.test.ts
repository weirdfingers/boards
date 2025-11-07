import { describe, it, expect } from "vitest";
import type { JSONSchema7 } from "json-schema";
import {
  parseGeneratorSchema,
  isArtifactReference,
  getArtifactType,
  parseArtifactSlot,
  parseSettingsField,
} from "../schemaParser";

describe("schemaParser", () => {
  describe("isArtifactReference", () => {
    it("should identify direct artifact references", () => {
      const property: JSONSchema7 = {
        $ref: "#/$defs/AudioArtifact",
      };
      expect(isArtifactReference(property)).toBe(true);
    });

    it("should identify array artifact references", () => {
      const property: JSONSchema7 = {
        type: "array",
        items: {
          $ref: "#/$defs/ImageArtifact",
        },
      };
      expect(isArtifactReference(property)).toBe(true);
    });

    it("should return false for non-artifact references", () => {
      const property: JSONSchema7 = {
        type: "string",
      };
      expect(isArtifactReference(property)).toBe(false);
    });

    it("should return false for undefined property", () => {
      expect(isArtifactReference(undefined)).toBe(false);
    });

    it("should return false for boolean schema", () => {
      expect(isArtifactReference(true)).toBe(false);
    });
  });

  describe("getArtifactType", () => {
    it("should extract audio type", () => {
      expect(getArtifactType("#/$defs/AudioArtifact")).toBe("audio");
    });

    it("should extract video type", () => {
      expect(getArtifactType("#/$defs/VideoArtifact")).toBe("video");
    });

    it("should extract image type", () => {
      expect(getArtifactType("#/$defs/ImageArtifact")).toBe("image");
    });

    it("should extract text type", () => {
      expect(getArtifactType("#/$defs/TextArtifact")).toBe("text");
    });

    it("should fallback to image for unknown patterns", () => {
      expect(getArtifactType("#/$defs/UnknownType")).toBe("image");
    });
  });

  describe("parseArtifactSlot", () => {
    it("should parse single artifact slot", () => {
      const property: JSONSchema7 = {
        $ref: "#/$defs/AudioArtifact",
        title: "Audio Source",
        description: "Audio file to process",
      };

      const slot = parseArtifactSlot("audio_source", property, true);

      expect(slot).toEqual({
        name: "Audio Source",
        fieldName: "audio_source",
        artifactType: "audio",
        required: true,
        description: "Audio file to process",
        isArray: false,
      });
    });

    it("should parse array artifact slot", () => {
      const property: JSONSchema7 = {
        type: "array",
        items: {
          $ref: "#/$defs/ImageArtifact",
        },
        title: "Reference Images",
        description: "Images for style transfer",
        minItems: 1,
        maxItems: 5,
      };

      const slot = parseArtifactSlot("reference_images", property, false);

      expect(slot).toEqual({
        name: "Reference Images",
        fieldName: "reference_images",
        artifactType: "image",
        required: false,
        description: "Images for style transfer",
        isArray: true,
        minItems: 1,
        maxItems: 5,
      });
    });

    it("should use fieldName as name if title is missing", () => {
      const property: JSONSchema7 = {
        $ref: "#/$defs/VideoArtifact",
      };

      const slot = parseArtifactSlot("video_input", property, false);

      expect(slot.name).toBe("video_input");
      expect(slot.fieldName).toBe("video_input");
    });
  });

  describe("parseSettingsField", () => {
    it("should parse slider field (float)", () => {
      const property: JSONSchema7 = {
        type: "number",
        title: "Strength",
        description: "Effect strength",
        minimum: 0.0,
        maximum: 1.0,
        default: 0.75,
      };

      const field = parseSettingsField("strength", property);

      expect(field).toEqual({
        type: "slider",
        fieldName: "strength",
        title: "Strength",
        description: "Effect strength",
        min: 0.0,
        max: 1.0,
        default: 0.75,
        isInteger: false,
      });
    });

    it("should parse slider field (integer)", () => {
      const property: JSONSchema7 = {
        type: "integer",
        title: "Steps",
        description: "Number of steps",
        minimum: 1,
        maximum: 100,
        default: 50,
        multipleOf: 5,
      };

      const field = parseSettingsField("steps", property);

      expect(field).toEqual({
        type: "slider",
        fieldName: "steps",
        title: "Steps",
        description: "Number of steps",
        min: 1,
        max: 100,
        step: 5,
        default: 50,
        isInteger: true,
      });
    });

    it("should parse dropdown field", () => {
      const property: JSONSchema7 = {
        type: "string",
        title: "Style",
        description: "Art style",
        enum: ["realistic", "anime", "abstract"],
        default: "realistic",
      };

      const field = parseSettingsField("style", property);

      expect(field).toEqual({
        type: "dropdown",
        fieldName: "style",
        title: "Style",
        description: "Art style",
        options: ["realistic", "anime", "abstract"],
        default: "realistic",
      });
    });

    it("should parse text input field", () => {
      const property: JSONSchema7 = {
        type: "string",
        title: "Negative Prompt",
        description: "What to avoid",
        default: "",
        pattern: "^[a-zA-Z0-9\\s,]+$",
      };

      const field = parseSettingsField("negative_prompt", property);

      expect(field).toEqual({
        type: "text",
        fieldName: "negative_prompt",
        title: "Negative Prompt",
        description: "What to avoid",
        default: "",
        pattern: "^[a-zA-Z0-9\\s,]+$",
      });
    });

    it("should parse number input field", () => {
      const property: JSONSchema7 = {
        type: "integer",
        title: "Seed",
        description: "Random seed",
        default: -1,
      };

      const field = parseSettingsField("seed", property);

      expect(field).toEqual({
        type: "number",
        fieldName: "seed",
        title: "Seed",
        description: "Random seed",
        default: -1,
        isInteger: true,
      });
    });

    it("should use fieldName as title if missing", () => {
      const property: JSONSchema7 = {
        type: "string",
        enum: ["option1", "option2"],
      };

      const field = parseSettingsField("my_field", property);

      expect(field?.title).toBe("my_field");
    });

    it("should return null for unsupported types", () => {
      const property: JSONSchema7 = {
        type: "object",
      };

      const field = parseSettingsField("complex", property);

      expect(field).toBeNull();
    });
  });

  describe("parseGeneratorSchema", () => {
    it("should parse complete lipsync schema", () => {
      const schema: JSONSchema7 = {
        $defs: {
          AudioArtifact: {
            type: "object",
            properties: {
              generation_id: { type: "string" },
              storage_url: { type: "string" },
              format: { type: "string" },
            },
            required: ["generation_id", "storage_url", "format"],
          },
          VideoArtifact: {
            type: "object",
            properties: {
              generation_id: { type: "string" },
              storage_url: { type: "string" },
              format: { type: "string" },
            },
            required: ["generation_id", "storage_url", "format"],
          },
        },
        type: "object",
        properties: {
          audio_source: {
            $ref: "#/$defs/AudioArtifact",
            description: "Audio track for lip sync",
          },
          video_source: {
            $ref: "#/$defs/VideoArtifact",
            description: "Video to sync lips in",
          },
          prompt: {
            type: "string",
            description: "Optional prompt for generation",
            default: "",
          },
        },
        required: ["audio_source", "video_source"],
      };

      const parsed = parseGeneratorSchema(schema);

      expect(parsed.artifactSlots).toHaveLength(2);
      expect(parsed.artifactSlots[0]).toMatchObject({
        fieldName: "audio_source",
        artifactType: "audio",
        required: true,
        isArray: false,
      });
      expect(parsed.artifactSlots[1]).toMatchObject({
        fieldName: "video_source",
        artifactType: "video",
        required: true,
        isArray: false,
      });

      expect(parsed.promptField).toMatchObject({
        fieldName: "prompt",
        description: "Optional prompt for generation",
        required: false,
        default: "",
      });

      expect(parsed.settingsFields).toHaveLength(0);
    });

    it("should parse FLUX Pro schema with settings", () => {
      const schema: JSONSchema7 = {
        type: "object",
        description: "Input schema for FLUX.1.1 Pro image generation.",
        properties: {
          prompt: {
            type: "string",
            title: "Prompt",
            description: "Text prompt for image generation",
          },
          aspect_ratio: {
            type: "string",
            title: "Aspect Ratio",
            description: "Image aspect ratio",
            default: "1:1",
            enum: ["1:1", "16:9", "21:9", "2:3", "3:2", "4:5", "5:4", "9:16", "9:21"],
          },
          safety_tolerance: {
            type: "integer",
            title: "Safety Tolerance",
            description: "Safety tolerance level (1-5)",
            default: 2,
            minimum: 1,
            maximum: 5,
          },
        },
        required: ["prompt"],
      };

      const parsed = parseGeneratorSchema(schema);

      expect(parsed.artifactSlots).toHaveLength(0);

      expect(parsed.promptField).toMatchObject({
        fieldName: "prompt",
        description: "Text prompt for image generation",
        required: true,
      });

      expect(parsed.settingsFields).toHaveLength(2);
      expect(parsed.settingsFields[0]).toMatchObject({
        type: "dropdown",
        fieldName: "aspect_ratio",
        title: "Aspect Ratio",
        options: ["1:1", "16:9", "21:9", "2:3", "3:2", "4:5", "5:4", "9:16", "9:21"],
        default: "1:1",
      });
      expect(parsed.settingsFields[1]).toMatchObject({
        type: "slider",
        fieldName: "safety_tolerance",
        title: "Safety Tolerance",
        min: 1,
        max: 5,
        default: 2,
        isInteger: true,
      });
    });

    it("should parse schema with array artifacts", () => {
      const schema: JSONSchema7 = {
        $defs: {
          ImageArtifact: {
            type: "object",
            properties: {
              generation_id: { type: "string" },
              storage_url: { type: "string" },
            },
          },
        },
        type: "object",
        properties: {
          reference_images: {
            type: "array",
            items: {
              $ref: "#/$defs/ImageArtifact",
            },
            title: "Reference Images",
            description: "Style reference images",
            minItems: 1,
            maxItems: 3,
          },
          prompt: {
            type: "string",
            description: "Generation prompt",
          },
          strength: {
            type: "number",
            title: "Strength",
            minimum: 0.0,
            maximum: 1.0,
            default: 0.8,
          },
        },
        required: ["reference_images", "prompt"],
      };

      const parsed = parseGeneratorSchema(schema);

      expect(parsed.artifactSlots).toHaveLength(1);
      expect(parsed.artifactSlots[0]).toMatchObject({
        fieldName: "reference_images",
        artifactType: "image",
        required: true,
        isArray: true,
        minItems: 1,
        maxItems: 3,
      });

      expect(parsed.promptField).toMatchObject({
        fieldName: "prompt",
        required: true,
      });

      expect(parsed.settingsFields).toHaveLength(1);
      expect(parsed.settingsFields[0]).toMatchObject({
        type: "slider",
        fieldName: "strength",
        min: 0.0,
        max: 1.0,
      });
    });

    it("should handle schema with no properties", () => {
      const schema: JSONSchema7 = {
        type: "object",
      };

      const parsed = parseGeneratorSchema(schema);

      expect(parsed.artifactSlots).toHaveLength(0);
      expect(parsed.promptField).toBeNull();
      expect(parsed.settingsFields).toHaveLength(0);
    });

    it("should handle mixed field types", () => {
      const schema: JSONSchema7 = {
        $defs: {
          AudioArtifact: {
            type: "object",
            properties: {
              generation_id: { type: "string" },
            },
          },
        },
        type: "object",
        properties: {
          audio_input: {
            $ref: "#/$defs/AudioArtifact",
            description: "Audio to process",
          },
          prompt: {
            type: "string",
            description: "Processing instructions",
          },
          language: {
            type: "string",
            title: "Language",
            default: "en",
          },
          temperature: {
            type: "number",
            title: "Temperature",
            minimum: 0.0,
            maximum: 2.0,
            default: 1.0,
          },
          format: {
            type: "string",
            title: "Output Format",
            enum: ["json", "text", "srt"],
            default: "text",
          },
          seed: {
            type: "integer",
            title: "Seed",
            default: -1,
          },
        },
        required: ["audio_input", "prompt"],
      };

      const parsed = parseGeneratorSchema(schema);

      // Should have 1 artifact slot
      expect(parsed.artifactSlots).toHaveLength(1);
      expect(parsed.artifactSlots[0].fieldName).toBe("audio_input");

      // Should have prompt field
      expect(parsed.promptField).not.toBeNull();
      expect(parsed.promptField?.fieldName).toBe("prompt");

      // Should have 4 settings fields
      expect(parsed.settingsFields).toHaveLength(4);
      const fieldsByName = Object.fromEntries(
        parsed.settingsFields.map((f) => [f.fieldName, f])
      );

      expect(fieldsByName.language).toMatchObject({
        type: "text",
        fieldName: "language",
      });
      expect(fieldsByName.temperature).toMatchObject({
        type: "slider",
        fieldName: "temperature",
      });
      expect(fieldsByName.format).toMatchObject({
        type: "dropdown",
        fieldName: "format",
      });
      expect(fieldsByName.seed).toMatchObject({
        type: "number",
        fieldName: "seed",
      });
    });

    it("should handle optional vs required fields", () => {
      const schema: JSONSchema7 = {
        $defs: {
          ImageArtifact: {
            type: "object",
            properties: {
              generation_id: { type: "string" },
            },
          },
        },
        type: "object",
        properties: {
          required_image: {
            $ref: "#/$defs/ImageArtifact",
          },
          optional_image: {
            $ref: "#/$defs/ImageArtifact",
          },
          prompt: {
            type: "string",
          },
        },
        required: ["required_image", "prompt"],
      };

      const parsed = parseGeneratorSchema(schema);

      expect(parsed.artifactSlots[0].required).toBe(true);
      expect(parsed.artifactSlots[1].required).toBe(false);
      expect(parsed.promptField?.required).toBe(true);
    });
  });
});
