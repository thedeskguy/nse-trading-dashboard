"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  BarChart3,
  Activity,
  ScanSearch,
  Settings,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/hooks/useAuth";

const navItems = [
  { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { label: "Stocks", href: "/dashboard/stocks", icon: BarChart3 },
  { label: "Options", href: "/dashboard/options/NIFTY", icon: Activity },
  { label: "Scanner", href: "/dashboard/scanner", icon: ScanSearch },
  { label: "Settings", href: "/dashboard/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user, loading, signOut } = useAuth();

  return (
    <aside className="hidden md:flex flex-col w-56 shrink-0 h-full border-r border-border bg-card">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-[1.1rem] border-b border-border">
        <div className="w-2 h-2 rounded-full bg-primary" />
        <span className="font-bold text-[15px] tracking-tight">TradeDash</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2.5 py-3 space-y-0.5">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm transition-all duration-200",
                isActive
                  ? "bg-primary/10 text-primary font-medium"
                  : "text-muted-foreground hover:text-foreground hover:bg-muted"
              )}
            >
              <item.icon
                size={15}
                strokeWidth={isActive ? 2.5 : 1.75}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* User footer */}
      <div className="px-2.5 pb-4 pt-2 border-t border-border">
        {loading ? (
          <div className="px-3 py-2.5 space-y-1.5">
            <div className="flex items-center gap-2">
              <Skeleton className="w-5 h-5 rounded-full shrink-0" />
              <Skeleton className="h-3 flex-1 rounded" />
            </div>
            <Skeleton className="h-2.5 w-12 ml-7 rounded" />
          </div>
        ) : (
          <button
            onClick={signOut}
            className="w-full px-3 py-2.5 rounded-xl hover:bg-muted cursor-pointer transition-colors text-left"
          >
            <div className="flex items-center gap-2 mb-0.5">
              <div className="w-5 h-5 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                <span className="text-[9px] font-bold text-primary">
                  {user?.email?.[0]?.toUpperCase() ?? "?"}
                </span>
              </div>
              <div className="text-xs font-medium truncate">{user?.email ?? "Guest"}</div>
            </div>
            <div className="text-xs text-muted-foreground ml-7">Sign out</div>
          </button>
        )}
      </div>
    </aside>
  );
}
