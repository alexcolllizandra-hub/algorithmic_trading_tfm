"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { useAuth } from "@/lib/auth/AuthContext";
import { cn } from "@/lib/cn";

const LINKS = [
  { href: "#en-simple", label: "En simple" },
  { href: "#sobreajuste", label: "El problema" },
  { href: "#arquitectura", label: "Arquitectura" },
  { href: "#datos", label: "Datos reales" },
  { href: "#veredicto", label: "Resultado" },
  { href: "#roadmap", label: "Roadmap" },
];

export function SiteHeader() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const { configured, user, signOut } = useAuth();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <header
      className={cn(
        "sticky top-0 z-50 transition-colors duration-300",
        scrolled
          ? "border-b border-border bg-bg/85 backdrop-blur-md"
          : "border-b border-transparent"
      )}
    >
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center gap-6 px-6">
        <Link href="/" className="flex items-center gap-2.5 font-semibold tracking-tight">
          <span className="text-accent" aria-hidden>
            {"\u25C8"}
          </span>
          Alx Systems
        </Link>

        <nav className="ml-auto hidden items-center gap-7 lg:flex" aria-label="Secciones">
          {LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              className="text-sm text-muted transition-colors hover:text-fg"
            >
              {link.label}
            </a>
          ))}
        </nav>

        <div className="ml-auto hidden items-center gap-2.5 lg:ml-0 lg:flex">
          <Link
            href="/panel"
            className="rounded-md border border-border bg-surface px-3.5 py-1.5 text-sm font-medium transition-colors hover:border-accent/50 hover:text-accent"
          >
            Panel de investigación
          </Link>

          {configured &&
            (user ? (
              <button
                type="button"
                onClick={() => void signOut()}
                className="rounded-md px-3 py-1.5 text-sm text-muted transition-colors hover:text-fg"
              >
                Salir
              </button>
            ) : (
              <Link
                href="/acceso"
                className="rounded-md bg-accent px-3.5 py-1.5 text-sm font-semibold text-accent-fg transition-opacity hover:opacity-90"
              >
                Entrar
              </Link>
            ))}
        </div>

        <button
          type="button"
          onClick={() => setOpen((value) => !value)}
          aria-expanded={open}
          aria-label={open ? "Cerrar menú" : "Abrir menú"}
          className="ml-auto rounded-md border border-border px-3 py-1.5 text-sm lg:hidden"
        >
          {open ? "\u2715" : "\u2261"}
        </button>
      </div>

      {open && (
        <nav className="border-t border-border bg-bg lg:hidden" aria-label="Secciones">
          <ul className="mx-auto max-w-6xl px-6 py-3">
            {LINKS.map((link) => (
              <li key={link.href}>
                <a
                  href={link.href}
                  onClick={() => setOpen(false)}
                  className="block py-2.5 text-sm text-muted hover:text-fg"
                >
                  {link.label}
                </a>
              </li>
            ))}
            <li>
              <Link
                href="/panel"
                className="block py-2.5 text-sm font-medium text-accent"
                onClick={() => setOpen(false)}
              >
                Panel de investigación
              </Link>
            </li>
            {configured && (
              <li>
                {user ? (
                  <button
                    type="button"
                    onClick={() => {
                      setOpen(false);
                      void signOut();
                    }}
                    className="block py-2.5 text-sm text-muted"
                  >
                    Salir
                  </button>
                ) : (
                  <Link
                    href="/acceso"
                    className="block py-2.5 text-sm font-medium text-accent"
                    onClick={() => setOpen(false)}
                  >
                    Entrar
                  </Link>
                )}
              </li>
            )}
          </ul>
        </nav>
      )}
    </header>
  );
}
