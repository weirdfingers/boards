"use client";

import { useBoards } from "@weirdfingers/boards";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";

export default function Home() {
  const { boards, createBoard } = useBoards();

  return (
    <main className="container mx-auto p-4">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">Boards</h1>
        <Button onClick={() => createBoard({ title: "New Board" })}>
          Create Board
        </Button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {boards.map((board) => (
          <Link href={`/boards/${board.id}`} key={board.id}>
            <Card>
              <CardHeader>
                <CardTitle>{board.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p>{board.description || "No description"}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </main>
  );
}
