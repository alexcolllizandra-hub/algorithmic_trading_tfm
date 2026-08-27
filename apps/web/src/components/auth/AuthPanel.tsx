"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/lib/auth/AuthContext";
import { cn } from "@/lib/cn";
import { PRIVACY_POLICY_READY } from "@/lib/legal";

type Mode = "signin" | "signup" | "reset";

const TITLE: Record<Mode, string> = {
  signin: "Entrar",
  signup: "Crear cuenta",
  reset: "Recuperar contraseña",
};

const LEAD: Record<Mode, string> = {
  signin: "Accede al panel de investigación y al historial de experimentos.",
  signup: "Una cuenta te permite guardar vistas del estudio y seguir los experimentos nuevos.",
  reset: "Te enviamos un enlace para elegir una contraseña nueva.",
};

function Field({
  id,
  label,
  type,
  value,
  onChange,
  autoComplete,
  hint,
  required = true,
}: {
  id: string;
  label: string;
  type: string;
  value: string;
  onChange: (v: string) => void;
  autoComplete?: string;
  hint?: string;
  required?: boolean;
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium">
        {label}
      </label>
      <input
        id={id}
        name={id}
        type={type}
        value={value}
        required={required}
        autoComplete={autoComplete}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1.5 w-full rounded-md border border-border bg-surface-2 px-3.5 py-2.5 text-sm outline-none transition-colors placeholder:text-muted focus:border-accent/60"
      />
      {hint && <p className="mt-1.5 text-xs text-muted">{hint}</p>}
    </div>
  );
}

export function AuthPanel() {
  const router = useRouter();
  const {
    configured,
    loading,
    user,
    recoveryMode,
    signIn,
    signUp,
    requestPasswordReset,
    updatePassword,
  } = useAuth();

  const [mode, setMode] = useState<Mode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  // A signed-in visitor who is not mid-recovery has nothing to do here.
  useEffect(() => {
    if (!loading && user && !recoveryMode) {
      router.replace("/panel");
    }
  }, [loading, user, recoveryMode, router]);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setNotice(null);

    // Belt and braces: the tab is hidden, but a stale state must not create an
    // account while the privacy notice is incomplete.
    if (mode === "signup" && !recoveryMode && !PRIVACY_POLICY_READY) {
      setError("El registro está cerrado hasta que se publique la política de privacidad.");
      return;
    }

    setBusy(true);

    if (recoveryMode) {
      const result = await updatePassword(password);
      setBusy(false);
      if (!result.ok) return setError(result.message ?? "No se pudo cambiar la contraseña.");
      setNotice("Contraseña actualizada. Ya puedes usarla para entrar.");
      setPassword("");
      return;
    }

    if (mode === "signin") {
      const result = await signIn(email, password);
      setBusy(false);
      if (!result.ok) return setError(result.message ?? "No se pudo iniciar sesión.");
      router.replace("/panel");
      return;
    }

    if (mode === "signup") {
      const result = await signUp(email, password, fullName.trim());
      setBusy(false);
      if (!result.ok) return setError(result.message ?? "No se pudo crear la cuenta.");
      if (result.needsConfirmation) {
        setNotice(
          `Te hemos enviado un correo a ${email}. Confirma la cuenta desde ese enlace para entrar.`
        );
        return;
      }
      router.replace("/panel");
      return;
    }

    const result = await requestPasswordReset(email);
    setBusy(false);
    if (!result.ok) return setError(result.message ?? "No se pudo enviar el correo.");
    setNotice(`Si existe una cuenta con ${email}, recibirás un enlace para cambiar la contraseña.`);
  }

  // Sign-up collects personal data, so it stays closed until the privacy notice
  // names a controller. Sign-in and recovery only touch accounts that already
  // exist, so they are unaffected.
  const signupOpen = PRIVACY_POLICY_READY;
  const activeMode: Mode = recoveryMode
    ? "reset"
    : signupOpen
      ? mode
      : mode === "signup"
        ? "signin"
        : mode;
  const heading = recoveryMode ? "Elige una contraseña nueva" : TITLE[activeMode];

  return (
    <div className="mx-auto w-full max-w-md">
      <div className="rounded-card border border-border bg-surface p-7 md:p-8">
        <h1 className="text-2xl font-semibold tracking-tight">{heading}</h1>
        <p className="mt-2 text-sm leading-relaxed text-muted">
          {recoveryMode ? "Escribe la contraseña nueva y se guardará al enviar." : LEAD[activeMode]}
        </p>

        {!configured && (
          <div className="mt-6 rounded-md border border-warn/30 bg-warn/5 p-4 text-sm leading-relaxed text-muted">
            El acceso no está activado en este despliegue. La investigación es pública y se puede
            consultar entera sin cuenta.
          </div>
        )}

        {!recoveryMode && configured && !signupOpen && (
          <div className="mt-6 rounded-md border border-warn/30 bg-warn/5 p-4 text-sm leading-relaxed text-muted">
            El registro de cuentas nuevas está cerrado mientras se termina la{" "}
            <Link href="/privacidad" className="text-accent underline-offset-4 hover:underline">
              política de privacidad
            </Link>
            . No se recoge ningún dato personal hasta entonces. Si ya tienes cuenta, puedes entrar
            con normalidad, y la investigación se lee entera sin cuenta.
          </div>
        )}

        {!recoveryMode && configured && signupOpen && (
          <div
            role="tablist"
            aria-label="Tipo de acceso"
            className="mt-6 grid grid-cols-2 gap-1 rounded-md border border-border bg-surface-2 p-1"
          >
            {(["signin", "signup"] as const).map((m) => (
              <button
                key={m}
                type="button"
                role="tab"
                aria-selected={mode === m}
                onClick={() => {
                  setMode(m);
                  setError(null);
                  setNotice(null);
                }}
                className={cn(
                  "rounded px-3 py-2 text-sm font-medium transition-colors",
                  mode === m ? "bg-accent text-accent-fg" : "text-muted hover:text-fg"
                )}
              >
                {TITLE[m]}
              </button>
            ))}
          </div>
        )}

        <form onSubmit={onSubmit} className="mt-6 space-y-4">
          {activeMode === "signup" && !recoveryMode && (
            <Field
              id="fullName"
              label="Nombre"
              type="text"
              value={fullName}
              onChange={setFullName}
              autoComplete="name"
              hint="Solo se usa para saludarte en los correos."
            />
          )}

          {!recoveryMode && (
            <Field
              id="email"
              label="Correo electrónico"
              type="email"
              value={email}
              onChange={setEmail}
              autoComplete="email"
            />
          )}

          {activeMode !== "reset" && (
            <Field
              id="password"
              label="Contraseña"
              type="password"
              value={password}
              onChange={setPassword}
              autoComplete={activeMode === "signup" ? "new-password" : "current-password"}
              hint={activeMode === "signup" ? "Mínimo 6 caracteres." : undefined}
            />
          )}

          {recoveryMode && (
            <Field
              id="password"
              label="Contraseña nueva"
              type="password"
              value={password}
              onChange={setPassword}
              autoComplete="new-password"
              hint="Mínimo 6 caracteres."
            />
          )}

          {error && (
            <p
              role="alert"
              className="rounded-md border border-negative/30 bg-negative/10 px-3.5 py-2.5 text-sm text-negative"
            >
              {error}
            </p>
          )}
          {notice && (
            <p
              role="status"
              className="rounded-md border border-accent/30 bg-accent/10 px-3.5 py-2.5 text-sm text-fg"
            >
              {notice}
            </p>
          )}

          <button
            type="submit"
            disabled={busy || !configured}
            className="w-full rounded-md bg-accent px-4 py-2.5 text-sm font-semibold text-accent-fg transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy ? "Un momento…" : recoveryMode ? "Guardar contraseña" : TITLE[activeMode]}
          </button>
        </form>

        {!recoveryMode && configured && (
          <div className="mt-5 text-sm">
            {mode === "signin" ? (
              <button
                type="button"
                onClick={() => {
                  setMode("reset");
                  setError(null);
                  setNotice(null);
                }}
                className="text-muted underline-offset-4 hover:text-accent hover:underline"
              >
                He olvidado la contraseña
              </button>
            ) : mode === "reset" ? (
              <button
                type="button"
                onClick={() => {
                  setMode("signin");
                  setError(null);
                  setNotice(null);
                }}
                className="text-muted underline-offset-4 hover:text-accent hover:underline"
              >
                Volver a entrar
              </button>
            ) : null}
          </div>
        )}
      </div>

      {activeMode === "signup" && (
        <p className="mt-5 text-center text-xs leading-relaxed text-muted">
          Al crear la cuenta aceptas el tratamiento de tus datos descrito en la{" "}
          <Link href="/privacidad" className="text-accent underline-offset-4 hover:underline">
            política de privacidad
          </Link>
          .
        </p>
      )}

      <p className="mt-6 text-center text-sm text-muted">
        <Link href="/" className="underline-offset-4 hover:text-accent hover:underline">
          Volver a la investigación
        </Link>
      </p>
    </div>
  );
}
