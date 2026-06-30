import { AuthForm } from "@/features/auth/ui/auth-form";
import { SupportLink } from "@/shared/ui/support-link";

export function LoginScreen() {
  return (
    <div className="grid min-h-[calc(100vh-9rem)] place-items-center gap-4 py-8">
      <AuthForm mode="login" />
      <SupportLink />
    </div>
  );
}

export function RegisterScreen() {
  return (
    <div className="grid min-h-[calc(100vh-9rem)] place-items-center gap-4 py-8">
      <AuthForm mode="register" />
      <SupportLink />
    </div>
  );
}
