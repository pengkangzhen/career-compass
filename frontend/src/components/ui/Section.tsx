import type { ReactNode } from "react";

type Props = {
  title: ReactNode;
  // Optional accessory on the right side of the heading (e.g. a count badge).
  accessory?: ReactNode;
  children: ReactNode;
};

export function Section({ title, accessory, children }: Props) {
  return (
    <section>
      <div className="mb-3 flex items-center justify-between gap-2">
        <h3 className="text-base font-semibold">{title}</h3>
        {accessory}
      </div>
      {children}
    </section>
  );
}
