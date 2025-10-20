"use client";

import React from "react";
import { BoardsProvider, NoAuthProvider } from "@weirdfingers/boards";

export function Providers({ children }: { children: React.ReactNode }) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8088";

  return (
    <BoardsProvider
      authProvider={new NoAuthProvider()}
      graphqlUrl={`${apiUrl}/graphql`}
    >
      {children}
    </BoardsProvider>
  );
}
