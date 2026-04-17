"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { Moon, Sun, Search } from "lucide-react";
import { useTheme } from "next-themes";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useStockSearch } from "@/lib/api/market";

function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}

export function TopBar() {
  const { theme, setTheme } = useTheme();
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const debouncedQuery = useDebounce(query, 250);

  const { data, isFetching } = useStockSearch(debouncedQuery);
  const results = data?.results ?? [];

  // Close dropdown on outside click
  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const handleSelect = useCallback(
    (ticker: string) => {
      router.push(`/dashboard/stocks/${ticker}`);
      setQuery("");
      setOpen(false);
    },
    [router]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      const t = query.trim().toUpperCase();
      if (!t) return;
      const ticker = t.includes(".") ? t : `${t}.NS`;
      handleSelect(ticker);
    }
    if (e.key === "Escape") setOpen(false);
  };

  return (
    <header className="h-14 shrink-0 border-b border-border flex items-center gap-3 px-5 bg-background/80 backdrop-blur-sm sticky top-0 z-20">
      <div ref={containerRef} className="relative flex-1 max-w-xs">
        <Search
          size={13}
          className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground pointer-events-none z-10"
        />
        <Input
          placeholder="Search stocks..."
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          onFocus={() => query && setOpen(true)}
          onKeyDown={handleKeyDown}
          className="pl-8 h-8 rounded-full bg-muted border-0 text-sm focus-visible:ring-1 focus-visible:ring-primary/50"
        />

        {/* Dropdown */}
        {open && query.trim().length >= 1 && (
          <div className="absolute top-full mt-1.5 left-0 right-0 bg-card border border-border rounded-xl shadow-lg overflow-hidden z-50">
            {isFetching && results.length === 0 ? (
              <div className="px-3 py-2.5 text-xs text-muted-foreground">Searching…</div>
            ) : results.length === 0 ? (
              <div className="px-3 py-2.5 text-xs text-muted-foreground">No matches found</div>
            ) : (
              <ul>
                {results.map((r) => (
                  <li key={r.ticker}>
                    <button
                      className="w-full text-left px-3 py-2.5 hover:bg-muted/60 transition-colors flex items-center justify-between gap-3"
                      onMouseDown={(e) => {
                        e.preventDefault(); // prevent input blur before click fires
                        handleSelect(r.ticker);
                      }}
                    >
                      <div className="min-w-0">
                        <div className="text-sm font-medium truncate">{r.name}</div>
                        <div className="text-xs text-muted-foreground">{r.ticker}</div>
                      </div>
                      <span className="text-[10px] text-muted-foreground/60 shrink-0">NSE</span>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      <div className="ml-auto flex items-center gap-1.5">
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 rounded-full"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          aria-label="Toggle theme"
        >
          <Sun size={14} className="hidden dark:block" />
          <Moon size={14} className="block dark:hidden" />
        </Button>
      </div>
    </header>
  );
}
