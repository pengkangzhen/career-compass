import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useCallback, useState } from "react";
import { api } from "../../api/client";
import type { MatrixView } from "../../api/types";
import { Alert, Empty, Section, TagList } from "../../components/ui";
import { SegmentedControl } from "../../components/layout/PageShell";
import { MatrixTable } from "./MatrixTable";

export function MatrixView({
  data,
  onRefresh,
}: {
  data: MatrixView;
  onRefresh?: () => Promise<void> | void;
}) {
  const [viewMode, setViewMode] = useState<"editable" | "document">("editable");

  if (data.empty) {
    return <Empty message={data.message ?? "暂无矩阵"} hint={data.hint} />;
  }

  const hasMarkdownDoc = !!data.content;
  const hasEditableRows = !!data.primary && data.primary.length > 0;
  const showToggleSwitch = hasMarkdownDoc && hasEditableRows;
  const showDocument = viewMode === "document" && hasMarkdownDoc && !hasEditableRows;

  if ((data.format === "markdown" && data.content) || showDocument) {
    return (
      <div className="space-y-4">
        {showToggleSwitch && (
          <SegmentedControl
            value={viewMode}
            onChange={setViewMode}
            ariaLabel="矩阵视图模式"
            options={[
              { value: "editable", label: "可编辑视图" },
              { value: "document", label: "渲染文档" },
            ]}
          />
        )}
        <div className="prose-beidou max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.content!}</ReactMarkdown>
        </div>
      </div>
    );
  }

  const editable = !!onRefresh && hasEditableRows;

  const handleAddNote = useCallback(
    async (direction: string, text: string) => {
      const res = await api.matrixFeedbackAdd("note", direction, { text });
      if (!res.ok) {
        window.alert(res.error ?? "记录备注失败");
        return;
      }
      await onRefresh!();
    },
    [onRefresh],
  );

  return (
    <div className="space-y-4">
      {showToggleSwitch && (
        <SegmentedControl
          value={viewMode}
          onChange={setViewMode}
          ariaLabel="矩阵视图模式"
          options={[
            { value: "editable", label: "可编辑视图" },
            { value: "document", label: "渲染文档" },
          ]}
        />
      )}
      <div className="space-y-6">
        {data.unified_theme && (
          <Alert tone="hint" title="统一架构">
            {data.unified_theme}
          </Alert>
        )}
        {data.shared_assets && data.shared_assets.length > 0 && (
          <Section title="共享资产">
            <TagList items={data.shared_assets} />
          </Section>
        )}
        {hasEditableRows && (
          <MatrixTable
            title="机会方向"
            rows={data.primary!}
            hidden={data.hidden_directions ?? []}
            orderOverrides={data.order_overrides ?? []}
            notes={data.notes ?? {}}
            editable={editable}
            onRefresh={onRefresh}
            onAddNote={editable ? handleAddNote : undefined}
          />
        )}
        {viewMode === "document" && hasMarkdownDoc && (
          <Section title="渲染文档">
            <div className="prose-beidou max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{data.content!}</ReactMarkdown>
            </div>
          </Section>
        )}
        {data.hint && <p className="text-xs text-[var(--color-muted)]">{data.hint}</p>}
      </div>
    </div>
  );
}
