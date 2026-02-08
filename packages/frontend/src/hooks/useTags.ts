/**
 * Hooks for managing tags on generations.
 *
 * This module provides three hooks:
 * - useManageTags: CRUD operations for tags
 * - useTagGeneration: Add/remove tags from a generation
 * - useGenerationTags: Get tags for a specific generation
 */

import { useCallback, useMemo } from "react";
import { useQuery, useMutation } from "urql";
import {
  GET_TAGS,
  GET_TAG,
  GET_TAG_BY_SLUG,
  GET_GENERATION_TAGS,
  CREATE_TAG,
  UPDATE_TAG,
  DELETE_TAG,
  ADD_TAG_TO_GENERATION,
  REMOVE_TAG_FROM_GENERATION,
  Tag,
  CreateTagInput,
  UpdateTagInput,
} from "../graphql/operations";

/**
 * Hook return type for useManageTags
 */
export interface ManageTagsHook {
  /** List of all tags for the current tenant */
  tags: Tag[];
  /** Loading state */
  loading: boolean;
  /** Error if any */
  error: Error | null;
  /** Create a new tag */
  createTag: (input: CreateTagInput) => Promise<Tag>;
  /** Update an existing tag */
  updateTag: (input: UpdateTagInput) => Promise<Tag>;
  /** Delete a tag */
  deleteTag: (id: string) => Promise<boolean>;
  /** Refresh the tags list */
  refresh: () => Promise<void>;
  /** Get a tag by ID */
  getTagById: (id: string) => Tag | undefined;
  /** Get a tag by slug */
  getTagBySlug: (slug: string) => Tag | undefined;
}

/**
 * Hook for managing tags (CRUD operations).
 *
 * Provides functions for creating, updating, deleting, and listing tags.
 *
 * @param options - Query options
 * @param options.limit - Maximum number of tags to fetch (default: 100)
 * @param options.offset - Offset for pagination (default: 0)
 * @returns ManageTagsHook with tag list and CRUD operations
 *
 * @example
 * ```tsx
 * function TagManager() {
 *   const { tags, createTag, deleteTag, loading } = useManageTags();
 *
 *   const handleCreate = async () => {
 *     await createTag({ name: "Favorite", description: "My favorite images" });
 *   };
 *
 *   if (loading) return <div>Loading...</div>;
 *
 *   return (
 *     <ul>
 *       {tags.map(tag => (
 *         <li key={tag.id}>
 *           {tag.name}
 *           <button onClick={() => deleteTag(tag.id)}>Delete</button>
 *         </li>
 *       ))}
 *     </ul>
 *   );
 * }
 * ```
 */
export function useManageTags(options?: {
  limit?: number;
  offset?: number;
}): ManageTagsHook {
  const [{ data, fetching, error }, reexecuteQuery] = useQuery({
    query: GET_TAGS,
    variables: {
      limit: options?.limit ?? 100,
      offset: options?.offset ?? 0,
    },
    requestPolicy: "cache-and-network",
  });

  const [, createTagMutation] = useMutation(CREATE_TAG);
  const [, updateTagMutation] = useMutation(UPDATE_TAG);
  const [, deleteTagMutation] = useMutation(DELETE_TAG);

  const tags = useMemo(() => data?.tags ?? [], [data?.tags]);

  const createTag = useCallback(
    async (input: CreateTagInput): Promise<Tag> => {
      const result = await createTagMutation({ input });

      if (result.error) {
        throw new Error(result.error.message);
      }

      if (!result.data?.createTag) {
        throw new Error("Failed to create tag");
      }

      // Refresh tags list
      reexecuteQuery({ requestPolicy: "network-only" });

      return result.data.createTag;
    },
    [createTagMutation, reexecuteQuery]
  );

  const updateTag = useCallback(
    async (input: UpdateTagInput): Promise<Tag> => {
      const result = await updateTagMutation({ input });

      if (result.error) {
        throw new Error(result.error.message);
      }

      if (!result.data?.updateTag) {
        throw new Error("Failed to update tag");
      }

      // Refresh tags list
      reexecuteQuery({ requestPolicy: "network-only" });

      return result.data.updateTag;
    },
    [updateTagMutation, reexecuteQuery]
  );

  const deleteTag = useCallback(
    async (id: string): Promise<boolean> => {
      const result = await deleteTagMutation({ id });

      if (result.error) {
        throw new Error(result.error.message);
      }

      if (!result.data?.deleteTag) {
        throw new Error("Failed to delete tag");
      }

      // Refresh tags list
      reexecuteQuery({ requestPolicy: "network-only" });

      return true;
    },
    [deleteTagMutation, reexecuteQuery]
  );

  const refresh = useCallback(async (): Promise<void> => {
    await reexecuteQuery({ requestPolicy: "network-only" });
  }, [reexecuteQuery]);

  const getTagById = useCallback(
    (id: string): Tag | undefined => {
      return tags.find((tag: Tag) => tag.id === id);
    },
    [tags]
  );

  const getTagBySlug = useCallback(
    (slug: string): Tag | undefined => {
      return tags.find((tag: Tag) => tag.slug === slug);
    },
    [tags]
  );

  return {
    tags,
    loading: fetching,
    error: error ? new Error(error.message) : null,
    createTag,
    updateTag,
    deleteTag,
    refresh,
    getTagById,
    getTagBySlug,
  };
}

/**
 * Hook return type for useTagGeneration
 */
export interface TagGenerationHook {
  /** Tags currently on the generation */
  tags: Tag[];
  /** Loading state */
  loading: boolean;
  /** Error if any */
  error: Error | null;
  /** Add a tag to the generation */
  addTag: (tagId: string) => Promise<Tag>;
  /** Remove a tag from the generation */
  removeTag: (tagId: string) => Promise<boolean>;
  /** Refresh the tags list */
  refresh: () => Promise<void>;
  /** Check if generation has a specific tag */
  hasTag: (tagId: string) => boolean;
}

/**
 * Hook for adding/removing tags from a specific generation.
 *
 * @param generationId - The ID of the generation to manage tags for
 * @returns TagGenerationHook with tag list and add/remove operations
 *
 * @example
 * ```tsx
 * function GenerationTagEditor({ generationId }: { generationId: string }) {
 *   const { tags, addTag, removeTag, hasTag } = useTagGeneration(generationId);
 *   const { tags: allTags } = useManageTags();
 *
 *   return (
 *     <div>
 *       <h3>Tags on this generation:</h3>
 *       {tags.map(tag => (
 *         <span key={tag.id}>
 *           {tag.name}
 *           <button onClick={() => removeTag(tag.id)}>x</button>
 *         </span>
 *       ))}
 *
 *       <h3>Add tags:</h3>
 *       {allTags
 *         .filter(t => !hasTag(t.id))
 *         .map(tag => (
 *           <button key={tag.id} onClick={() => addTag(tag.id)}>
 *             + {tag.name}
 *           </button>
 *         ))}
 *     </div>
 *   );
 * }
 * ```
 */
export function useTagGeneration(generationId: string): TagGenerationHook {
  const [{ data, fetching, error }, reexecuteQuery] = useQuery({
    query: GET_GENERATION_TAGS,
    variables: { id: generationId },
    pause: !generationId,
    requestPolicy: "cache-and-network",
  });

  const [, addTagMutation] = useMutation(ADD_TAG_TO_GENERATION);
  const [, removeTagMutation] = useMutation(REMOVE_TAG_FROM_GENERATION);

  const tags = useMemo(
    () => data?.generation?.tags ?? [],
    [data?.generation?.tags]
  );

  const addTag = useCallback(
    async (tagId: string): Promise<Tag> => {
      if (!generationId) {
        throw new Error("Generation ID is required");
      }

      const result = await addTagMutation({
        generationId,
        tagId,
      });

      if (result.error) {
        throw new Error(result.error.message);
      }

      if (!result.data?.addTagToGeneration) {
        throw new Error("Failed to add tag to generation");
      }

      // Refresh tags list
      reexecuteQuery({ requestPolicy: "network-only" });

      return result.data.addTagToGeneration;
    },
    [generationId, addTagMutation, reexecuteQuery]
  );

  const removeTag = useCallback(
    async (tagId: string): Promise<boolean> => {
      if (!generationId) {
        throw new Error("Generation ID is required");
      }

      const result = await removeTagMutation({
        generationId,
        tagId,
      });

      if (result.error) {
        throw new Error(result.error.message);
      }

      if (!result.data?.removeTagFromGeneration) {
        throw new Error("Failed to remove tag from generation");
      }

      // Refresh tags list
      reexecuteQuery({ requestPolicy: "network-only" });

      return true;
    },
    [generationId, removeTagMutation, reexecuteQuery]
  );

  const refresh = useCallback(async (): Promise<void> => {
    await reexecuteQuery({ requestPolicy: "network-only" });
  }, [reexecuteQuery]);

  const hasTag = useCallback(
    (tagId: string): boolean => {
      return tags.some((tag: Tag) => tag.id === tagId);
    },
    [tags]
  );

  return {
    tags,
    loading: fetching,
    error: error ? new Error(error.message) : null,
    addTag,
    removeTag,
    refresh,
    hasTag,
  };
}

/**
 * Hook return type for useTag
 */
export interface TagHook {
  /** The tag data */
  tag: Tag | null;
  /** Loading state */
  loading: boolean;
  /** Error if any */
  error: Error | null;
  /** Refresh the tag data */
  refresh: () => Promise<void>;
}

/**
 * Hook for fetching a single tag by ID.
 *
 * @param id - The tag ID
 * @returns TagHook with tag data
 *
 * @example
 * ```tsx
 * function TagDetail({ tagId }: { tagId: string }) {
 *   const { tag, loading, error } = useTag(tagId);
 *
 *   if (loading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *   if (!tag) return <div>Tag not found</div>;
 *
 *   return (
 *     <div>
 *       <h1>{tag.name}</h1>
 *       <p>{tag.description}</p>
 *     </div>
 *   );
 * }
 * ```
 */
export function useTag(id: string): TagHook {
  const [{ data, fetching, error }, reexecuteQuery] = useQuery({
    query: GET_TAG,
    variables: { id },
    pause: !id,
    requestPolicy: "cache-and-network",
  });

  const refresh = useCallback(async (): Promise<void> => {
    await reexecuteQuery({ requestPolicy: "network-only" });
  }, [reexecuteQuery]);

  return {
    tag: data?.tag ?? null,
    loading: fetching,
    error: error ? new Error(error.message) : null,
    refresh,
  };
}

/**
 * Hook for fetching a single tag by slug.
 *
 * @param slug - The tag slug
 * @returns TagHook with tag data
 *
 * @example
 * ```tsx
 * function TagPage({ slug }: { slug: string }) {
 *   const { tag, loading, error } = useTagBySlug(slug);
 *
 *   if (loading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *   if (!tag) return <div>Tag not found</div>;
 *
 *   return (
 *     <div>
 *       <h1>{tag.name}</h1>
 *       <p>Slug: {tag.slug}</p>
 *     </div>
 *   );
 * }
 * ```
 */
export function useTagBySlug(slug: string): TagHook {
  const [{ data, fetching, error }, reexecuteQuery] = useQuery({
    query: GET_TAG_BY_SLUG,
    variables: { slug },
    pause: !slug,
    requestPolicy: "cache-and-network",
  });

  const refresh = useCallback(async (): Promise<void> => {
    await reexecuteQuery({ requestPolicy: "network-only" });
  }, [reexecuteQuery]);

  return {
    tag: data?.tagBySlug ?? null,
    loading: fetching,
    error: error ? new Error(error.message) : null,
    refresh,
  };
}
