import React from "react";
import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import SupabaseProvider from "@/components/providers/supabase-provider";
import { BoardsProviderWrapper } from "@/components/providers/boards-provider";
import { createClient } from "@/utils/supabase/server";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Stylist",
  description: "Virtual try-on experience",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const supabase = createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <html lang="en">
      <body className={`${inter.variable} min-h-dvh antialiased`}>
        <SupabaseProvider initialUser={user}>
          <BoardsProviderWrapper>{children}</BoardsProviderWrapper>
        </SupabaseProvider>
      </body>
    </html>
  );
}
