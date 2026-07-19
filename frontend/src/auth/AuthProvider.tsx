import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ApiError, api, type User } from "../api/types";
import { clearTokens, loadTokens, saveTokens } from "./tokens";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

async function fetchMe(): Promise<User | null> {
  const tokens = loadTokens();
  try {
    return await api.authMe(tokens ? { accessToken: tokens.access_token } : undefined);
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    const me = await fetchMe();
    setUser(me);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const tokens = loadTokens();
      if (!tokens) {
        if (!cancelled) setLoading(false);
        return;
      }
      try {
        const me = await fetchMe();
        if (cancelled) return;
        setUser(me);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    let tokens;
    try {
      tokens = await api.authLogin({ email, password });
    } catch (err) {
      if (err instanceof ApiError) {
        throw new Error(translateAuthError(err, "登录失败，请检查邮箱和密码"));
      }
      throw err;
    }
    saveTokens(tokens);
    const me = await api.authMe({ accessToken: tokens.access_token });
    setUser(me);
  }, []);

  const register = useCallback(async (email: string, password: string) => {
    try {
      await api.authRegister({ email, password });
    } catch (err) {
      if (err instanceof ApiError) {
        throw new Error(translateAuthError(err, "注册失败"));
      }
      throw err;
    }
  }, []);

  const logout = useCallback(async () => {
    const tokens = loadTokens();
    try {
      await api.authLogout(tokens ? { accessToken: tokens.access_token } : undefined);
    } catch {
      // best-effort — ignore network/server errors on logout
    }
    clearTokens();
    setUser(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({ user, loading, login, register, logout, refreshUser }),
    [user, loading, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

const ERROR_CODE_MAP: Record<string, string> = {
  EMAIL_ALREADY_REGISTERED: "该邮箱已注册",
  INVALID_CREDENTIALS: "邮箱或密码错误",
  BAD_CREDENTIALS: "邮箱或密码错误",
  USER_INACTIVE: "账户已被停用",
  WEAK_PASSWORD: "密码强度不足",
  INVALID_EMAIL: "邮箱格式不正确",
};

function translateAuthError(err: ApiError, fallback: string): string {
  if (err.code && ERROR_CODE_MAP[err.code]) return ERROR_CODE_MAP[err.code];
  if (err.status === 401) return "邮箱或密码错误";
  if (err.status === 409) return "该邮箱已注册";
  return err.message || fallback;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
