import type { Project } from "./data/portfolio";

export function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric"
  }).format(new Date(`${value}T00:00:00`));
}

export function projectTone(project: Project) {
  if (project.status === "Needs manual summary") {
    return "Manual";
  }

  return project.isFork ? "Forked build" : "Original";
}
