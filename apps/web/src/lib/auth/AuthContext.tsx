"use client";

// Authentication state for the whole app.
//
// Deliberately thin: Supabase owns the session, this only exposes it to React
// and translates errors into Spanish messages a visitor can act on. When the
// deployment has no Supabase credentials, `configured` is false and every
// action returns a clear message instead of throwing.

import type { Session, User } from "@supabase/supabase-js";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { getSupabaseBrowserClient, isAuthConfigured } from "@/lib/supabase/client";

export interface AuthResult {
  ok: boolean;
  message?: string;
  /** Set when the account was created but still needs email confirmation. */
  needsConfirmation?: boolean;
}

interface AuthContextValue {
  configured: boolean;
  loading: boolean;
  user: User | null;
  session: Session | null;
  /** True while the user is completing a password-recovery link. */
  recoveryMode: boolean;
  signUp: (email: string, password: string, fullName: string) => Promise<AuthResult>;
  signIn: (email: string, password: string) => Promise<AuthResult>;
  signOut: () => Promise<void>;
  requestPasswordReset: (email: string) => Promise<AuthResult>;
  updatePassword: (password: string) => Promise<AuthResult>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const NOT_CONFIGURED =
  "El acceso no está configurado en este despliegue. Falta NEXT_PUBLIC_SUPABASE_URL " +
  "o NEXT_PUBLIC_SUPABASE_ANON_KEY.";

/** Supabase returns English messages; these are the ones a visitor actually hits. */
function translate(message: string): string {
  const map: Record<string, string> = {
    "Invalid login credentials": "Correo o contraseña incorrectos.",
    "Email not confirmed": "Todavía no has confirmado tu correo. Revisa la bandeja de entrada.",
    "User already registered": "Ya existe una cuenta con este correo.",
    "Password should be at least 6 characters": "La contraseña debe tener al menos 6 caracteres.",
    "Unable to validate email address: invalid format": "El correo no tiene un formato válido.",
    "For security purposes, you can only request this after 60 seconds.":
      "Por seguridad, espera un minuto antes de volver a intentarlo.",
    "New password should be different from the old password.":
      "La contraseña nueva debe ser distinta de la anterior.",
  };
  return map[message] ?? message;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const supabase = getSupabaseBrowserClient();
  const configured = isAuthConfigured();

  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(configured);
  const [recoveryMode, setRecoveryMode] = useState(false);

  useEffect(() => {
    if (!supabase) {
      setLoading(false);
      return;
    }
    let active = true;

    supabase.auth.getSession().then(({ data }) => {
      if (!active) return;
      setSession(data.session);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, nextSession) => {
      setSession(nextSession);
      setLoading(false);
      if (event === "PASSWORD_RECOVERY") setRecoveryMode(true);
      if (event === "SIGNED_OUT") setRecoveryMode(false);
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, [supabase]);

  const signUp = useCallback<AuthContextValue["signUp"]>(
    async (email, password, fullName) => {
      if (!supabase) return { ok: false, message: NOT_CONFIGURED };
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          // `full_name` lands in user_metadata and is what the welcome email greets.
          data: { full_name: fullName },
          emailRedirectTo: `${window.location.origin}/acceso`,
        },
      });
      if (error) return { ok: false, message: translate(error.message) };
      // No session immediately after signUp means email confirmation is enabled.
      return { ok: true, needsConfirmation: !data.session };
    },
    [supabase]
  );

  const signIn = useCallback<AuthContextValue["signIn"]>(
    async (email, password) => {
      if (!supabase) return { ok: false, message: NOT_CONFIGURED };
      const { error } = await supabase.auth.signInWithPassword({ email, password });
      if (error) return { ok: false, message: translate(error.message) };
      return { ok: true };
    },
    [supabase]
  );

  const signOut = useCallback(async () => {
    if (!supabase) return;
    await supabase.auth.signOut();
  }, [supabase]);

  const requestPasswordReset = useCallback<AuthContextValue["requestPasswordReset"]>(
    async (email) => {
      if (!supabase) return { ok: false, message: NOT_CONFIGURED };
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/acceso`,
      });
      if (error) return { ok: false, message: translate(error.message) };
      return { ok: true };
    },
    [supabase]
  );

  const updatePassword = useCallback<AuthContextValue["updatePassword"]>(
    async (password) => {
      if (!supabase) return { ok: false, message: NOT_CONFIGURED };
      const { error } = await supabase.auth.updateUser({ password });
      if (error) return { ok: false, message: translate(error.message) };
      setRecoveryMode(false);
      return { ok: true };
    },
    [supabase]
  );

  const value = useMemo<AuthContextValue>(
    () => ({
      configured,
      loading,
      session,
      user: session?.user ?? null,
      recoveryMode,
      signUp,
      signIn,
      signOut,
      requestPasswordReset,
      updatePassword,
    }),
    [
      configured,
      loading,
      session,
      recoveryMode,
      signUp,
      signIn,
      signOut,
      requestPasswordReset,
      updatePassword,
    ]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>.");
  return ctx;
}
