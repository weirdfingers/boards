"use client";

import { useSupabase } from "@/hooks/use-supabase";
import { Header } from "@/components/header";

export default function Home() {
  const { user } = useSupabase();

  if (!user) {
    return (
      <div className="flex min-h-dvh flex-col items-center justify-center p-4">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-semibold">AI Stylist</h1>
          <p className="text-muted-foreground">This is a private application.</p>
          <p className="text-sm text-muted-foreground">
            Please check your messages for an invitation link.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      <main className="flex-1 px-4 pb-6">
        <div className="mx-auto w-full max-w-lg">
          {/* Outfit slots and generate button will be added by at-uupb and at-wwr7 */}
        </div>
      </main>
    </div>
  );
}
