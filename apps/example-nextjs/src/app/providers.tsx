"use client";

import React from "react";
import {
  BoardsProvider,
  NoAuthProvider,
} from "@weirdfingers/boards";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <BoardsProvider
      authProvider={new NoAuthProvider()}
      graphqlUrl="http://localhost:8000/graphql/"
    >
      {children}
    </BoardsProvider>
  );
}
