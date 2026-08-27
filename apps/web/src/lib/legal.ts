// Identity of the data controller, and the switch that depends on it.
//
// A privacy notice that does not name a controller and a way to reach them is
// not a privacy notice, so these two values gate account creation rather than
// being defaulted to something plausible. Until both are filled in, `/privacidad`
// renders as an explicit draft and the sign-up form refuses to collect anything.
//
// To go live: set both constants and nothing else changes.

/** Legal or natural person responsible for the processing. */
export const DATA_CONTROLLER: string | null = "Àlex Coll Lizandra";

/** Address where data-subject rights are exercised. */
export const PRIVACY_CONTACT: string | null = "soporte.alxsystems@gmail.com";

/** Jurisdiction whose supervisory authority the notice points at. */
export const SUPERVISORY_AUTHORITY = {
  name: "Agencia Española de Protección de Datos (AEPD)",
  url: "https://www.aepd.es",
} as const;

/**
 * True only when the notice is complete enough to publish.
 *
 * Personal data must not be collected before this is true: the lawful basis for
 * the processing depends on the subject having been told who is processing it.
 */
export const PRIVACY_POLICY_READY: boolean = DATA_CONTROLLER !== null && PRIVACY_CONTACT !== null;

/** Sub-processors that receive personal data, and what each one does with it. */
export interface Processor {
  name: string;
  role: string;
  location: string;
  url: string;
}

export const PROCESSORS: Processor[] = [
  {
    name: "Supabase",
    role: "Autenticación y almacenamiento de la cuenta: correo, nombre y contraseña cifrada.",
    location: "Infraestructura alojada en la región elegida para el proyecto.",
    url: "https://supabase.com/privacy",
  },
  {
    name: "Resend",
    role: "Envío de los correos transaccionales: confirmación de cuenta, recuperación de contraseña y bienvenida.",
    location: "Estados Unidos, bajo cláusulas contractuales tipo.",
    url: "https://resend.com/legal/privacy-policy",
  },
];
