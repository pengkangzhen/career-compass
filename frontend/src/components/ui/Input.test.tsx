import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Input } from "./Input";

describe("Input", () => {
  it("renders label and the input element", () => {
    render(<Input label="Email" placeholder="you@x.com" />);
    expect(screen.getByText("Email")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("you@x.com")).toBeInTheDocument();
  });

  it("shows warn-colored border and error text when error is set", () => {
    render(<Input label="Email" error="invalid" />);
    const input = screen.getByDisplayValue("") as HTMLInputElement;
    expect(input.tagName).toBe("INPUT");
    expect(input.className).toContain("border-[var(--color-warn)]");
    expect(screen.getByText("invalid")).toBeInTheDocument();
  });

  it("shows hint text when no error", () => {
    render(<Input label="Email" hint="we never share" />);
    expect(screen.getByText("we never share")).toBeInTheDocument();
  });

  it("prefers error over hint when both are set", () => {
    render(<Input label="Email" hint="hint-text" error="err-text" />);
    expect(screen.queryByText("hint-text")).not.toBeInTheDocument();
    expect(screen.getByText("err-text")).toBeInTheDocument();
  });
});
