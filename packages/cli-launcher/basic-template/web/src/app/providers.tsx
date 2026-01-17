"use client";

import React from "react";
import { BoardsProvider, NoAuthProvider } from "@weirdfingers/boards";

export function Providers({ children }: { children: React.ReactNode }) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8800";

  return (
    <BoardsProvider
      authProvider={new NoAuthProvider()}
      apiUrl={apiUrl}
    >
      {children}
    </BoardsProvider>
  );
}
