"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import { navItems } from "@/components/layout/nav";
import { useI18n } from "@/lib/i18n";
import { cn } from "@/lib/cn";

export function Sidebar() {
  const t = useI18n();
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  const isActive = (href: string) => (href === "/" ? pathname === "/" : pathname.startsWith(href));

  return (
    <aside
      className={cn(
        "sticky top-0 flex h-screen shrink-0 flex-col border-r border-border bg-surface transition-all duration-200",
        collapsed ? "w-16" : "w-64"
      )}
    >
      <div className="flex items-center gap-2 border-b border-border px-4 py-4">
        <span className="text-lg text-accent">{"\u25C8"}</span>
        {!collapsed && (
          <div className="leading-tight">
            <div className="font-semibold">perp-lab</div>
            <div className="text-xs text-muted">{t.app.tagline}</div>
          </div>
        )}
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-2 py-3" aria-label="Primary">
        {navItems(t).map((item) => (
          <Link
            key={item.href}
            href={item.href}
            title={collapsed ? item.label : undefined}
            aria-current={isActive(item.href) ? "page" : undefined}
            className={cn(
              "flex items-center gap-3 rounded-md px-3 py-2 text-sm transition",
              isActive(item.href)
                ? "bg-accent/15 text-fg"
                : "text-muted hover:bg-surface-2 hover:text-fg"
            )}
          >
            <span className="w-5 text-center text-base" aria-hidden>
              {item.icon}
            </span>
            {!collapsed && (
              <span className="flex flex-col">
                <span className="font-medium">{item.label}</span>
                <span className="text-xs text-muted">{item.description}</span>
              </span>
            )}
          </Link>
        ))}
      </nav>

      <button
        type="button"
        onClick={() => setCollapsed((c) => !c)}
        aria-label={collapsed ? "Expand navigation" : "Collapse navigation"}
        className="border-t border-border px-4 py-3 text-left text-sm text-muted hover:text-fg"
      >
        {collapsed ? "\u00BB" : "\u00AB Collapse"}
      </button>
    </aside>
  );
}
