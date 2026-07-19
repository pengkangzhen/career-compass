import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { validateEmail, validatePassword } from "./validation";

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
    <AuthShell title="登录北斗星" subtitle="登录后继续你的职业规划">
      <form onSubmit={(e) => void handleSubmit(e)} className="space-y-4" noValidate>
        <Field
          label="邮箱"
          type="email"
          value={email}
          onChange={setEmail}
          placeholder="you@example.com"
          error={errors.email}
          autoComplete="email"
          disabled={busy}
        />
        <Field
          label="密码"
          type="password"
          value={password}
          onChange={setPassword}
          placeholder="至少 8 位"
          error={errors.password}
          autoComplete="current-password"
          disabled={busy}
        />
        {errors.form && <FormError message={errors.form} />}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-xl bg-[var(--color-accent)] px-4 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "登录中…" : "登录"}
        </button>
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
          <h1 className="text-xl font-semibold tracking-tight">
            <span className="text-[var(--color-text)]">北斗星</span>
            <span className="ml-2 text-sm font-normal text-[var(--color-accent-2)]">
              Beidou
            </span>
          </h1>
          <p className="mt-1 text-sm text-[var(--color-text)]">{title}</p>
          <p className="mt-0.5 text-xs text-[var(--color-muted)]">{subtitle}</p>
        </div>
        {children}
      </div>
    </div>
  );
}

export function Field({
  label,
  type,
  value,
  onChange,
  placeholder,
  error,
  autoComplete,
  disabled,
}: {
  label: string;
  type: "email" | "password" | "text";
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  error?: string;
  autoComplete?: string;
  disabled?: boolean;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-[var(--color-muted)]">
        {label}
      </span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoComplete={autoComplete}
        disabled={disabled}
        className={`w-full rounded-md border bg-[var(--color-surface)] px-3 py-2 text-sm outline-none transition focus:border-[var(--color-accent)] disabled:opacity-60 ${
          error ? "border-[var(--color-warn)]" : "border-[var(--color-border)]"
        }`}
      />
      {error && (
        <span className="mt-1 block text-xs text-[var(--color-warn)]">{error}</span>
      )}
    </label>
  );
}

export function FormError({ message }: { message: string }) {
  return (
    <div className="rounded-md border border-[var(--color-warn)]/30 bg-[var(--color-warn)]/10 px-3 py-2 text-xs text-[var(--color-warn)]">
      {message}
    </div>
  );
}
