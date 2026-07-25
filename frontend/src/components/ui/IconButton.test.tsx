import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { IconButton } from "./IconButton";

describe("IconButton", () => {
  it("uses title as aria-label for accessibility", () => {
    render(
      <IconButton title="Delete" tone="danger">
        ✕
      </IconButton>,
    );
    const btn = screen.getByRole("button", { name: "Delete" });
    expect(btn).toHaveAttribute("title", "Delete");
  });

  it("applies danger tone classes (hover-warn)", () => {
    render(
      <IconButton title="x" tone="danger">
        ✕
      </IconButton>,
    );
    expect(screen.getByRole("button").className).toContain("hover:border-[var(--color-warn)]");
  });

  it("fires onClick when enabled", async () => {
    const onClick = vi.fn();
    render(
      <IconButton title="edit" onClick={onClick}>
        📝
      </IconButton>,
    );
    await userEvent.click(screen.getByRole("button"));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it("does not fire onClick when disabled", async () => {
    const onClick = vi.fn();
    render(
      <IconButton title="edit" disabled onClick={onClick}>
        📝
      </IconButton>,
    );
    await userEvent.click(screen.getByRole("button"));
    expect(onClick).not.toHaveBeenCalled();
  });
});
