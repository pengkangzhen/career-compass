import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { validateEmail, validatePassword } from "./validation";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{
    email?: string;
    password?: string;
    form?: string;
  }>({});
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const emailErr = validateEmail(email);
    const passwordErr = validatePassword(password);
    if (emailErr || passwordErr) {
      setErrors({
        email: emailErr ?? undefined,
        password: passwordErr ?? undefined,
      });
      return;
    }
    setBusy(true);
    setErrors({});
    try {
      await login(email.trim(), password);
      navigate("/", { replace: true });
    } catch (err) {
      setErrors({
        form:
          err instanceof Error && err.message
            ? err.message
            : "登录失败，请检查邮箱和密码",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="登录北斗星" subtitle="你的AI职业规划决策引擎">
      <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4" noValidate>
        <Input
          label="邮箱"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          error={errors.email}
          autoComplete="email"
          disabled={busy}
        />
        <Input
          label="密码"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="至少 8 位"
          error={errors.password}
          autoComplete="current-password"
          disabled={busy}
        />
        {errors.form && <FormError message={errors.form} />}
        <Button type="submit" block loading={busy}>
          {busy ? "登录中…" : "登录"}
        </Button>
      </form>
      <p className="mt-5 text-center text-xs text-[var(--color-muted)]">
        还没有账号？{" "}
        <Link to="/register" className="text-[var(--color-accent)] hover:underline">
          立即注册
        </Link>
      </p>
    </AuthShell>
  );
}

export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-full items-center justify-center px-4 py-10">
      <div className="w-full max-w-sm rounded-2xl border border-[var(--color-border)] bg-[var(--color-surface)]/70 p-6 backdrop-blur-sm md:p-8">
        <div className="mb-6 text-center">
          <h1 className="text-xl font-semibold tracking-tight text-[var(--color-text)]">
            {title}
          </h1>
          <p className="mt-1 text-xs text-[var(--color-muted)]">{subtitle}</p>
        </div>
        {children}
      </div>
    </div>
  );
}

export function FormError({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-[var(--color-warn)]/30 bg-[var(--color-warn)]/10 px-3 py-2 text-xs text-[var(--color-warn)]">
      {message}
    </div>
  );
}
