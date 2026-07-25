import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { JobsView } from "./JobsView";
import type { JobsView as JobsViewData } from "../../api/types";

describe("JobsView", () => {
  it("renders the empty placeholder when data.empty", () => {
    const data: JobsViewData = {
      empty: true,
      jobs: [],
      message: "暂无收藏",
      hint: "run: career-compass job add",
    };
    render(<JobsView data={data} />);
    expect(screen.getByText("暂无收藏")).toBeInTheDocument();
    expect(screen.getByText(/job add/)).toBeInTheDocument();
  });

  it("renders count + each job card when populated", () => {
    const data: JobsViewData = {
      empty: false,
      count: 2,
      jobs: [
        {
          company: "ByteDance",
          role: "算法工程师",
          location: "北京",
          source: "脉脉",
          saved_on: "2024-01-01",
          status: "interested",
          id: "j1",
        },
        {
          company: "Stripe",
          role: "Backend Eng",
          location: "Remote",
          saved_on: "2024-02-01",
          status: "researching",
          id: "j2",
        },
      ],
    };
    render(<JobsView data={data} />);
    expect(screen.getByText(/共 2 个收藏/)).toBeInTheDocument();
    // JobCard renders "company · role" — both companies present.
    expect(screen.getByText(/ByteDance/)).toBeInTheDocument();
    expect(screen.getByText(/Stripe/)).toBeInTheDocument();
  });

  it("renders the inline form when onRefresh is provided (create mode opens expanded)", () => {
    const data: JobsViewData = { empty: true, jobs: [] };
    render(<JobsView data={data} onRefresh={vi.fn()} />);
    // Initial state: create-mode form is open by default — the form title is visible.
    expect(screen.getByText(/新增心仪岗位/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/字节跳动/)).toBeInTheDocument();
  });
});
