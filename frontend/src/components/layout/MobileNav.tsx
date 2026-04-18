"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { LayoutDashboard, BarChart3, Activity, ScanSearch, Settings } from "lucide-react";

const navItems = [
  { label: "Home",    href: "/dashboard",                  icon: LayoutDashboard },
  { label: "Stocks",  href: "/dashboard/stocks",            icon: BarChart3 },
  { label: "Options", href: "/dashboard/options/NIFTY",     icon: Activity },
  { label: "Scanner", href: "/dashboard/scanner",           icon: ScanSearch },
  { label: "Settings",href: "/dashboard/settings",          icon: Settings },
];

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 border-t border-border bg-card/95 backdrop-blur-sm">
      <div className="flex items-center justify-around px-2 py-2 safe-area-bottom">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex flex-col items-center gap-1 px-3 py-1.5 rounded-xl transition-colors min-w-0",
                isActive ? "text-primary" : "text-muted-foreground"
              )}
            >
              <item.icon size={20} strokeWidth={isActive ? 2.5 : 1.75} />
              <span className="text-[10px] font-medium leading-none">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
