"use client";

import React from "react";
import { useParams, useRouter } from "next/navigation";
import { useLineage, type AncestryNode, type DescendantNode } from "@weirdfingers/boards";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Loader2 } from "lucide-react";

export default function LineageExplorerPage() {
  const params = useParams();
  const router = useRouter();
  const generationId = params.generationId as string;

  const { ancestry, descendants, loading, error } = useLineage(generationId, {
    maxDepth: 10,
  });

  if (loading) {
    return (
      <div className="container mx-auto p-6 flex items-center justify-center min-h-screen">
        <div className="flex items-center gap-2">
          <Loader2 className="h-6 w-6 animate-spin" />
          <span>Loading lineage...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Card className="p-6 border-red-500">
          <h2 className="text-xl font-bold text-red-600 mb-2">Error</h2>
          <p className="text-red-600">{error.message}</p>
          <Button
            onClick={() => router.back()}
            variant="outline"
            className="mt-4"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Go Back
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      <div className="mb-6">
        <Button
          onClick={() => router.back()}
          variant="outline"
          className="mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Button>
        <h1 className="text-3xl font-bold">Artifact Lineage Explorer</h1>
        <p className="text-muted-foreground mt-2">
          Explore the ancestry and descendants of generation {generationId}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Ancestry Section */}
        <Card className="p-6">
          <h2 className="text-2xl font-bold mb-4">Ancestry</h2>
          <p className="text-muted-foreground mb-4">
            Shows all parent generations that contributed to this artifact
          </p>
          {ancestry ? (
            <AncestryTree node={ancestry} currentGenerationId={generationId} />
          ) : (
            <p className="text-muted-foreground">No ancestry data available</p>
          )}
        </Card>

        {/* Descendants Section */}
        <Card className="p-6">
          <h2 className="text-2xl font-bold mb-4">Descendants</h2>
          <p className="text-muted-foreground mb-4">
            Shows all child generations that used this artifact as input
          </p>
          {descendants ? (
            <DescendantTree node={descendants} currentGenerationId={generationId} />
          ) : (
            <p className="text-muted-foreground">
              No descendants data available
            </p>
          )}
        </Card>
      </div>
    </div>
  );
}

interface AncestryTreeProps {
  node: AncestryNode;
  currentGenerationId: string;
}

function AncestryTree({ node, currentGenerationId }: AncestryTreeProps) {
  const router = useRouter();
  const isCurrentGeneration = node.generation.id === currentGenerationId;

  return (
    <div className="space-y-2">
      <div
        className={`p-3 rounded-lg border ${
          isCurrentGeneration
            ? "bg-primary/10 border-primary"
            : "bg-card hover:bg-accent cursor-pointer"
        }`}
        onClick={() => {
          if (!isCurrentGeneration) {
            router.push(`/lineage/${node.generation.id}`);
          }
        }}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm text-muted-foreground">
                Depth: {node.depth}
              </span>
              {node.role && (
                <span className="px-2 py-0.5 text-xs rounded-full bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300">
                  {node.role}
                </span>
              )}
            </div>
            <p className="font-semibold mt-1">{node.generation.generatorName}</p>
            <p className="text-sm text-muted-foreground">
              {node.generation.artifactType} • {node.generation.status}
            </p>
            <p className="text-xs text-muted-foreground font-mono mt-1">
              {node.generation.id.slice(0, 8)}...
            </p>
          </div>
          {node.generation.thumbnailUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={node.generation.thumbnailUrl}
              alt="Thumbnail"
              className="w-16 h-16 object-cover rounded"
            />
          )}
        </div>
      </div>

      {node.parents && node.parents.length > 0 && (
        <div className="ml-6 pl-4 border-l-2 border-muted space-y-2">
          {node.parents.map((parent, idx) => (
            <AncestryTree
              key={`${parent.generation.id}-${idx}`}
              node={parent}
              currentGenerationId={currentGenerationId}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface DescendantTreeProps {
  node: DescendantNode;
  currentGenerationId: string;
}

function DescendantTree({ node, currentGenerationId }: DescendantTreeProps) {
  const router = useRouter();
  const isCurrentGeneration = node.generation.id === currentGenerationId;

  return (
    <div className="space-y-2">
      <div
        className={`p-3 rounded-lg border ${
          isCurrentGeneration
            ? "bg-primary/10 border-primary"
            : "bg-card hover:bg-accent cursor-pointer"
        }`}
        onClick={() => {
          if (!isCurrentGeneration) {
            router.push(`/lineage/${node.generation.id}`);
          }
        }}
      >
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="font-mono text-sm text-muted-foreground">
                Depth: {node.depth}
              </span>
              {node.role && (
                <span className="px-2 py-0.5 text-xs rounded-full bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">
                  {node.role}
                </span>
              )}
            </div>
            <p className="font-semibold mt-1">{node.generation.generatorName}</p>
            <p className="text-sm text-muted-foreground">
              {node.generation.artifactType} • {node.generation.status}
            </p>
            <p className="text-xs text-muted-foreground font-mono mt-1">
              {node.generation.id.slice(0, 8)}...
            </p>
          </div>
          {node.generation.thumbnailUrl && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={node.generation.thumbnailUrl}
              alt="Thumbnail"
              className="w-16 h-16 object-cover rounded"
            />
          )}
        </div>
      </div>

      {node.children && node.children.length > 0 && (
        <div className="ml-6 pl-4 border-l-2 border-muted space-y-2">
          {node.children.map((child, idx) => (
            <DescendantTree
              key={`${child.generation.id}-${idx}`}
              node={child}
              currentGenerationId={currentGenerationId}
            />
          ))}
        </div>
      )}
    </div>
  );
}
