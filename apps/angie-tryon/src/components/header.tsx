"use client";

import { ChevronLeft, MoreVertical } from "lucide-react";
import { Button } from "@/components/ui/button";

interface HeaderProps {
  showBack?: boolean;
  onBack?: () => void;
}

export function Header({ showBack, onBack }: HeaderProps) {
  return (
    <header className="flex h-14 items-center justify-between px-4">
      <div className="w-10">
        {showBack && (
          <Button variant="ghost" size="icon" onClick={onBack} aria-label="Go back">
            <ChevronLeft className="h-5 w-5" />
          </Button>
        )}
      </div>
      <h1 className="text-lg font-semibold">AI Stylist</h1>
      <div className="w-10">
        <Button variant="ghost" size="icon" aria-label="Menu">
          <MoreVertical className="h-5 w-5" />
        </Button>
      </div>
    </header>
  );
}
