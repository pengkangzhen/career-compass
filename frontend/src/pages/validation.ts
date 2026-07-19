const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function validateEmail(email: string): string | null {
  if (!email.trim()) return "请填写邮箱";
  if (!EMAIL_RE.test(email.trim())) return "邮箱格式不正确";
  return null;
}

export function validatePassword(password: string): string | null {
  if (!password) return "请填写密码";
  if (password.length < 8) return "密码至少 8 位";
  return null;
}

export function validatePasswordConfirm(
  password: string,
  confirm: string,
): string | null {
  if (!confirm) return "请再次输入密码";
  if (password !== confirm) return "两次输入的密码不一致";
  return null;
}
