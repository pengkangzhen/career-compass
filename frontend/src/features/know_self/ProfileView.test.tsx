import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProfileView } from "./ProfileView";
import type { ProfileView as ProfileViewData } from "../../api/types";

// Empty-state smoke: when the API returns empty:true, the panel must show a
// friendly placeholder rather than crash on undefined fields.
describe("ProfileView (empty)", () => {
  it("renders the empty placeholder", () => {
    const data: ProfileViewData = { empty: true, message: "暂无画像" };
    render(<ProfileView data={data} />);
    expect(screen.getByText("暂无画像")).toBeInTheDocument();
  });

  it("falls back to default empty message when none provided", () => {
    const data: ProfileViewData = { empty: true };
    render(<ProfileView data={data} />);
    expect(screen.getByText("暂无画像")).toBeInTheDocument();
  });
});

describe("ProfileView (populated)", () => {
  const populated: ProfileViewData = {
    empty: false,
    title: "张三 · 资深工程师",
    validation: { errors: [], warnings: [] },
    core_skills: ["Python", "TypeScript"],
    adjacent_skills: ["Rust"],
    evidence: [
      { claim: "主导 X 系统重构", proof: "Q3 perf report" },
    ],
    constraints: { risk_appetite: "moderate" },
    narrative_md: "## 个人叙事\n\n一段介绍。",
  };

  it("renders title, skills, evidence, narrative", () => {
    render(<ProfileView data={populated} />);
    expect(screen.getByText("张三 · 资深工程师")).toBeInTheDocument();
    expect(screen.getByText("Python")).toBeInTheDocument();
    expect(screen.getByText("主导 X 系统重构")).toBeInTheDocument();
    expect(screen.getByText(/个人叙事/)).toBeInTheDocument();
  });

  it("shows ok-alert when validation passes cleanly", () => {
    render(<ProfileView data={populated} />);
    expect(screen.getByText(/画像校验通过/)).toBeInTheDocument();
  });

  it("shows warn-alert when validation has errors", () => {
    const data: ProfileViewData = {
      ...populated,
      validation: { errors: ["缺教育背景", "缺核心技能"], warnings: [] },
    };
    render(<ProfileView data={data} />);
    expect(screen.getByText("缺教育背景")).toBeInTheDocument();
    expect(screen.getByText("缺核心技能")).toBeInTheDocument();
  });
});
