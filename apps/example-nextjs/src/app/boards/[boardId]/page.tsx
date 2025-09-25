"use client";

import { useBoard } from "@weirdfingers/boards";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useParams } from "next/navigation";

export default function BoardPage() {
  const params = useParams();
  const boardId = params.boardId as string;
  const { board } = useBoard(boardId);

  if (!board) {
    return <div>Loading...</div>;
  }

  return (
    <main className="container mx-auto p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">{board.title}</h1>
        <Button
          onClick={() =>
            console.log("createGeneration({ prompt: 'A new generation' })")
          }
        >
          Create Generation
        </Button>
      </div>
      <p className="mb-4">{board.description || "No description"}</p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {board.generations.map((generation) => (
          <Card key={generation.id}>
            <CardHeader>
              <CardTitle>Generation {generation.id}</CardTitle>
            </CardHeader>
            <CardContent>
              <p>{generation.status}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </main>
  );
}
