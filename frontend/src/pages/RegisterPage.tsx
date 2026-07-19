import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import {
  validateEmail,
  validatePassword,
  validatePasswordConfirm,
} from "./validation";
import { AuthShell, Field, FormError } from "./LoginPage";

export function RegisterPage() {
  const { user, register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [errors, setErrors] = useState<{
    email?: string;
    password?: string;
    confirm?: string;
    form?: string;
  }>({});
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const emailErr = validateEmail(email);
    const passwordErr = validatePassword(password);
    const confirmErr = validatePasswordConfirm(password, confirm);
    if (emailErr || passwordErr || confirmErr) {
      setErrors({
        email: emailErr ?? undefined,
        password: passwordErr ?? undefined,
        confirm: confirmErr ?? undefined,
      });
      return;
    }
    setBusy(true);
    setErrors({});
    try {
      await register(email.trim(), password);
      navigate("/login?registered=1", { replace: true });
    } catch (err) {
      setErrors({
        form:
          err instanceof Error ? err.message : "注册失败，请稍后重试",
      });
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell title="创建北斗星账号" subtitle="注册后即可登录使用">
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
          autoComplete="new-password"
          disabled={busy}
        />
        <Field
          label="确认密码"
          type="password"
          value={confirm}
          onChange={setConfirm}
          placeholder="再次输入密码"
          error={errors.confirm}
          autoComplete="new-password"
          disabled={busy}
        />
        {errors.form && <FormError message={errors.form} />}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-xl bg-[var(--color-accent)] px-4 py-2.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "注册中…" : "注册"}
        </button>
      </form>
      <p className="mt-5 text-center text-xs text-[var(--color-muted)]">
        已有账号？{" "}
        <Link to="/login" className="text-[var(--color-accent)] hover:underline">
          返回登录
        </Link>
      </p>
    </AuthShell>
  );
}
