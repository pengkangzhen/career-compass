import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Button } from "./Button";

describe("Button", () => {
  it("renders primary variant by default with the label", () => {
    render(<Button>Save</Button>);
    const btn = screen.getByRole("button", { name: "Save" });
    expect(btn).toBeInTheDocument();
    // Primary variant includes the accent background class.
    expect(btn.className).toContain("bg-[var(--color-accent)]");
    expect(btn.className).toContain("text-white");
  });

  it("applies secondary variant classes", () => {
    render(<Button variant="secondary">Cancel</Button>);
    const btn = screen.getByRole("button", { name: "Cancel" });
    expect(btn.className).toContain("border");
    expect(btn.className).toContain("bg-transparent");
  });

  it("applies size classes (sm vs md)", () => {
    const { rerender } = render(<Button size="md">M</Button>);
    expect(screen.getByRole("button").className).toContain("px-4");
    rerender(<Button size="sm">S</Button>);
    expect(screen.getByRole("button").className).toContain("px-3");
  });

  it("respects block prop (w-full)", () => {
    render(<Button block>Full</Button>);
    expect(screen.getByRole("button").className).toContain("w-full");
  });

  it("renders the leading node before children", () => {
    render(<Button leading={<span data-testid="icon">+</span>}>Add</Button>);
    const btn = screen.getByTestId("icon").parentElement!;
    // The leading node is the first child of the button.
    expect(btn.firstChild).toBe(screen.getByTestId("icon"));
  });

  it("fires onClick when not disabled", async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Go</Button>);
    await userEvent.click(screen.getByRole("button", { name: "Go" }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("does not fire onClick when disabled", async () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Go
      </Button>,
    );
    await userEvent.click(screen.getByRole("button", { name: "Go" }));
    expect(onClick).not.toHaveBeenCalled();
  });

  it("does not fire onClick when loading (implicit disabled)", async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Go
      </Button>,
    );
    const btn = screen.getByRole("button", { name: "Go" });
    expect(btn).toBeDisabled();
    await userEvent.click(btn);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("defaults to type=button (prevents form submit accidents)", () => {
    render(<Button>X</Button>);
    expect(screen.getByRole("button")).toHaveAttribute("type", "button");
  });
});
