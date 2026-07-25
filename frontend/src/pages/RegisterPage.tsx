import { useState } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import {
  validateEmail,
  validatePassword,
  validatePasswordConfirm,
} from "./validation";
import { AuthShell, FormError } from "./LoginPage";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";

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
          autoComplete="new-password"
          disabled={busy}
        />
        <Input
          label="确认密码"
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          placeholder="再次输入密码"
          error={errors.confirm}
          autoComplete="new-password"
          disabled={busy}
        />
        {errors.form && <FormError message={errors.form} />}
        <Button type="submit" block loading={busy}>
          {busy ? "注册中…" : "注册"}
        </Button>
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
