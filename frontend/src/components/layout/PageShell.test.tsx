import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PageShell, SegmentedControl, type PageAction } from "./PageShell";

describe("PageShell", () => {
  it("renders title, eyebrow, and subtitle", () => {
    render(
      <PageShell title="对话" eyebrow="认识自己" subtitle="聊聊你的背景">
        body
      </PageShell>,
    );
    expect(screen.getByText("对话")).toBeInTheDocument();
    expect(screen.getByText("认识自己")).toBeInTheDocument();
    expect(screen.getByText("聊聊你的背景")).toBeInTheDocument();
    expect(screen.getByText("body")).toBeInTheDocument();
  });

  it("renders nothing in the actions column when actions are absent", () => {
    const { container } = render(<PageShell title="t">x</PageShell>);
    const buttons = container.querySelectorAll("button");
    expect(buttons).toHaveLength(0);
  });

  it("renders each action as a button", () => {
    const actions: PageAction[] = [
      { key: "a", label: "Save", onClick: vi.fn(), variant: "primary" },
      { key: "b", label: "Cancel", onClick: vi.fn() },
    ];
    render(<PageShell title="t" actions={actions}>x</PageShell>);
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  it("primary action gets accent bg; secondary gets border", () => {
    const actions: PageAction[] = [
      { key: "p", label: "P", onClick: vi.fn(), variant: "primary" },
      { key: "s", label: "S", onClick: vi.fn() },
    ];
    render(<PageShell title="t" actions={actions}>x</PageShell>);
    const p = screen.getByRole("button", { name: "P" });
    const s = screen.getByRole("button", { name: "S" });
    expect(p.className).toContain("bg-[var(--color-accent)]");
    expect(s.className).toContain("border");
  });

  it("fires action onClick", async () => {
    const onClick = vi.fn();
    const actions: PageAction[] = [{ key: "go", label: "Go", onClick }];
    render(<PageShell title="t" actions={actions}>x</PageShell>);
    await userEvent.click(screen.getByRole("button", { name: "Go" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("disabled action button is not clickable", async () => {
    const onClick = vi.fn();
    const actions: PageAction[] = [{ key: "go", label: "Go", onClick, disabled: true }];
    render(<PageShell title="t" actions={actions}>x</PageShell>);
    const btn = screen.getByRole("button", { name: "Go" });
    expect(btn).toBeDisabled();
    await userEvent.click(btn);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("renders leading content inline (e.g. segmented control)", () => {
    render(
      <PageShell
        title="t"
        leading={<span data-testid="leading">[seg]</span>}
      >
        x
      </PageShell>,
    );
    expect(screen.getByTestId("leading")).toBeInTheDocument();
  });
});

describe("SegmentedControl", () => {
  const opts: { value: "a" | "b"; label: string }[] = [
    { value: "a", label: "Alpha" },
    { value: "b", label: "Beta" },
  ];

  it("marks the active option", () => {
    render(
      <SegmentedControl
        value="a"
        options={opts}
        onChange={() => {}}
        ariaLabel="x"
      />,
    );
    const a = screen.getByRole("radio", { name: "Alpha", checked: true });
    const b = screen.getByRole("radio", { name: "Beta", checked: false });
    expect(a).toHaveAttribute("aria-checked", "true");
    expect(b).toHaveAttribute("aria-checked", "false");
  });

  it("fires onChange with the selected value", async () => {
    const onChange = vi.fn();
    render(
      <SegmentedControl value="a" options={opts} onChange={onChange} ariaLabel="x" />,
    );
    await userEvent.click(screen.getByRole("radio", { name: "Beta" }));
    expect(onChange).toHaveBeenCalledWith("b");
  });
});
