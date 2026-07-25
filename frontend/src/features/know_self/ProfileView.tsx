import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { ProfileView } from "../../api/types";
import { Alert, Badge, Empty, Section, TagList } from "../../components/ui";

export function ProfileView({ data }: { data: ProfileView }) {
  if (data.empty) {
    return <Empty message={data.message ?? "暂无画像"} />;
  }

  const v = data.validation;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">{data.title}</h2>
        {v && v.errors.length > 0 && (
          <Alert tone="warn" title="待补齐">
            <ul className="list-disc pl-4">
              {v.errors.slice(0, 8).map((e) => (
                <li key={e}>{e}</li>
              ))}
            </ul>
          </Alert>
        )}
        {v && !v.errors.length && v.warnings.length > 0 && (
          <Alert tone="hint" title="建议完善">
            <ul className="list-disc pl-4">
              {v.warnings.slice(0, 5).map((w) => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          </Alert>
        )}
        {v && !v.errors.length && !v.warnings.length && (
          <Alert tone="ok">✅ 画像校验通过</Alert>
        )}
      </div>

      {data.education && data.education.length > 0 && (
        <Section title="教育背景">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-muted)]">
                  <th className="py-2 pr-3">层次</th>
                  <th className="py-2 pr-3">院校</th>
                  <th className="py-2 pr-3">专业</th>
                  <th className="py-2 pr-3">时间</th>
                  <th className="py-2">备注</th>
                </tr>
              </thead>
              <tbody>
                {data.education.map((e, i) => (
                  <tr key={i} className="border-b border-[var(--color-border)]/50">
                    <td className="py-2 pr-3">{e.level}</td>
                    <td className="py-2 pr-3">
                      {e.school}
                      {e.school_tier && (
                        <Badge tone="neutral" size="xs" className="ml-1">
                          {e.school_tier}
                        </Badge>
                      )}
                    </td>
                    <td className="py-2 pr-3">
                      {e.major}
                      {e.department ? ` · ${e.department}` : ""}
                    </td>
                    <td className="py-2 pr-3">{e.time}</td>
                    <td className="py-2 text-[var(--color-muted)]">{e.notes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Section>
      )}

      {data.core_skills && data.core_skills.length > 0 && (
        <Section title="核心技能">
          <TagList items={data.core_skills} />
        </Section>
      )}

      {data.adjacent_skills && data.adjacent_skills.length > 0 && (
        <Section title="相邻技能">
          <TagList items={data.adjacent_skills} muted />
        </Section>
      )}

      {data.evidence && data.evidence.length > 0 && (
        <Section title="优势证据">
          <div className="space-y-2">
            {data.evidence.map((ev, i) => (
              <div
                key={i}
                className="rounded-lg border border-[var(--color-border)] bg-black/15 p-3"
              >
                <p className="font-medium text-sm">{ev.claim}</p>
                <p className="mt-1 text-xs text-[var(--color-muted)]">{ev.proof}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      {data.constraints && (
        <Section title="硬约束">
          <ul className="list-disc pl-5 text-sm text-[var(--color-muted)]">
            {data.constraints.age != null && <li>年龄: {data.constraints.age}</li>}
            <li>风险偏好: {data.constraints.risk_appetite}</li>
            {data.constraints.notes && <li>{data.constraints.notes}</li>}
          </ul>
        </Section>
      )}

      {data.narrative_md && (
        <Section title="叙事">
          <div className="prose-beidou">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.narrative_md}</ReactMarkdown>
          </div>
        </Section>
      )}
    </div>
  );
}
