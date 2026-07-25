import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge, TagList } from "./Badge";

describe("Badge", () => {
  it("renders children with default neutral tone", () => {
    render(<Badge>beta</Badge>);
    const el = screen.getByText("beta");
    expect(el.className).toContain("bg-[var(--color-border)]");
    expect(el.className).toContain("rounded-lg");
  });

  it("applies accent tone classes", () => {
    render(<Badge tone="accent">new</Badge>);
    expect(screen.getByText("new").className).toContain("text-[var(--color-accent)]");
  });

  it("applies size xs for dense inline annotations", () => {
    render(<Badge size="xs">v1</Badge>);
    expect(screen.getByText("v1").className).toContain("text-[10px]");
  });
});

describe("TagList", () => {
  it("renders a badge per item", () => {
    render(<TagList items={["python", "rust", "go"]} />);
    expect(screen.getByText("python")).toBeInTheDocument();
    expect(screen.getByText("rust")).toBeInTheDocument();
    expect(screen.getByText("go")).toBeInTheDocument();
  });

  it("renders muted tone when muted=true (legacy alias)", () => {
    render(<TagList items={["x"]} muted />);
    expect(screen.getByText("x").className).toContain("text-[var(--color-muted)]");
  });

  it("renders no badges for empty list", () => {
    const { container } = render(<TagList items={[]} />);
    expect(container.querySelectorAll("span")).toHaveLength(0);
  });
});
