"use client";

import React, { useMemo } from "react";
import { BoardsProvider } from "@weirdfingers/boards";
import { SupabaseAuthProvider } from "@weirdfingers/boards-auth-supabase";

export function BoardsProviderWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  const apiUrl =
    process.env.NEXT_PUBLIC_BOARDS_API_URL || "http://localhost:8088";

  const authProvider = useMemo(
    () =>
      new SupabaseAuthProvider({
        url: process.env.NEXT_PUBLIC_SUPABASE_URL!,
        anonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
      }),
    []
  );

  return (
    <BoardsProvider authProvider={authProvider} apiUrl={apiUrl}>
      {children}
    </BoardsProvider>
  );
}
