"use client";

import { useBoards } from "@weirdfingers/boards";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function Home() {
  const { boards, loading, createBoard } = useBoards();

  const handleCreateBoard = () => {
    createBoard({ title: "New Board", description: "Created from basic template" });
  };

  return (
    <main className="container mx-auto p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold">My Boards</h1>
        <Button onClick={handleCreateBoard}>
          Create Board
        </Button>
      </div>

      {loading ? (
        <p>Loading boards...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {boards.map((board) => (
            <Card key={board.id}>
              <CardHeader>
                <CardTitle>{board.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {board.description || "No description"}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {!loading && boards.length === 0 && (
        <p className="text-muted-foreground">No boards yet. Create one to get started!</p>
      )}
    </main>
  );
}
