import type { JobsView } from "../../api/types";
import { Empty } from "../../components/ui";
import { JobCard } from "./JobCard";
import { JobForm } from "./JobForm";

export function JobsView({
  data,
  onRefresh,
}: {
  data: JobsView;
  onRefresh?: () => Promise<void> | void;
}) {
  return (
    <div className="space-y-4">
      {onRefresh && (
        <JobForm mode="create" onSubmit={onRefresh} onCancel={() => {}} />
      )}
      {data.empty ? (
        <Empty message={data.message ?? "暂无收藏"} hint={data.hint} />
      ) : (
        <>
          <p className="text-sm text-[var(--color-muted)]">
            共 {data.count ?? data.jobs.length} 个收藏
          </p>
          {data.jobs.map((job, i) => (
            <JobCard key={job.id ?? i} job={job} onRefresh={onRefresh} />
          ))}
        </>
      )}
    </div>
  );
}
