import { describe, it, expect } from "vitest";
import { UPDATE_BOARD, type UpdateBoardInput } from "../operations";

describe("UPDATE_BOARD mutation", () => {
  it("should have correct signature with id inside input", () => {
    const mutationString = UPDATE_BOARD.loc?.source.body || "";

    // Should have single $input parameter
    expect(mutationString).toContain(
      "mutation UpdateBoard($input: UpdateBoardInput!)"
    );

    // Should call updateBoard with input only
    expect(mutationString).toContain("updateBoard(input: $input)");

    // Should NOT have separate $id parameter (the bug from issue #189)
    expect(mutationString).not.toContain("$id: UUID!");
    expect(mutationString).not.toContain("updateBoard(id: $id");
  });
});

describe("UpdateBoardInput interface", () => {
  it("should include id as a required field", () => {
    // TypeScript compile-time check - if this compiles, the interface is correct
    const validInput: UpdateBoardInput = {
      id: "board-123",
      title: "Test",
    };

    expect(validInput.id).toBe("board-123");
  });

  it("should allow optional fields", () => {
    // Should compile with just id
    const minimalInput: UpdateBoardInput = {
      id: "board-123",
    };

    expect(minimalInput.id).toBe("board-123");

    // Should compile with all fields
    const fullInput: UpdateBoardInput = {
      id: "board-123",
      title: "Test Title",
      description: "Test Description",
      isPublic: true,
      settings: { foo: "bar" },
      metadata: { baz: "qux" },
    };

    expect(fullInput.title).toBe("Test Title");
  });
});
